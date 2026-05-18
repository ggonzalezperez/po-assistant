from po_assistant.workflow.triage import _decision_label, _build_answers_text


def test_decision_label_discovery():
    assert _decision_label(4) == "Entra a Discovery"


def test_decision_label_aplazado():
    assert _decision_label(5) == "Aplazado — Comité Semanal"


def test_decision_label_incidencia():
    assert _decision_label(1) == "Redirigido — Incidencia técnica"


def test_decision_label_urgencia():
    assert _decision_label(2) == "Urgencia — Vía urgencias"


def test_decision_label_devuelto():
    assert _decision_label(3) == "Devuelto — Clarificación necesaria"


def test_build_answers_text():
    answers = {
        "decision": 4,
        "justificacion": "La petición tiene un problema claro.",
        "asignado_a": "Ana García",
    }
    text = _build_answers_text(answers)
    assert "Entra a Discovery" in text
    assert "La petición tiene un problema claro." in text
    assert "Ana García" in text
