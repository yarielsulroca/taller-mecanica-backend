"""Fechas de vencimiento de gastos fijos y períodos de sueldo. Funciones puras, sin I/O."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

from taller.domain.enums import PeriodicidadGasto, PeriodicidadPago

_ARGENTINA = timezone(timedelta(hours=-3))


def fecha_argentina(momento: datetime) -> date:
    """Fecha calendario en Argentina (UTC−3, sin horario de verano)."""
    return momento.astimezone(_ARGENTINA).date()


_MESES = {
    PeriodicidadGasto.MENSUAL: 1,
    PeriodicidadGasto.BIMESTRAL: 2,
    PeriodicidadGasto.TRIMESTRAL: 3,
    PeriodicidadGasto.ANUAL: 12,
}


def _fin_de_mes(anio: int, mes: int) -> date:
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _dia_del_mes(anio: int, mes: int, dia: int) -> date:
    """El día pedido o el último del mes si no existe (31 en abril → 30)."""
    return date(anio, mes, min(dia, calendar.monthrange(anio, mes)[1]))


def _sumar_meses(anio: int, mes: int, meses: int) -> tuple[int, int]:
    total = anio * 12 + (mes - 1) + meses
    return total // 12, total % 12 + 1


def _quincenas(desde: date, hasta: date) -> list[tuple[date, date]]:
    periodos: list[tuple[date, date]] = []
    anio, mes = desde.year, desde.month
    while date(anio, mes, 1) <= hasta:
        periodos.append((date(anio, mes, 1), date(anio, mes, 15)))
        periodos.append((date(anio, mes, 16), _fin_de_mes(anio, mes)))
        anio, mes = _sumar_meses(anio, mes, 1)
    return periodos


def vencimientos_gasto(
    periodicidad: PeriodicidadGasto,
    dia_vencimiento: int,
    inicio: date,
    fin: date | None,
    desde: date,
    hasta: date,
) -> list[date]:
    """Vencimientos dentro de [desde, hasta], respetando el inicio y el fin del gasto.

    - semanal: cada 7 días a partir del inicio.
    - quincenal: los días 15 y último de cada mes.
    - mensual/bimestral/trimestral/anual: el `dia_vencimiento`, contando los meses desde el inicio.
    """
    tope = min(hasta, fin) if fin else hasta
    piso = max(desde, inicio)
    if piso > tope:
        return []
    fechas: list[date]
    if periodicidad is PeriodicidadGasto.SEMANAL:
        salto = max(0, (piso - inicio).days + 6) // 7
        fechas = []
        actual = inicio + timedelta(days=7 * salto)
        while actual <= tope:
            fechas.append(actual)
            actual += timedelta(days=7)
    elif periodicidad is PeriodicidadGasto.QUINCENAL:
        fechas = [fin_q for _, fin_q in _quincenas(piso, tope)]
    else:
        paso = _MESES[periodicidad]
        fechas = []
        anio, mes = inicio.year, inicio.month
        while date(anio, mes, 1) <= tope:
            fechas.append(_dia_del_mes(anio, mes, dia_vencimiento))
            anio, mes = _sumar_meses(anio, mes, paso)
    return [f for f in fechas if piso <= f <= tope and f >= inicio]


def periodos_sueldo(
    periodicidad: PeriodicidadPago, desde: date, hasta: date
) -> list[tuple[date, date]]:
    """Períodos de pago cuyo cierre (= vencimiento) cae en [desde, hasta].

    - semanal: lunes a sábado; se paga el sábado.
    - quincenal: 1–15 y 16–fin de mes.
    - mensual: el mes calendario; se paga el último día.
    - por jornal: no genera vencimientos (se paga cada jornada).
    """
    if periodicidad is PeriodicidadPago.SEMANAL:
        lunes = desde - timedelta(days=desde.weekday())
        periodos = []
        while lunes <= hasta:
            periodos.append((lunes, lunes + timedelta(days=5)))
            lunes += timedelta(days=7)
    elif periodicidad is PeriodicidadPago.QUINCENAL:
        periodos = _quincenas(desde, hasta)
    elif periodicidad is PeriodicidadPago.MENSUAL:
        periodos = []
        anio, mes = desde.year, desde.month
        while date(anio, mes, 1) <= hasta:
            periodos.append((date(anio, mes, 1), _fin_de_mes(anio, mes)))
            anio, mes = _sumar_meses(anio, mes, 1)
    else:
        return []
    return [(ini, cierre) for ini, cierre in periodos if desde <= cierre <= hasta]
