from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from taller.adapters.outbound.postgres.models import (
    ClienteORM,
    EmpresaORM,
    FotoVehiculoORM,
    ProveedorORM,
    RubroORM,
    TipoPagoORM,
    TrabajadorORM,
    VehiculoORM,
)
from taller.domain.entities.catalogos import Rubro, TipoPago
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.empresa import Empresa
from taller.domain.entities.foto_vehiculo import FotoVehiculo
from taller.domain.entities.proveedor import Proveedor
from taller.domain.entities.trabajador import Trabajador
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import (
    CondicionIva,
    FormaJuridica,
    PeriodicidadPago,
    TipoDocumento,
    TipoPersona,
    TipoRemuneracion,
    VistaFoto,
)
from taller.domain.value_objects.cuit import Cuit
from taller.domain.value_objects.patente import Patente


def _solo_activos(stmt: Select[Any], columna: Any, incluir_archivados: bool) -> Select[Any]:
    if not incluir_archivados:
        return stmt.where(columna.is_(None))
    return stmt


# --- mapeos ORM -> dominio --------------------------------------------------
def _empresa(o: EmpresaORM) -> Empresa:
    return Empresa(
        id=o.id,
        archivado_en=o.archivado_en,
        razon_social=o.razon_social,
        cuit=Cuit(o.cuit),
        cond_iva=CondicionIva(o.cond_iva),
        tipo_persona=TipoPersona(o.tipo_persona),
        forma_juridica=FormaJuridica(o.forma_juridica) if o.forma_juridica else None,
        telefono=o.telefono,
        email=o.email,
        direccion=o.direccion,
    )


def _cliente(o: ClienteORM) -> Cliente:
    return Cliente(
        id=o.id,
        archivado_en=o.archivado_en,
        nombre=o.nombre,
        tipo_doc=TipoDocumento(o.tipo_doc),
        nro_doc=o.nro_doc,
        cond_iva=CondicionIva(o.cond_iva),
        tipo_persona=TipoPersona(o.tipo_persona),
        forma_juridica=FormaJuridica(o.forma_juridica) if o.forma_juridica else None,
        empresa_id=o.empresa_id,
        telefono=o.telefono,
        email=o.email,
        direccion=o.direccion,
    )


def _vehiculo(o: VehiculoORM) -> Vehiculo:
    return Vehiculo(
        id=o.id,
        archivado_en=o.archivado_en,
        patente=Patente(o.patente),
        cliente_id=o.cliente_id,
        marca=o.marca,
        modelo=o.modelo,
        anio=o.anio,
        vin=o.vin,
        motor=o.motor,
        color=o.color,
        km_actual=o.km_actual,
    )


def _proveedor(o: ProveedorORM) -> Proveedor:
    return Proveedor(
        id=o.id,
        archivado_en=o.archivado_en,
        razon_social=o.razon_social,
        cuit=Cuit(o.cuit),
        tipo_persona=TipoPersona(o.tipo_persona),
        forma_juridica=FormaJuridica(o.forma_juridica) if o.forma_juridica else None,
        telefono=o.telefono,
        email=o.email,
        cond_pago=o.cond_pago,
        cond_iva=CondicionIva(o.cond_iva) if o.cond_iva else None,
    )


def _trabajador(o: TrabajadorORM) -> Trabajador:
    return Trabajador(
        id=o.id,
        archivado_en=o.archivado_en,
        nombre=o.nombre,
        rol=o.rol,
        tipo_remuneracion=TipoRemuneracion(o.tipo_remuneracion),
        periodicidad_pago=PeriodicidadPago(o.periodicidad_pago),
        monto_periodo=o.monto_periodo,
        valor_hora=o.valor_hora,
        porcentaje_comision=o.porcentaje_comision,
    )


def _rubro(o: RubroORM) -> Rubro:
    return Rubro(id=o.id, archivado_en=o.archivado_en, nombre=o.nombre, tipo=o.tipo)


def _tipo_pago(o: TipoPagoORM) -> TipoPago:
    return TipoPago(
        id=o.id,
        archivado_en=o.archivado_en,
        nombre=o.nombre,
        schema_extra=dict(o.schema_extra),
    )


