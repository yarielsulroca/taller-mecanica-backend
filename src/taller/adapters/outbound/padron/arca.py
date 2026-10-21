"""Padrón oficial de ARCA: WSAA (autenticación) + WS Constancia de Inscripción (A5).

Flujo: se firma un ticket de acceso (TRA) con el certificado del contribuyente,
WSAA devuelve token y sign (validez ~12 h, se reutilizan) y con ellos se llama a
``getPersona_v2``. Las funciones de armado/lectura son puras y se testean sin red.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key, pkcs7

from taller.domain.entities.conexion_arca import AmbienteArca, ConexionArca
from taller.domain.enums import CondicionIva, TipoPersona
from taller.domain.exceptions import ServicioExternoNoDisponible
from taller.domain.ports.padron import CredencialesArca, DatosPadron

URL_WSAA = {
    AmbienteArca.HOMOLOGACION: "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
    AmbienteArca.PRODUCCION: "https://wsaa.afip.gov.ar/ws/services/LoginCms",
}
URL_PADRON = {
    AmbienteArca.HOMOLOGACION: "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5",
    AmbienteArca.PRODUCCION: "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5",
}

_IMPUESTO_IVA = "30"
_IMPUESTO_IVA_EXENTO = "32"
_MARGEN_RENOVACION = timedelta(minutes=5)

# Mapeo del texto del padrón a la condición IVA de AFIP. Se compara en minúsculas
# por contención; si no hubo coincidencia se conserva el texto crudo para que el
# operador decida (nunca se inventa).
_MAPA_COND_IVA: tuple[tuple[str, CondicionIva], ...] = (
    ("responsable inscripto", CondicionIva.RESPONSABLE_INSCRIPTO),
    ("sujeto exento", CondicionIva.EXENTO),
    ("exento", CondicionIva.EXENTO),
    ("consumidor final", CondicionIva.CONSUMIDOR_FINAL),
    ("responsable monotributo", CondicionIva.MONOTRIBUTO),
    ("monotributista social", CondicionIva.MONOTRIBUTISTA_SOCIAL),
    ("independiente promovido", CondicionIva.MONOTRIBUTISTA_INDEPENDIENTE_PROMOVIDO),
    ("no categorizado", CondicionIva.NO_CATEGORIZADO),
    ("proveedor del exterior", CondicionIva.PROVEEDOR_EXTERIOR),
    ("proveedor exterior", CondicionIva.PROVEEDOR_EXTERIOR),
    ("cliente del exterior", CondicionIva.CLIENTE_EXTERIOR),
    ("cliente exterior", CondicionIva.CLIENTE_EXTERIOR),
    ("no alcanzado", CondicionIva.IVA_NO_ALCANZADO),
    ("liberado", CondicionIva.IVA_LIBERADO_LEY_19640),
)


def mapear_cond_iva(texto: str | None) -> CondicionIva | None:
    if not texto:
        return None
    normalizado = texto.strip().lower()
    for clave, valor in _MAPA_COND_IVA:
        if clave in normalizado:
            return valor
    return None


def mapear_tipo_persona(texto: str | None) -> TipoPersona | None:
    if not texto:
        return None
    normalizado = texto.strip().lower()
    if "jurid" in normalizado or "juríd" in normalizado:
        return TipoPersona.JURIDICA
    if "fisic" in normalizado or "físic" in normalizado:
        return TipoPersona.FISICA
    return None


# --- WSAA ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ticket:
    token: str
    sign: str
    vence: datetime

    def vigente(self, ahora: datetime) -> bool:
        return self.vence - _MARGEN_RENOVACION > ahora


def armar_tra(servicio: str, ahora: datetime) -> bytes:
    desde = (ahora - timedelta(minutes=10)).replace(microsecond=0).isoformat()
    hasta = (ahora + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<loginTicketRequest version="1.0"><header>'
        f"<uniqueId>{int(ahora.timestamp())}</uniqueId>"
        f"<generationTime>{desde}</generationTime>"
        f"<expirationTime>{hasta}</expirationTime>"
        f"</header><service>{escape(servicio)}</service></loginTicketRequest>"
    ).encode()


def firmar_tra(tra: bytes, credenciales: CredencialesArca) -> str:
    """CMS (PKCS#7) firmado con el certificado, en base64, como lo pide WSAA."""
    cert = x509.load_pem_x509_certificate(credenciales.certificado)
    clave = load_pem_private_key(credenciales.clave, password=None)
    if not isinstance(clave, rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey):
        raise ServicioExternoNoDisponible("La clave privada cargada no es RSA ni EC")
    firmado = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra)
        .add_signer(cert, clave, hashes.SHA256())
        .sign(Encoding.DER, [])
    )
    return base64.b64encode(firmado).decode()


