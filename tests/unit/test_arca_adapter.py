from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from taller.adapters.outbound.padron.arca import (
    URL_PADRON,
    URL_WSAA,
    ArcaPadron,
    armar_tra,
    firmar_tra,
    leer_persona,
    leer_ticket,
)
from taller.adapters.outbound.padron.boveda_arca import ArchivoBovedaArca
from taller.domain.entities.conexion_arca import AmbienteArca
from taller.domain.enums import CondicionIva, TipoPersona
from taller.domain.exceptions import ArchivoInvalido, ServicioExternoNoDisponible
from taller.domain.ports.padron import CredencialesArca

AHORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _credenciales(cuit: str = "20123456786") -> CredencialesArca:
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "taller"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CUIT {cuit}"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(1)
        .not_valid_before(AHORA - timedelta(days=1))
        .not_valid_after(AHORA + timedelta(days=730))
        .sign(clave, hashes.SHA256())
    )
    return CredencialesArca(
        certificado=cert.public_bytes(serialization.Encoding.PEM),
        clave=clave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


def _login_ok(vence: datetime) -> str:
    interno = (
        "&lt;loginTicketResponse&gt;&lt;header&gt;"
        f"&lt;expirationTime&gt;{vence.isoformat()}&lt;/expirationTime&gt;"
        "&lt;/header&gt;&lt;credentials&gt;&lt;token&gt;TOK&lt;/token&gt;"
        "&lt;sign&gt;SIG&lt;/sign&gt;&lt;/credentials&gt;&lt;/loginTicketResponse&gt;"
    )
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soapenv:Body><loginCmsResponse>"
        f"<loginCmsReturn>{interno}</loginCmsReturn>"
        "</loginCmsResponse></soapenv:Body></soapenv:Envelope>"
    )


def _sobre(cuerpo: str) -> str:
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        f'<soap:Body><ns2:getPersona_v2Response xmlns:ns2="http://a5.soap.ws.server.puc.sr/">'
        f"<personaReturn>{cuerpo}</personaReturn>"
        "</ns2:getPersona_v2Response></soap:Body></soap:Envelope>"
    )


PERSONA_RI = _sobre(
    "<datosGenerales><razonSocial>REPUESTOS DEL SUR SA</razonSocial>"
    "<tipoPersona>JURIDICA</tipoPersona><estadoClave>ACTIVO</estadoClave>"
    "<domicilioFiscal><direccion>AV SIEMPRE VIVA 742</direccion>"
    "<localidad>CORDOBA</localidad><descripcionProvincia>CORDOBA</descripcionProvincia>"
    "<codPostal>5000</codPostal></domicilioFiscal></datosGenerales>"
    "<datosRegimenGeneral><impuesto><idImpuesto>30</idImpuesto>"
    "<descripcionImpuesto>IVA</descripcionImpuesto></impuesto>"
    "<impuesto><idImpuesto>10</idImpuesto></impuesto></datosRegimenGeneral>"
)

PERSONA_MONO = _sobre(
    "<datosGenerales><apellido>PEREZ</apellido><nombre>JUAN</nombre>"
    "<tipoPersona>FISICA</tipoPersona><estadoClave>ACTIVO</estadoClave></datosGenerales>"
    "<datosMonotributo><impuesto><idImpuesto>20</idImpuesto></impuesto></datosMonotributo>"
)

FAULT_NO_EXISTE = (
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
    "<soap:Fault><faultcode>soap:Server</faultcode>"
    "<faultstring>No existe persona con ese Id</faultstring></soap:Fault>"
    "</soap:Body></soap:Envelope>"
)


def test_lee_responsable_inscripto() -> None:
    datos = leer_persona(PERSONA_RI, "30712345678")
    assert datos is not None
    assert datos.fuente == "arca"
    assert datos.razon_social == "REPUESTOS DEL SUR SA"
    assert datos.cond_iva == CondicionIva.RESPONSABLE_INSCRIPTO
    assert datos.tipo_persona == TipoPersona.JURIDICA
    assert datos.direccion == "AV SIEMPRE VIVA 742 - CORDOBA - CORDOBA (5000)"