# --- repositorios -----------------------------------------------------------
class SqlEmpresaRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, empresa_id: UUID) -> Empresa | None:
        orm = self._s.get(EmpresaORM, empresa_id)
        return _empresa(orm) if orm is not None else None

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Empresa]:
        stmt = _solo_activos(select(EmpresaORM), EmpresaORM.archivado_en, incluir_archivados)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(EmpresaORM.razon_social).like(patron),
                    EmpresaORM.cuit.like(f"%{q}%"),
                )
            )
        return [_empresa(o) for o in self._s.scalars(stmt.order_by(EmpresaORM.razon_social))]

    def existe_cuit(self, cuit: str, *, excluir_id: UUID | None = None) -> bool:
        stmt = select(EmpresaORM.id).where(EmpresaORM.cuit == cuit)
        if excluir_id is not None:
            stmt = stmt.where(EmpresaORM.id != excluir_id)
        return self._s.scalar(stmt) is not None

    def guardar(self, empresa: Empresa) -> None:
        orm = self._s.get(EmpresaORM, empresa.id)
        if orm is None:
            orm = EmpresaORM(id=empresa.id)
            self._s.add(orm)
        orm.razon_social = empresa.razon_social
        orm.cuit = str(empresa.cuit)
        orm.cond_iva = empresa.cond_iva.value
        orm.tipo_persona = empresa.tipo_persona.value
        orm.forma_juridica = empresa.forma_juridica.value if empresa.forma_juridica else None
        orm.telefono = empresa.telefono
        orm.email = empresa.email
        orm.direccion = empresa.direccion
        orm.archivado_en = empresa.archivado_en


class SqlClienteRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, cliente_id: UUID) -> Cliente | None:
        orm = self._s.get(ClienteORM, cliente_id)
        return _cliente(orm) if orm is not None else None

    def listar(
        self,
        *,
        q: str | None = None,
        empresa_id: UUID | None = None,
        incluir_archivados: bool = False,
    ) -> list[Cliente]:
        stmt = _solo_activos(select(ClienteORM), ClienteORM.archivado_en, incluir_archivados)
        if empresa_id is not None:
            stmt = stmt.where(ClienteORM.empresa_id == empresa_id)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ClienteORM.nombre).like(patron),
                    ClienteORM.nro_doc.like(f"%{q}%"),
                )
            )
        return [_cliente(o) for o in self._s.scalars(stmt.order_by(ClienteORM.nombre))]

    def guardar(self, cliente: Cliente) -> None:
        orm = self._s.get(ClienteORM, cliente.id)
        if orm is None:
            orm = ClienteORM(id=cliente.id)
            self._s.add(orm)
        orm.nombre = cliente.nombre
        orm.tipo_doc = cliente.tipo_doc.value
        orm.nro_doc = cliente.nro_doc
        orm.cond_iva = cliente.cond_iva.value
        orm.tipo_persona = cliente.tipo_persona.value
        orm.forma_juridica = cliente.forma_juridica.value if cliente.forma_juridica else None
        orm.empresa_id = cliente.empresa_id
        orm.telefono = cliente.telefono
        orm.email = cliente.email
        orm.direccion = cliente.direccion
        orm.archivado_en = cliente.archivado_en


class SqlVehiculoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, vehiculo_id: UUID) -> Vehiculo | None:
        orm = self._s.get(VehiculoORM, vehiculo_id)
        return _vehiculo(orm) if orm is not None else None

    def obtener_por_patente(self, patente: str) -> Vehiculo | None:
        orm = self._s.scalar(select(VehiculoORM).where(VehiculoORM.patente == patente))
        return _vehiculo(orm) if orm is not None else None

    def listar(
        self,
        *,
        cliente_id: UUID | None = None,
        q: str | None = None,
        incluir_archivados: bool = False,
    ) -> list[Vehiculo]:
        stmt = _solo_activos(select(VehiculoORM), VehiculoORM.archivado_en, incluir_archivados)
        if cliente_id is not None:
            stmt = stmt.where(VehiculoORM.cliente_id == cliente_id)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(VehiculoORM.patente).like(patron),
                    func.lower(VehiculoORM.marca).like(patron),
                    func.lower(VehiculoORM.modelo).like(patron),
                )
            )
        return [_vehiculo(o) for o in self._s.scalars(stmt.order_by(VehiculoORM.patente))]

    def existe_patente(self, patente: str, *, excluir_id: UUID | None = None) -> bool:
        stmt = select(VehiculoORM.id).where(VehiculoORM.patente == patente)
        if excluir_id is not None:
            stmt = stmt.where(VehiculoORM.id != excluir_id)
        return self._s.scalar(stmt) is not None

    def guardar(self, vehiculo: Vehiculo) -> None:
        orm = self._s.get(VehiculoORM, vehiculo.id)
        if orm is None:
            orm = VehiculoORM(id=vehiculo.id)
            self._s.add(orm)
        orm.patente = str(vehiculo.patente)
        orm.cliente_id = vehiculo.cliente_id
        orm.marca = vehiculo.marca
        orm.modelo = vehiculo.modelo
        orm.anio = vehiculo.anio
        orm.vin = vehiculo.vin
        orm.motor = vehiculo.motor
        orm.color = vehiculo.color
        orm.km_actual = vehiculo.km_actual
        orm.archivado_en = vehiculo.archivado_en


class SqlProveedorRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, proveedor_id: UUID) -> Proveedor | None:
        orm = self._s.get(ProveedorORM, proveedor_id)
        return _proveedor(orm) if orm is not None else None

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Proveedor]:
        stmt = _solo_activos(select(ProveedorORM), ProveedorORM.archivado_en, incluir_archivados)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ProveedorORM.razon_social).like(patron),
                    ProveedorORM.cuit.like(f"%{q}%"),
                )
            )
        return [_proveedor(o) for o in self._s.scalars(stmt.order_by(ProveedorORM.razon_social))]

    def existe_cuit(self, cuit: str, *, excluir_id: UUID | None = None) -> bool:
        stmt = select(ProveedorORM.id).where(ProveedorORM.cuit == cuit)
        if excluir_id is not None:
            stmt = stmt.where(ProveedorORM.id != excluir_id)
        return self._s.scalar(stmt) is not None

    def guardar(self, proveedor: Proveedor) -> None:
        orm = self._s.get(ProveedorORM, proveedor.id)
        if orm is None:
            orm = ProveedorORM(id=proveedor.id)
            self._s.add(orm)
        orm.razon_social = proveedor.razon_social
        orm.cuit = str(proveedor.cuit)
        orm.tipo_persona = proveedor.tipo_persona.value
        orm.forma_juridica = proveedor.forma_juridica.value if proveedor.forma_juridica else None
        orm.telefono = proveedor.telefono
        orm.email = proveedor.email
        orm.cond_pago = proveedor.cond_pago
        orm.cond_iva = proveedor.cond_iva.value if proveedor.cond_iva else None
        orm.archivado_en = proveedor.archivado_en


class SqlTrabajadorRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, trabajador_id: UUID) -> Trabajador | None:
        orm = self._s.get(TrabajadorORM, trabajador_id)
        return _trabajador(orm) if orm is not None else None

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Trabajador]:
        stmt = _solo_activos(select(TrabajadorORM), TrabajadorORM.archivado_en, incluir_archivados)
        if q:
            patron = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(TrabajadorORM.nombre).like(patron),
                    func.lower(TrabajadorORM.rol).like(patron),
                )
            )
        return [_trabajador(o) for o in self._s.scalars(stmt.order_by(TrabajadorORM.nombre))]

    def guardar(self, trabajador: Trabajador) -> None:
        orm = self._s.get(TrabajadorORM, trabajador.id)
        if orm is None:
            orm = TrabajadorORM(id=trabajador.id)
            self._s.add(orm)
        orm.nombre = trabajador.nombre
        orm.rol = trabajador.rol
        orm.tipo_remuneracion = trabajador.tipo_remuneracion.value
        orm.periodicidad_pago = trabajador.periodicidad_pago.value
        orm.monto_periodo = trabajador.monto_periodo
        orm.valor_hora = trabajador.valor_hora
        orm.porcentaje_comision = trabajador.porcentaje_comision
        orm.archivado_en = trabajador.archivado_en


