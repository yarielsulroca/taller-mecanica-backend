from __future__ import annotations

from taller.adapters.outbound.ocr.imagen import texto_de_imagen, texto_de_pdf_escaneado
from taller.adapters.outbound.ocr.parser import parsear
from taller.adapters.outbound.ocr.pdf import texto_de_pdf
from taller.domain.ports.ocr import DatosComprobante

# Un PDF de AFIP con texto embebido ronda los miles de caracteres. Por debajo de esto es
# un escaneo (o trae sólo un sello suelto) y hay que rasterizarlo.
_MINIMO_TEXTO_PDF = 120
_FIRMAS_IMAGEN = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"BM", b"II*\x00", b"MM\x00*")


def _es_pdf(data: bytes, mime: str, nombre: str) -> bool:
    return "pdf" in mime or nombre.lower().endswith(".pdf") or data[:4] == b"%PDF"


def _es_imagen(data: bytes, mime: str) -> bool:
    if mime.startswith("image/"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return any(data.startswith(firma) for firma in _FIRMAS_IMAGEN)


def _con_texto(texto: str) -> bool:
    return len("".join(texto.split())) >= _MINIMO_TEXTO_PDF


class OcrPypdfTesseract:
    """PDF con texto → pypdf. PDF escaneado o foto → Tesseract (opcional)."""

    def extraer(self, *, contenido: bytes, content_type: str, nombre: str) -> DatosComprobante:
        mime = (content_type or "").lower()
        if _es_pdf(contenido, mime, nombre):
            texto = texto_de_pdf(contenido)
            if not _con_texto(texto):
                texto = texto_de_pdf_escaneado(contenido)
            return parsear(texto)
        if _es_imagen(contenido, mime):
            return parsear(texto_de_imagen(contenido))
        return DatosComprobante()
