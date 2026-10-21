from __future__ import annotations

from uuid import UUID

from taller.domain.entities.catalogos import Rubro, TipoPago
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.empresa import Empresa
from taller.domain.entities.foto_vehiculo import FotoVehiculo
from taller.domain.entities.proveedor import Proveedor
from taller.domain.entities.trabajador import Trabajador
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import VistaFoto


class _FakeBase:
    def __init__(self, items: list | None = None) -> None:
        self._items: dict[UUID, object] = {i.id: i for i in (items or [])}  # type: ignore[attr-defined]

    def _todos(self, incluir_archivados: bool) -> list:  # type: ignore[type-arg]
        valores = list(self._items.values())
        if incluir_archivados:
            return valores
        return [x for x in valores if getattr(x, "activo", True)]


class FakeEmpresaRepository(_FakeBase):
    def obtener(self, empresa_id: UUID) -> Empresa | None:
        return self._items.get(empresa_id)  # type: ignore[return-value]

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Empresa]:
        items = self._todos(incluir_archivados)
        if q:
            items = [
                e
                for e in items
                if q.lower() in e.razon_social.lower() or q in str(e.cuit)  # type: ignore[attr-defined]
            ]
        return items  # type: ignore[return-value]

    def existe_cuit(self, cuit: str, *, excluir_id: UUID | None = None) -> bool:
        return any(
            str(e.cuit) == cuit and e.id != excluir_id  # type: ignore[attr-defined]
            for e in self._items.values()
        )

    def guardar(self, empresa: Empresa) -> None:
        self._items[empresa.id] = empresa


class FakeClienteRepository(_FakeBase):
    def obtener(self, cliente_id: UUID) -> Cliente | None:
        return self._items.get(cliente_id)  # type: ignore[return-value]

    def listar(
        self,
        *,
        q: str | None = None,
        empresa_id: UUID | None = None,
        incluir_archivados: bool = False,
    ) -> list[Cliente]:
        items = self._todos(incluir_archivados)
        if empresa_id is not None:
            items = [c for c in items if c.empresa_id == empresa_id]  # type: ignore[attr-defined]
        if q:
            items = [
                c
                for c in items
                if q.lower() in c.nombre.lower() or q in c.nro_doc  # type: ignore[attr-defined]
            ]
        return items  # type: ignore[return-value]

    def guardar(self, cliente: Cliente) -> None:
        self._items[cliente.id] = cliente


class FakeVehiculoRepository(_FakeBase):
    def obtener(self, vehiculo_id: UUID) -> Vehiculo | None:
        return self._items.get(vehiculo_id)  # type: ignore[return-value]

    def obtener_por_patente(self, patente: str) -> Vehiculo | None:
        for v in self._items.values():
            if str(v.patente) == patente:  # type: ignore[attr-defined]
                return v  # type: ignore[return-value]
        return None

    def listar(
        self,
        *,
        cliente_id: UUID | None = None,
        q: str | None = None,
        incluir_archivados: bool = False,
    ) -> list[Vehiculo]:
        items = self._todos(incluir_archivados)
        if cliente_id is not None:
            items = [v for v in items if v.cliente_id == cliente_id]  # type: ignore[attr-defined]
        if q:
            items = [
                v
                for v in items
                if q.lower() in str(v.patente).lower()  # type: ignore[attr-defined]
            ]
        return items  # type: ignore[return-value]

    def existe_patente(self, patente: str, *, excluir_id: UUID | None = None) -> bool:
        return any(
            str(v.patente) == patente and v.id != excluir_id  # type: ignore[attr-defined]
            for v in self._items.values()
        )

    def guardar(self, vehiculo: Vehiculo) -> None:
        self._items[vehiculo.id] = vehiculo


class FakeFotoVehiculoRepository(_FakeBase):
    def obtener(self, foto_id: UUID) -> FotoVehiculo | None:
        return self._items.get(foto_id)  # type: ignore[return-value]

    def listar(self, vehiculo_id: UUID) -> list[FotoVehiculo]:
        return [
            f
            for f in self._todos(incluir_archivados=False)
            if f.vehiculo_id == vehiculo_id  # type: ignore[attr-defined]
        ]

    def delanteras(self, vehiculo_ids: list[UUID]) -> dict[UUID, UUID]:
        return {
            f.vehiculo_id: f.id  # type: ignore[attr-defined]
            for f in self._todos(incluir_archivados=False)
            if f.vehiculo_id in vehiculo_ids  # type: ignore[attr-defined]
            and f.vista is VistaFoto.DELANTERA  # type: ignore[attr-defined]
        }

    def guardar(self, foto: FotoVehiculo) -> None:
        self._items[foto.id] = foto


class FakeProveedorRepository(_FakeBase):
    def obtener(self, proveedor_id: UUID) -> Proveedor | None:
        return self._items.get(proveedor_id)  # type: ignore[return-value]

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Proveedor]:
        items = self._todos(incluir_archivados)
        if q:
            items = [
                p
                for p in items
                if q.lower() in p.razon_social.lower() or q in str(p.cuit)  # type: ignore[attr-defined]
            ]
        return items  # type: ignore[return-value]

    def existe_cuit(self, cuit: str, *, excluir_id: UUID | None = None) -> bool:
        return any(
            str(p.cuit) == cuit and p.id != excluir_id  # type: ignore[attr-defined]
            for p in self._items.values()
        )

    def guardar(self, proveedor: Proveedor) -> None:
        self._items[proveedor.id] = proveedor


class FakeTrabajadorRepository(_FakeBase):
    def obtener(self, trabajador_id: UUID) -> Trabajador | None:
        return self._items.get(trabajador_id)  # type: ignore[return-value]

    def listar(self, *, q: str | None = None, incluir_archivados: bool = False) -> list[Trabajador]:
        items = self._todos(incluir_archivados)
        if q:
            items = [
                t
                for t in items
                if q.lower() in t.nombre.lower() or q.lower() in t.rol.lower()  # type: ignore[attr-defined]
            ]
        return items  # type: ignore[return-value]

    def guardar(self, trabajador: Trabajador) -> None:
        self._items[trabajador.id] = trabajador


class FakeRubroRepository(_FakeBase):
    def obtener(self, rubro_id: UUID) -> Rubro | None:
        return self._items.get(rubro_id)  # type: ignore[return-value]

    def listar(self, *, incluir_archivados: bool = False) -> list[Rubro]:
        return self._todos(incluir_archivados)  # type: ignore[return-value]

    def guardar(self, rubro: Rubro) -> None:
        self._items[rubro.id] = rubro


class FakeTipoPagoRepository(_FakeBase):
    def obtener(self, tipo_pago_id: UUID) -> TipoPago | None:
        return self._items.get(tipo_pago_id)  # type: ignore[return-value]

    def listar(self, *, incluir_archivados: bool = False) -> list[TipoPago]:
        return self._todos(incluir_archivados)  # type: ignore[return-value]

    def guardar(self, tipo_pago: TipoPago) -> None:
        self._items[tipo_pago.id] = tipo_pago
