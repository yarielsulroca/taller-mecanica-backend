from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

# Original / duplicado / triplicado repiten la misma factura.
_MAX_PAGINAS = 2


def texto_de_pdf(data: bytes) -> str:
    """Texto embebido del PDF (exacto y barato). Vacío si es un escaneo o está dañado."""
    try:
        lector = PdfReader(BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in lector.pages[:_MAX_PAGINAS])
    except Exception:
        return ""