def _foto_vehiculo(o: FotoVehiculoORM) -> FotoVehiculo:
    return FotoVehiculo(
        id=o.id,
        archivado_en=o.archivado_en,
        vehiculo_id=o.vehiculo_id,
        archivo_path=o.archivo_path,
        nombre_original=o.nombre_original,
        content_type=o.content_type,
        autor_id=o.autor_id,
        vista=VistaFoto(o.vista),
        nota=o.nota,
        creada_en=o.creada_en,
    )


class SqlFotoVehiculoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, foto_id: UUID) -> FotoVehiculo | None:
        orm = self._s.get(FotoVehiculoORM, foto_id)
        return _foto_vehiculo(orm) if orm is not None else None

    def listar(self, vehiculo_id: UUID) -> list[FotoVehiculo]:
        stmt = (
            select(FotoVehiculoORM)
            .where(FotoVehiculoORM.vehiculo_id == vehiculo_id)
            .where(FotoVehiculoORM.archivado_en.is_(None))
            .order_by(FotoVehiculoORM.creada_en, FotoVehiculoORM.id)
        )
        return [_foto_vehiculo(o) for o in self._s.scalars(stmt)]

    def delanteras(self, vehiculo_ids: list[UUID]) -> dict[UUID, UUID]:
        stmt = (
            select(FotoVehiculoORM.vehiculo_id, FotoVehiculoORM.id)
            .where(FotoVehiculoORM.vehiculo_id.in_(vehiculo_ids))
            .where(FotoVehiculoORM.vista == VistaFoto.DELANTERA.value)
            .where(FotoVehiculoORM.archivado_en.is_(None))
        )
        return {vehiculo_id: foto_id for vehiculo_id, foto_id in self._s.execute(stmt)}

    def guardar(self, foto: FotoVehiculo) -> None:
        orm = self._s.get(FotoVehiculoORM, foto.id)
        if orm is None:
            orm = FotoVehiculoORM(id=foto.id)
            self._s.add(orm)
        orm.vehiculo_id = foto.vehiculo_id
        orm.archivo_path = foto.archivo_path
        orm.nombre_original = foto.nombre_original
        orm.content_type = foto.content_type
        orm.autor_id = foto.autor_id
        orm.vista = foto.vista.value
        orm.nota = foto.nota
        orm.creada_en = foto.creada_en
        orm.archivado_en = foto.archivado_en
        self._s.flush()


class SqlRubroRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, rubro_id: UUID) -> Rubro | None:
        orm = self._s.get(RubroORM, rubro_id)
        return _rubro(orm) if orm is not None else None

    def listar(self, *, incluir_archivados: bool = False) -> list[Rubro]:
        stmt = _solo_activos(select(RubroORM), RubroORM.archivado_en, incluir_archivados)
        return [_rubro(o) for o in self._s.scalars(stmt.order_by(RubroORM.nombre))]

    def guardar(self, rubro: Rubro) -> None:
        orm = self._s.get(RubroORM, rubro.id)
        if orm is None:
            orm = RubroORM(id=rubro.id)
            self._s.add(orm)
        orm.nombre = rubro.nombre
        orm.tipo = rubro.tipo
        orm.archivado_en = rubro.archivado_en


class SqlTipoPagoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, tipo_pago_id: UUID) -> TipoPago | None:
        orm = self._s.get(TipoPagoORM, tipo_pago_id)
        return _tipo_pago(orm) if orm is not None else None

    def listar(self, *, incluir_archivados: bool = False) -> list[TipoPago]:
        stmt = _solo_activos(select(TipoPagoORM), TipoPagoORM.archivado_en, incluir_archivados)
        return [_tipo_pago(o) for o in self._s.scalars(stmt.order_by(TipoPagoORM.nombre))]

    def guardar(self, tipo_pago: TipoPago) -> None:
        orm = self._s.get(TipoPagoORM, tipo_pago.id)
        if orm is None:
            orm = TipoPagoORM(id=tipo_pago.id)
            self._s.add(orm)
        orm.nombre = tipo_pago.nombre
        orm.schema_extra = dict(tipo_pago.schema_extra)
        orm.archivado_en = tipo_pago.archivado_en
