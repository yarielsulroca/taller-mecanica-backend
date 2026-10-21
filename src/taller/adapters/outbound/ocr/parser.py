"""Parseo de comprobantes AFIP (texto de pypdf o de Tesseract). Nunca inventa (RN-053)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from taller.domain.enums import TipoComprobante
from taller.domain.ports.ocr import DatosComprobante

# Señales mínimas para considerar que el texto es un comprobante: una foto ilegible no
# devuelve vacío sino ruido, y del ruido sale un número inventado.
_SENALES = (
    "cuit",
    "factura",
    "importe",
    "total",
    "iva",
    "ticket",
    "recibo",
    "nota",
    "comprobante",
    "punto de venta",
    "cae",
)
_MINIMO_SENALES = 3

_CUIT = re.compile(r"\b(\d{2}-?\d{8}-?\d)\b")
_FACTURA = re.compile(r"\bFACTURA\s+([ABC])\b", re.I)
_NOTA_CREDITO = re.compile(r"NOTA\s+DE\s+CR[EÉ]DITO", re.I)
_NOTA_DEBITO = re.compile(r"NOTA\s+DE\s+D[EÉ]BITO", re.I)
_PV_NRO = re.compile(r"\b(\d{4,5})\s*[-/]\s*(\d{1,8})\b")
_PV = re.compile(r"PUNTO\s+DE\s+VENTA\s*:?\s*(\d{1,5})", re.I)
_NRO = re.compile(r"(?:COMP(?:ROBANTE)?\.?\s*N(?:RO|UMERO|\.|°|º)?)\s*:?\s*(\d{1,8})", re.I)
_COMP_NRO = re.compile(r"Comp(?:ro)?\.?\s*Nro\.?\s*:?\s*(\d{1,5})\s+(\d{1,8})", re.I)
_FECHA = re.compile(
    r"FECHA(?:\s+DE\s+EMISI[OÓ]N)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)
_FECHA_SOLA = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b")
_RAZON = re.compile(r"RAZ[OÓ]N\s+SOCIAL\s*:?[ \t]*(\S.*)", re.I)
_COPIA = re.compile(r"^\s*(?:ORIGINAL|DUPLICADO|TRIPLICADO)\s*$", re.I | re.M)
_ENTRECOMILLAS = re.compile(r"\"([^\"\n]{3,80})\"")
# Tesseract en español suele pegar la N y leer "°" como "*", "”" u "o": "CAEN”: 863...".
_CAE = re.compile(r"\bCAE(?:\s*N)?[^\d\n]{0,4}(\d{14})\b", re.I)
_CAE_ETIQUETA = re.compile(r"\bCAEN?\b", re.I)
_CAE_NUMERO = re.compile(r"\b(\d{14})\b")
_IMPORTE = r"([\d]{1,3}(?:\.\d{3})*,\d{2}|[\d]+[.,]\d{2}|[\d]+)"
_RECEPTOR = re.compile(r"(CUIT\s+(?:DEL\s+)?(?:COMPRADOR|RECEPTOR|CLIENTE).*)", re.I | re.S)
_ROTULO_RECEPTOR = re.compile(r"(?:COMPRADOR|RECEPTOR|CLIENTE)[^\n]{0,25}$", re.I)

# En el layout en columnas de AFIP, pypdf emite las etiquetas seguidas y los valores
# después, así que un "valor" puede ser en realidad la etiqueta siguiente.
_ETIQUETAS = (
    "domicilio",
    "condición",
    "condicion",
    "cuit",
    "ingresos brutos",
    "fecha",
    "período",
    "periodo",
    "apellido y nombre",
    "razón social",
    "razon social",
    "punto de venta",
    "comp",
    "código",
    "codigo",
    "importe",
    "subtotal",
)
_PALABRAS_ETIQUETA = sorted({e.split()[0] for e in _ETIQUETAS}, key=len, reverse=True)
_ETIQUETA_INTERCALADA = re.compile(
    r"\s+(?:" + "|".join(re.escape(p) for p in _PALABRAS_ETIQUETA) + r")\b[^:\n]{0,40}:",
    re.I,
)

# Sin \b inicial: pypdf suele pegarlo a lo anterior ("FACTURACCOD. 011").
_CODIGO_AFIP = re.compile(r"COD\.?\s*(\d{1,3})\b", re.I)
_POR_CODIGO = {
    1: TipoComprobante.FACTURA_A,
    2: TipoComprobante.NOTA_DEBITO,
    3: TipoComprobante.NOTA_CREDITO,
    6: TipoComprobante.FACTURA_B,
    7: TipoComprobante.NOTA_DEBITO,
    8: TipoComprobante.NOTA_CREDITO,
    11: TipoComprobante.FACTURA_C,
    12: TipoComprobante.NOTA_DEBITO,
    13: TipoComprobante.NOTA_CREDITO,
}
_LETRA = {
    "A": TipoComprobante.FACTURA_A,
    "B": TipoComprobante.FACTURA_B,
    "C": TipoComprobante.FACTURA_C,
}
_PESOS_CUIT = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _solo_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())


def cuit_valido(digitos: str) -> bool:
    """Dígito verificador de AFIP: un CUIT mal leído por el OCR casi nunca lo cumple."""
    if len(digitos) != 11 or not digitos.isdigit():
        return False
    resto = sum(int(d) * p for d, p in zip(digitos[:10], _PESOS_CUIT, strict=True)) % 11
    verificador = 0 if resto == 0 else 9 if resto == 1 else 11 - resto
    return verificador == int(digitos[10])


def parse_importe(texto: str) -> Decimal | None:
    """Importe en formato argentino (1.234,56), con coma o punto decimal, o entero."""
    bruto = texto.strip().replace(" ", "").replace("$", "")
    if not bruto:
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{2}", bruto):
        bruto = bruto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d{2}", bruto):
        bruto = bruto.replace(",", ".")
    elif re.fullmatch(r"\d+\.\d{2}", bruto):
        pass
    elif re.fullmatch(r"\d+", bruto):
        bruto = f"{bruto}.00"
    else:
        return None
    try:
        return Decimal(bruto)
    except InvalidOperation:
        return None


def _importe_etiqueta(texto: str, *etiquetas: str) -> Decimal | None:
    for etiqueta in etiquetas:
        # El "$" va entre la etiqueta y el número: "Importe Total: $ 63550,00".
        hallado = re.search(rf"{etiqueta}\s*:?\s*\$?\s*{_IMPORTE}", texto, re.I)
        if hallado:
            valor = parse_importe(hallado.group(1))
            if valor is not None:
                return valor
        # Layout en columnas: el número aparece antes de la etiqueta (hasta 400 chars).
        posiciones = list(re.finditer(rf"{etiqueta}\s*:?\s*\$?", texto, re.I))
        if not posiciones:
            continue
        ultima = posiciones[-1]
        fragmento = texto[max(0, ultima.start() - 400) : ultima.start()]
        for numero in reversed(list(re.finditer(_IMPORTE, fragmento))):
            crudo = numero.group(1)
            # Enteros sueltos (CUIT, años, códigos) no son importes en este fallback.
            if re.fullmatch(r"\d+", crudo):
                continue
            valor = parse_importe(crudo)
            if valor is not None:
                return valor
    return None


def _total(texto: str) -> Decimal | None:
    valor = _importe_etiqueta(texto, r"IMPORTE\s+TOTAL", r"(?<![A-Za-z])TOTAL")
    # Un total en cero es el renglón "Otros Tributos: $ 0,00" mal leído (RN-059).
    return valor or None


def _fecha(valor: str) -> date | None:
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def _tipo(texto: str) -> TipoComprobante | None:
    if _NOTA_CREDITO.search(texto):
        return TipoComprobante.NOTA_CREDITO
    if _NOTA_DEBITO.search(texto):
        return TipoComprobante.NOTA_DEBITO
    letra = _FACTURA.search(texto)
    if letra:
        return _LETRA[letra.group(1).upper()]
    # La letra sale suelta en un recuadro y el OCR la pierde; el código sobrevive.
    codigo = _CODIGO_AFIP.search(texto)
    if codigo and int(codigo.group(1)) in _POR_CODIGO:
        return _POR_CODIGO[int(codigo.group(1))]
    bajo = texto.lower()
    if "ticket" in bajo:
        return TipoComprobante.TICKET
    if "recibo" in bajo:
        return TipoComprobante.RECIBO
    return None


def _recortar_en_etiqueta(valor: str) -> str:
    # El OCR junta columnas vecinas: "ACME S.A. Fecha de Emisión: 11/09/2026".
    corte = _ETIQUETA_INTERCALADA.search(valor)
    return valor[: corte.start()].strip() if corte else valor.strip()


def _es_etiqueta(valor: str) -> bool:
    limpio = valor.strip().rstrip(":").strip()
    if not limpio or valor.strip().endswith(":"):
        return True
    bajo = limpio.lower()
    return any(bajo.startswith(e) for e in _ETIQUETAS)


def _razon_social(texto: str) -> str | None:
    candidatos = [m.group(1) for m in _RAZON.finditer(texto)]
    # El nombre del emisor encabeza cada copia (ORIGINAL / DUPLICADO / TRIPLICADO).
    for match in _COPIA.finditer(texto):
        resto = texto[match.end() :].lstrip("\n")
        candidatos.append(resto.split("\n")[0])
    # Pie de la factura electrónica: el emisor va entre comillas.
    candidatos.extend(m.group(1) for m in _ENTRECOMILLAS.finditer(texto))
    for bruto in candidatos:
        valor = _recortar_en_etiqueta(bruto.strip().split("\n")[0])
        if valor and not _es_etiqueta(valor):
            return valor
    return None


def _cae(texto: str) -> str | None:
    match = _CAE.search(texto)
    if match:
        return match.group(1)
    # Layout en columnas: la etiqueta "CAE N°:" queda lejos de su valor.
    etiqueta = _CAE_ETIQUETA.search(texto)
    if etiqueta:
        cercano = _CAE_NUMERO.search(texto[etiqueta.end() : etiqueta.end() + 400])
        if cercano:
            return cercano.group(1)
    return None


def _cuit_emisor(texto: str) -> str | None:
    """El primer CUIT válido que no esté rotulado como del receptor."""
    receptor = _RECEPTOR.search(texto)
    bloques = [texto[: receptor.start()]] if receptor else []
    bloques.append(texto)
    for bloque in bloques:
        for match in _CUIT.finditer(bloque):
            digitos = _solo_digitos(match.group(1))
            rotulo = bloque[max(0, match.start() - 40) : match.start()]
            if cuit_valido(digitos) and not _ROTULO_RECEPTOR.search(rotulo):
                return digitos
    return None


def _punto_y_numero(texto: str) -> tuple[int | None, int | None]:
    pto: int | None = None
    nro: int | None = None
    comp = _COMP_NRO.search(texto)
    if comp:
        pto, nro = int(comp.group(1)), int(comp.group(2))
    compuesto = _PV_NRO.search(texto)
    if compuesto:
        pto = pto if pto is not None else int(compuesto.group(1))
        nro = nro if nro is not None else int(compuesto.group(2))
    if pto is None and (m := _PV.search(texto)):
        pto = int(m.group(1))
    if nro is None and (m := _NRO.search(texto)):
        nro = int(m.group(1))
    return pto, nro


def parsear(texto: str) -> DatosComprobante:
    """Extrae los campos de un comprobante. Si un dato no está, queda vacío."""
    if not (texto or "").strip():
        return DatosComprobante()
    bajo = texto.lower()
    if sum(1 for s in _SENALES if s in bajo) < _MINIMO_SENALES:
        return DatosComprobante()

    pto_venta, numero = _punto_y_numero(texto)
    m_fecha = _FECHA.search(texto) or _FECHA_SOLA.search(texto)
    return DatosComprobante(
        tipo=_tipo(texto),
        emisor_cuit=_cuit_emisor(texto),
        emisor_razon_social=_razon_social(texto),
        pto_venta=pto_venta,
        numero=numero,
        fecha=_fecha(m_fecha.group(1)) if m_fecha else None,
        neto=_importe_etiqueta(
            texto,
            r"IMPORTE\s+NETO\s+GRAVADO",
            r"NETO\s+GRAVADO(?:\s+21)?",
            r"(?<![A-Za-z])SUBTOTAL",
        ),
        iva21=_importe_etiqueta(texto, r"IVA\s*21(?:[.,]0+)?\s*%"),
        iva105=_importe_etiqueta(texto, r"IVA\s*10[.,]5\s*%"),
        iva27=_importe_etiqueta(texto, r"IVA\s*27(?:[.,]0+)?\s*%"),
        no_gravado=_importe_etiqueta(texto, r"IMPORTE\s+NO\s+GRAVADO", r"NO\s+GRAVADO"),
        percep_iva=_importe_etiqueta(texto, r"PERCEP(?:CI[OÓ]N)?\.?\s*(?:DE\s+)?IVA"),
        percep_iibb=_importe_etiqueta(
            texto, r"PERCEP(?:CI[OÓ]N)?\.?\s*(?:DE\s+)?(?:II?\.?\s*BB|INGRESOS\s+BRUTOS)"
        ),
        total=_total(texto),
        cae=_cae(texto),
    )