def sobre_login(cms: str) -> bytes:
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">'
        "<soapenv:Header/><soapenv:Body><wsaa:loginCms>"
        f"<wsaa:in0>{cms}</wsaa:in0>"
        "</wsaa:loginCms></soapenv:Body></soapenv:Envelope>"
    ).encode()


def leer_ticket(respuesta: str) -> Ticket:
    raiz = _parsear(respuesta)
    _fallar_si_fault(raiz, "ARCA rechazó el acceso")
    interno = _texto(raiz, "loginCmsReturn")
    if not interno:
        raise ServicioExternoNoDisponible("WSAA no devolvió el ticket de acceso")
    ticket = _parsear(interno)
    token, sign = _texto(ticket, "token"), _texto(ticket, "sign")
    vence = _texto(ticket, "expirationTime")
    if not token or not sign or not vence:
        raise ServicioExternoNoDisponible("El ticket de acceso de ARCA vino incompleto")
    return Ticket(token=token, sign=sign, vence=datetime.fromisoformat(vence))


# --- Constancia de inscripción (A5) -------------------------------------------


def sobre_persona(ticket: Ticket, cuit_representada: str, cuit: str) -> bytes:
    return (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:a5="http://a5.soap.ws.server.puc.sr/">'
        "<soapenv:Header/><soapenv:Body><a5:getPersona_v2>"
        f"<token>{escape(ticket.token)}</token>"
        f"<sign>{escape(ticket.sign)}</sign>"
        f"<cuitRepresentada>{cuit_representada}</cuitRepresentada>"
        f"<idPersona>{cuit}</idPersona>"
        "</a5:getPersona_v2></soapenv:Body></soapenv:Envelope>"
    ).encode()


def leer_persona(respuesta: str, cuit: str) -> DatosPadron | None:
    raiz = _parsear(respuesta)
    fault = _texto(raiz, "faultstring")
    if fault:
        if "no existe" in fault.lower():
            return None
        raise ServicioExternoNoDisponible(f"ARCA respondió con error: {fault}")

    generales = _buscar(raiz, "datosGenerales")
    error_constancia = _buscar(raiz, "errorConstancia")
    fuente_nombre = generales if generales is not None else error_constancia
    if fuente_nombre is None:
        return None

    razon = _texto(fuente_nombre, "razonSocial")
    if not razon:
        partes = [_texto(fuente_nombre, "apellido"), _texto(fuente_nombre, "nombre")]
        razon = " ".join(p for p in partes if p) or None

    cond_iva, cond_texto = _condicion_iva(raiz, error_constancia)
    return DatosPadron(
        cuit=cuit,
        fuente="arca",
        razon_social=razon,
        cond_iva=cond_iva,
        cond_iva_texto=cond_texto,
        direccion=_domicilio(generales),
        tipo_persona=mapear_tipo_persona(
            _texto(generales, "tipoPersona") if generales is not None else None
        ),
        estado=_texto(generales, "estadoClave") if generales is not None else None,
    )


def _condicion_iva(
    raiz: ET.Element, error_constancia: ET.Element | None
) -> tuple[CondicionIva | None, str | None]:
    if _buscar(raiz, "datosMonotributo") is not None:
        return CondicionIva.MONOTRIBUTO, "Responsable Monotributo"
    regimen = _buscar(raiz, "datosRegimenGeneral")
    if regimen is not None:
        impuestos = {
            _texto(i, "idImpuesto") for i in regimen.iter() if _local(i.tag) == "impuesto"
        }
        if _IMPUESTO_IVA in impuestos:
            return CondicionIva.RESPONSABLE_INSCRIPTO, "IVA Responsable Inscripto"
        if _IMPUESTO_IVA_EXENTO in impuestos:
            return CondicionIva.EXENTO, "IVA Sujeto Exento"
    if error_constancia is not None:
        errores = [_txt(e) for e in error_constancia.iter() if _local(e.tag) == "error"]
        return None, "; ".join(e for e in errores if e) or None
    return None, None


def _domicilio(generales: ET.Element | None) -> str | None:
    if generales is None:
        return None
    dom = _buscar(generales, "domicilioFiscal")
    if dom is None:
        return None
    partes = [
        _texto(dom, "direccion"),
        _texto(dom, "localidad"),
        _texto(dom, "descripcionProvincia"),
    ]
    texto = " - ".join(p for p in partes if p)
    cp = _texto(dom, "codPostal")
    if cp:
        texto = f"{texto} ({cp})" if texto else cp
    return texto or None


# --- XML sin depender de prefijos de namespace ---------------------------------


