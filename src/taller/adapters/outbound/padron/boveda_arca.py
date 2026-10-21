from __future__ import annotations

import os
import re
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_private_key,
)
from cryptography.x509.oid import NameOID

from taller.domain.exceptions import ArchivoInvalido
from taller.domain.ports.padron import CredencialesArca, InfoCertificado

_CERTIFICADO = "certificado.pem"
_CLAVE = "clave.key"


def _cargar_certificado(datos: bytes) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(datos)
    except ValueError:
        pass
    try:
        return x509.load_der_x509_certificate(datos)
    except ValueError as e:
        raise ArchivoInvalido("El certificado no es válido (se espera el .crt de ARCA)") from e


def _publica(clave: object) -> bytes:
    return clave.public_key().public_bytes(  # type: ignore[attr-defined]
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )


class ArchivoBovedaArca:
    """Certificado y clave privada en disco, fuera de la base y del webroot.

    La clave nunca se devuelve por la API ni se registra en logs o auditoría.
    """

    def __init__(self, directorio: str | Path) -> None:
        self._dir = Path(directorio)

    def guardar(self, certificado: bytes, clave: bytes) -> InfoCertificado:
        cert = _cargar_certificado(certificado)
        try:
            privada = load_pem_private_key(clave, password=None)
        except (ValueError, TypeError) as e:
            raise ArchivoInvalido(
                "La clave privada no es válida o tiene contraseña (se espera el .key sin clave)"
            ) from e
        if _publica(privada) != _publica(cert):
            raise ArchivoInvalido("La clave privada no corresponde a ese certificado")

        self._dir.mkdir(parents=True, exist_ok=True)
        self._escribir(_CERTIFICADO, cert.public_bytes(Encoding.PEM))
        self._escribir(_CLAVE, clave)
        return InfoCertificado(
            sujeto=cert.subject.rfc4514_string(),
            vence=cert.not_valid_after_utc.date(),
            cuit=self._cuit(cert),
        )

    def leer(self) -> CredencialesArca | None:
        cert, clave = self._dir / _CERTIFICADO, self._dir / _CLAVE
        if not cert.exists() or not clave.exists():
            return None
        return CredencialesArca(certificado=cert.read_bytes(), clave=clave.read_bytes())

    def _escribir(self, nombre: str, datos: bytes) -> None:
        destino = self._dir / nombre
        temporal = destino.with_suffix(".tmp")
        temporal.write_bytes(datos)
        os.chmod(temporal, 0o600)
        os.replace(temporal, destino)

    @staticmethod
    def _cuit(cert: x509.Certificate) -> str | None:
        # ARCA emite el certificado con serialNumber = "CUIT 20123456789".
        for attr in cert.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER):
            digitos = re.sub(r"\D", "", str(attr.value))
            if len(digitos) == 11:
                return digitos
        return None
