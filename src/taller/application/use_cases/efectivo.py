from __future__ import annotations

from taller.domain.entities.movimiento import Movimiento
from taller.domain.enums import MedioPago


def comprobar_efectivo(movimiento: Movimiento) -> None:
    """RN-114a: el efectivo se comprueba solo al registrar.

    El billete ya salió (o entró) del bolsillo en el momento del pago: no hay
    nada a verificar después, como sí pasa con transferencias, Mercado Pago o
    cheque (esos quedan `pendiente` hasta que se adjunta el comprobante y se
    comprueban a mano).
    """
    if movimiento.medio is MedioPago.EFECTIVO and movimiento.estado.value == "pendiente":
        movimiento.comprobar()
