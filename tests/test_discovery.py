from po_assistant.workflow.discovery import _build_answers_text, _extract_intake_text


def test_build_answers_text_all_fields():
    answers = {
        "problema_real": "Los agentes no encuentran cómo cancelar una reserva.",
        "frecuencia": "10-15 veces al día en tiendas grandes.",
        "usuario_directo": "Agente comercial de tienda.",
        "solicitante": "María Ruiz, Responsable de operaciones.",
        "validador_uat": "Luis Pérez, encargado de tienda piloto.",
        "situacion_actual": "El agente navega por tres menús distintos.",
        "que_duele": "Pierde tiempo y llama a soporte.",
        "por_que_importa": "Reduce carga del soporte y mejora NPS agentes.",
        "consecuencia": "Seguirá habiendo llamadas innecesarias al soporte.",
        "restricciones": "No puede tocar el módulo de contratos.",
        "riesgos": "Podría afectar al flujo de cancelación si hay errores.",
    }
    text = _build_answers_text(answers)
    assert "Los agentes no encuentran" in text
    assert "María Ruiz" in text
    assert "10-15 veces" in text


def test_extract_intake_text_trims_to_800():
    long_text = "a" * 1500
    result = _extract_intake_text(long_text)
    assert len(result) <= 800


def test_extract_intake_text_short_passthrough():
    short_text = "Petición corta."
    result = _extract_intake_text(short_text)
    assert result == short_text


def test_build_answers_text_missing_fields_show_placeholder():
    result = _build_answers_text({})
    assert result.count("[sin respuesta]") == 11
