"""OCR de fotos y PDFs escaneados con Tesseract.

Los PDF con texto embebido se leen con pypdf (ver `pdf.py`). Esto es el camino lento,
sólo para cuando no hay texto que leer.
"""

from __future__ import annotations

import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    import pypdfium2
    import pytesseract
    from PIL import Image, ImageOps

    _IMPORTADO = True
except ImportError:  # pragma: no cover - entorno sin las dependencias de OCR
    _IMPORTADO = False

_IDIOMAS = ("spa", "eng")
_MAX_PAGINAS = 2
# ~216 DPI: suficiente para el cuerpo de una factura sin disparar la memoria.
_ESCALA_PDF = 3
# Tesseract pierde precisión con imágenes chicas y se vuelve lento con las enormes.
_ANCHO_MINIMO = 1600
_ANCHO_MAXIMO = 4000
_TIMEOUT_SEGUNDOS = 60
_RUTAS_WINDOWS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


def _ubicar_tesseract() -> None:
    """Usa `TESSERACT_CMD`, el PATH o la instalación estándar de Windows."""
    if not _IMPORTADO:
        return
    explicito = os.environ.get("TESSERACT_CMD")
    if explicito:
        pytesseract.pytesseract.tesseract_cmd = explicito
        return
    if shutil.which("tesseract"):
        return
    for ruta in _RUTAS_WINDOWS:
        if ruta.exists():
            pytesseract.pytesseract.tesseract_cmd = str(ruta)
            return


_ubicar_tesseract()


def ocr_disponible() -> bool:
    """El binario de Tesseract es opcional: sin él el preview queda vacío, no rompe."""
    if not _IMPORTADO:
        return False
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def _enderezar(imagen: Any) -> Any:
    """Una factura de costado sale ilegible: Tesseract detecta el giro."""
    try:
        osd = pytesseract.image_to_osd(
            imagen, output_type=pytesseract.Output.DICT, timeout=_TIMEOUT_SEGUNDOS
        )
    except Exception:
        return imagen
    giro = int(osd.get("rotate", 0)) % 360
    # Tesseract informa grados horarios; PIL rota en antihorario.
    return imagen.rotate(-giro, expand=True) if giro else imagen


def _preparar(imagen: Any) -> Any:
    # Las fotos de celular guardan la rotación en EXIF en vez de aplicarla.
    imagen = ImageOps.exif_transpose(imagen).convert("L")
    imagen = _enderezar(imagen)
    ancho, alto = imagen.size
    if ancho < _ANCHO_MINIMO:
        factor = _ANCHO_MINIMO / ancho
    elif ancho > _ANCHO_MAXIMO:
        factor = _ANCHO_MAXIMO / ancho
    else:
        factor = 1.0
    if factor != 1.0:
        tamano = (round(ancho * factor), round(alto * factor))
        imagen = imagen.resize(tamano, Image.Resampling.LANCZOS)
    return ImageOps.autocontrast(imagen)


def _leer(imagen: Any) -> str:
    for idioma in _IDIOMAS:
        try:
            return str(pytesseract.image_to_string(imagen, lang=idioma, timeout=_TIMEOUT_SEGUNDOS))
        except pytesseract.TesseractError:
            continue  # falta ese paquete de idioma
        except RuntimeError:
            return ""  # timeout: no tiene sentido reintentar
    return ""


def texto_de_imagen(data: bytes) -> str:
    if not ocr_disponible():
        return ""
    try:
        with Image.open(BytesIO(data)) as imagen:
            return _leer(_preparar(imagen))
    except Exception:
        return ""


def texto_de_pdf_escaneado(data: bytes) -> str:
    if not ocr_disponible():
        return ""
    try:
        pdf = pypdfium2.PdfDocument(data)
    except Exception:
        return ""
    partes: list[str] = []
    try:
        for indice in range(min(len(pdf), _MAX_PAGINAS)):
            imagen = pdf[indice].render(scale=_ESCALA_PDF).to_pil()
            try:
                partes.append(_leer(_preparar(imagen)))
            finally:
                imagen.close()
    except Exception:
        return "\n".join(partes)
    finally:
        pdf.close()
    return "\n".join(partes)