def _parsear(texto: str) -> ET.Element:
    try:
        return ET.fromstring(texto)
    except ET.ParseError as e:
        raise ServicioExternoNoDisponible("Respuesta ilegible de ARCA") from e


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _buscar(elem: ET.Element, nombre: str) -> ET.Element | None:
    for e in elem.iter():
        if _local(e.tag) == nombre:
            return e
    return None


def _txt(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    return elem.text.strip() or None


def _texto(elem: ET.Element, nombre: str) -> str | None:
    return _txt(_buscar(elem, nombre))


def _fallar_si_fault(raiz: ET.Element, prefijo: str) -> None:
    fault = _texto(raiz, "faultstring")
    if fault:
        raise ServicioExternoNoDisponible(f"{prefijo}: {fault}")


# --- Adaptador ----------------------------------------------------------------

Enviar = Callable[[str, bytes], str]

_tickets: dict[str, Ticket] = {}
_lock = threading.Lock()


def enviar_http(timeout_seg: float) -> Enviar:
    def enviar(url: str, cuerpo: bytes) -> str:
        try:
            r = httpx.post(
                url,
                content=cuerpo,
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'},
                timeout=timeout_seg,
            )
        except httpx.HTTPError as e:
            raise ServicioExternoNoDisponible("No se pudo conectar con ARCA") from e
        # Los SOAP fault llegan con HTTP 500 y se leen del cuerpo.
        if r.status_code >= 500 and "faultstring" not in r.text:
            raise ServicioExternoNoDisponible(f"ARCA no está disponible (HTTP {r.status_code})")
        return r.text

    return enviar


class ArcaPadron:
    """Consulta la constancia de inscripción en ARCA con el certificado del taller."""

    def __init__(
        self,
        *,
        ambiente: AmbienteArca,
        cuit_representada: str,
        credenciales: CredencialesArca,
        servicio: str,
        enviar: Enviar,
        dir_cache: Path | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._ambiente = ambiente
        self._cuit_repr = cuit_representada
        self._credenciales = credenciales
        self._servicio = servicio
        self._enviar = enviar
        self._dir_cache = dir_cache
        self._ahora = ahora

    def consultar(self, cuit: str) -> DatosPadron | None:
        ticket = self._ticket()
        respuesta = self._enviar(
            URL_PADRON[self._ambiente], sobre_persona(ticket, self._cuit_repr, cuit)
        )
        return leer_persona(respuesta, cuit)

    def _ticket(self) -> Ticket:
        clave = f"{self._ambiente.value}-{self._servicio}-{self._cuit_repr}"
        with _lock:
            ticket = _tickets.get(clave) or self._leer_cache(clave)
            if ticket is None or not ticket.vigente(self._ahora()):
                cms = firmar_tra(armar_tra(self._servicio, self._ahora()), self._credenciales)
                ticket = leer_ticket(self._enviar(URL_WSAA[self._ambiente], sobre_login(cms)))
                self._escribir_cache(clave, ticket)
            _tickets[clave] = ticket
            return ticket

    # WSAA niega un ticket nuevo mientras el anterior siga vigente: se persiste
    # para sobrevivir a reinicios del backend.
    def _archivo_cache(self, clave: str) -> Path | None:
        return self._dir_cache / f"ticket-{clave}.json" if self._dir_cache else None

    def _leer_cache(self, clave: str) -> Ticket | None:
        archivo = self._archivo_cache(clave)
        if archivo is None or not archivo.exists():
            return None
        try:
            d = json.loads(archivo.read_text(encoding="utf-8"))
            return Ticket(d["token"], d["sign"], datetime.fromisoformat(d["vence"]))
        except (ValueError, KeyError, OSError):
            return None

    def _escribir_cache(self, clave: str, ticket: Ticket) -> None:
        archivo = self._archivo_cache(clave)
        if archivo is None:
            return
        archivo.parent.mkdir(parents=True, exist_ok=True)
        datos = {"token": ticket.token, "sign": ticket.sign, "vence": ticket.vence.isoformat()}
        archivo.write_text(json.dumps(datos), encoding="utf-8")
        os.chmod(archivo, 0o600)


def fabrica_padron_arca(
    servicio: str, timeout_seg: float, dir_cache: Path
) -> Callable[[ConexionArca, CredencialesArca], ArcaPadron]:
    def crear(conexion: ConexionArca, credenciales: CredencialesArca) -> ArcaPadron:
        if conexion.cuit is None:
            raise ServicioExternoNoDisponible("Falta el CUIT de la conexión con ARCA")
        return ArcaPadron(
            ambiente=conexion.ambiente,
            cuit_representada=str(conexion.cuit),
            credenciales=credenciales,
            servicio=servicio,
            enviar=enviar_http(timeout_seg),
            dir_cache=dir_cache,
        )

    return crear
