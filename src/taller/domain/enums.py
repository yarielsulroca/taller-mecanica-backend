from __future__ import annotations

from enum import StrEnum


class CondicionIva(StrEnum):
    RESPONSABLE_INSCRIPTO = "responsable_inscripto"
    EXENTO = "exento"
    CONSUMIDOR_FINAL = "consumidor_final"
    MONOTRIBUTO = "monotributo"
    NO_CATEGORIZADO = "no_categorizado"
    PROVEEDOR_EXTERIOR = "proveedor_exterior"
    CLIENTE_EXTERIOR = "cliente_exterior"
    IVA_LIBERADO_LEY_19640 = "iva_liberado_ley_19640"
    MONOTRIBUTISTA_SOCIAL = "monotributista_social"
    IVA_NO_ALCANZADO = "iva_no_alcanzado"
    MONOTRIBUTISTA_INDEPENDIENTE_PROMOVIDO = "monotributista_independiente_promovido"


# Etiquetas oficiales (para la UI y los comprobantes).
ETIQUETAS_CONDICION_IVA: dict[CondicionIva, str] = {
    CondicionIva.RESPONSABLE_INSCRIPTO: "IVA Responsable Inscripto",
    CondicionIva.EXENTO: "IVA Sujeto Exento",
    CondicionIva.CONSUMIDOR_FINAL: "Consumidor Final",
    CondicionIva.MONOTRIBUTO: "Responsable Monotributo",
    CondicionIva.NO_CATEGORIZADO: "Sujeto No Categorizado",
    CondicionIva.PROVEEDOR_EXTERIOR: "Proveedor del Exterior",
    CondicionIva.CLIENTE_EXTERIOR: "Cliente del Exterior",
    CondicionIva.IVA_LIBERADO_LEY_19640: "IVA Liberado - Ley N° 19.640",
    CondicionIva.MONOTRIBUTISTA_SOCIAL: "Monotributista Social",
    CondicionIva.IVA_NO_ALCANZADO: "IVA No Alcanzado",
    CondicionIva.MONOTRIBUTISTA_INDEPENDIENTE_PROMOVIDO: (
        "Monotributista Trabajador Independiente Promovido"
    ),
}


class TipoDocumento(StrEnum):
    DNI = "dni"
    CUIT = "cuit"
    CUIL = "cuil"
    PASAPORTE = "pasaporte"


class TipoPersona(StrEnum):
    FISICA = "fisica"
    JURIDICA = "juridica"


class FormaJuridica(StrEnum):
    SOCIEDAD_ANONIMA = "sa"
    SOCIEDAD_RESPONSABILIDAD_LIMITADA = "srl"
    SOCIEDAD_POR_ACCIONES_SIMPLIFICADA = "sas"
    SOCIEDAD_COLECTIVA = "sociedad_colectiva"
    SOCIEDAD_EN_COMANDITA = "sociedad_en_comandita"
    SOCIEDAD_UNIPERSONAL = "sociedad_unipersonal"
    COOPERATIVA = "cooperativa"
    ASOCIACION_CIVIL = "asociacion_civil"
    FUNDACION = "fundacion"
    CONSORCIO = "consorcio"
    MONOTRIBUTO = "monotributo"
    OTRO = "otro"


class TipoRemuneracion(StrEnum):
    SUELDO = "sueldo"
    JORNAL = "jornal"
    COMISION = "comision"


class EstadoOT(StrEnum):
    INICIADO = "iniciado"
    REVISION = "revision"
    PRESUPUESTADO = "presupuestado"
    RECHAZADO = "rechazado"
    EN_TALLER = "en_taller"
    PENDIENTE_PAGO = "pendiente_pago"
    COBRADO = "cobrado"
    ENTREGADO = "entregado"
    CERRADA = "cerrada"
    CANCELADA = "cancelada"


