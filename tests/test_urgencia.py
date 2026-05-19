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


def test_urgencia_card_importable():
    from po_assistant.display import urgencia_card
    assert callable(urgencia_card)


from po_assistant.workflow.urgencia import _parse_result, _build_description


def _sample_data(**overrides) -> dict:
    base = {
        "titulo": "[CRM] Resolver fallo en envío de pedidos al almacén",
        "descripcion": "Los pedidos no se están enviando al almacén desde las 09:00.",
        "prioridad_sugerida": "Alta",
        "razon_prioridad": "100% de pedidos bloqueados — operaciones detenidas.",
        "impacto": "100% de los pedidos bloqueados desde las 09:00h. Almacén sin trabajo.",
        "causa_probable": "Posible fallo en la integración con el servicio de mensajería del almacén.",
        "accion_correctiva": "Revisar logs del servicio de mensajería y reiniciar si necesario.",
        "rollback": "Revertir el último deploy en el módulo de pedidos.",
        "checks_verificacion": [
            "Un pedido de prueba llega al almacén sin errores",
            "El log de mensajería no muestra errores de conexión",
        ],
    }
    base.update(overrides)
    return base


def test_parse_result_complete():
    result = _parse_result(_sample_data())
    assert isinstance(result, UrgenciaResult)
    assert result.titulo == "[CRM] Resolver fallo en envío de pedidos al almacén"
    assert result.prioridad_sugerida == "Alta"
    assert len(result.checks_verificacion) == 2
    assert "Un pedido de prueba llega al almacén sin errores" in result.checks_verificacion


def test_parse_result_missing_optional_fields():
    """Campos opcionales deben tener default vacío, no KeyError."""
    result = _parse_result({"titulo": "T", "descripcion": "D"})
    assert result.impacto == ""
    assert result.causa_probable == ""
    assert result.rollback == ""
    assert result.checks_verificacion == []
    assert result.prioridad_sugerida == "Alta"


def test_build_description_contains_key_sections():
    result = _parse_result(_sample_data())
    desc = _build_description(result, "texto original del PO", "María Ruiz", "Carlos López", "2 horas")
    assert "## URGENCIA" in desc
    assert "texto original del PO" in desc
    assert "María Ruiz" in desc
    assert "Carlos López" in desc
    assert "2 horas" in desc
    assert "Un pedido de prueba llega al almacén sin errores" in desc
    assert "Flujo abreviado" in desc


def test_build_description_all_checks_present():
    checks = ["check_a", "check_b", "check_c"]
    result = _parse_result(_sample_data(checks_verificacion=checks))
    desc = _build_description(result, "t", "a", "d", "e")
    for check in checks:
        assert check in desc


def test_build_description_empty_checks():
    """Lista de checks vacía — descripción válida sin errores."""
    result = _parse_result(_sample_data(checks_verificacion=[]))
    desc = _build_description(result, "t", "a", "d", "e")
    assert "## URGENCIA" in desc
    assert "Flujo abreviado" in desc


def test_build_description_has_date_header():
    result = _parse_result(_sample_data())
    desc = _build_description(result, "t", "a", "d", "e")
    import re
    assert re.search(r"## URGENCIA — \d{4}-\d{2}-\d{2}", desc)
