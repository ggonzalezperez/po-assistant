"""Tests for urgencia workflow parsing and description building."""
import pytest
from po_assistant.models import UrgenciaResult


def test_urgencia_result_instantiation():
    r = UrgenciaResult(
        titulo="[CRM] Resolver fallo en envío de pedidos",
        descripcion="Los pedidos no llegan al almacén.",
        prioridad_sugerida="Alta",
        razon_prioridad="100% de pedidos bloqueados.",
        impacto="Almacén sin pedidos desde las 09:00h.",
        causa_probable="Posible fallo en el servicio de mensajería.",
        accion_correctiva="Reiniciar el servicio de mensajería.",
        rollback="Revertir el último deploy del módulo de pedidos.",
        checks_verificacion=["Un pedido de prueba llega al almacén", "Sin errores en log"],
    )
    assert r.titulo == "[CRM] Resolver fallo en envío de pedidos"
    assert r.prioridad_sugerida == "Alta"
    assert len(r.checks_verificacion) == 2