class Prioridad(StrEnum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class TipoItem(StrEnum):
    MANO_OBRA = "mano_obra"
    REPUESTO = "repuesto"
    SERVICIO = "servicio"


class EstadoItem(StrEnum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    NO_REALIZADO = "no_realizado"


class OrigenPieza(StrEnum):
    TALLER = "taller"
    CLIENTE = "cliente"


class TipoEvidencia(StrEnum):
    FOTO = "foto"
    VIDEO = "video"


class VistaFoto(StrEnum):
    DELANTERA = "delantera"
    TRASERA = "trasera"
    LATERAL_IZQUIERDA = "lateral_izquierda"
    LATERAL_DERECHA = "lateral_derecha"
    INTERIOR = "interior"
    MOTOR = "motor"
    OTRA = "otra"


class MomentoEvidencia(StrEnum):
    ANTES = "antes"
    DURANTE = "durante"
    DESPUES = "despues"


class MedioPago(StrEnum):
    EFECTIVO = "efectivo"
    TRANSFERENCIA = "transferencia"
    MERCADO_PAGO = "mercado_pago"
    TARJETA_DEBITO = "tarjeta_debito"
    TARJETA_CREDITO = "tarjeta_credito"
    CHEQUE = "cheque"
    OTRO = "otro"


class TipoComprobante(StrEnum):
    FACTURA_A = "factura_a"
    FACTURA_B = "factura_b"
    FACTURA_C = "factura_c"
    TICKET = "ticket"
    RECIBO = "recibo"
    NOTA_CREDITO = "nota_credito"
    NOTA_DEBITO = "nota_debito"
    REMITO = "remito"
    OTRO = "otro"


class OrigenComprobante(StrEnum):
    TALLER = "taller"
    CLIENTE = "cliente"
    PROVEEDOR = "proveedor"
    OTRO = "otro"


class ClasificacionComprobante(StrEnum):
    VENTA = "venta"
    COMPRA = "compra"
    PAGO = "pago"
    COSTO = "costo"


class EstadoComprobante(StrEnum):
    PENDIENTE = "pendiente"
    COMPROBADO = "comprobado"
    ANULADO = "anulado"


class CondicionPago(StrEnum):
    CONTADO = "contado"
    CUENTA_CORRIENTE = "cuenta_corriente"


class Periodicidad(StrEnum):
    UNICA = "unica"
    DIARIA = "diaria"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


class OrigenCuota(StrEnum):
    COBRO = "cobro"
    PAGO = "pago"


class RetencionTipo(StrEnum):
    """Retenciones/certificados que un gran pagador descuenta del cobro (H5)."""

    IIBB = "iibb"
    IVA = "iva"
    GANANCIAS = "ganancias"
    SUSS = "suss"
    OTRO = "otro"


class EstadoCuota(StrEnum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADA = "pagada"
    VENCIDA = "vencida"
    ANULADA = "anulada"


class PeriodicidadPago(StrEnum):
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    POR_JORNAL = "por_jornal"


class EstadoAdelanto(StrEnum):
    PENDIENTE = "pendiente"
    DESCONTADO = "descontado"
    ANULADO = "anulado"


class EstadoLiquidacion(StrEnum):
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    ANULADA = "anulada"


class SignoMovimiento(StrEnum):
    INGRESO = "ingreso"
    EGRESO = "egreso"


class NaturalezaMovimiento(StrEnum):
    VENTA_TRABAJO = "venta_trabajo"
    COMPRA_REPUESTO = "compra_repuesto"
    PAGO_PROVEEDOR = "pago_proveedor"
    PAGO_TRABAJADOR = "pago_trabajador"
    GASTO_OPERATIVO = "gasto_operativo"
    IMPUESTO = "impuesto"
    OTRO = "otro"


class EstadoMovimiento(StrEnum):
    PENDIENTE = "pendiente"
    COMPROBADO = "comprobado"
    ANULADO = "anulado"


class EstadoCompra(StrEnum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    PAGADA = "pagada"
    ANULADA = "anulada"


class TipoNotificacion(StrEnum):
    OT_SIN_ASIGNAR = "ot_sin_asignar"
    OT_ASIGNADA = "ot_asignada"
    OT_ESTADO = "ot_estado"
    OT_EN_PROCESO = "ot_en_proceso"
    OT_POR_COBRAR = "ot_por_cobrar"
    CUOTA_VENCIDA = "cuota_vencida"
    FACTURA_PENDIENTE = "factura_pendiente"
    ADELANTO_PENDIENTE = "adelanto_pendiente"
    VENCIMIENTO_PAGO = "vencimiento_pago"
    GENERICA = "generica"


class PeriodicidadGasto(StrEnum):
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    BIMESTRAL = "bimestral"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"


class OrigenObligacion(StrEnum):
    GASTO_FIJO = "gasto_fijo"
    SUELDO = "sueldo"


class EstadoObligacion(StrEnum):
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    OMITIDA = "omitida"


class Severidad(StrEnum):
    INFO = "info"
    ADVERTENCIA = "advertencia"
    CRITICA = "critica"