def test_lee_monotributista_persona_fisica() -> None:
    datos = leer_persona(PERSONA_MONO, "20123456786")
    assert datos is not None
    assert datos.razon_social == "PEREZ JUAN"
    assert datos.cond_iva == CondicionIva.MONOTRIBUTO
    assert datos.tipo_persona == TipoPersona.FISICA


def test_sin_impuestos_no_inventa_condicion() -> None:
    datos = leer_persona(_sobre("<datosGenerales><razonSocial>X</razonSocial></datosGenerales>"),
                         "30712345678")
    assert datos is not None
    assert datos.cond_iva is None


def test_cuit_inexistente_devuelve_none() -> None:
    assert leer_persona(FAULT_NO_EXISTE, "20333333334") is None


def test_otro_fault_es_servicio_no_disponible() -> None:
    fault = FAULT_NO_EXISTE.replace("No existe persona con ese Id", "Computador no autorizado")
    with pytest.raises(ServicioExternoNoDisponible, match="no autorizado"):
        leer_persona(fault, "20333333334")


def test_tra_y_firma_cms() -> None:
    tra = armar_tra("ws_sr_constancia_inscripcion", AHORA)
    assert b"<service>ws_sr_constancia_inscripcion</service>" in tra
    cms = firmar_tra(tra, _credenciales())
    assert len(cms) > 500


def test_ticket_con_fault_de_wsaa() -> None:
    fault = FAULT_NO_EXISTE.replace(
        "No existe persona con ese Id", "El CEE ya posee un TA valido"
    )
    with pytest.raises(ServicioExternoNoDisponible, match="TA valido"):
        leer_ticket(fault)


def test_adaptador_reutiliza_el_ticket(tmp_path: Path) -> None:
    llamadas: list[str] = []

    def enviar(url: str, cuerpo: bytes) -> str:
        llamadas.append(url)
        if url == URL_WSAA[AmbienteArca.HOMOLOGACION]:
            return _login_ok(AHORA + timedelta(hours=12))
        assert b"<token>TOK</token>" in cuerpo
        return PERSONA_RI

    def nuevo() -> ArcaPadron:
        return ArcaPadron(
            ambiente=AmbienteArca.HOMOLOGACION,
            cuit_representada="20123456786",
            credenciales=_credenciales(),
            servicio="servicio-test-cache",
            enviar=enviar,
            dir_cache=tmp_path,
            ahora=lambda: AHORA,
        )

    assert nuevo().consultar("30712345678") is not None
    assert nuevo().consultar("30712345678") is not None
    wsaa = [u for u in llamadas if u == URL_WSAA[AmbienteArca.HOMOLOGACION]]
    assert len(wsaa) == 1
    assert llamadas.count(URL_PADRON[AmbienteArca.HOMOLOGACION]) == 2


def test_boveda_valida_y_extrae_datos(tmp_path: Path) -> None:
    cred = _credenciales("20123456786")
    boveda = ArchivoBovedaArca(tmp_path)
    info = boveda.guardar(cred.certificado, cred.clave)
    assert info.cuit == "20123456786"
    assert info.vence == (AHORA + timedelta(days=730)).date()
    leidas = boveda.leer()
    assert leidas is not None
    assert leidas.clave == cred.clave


def test_boveda_rechaza_clave_de_otro_certificado(tmp_path: Path) -> None:
    uno, otro = _credenciales(), _credenciales()
    with pytest.raises(ArchivoInvalido, match="no corresponde"):
        ArchivoBovedaArca(tmp_path).guardar(uno.certificado, otro.clave)


def test_boveda_rechaza_basura(tmp_path: Path) -> None:
    with pytest.raises(ArchivoInvalido):
        ArchivoBovedaArca(tmp_path).guardar(b"no es un certificado", b"tampoco")
    assert ArchivoBovedaArca(tmp_path).leer() is None
