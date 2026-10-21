from __future__ import annotations

from datetime import date
from decimal import Decimal

from taller.adapters.outbound.ocr.adapter import OcrPypdfTesseract
from taller.adapters.outbound.ocr.parser import cuit_valido, parse_importe, parsear
from taller.domain.enums import TipoComprobante

_FACTURA_A = """
FACTURA A
Razón Social: Acme Proveedor S.A.
CUIT: 30-71234562-0
Punto de Venta: 0001
Comp. Nro: 00012345
Fecha de Emisión: 15/07/2026
Importe Neto Gravado: 1.000,00
IVA 21%: 210,00
Importe Total: $ 1.210,00
CAE N°: 12345678901234
"""

# Factura C real: pypdf emite etiquetas y valores en bloques separados porque el PDF
# de AFIP está maquetado en columnas.
_COLUMNAS = """
Fecha de Emisión:
ORIGINAL
SULROCA GONZALEZ YARIEL
Pedro Nolasco Carrion 480 Dpto:408 -
Período Facturado Desde: Hasta: Fecha de Vto. para el pago:
Condición frente al IVA:
Apellido y Nombre / Razón Social:
Domicilio:
11/09/2026 11/09/2026 11/09/2026
27963709973
VRF S.A.
CUIT:
Punto de Venta: Comp. Nro:00001 00000027
Razón Social:
FACTURACCOD. 011
Responsable Monotributo
27963709973
CUIT: 33711174929
0,00
63550,00
63550,00
Subtotal: $
Importe Otros Tributos: $
Importe Total: $
CAE N°:
Fecha de Vto. de CAE:
Comprobante Autorizado
21/09/2026
86372611526307
"SULROCA GONZALEZ YARIEL"
"""

# Salida real de Tesseract sobre la misma factura escaneada: etiqueta y valor juntos,
# columnas vecinas pegadas en la misma línea y "$" en el medio.
_TESSERACT = """
ORIGINAL
COD. 011
Punto de Venta: 00001 Comp. Nro: 00000027
Razón Social: SULROCA GONZALEZ YARIEL Fecha de Emisión: 11/09/2026
Domicilio Comercial: Pedro Nolasco Carrion 480 Dpto:408 - CUIT: 27963709973
Condición frente al IVA: Responsable Monotributo
CUIT: 33711174929 Apellido y Nombre / Razón Social: VRF S.A.
Subtotal: $ 63550,00
Importe Otros Tributos: $ 0,00
Importe Total: $ 63550,00
"SULROCA GONZALEZ YARIEL"
ARCA Pág. 1/1 CAE N°: 86372611526307
"""


def test_importe_argentino() -> None:
    assert parse_importe("1.234,56") == Decimal("1234.56")
    assert parse_importe("121,00") == Decimal("121.00")
    assert parse_importe("$ 63550,00") == Decimal("63550.00")
    assert parse_importe("12a") is None


def test_cuit_con_digito_verificador() -> None:
    assert cuit_valido("30712345620")
    assert cuit_valido("27963709973")
    assert not cuit_valido("20123456789")


def test_factura_a_completa() -> None:
    d = parsear(_FACTURA_A)
    assert d.tipo == TipoComprobante.FACTURA_A
    assert d.emisor_cuit == "30712345620"
    assert d.emisor_razon_social == "Acme Proveedor S.A."
    assert (d.pto_venta, d.numero) == (1, 12345)
    assert d.fecha == date(2026, 7, 15)
    assert d.neto == Decimal("1000.00")
    assert d.iva21 == Decimal("210.00")
    assert d.total == Decimal("1210.00")
    assert d.cae == "12345678901234"


def test_layout_en_columnas_de_pypdf() -> None:
    d = parsear(_COLUMNAS)
    assert d.tipo == TipoComprobante.FACTURA_C
    assert d.emisor_cuit == "27963709973"
    assert d.emisor_razon_social == "SULROCA GONZALEZ YARIEL"
    assert (d.pto_venta, d.numero) == (1, 27)
    assert d.fecha == date(2026, 9, 11)
    assert d.total == Decimal("63550.00")
    assert d.cae == "86372611526307"


def test_texto_de_tesseract() -> None:
    d = parsear(_TESSERACT)
    assert d.tipo == TipoComprobante.FACTURA_C
    assert d.emisor_cuit == "27963709973"
    assert d.emisor_razon_social == "SULROCA GONZALEZ YARIEL"
    assert (d.pto_venta, d.numero) == (1, 27)
    assert d.fecha == date(2026, 9, 11)
    assert d.cae == "86372611526307"
    # "Otros Tributos: $ 0,00" no es el total, y "Subtotal" tampoco.
    assert d.total == Decimal("63550.00")


def test_cae_con_simbolos_mal_leidos_por_tesseract() -> None:
    for linea in ("CAEN”: 86372613323488", "CAE N*: 86372613323488", "CAE No 86372613323488"):
        assert parsear(f"FACTURA C\n{linea}\nTotal: $ 100,00").cae == "86372613323488"


def test_cuit_del_emisor_y_no_del_receptor() -> None:
    texto = "FACTURA B\nCUIT del cliente: 30-71234562-0\nCUIT: 27-96370997-3\nTotal: $ 100,00"
    assert parsear(texto).emisor_cuit == "27963709973"


def test_cuit_invalido_se_ignora() -> None:
    assert parsear("FACTURA A\nCUIT: 20-12345678-9\nTotal: $ 100,00").emisor_cuit is None


def test_nota_de_credito() -> None:
    d = parsear("NOTA DE CREDITO B\nCUIT: 30-71234562-0\nImporte Total: $ 50,00")
    assert d.tipo == TipoComprobante.NOTA_CREDITO


def test_nunca_inventa_con_ruido() -> None:
    d = parsear("foto borrosa sin datos legibles 0001-00000123 25/09/2026")
    assert d.tipo is None
    assert d.total is None
    assert d.numero is None


def test_descarta_total_en_cero() -> None:
    assert parsear("FACTURA B\nCUIT: 30-71234562-0\nImporte Total: $ 0,00\n").total is None


def test_no_inventa_total_ni_razon_social() -> None:
    d = parsear("FACTURA B\nCUIT: 30-71234562-0\nRazón Social:\nDomicilio:\nIVA 21%: 21,00\n")
    assert d.total is None
    assert d.emisor_razon_social is None


def test_ticket_sin_cae() -> None:
    d = parsear("TICKET\nCUIT 30-71234562-0\nTOTAL $ 1500,00\nIVA 21%: $ 260,33\n")
    assert d.tipo == TipoComprobante.TICKET
    assert d.cae is None
    assert d.total == Decimal("1500.00")


def test_archivo_que_no_es_pdf_ni_imagen_queda_vacio() -> None:
    d = OcrPypdfTesseract().extraer(contenido=b"hola", content_type="text/plain", nombre="x.txt")
    assert d.total is None
