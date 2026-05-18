"""Tests for DoR Gate parsing and evaluation logic."""

from po_assistant.models import (
    DOR_CRITICAL_BLOCKS, DOR_BLOCK_NAMES, DorBlockResult, DorGateResult
)
from po_assistant.workflow.dor_gate import _parse_result


def _all_pass_data(overrides: dict | None = None) -> dict:
    bloques = [{"numero": i, "cumple": True, "gap": None, "accion": None} for i in range(1, 13)]
    if overrides:
        for b in bloques:
            if b["numero"] in overrides:
                b.update(overrides[b["numero"]])
    return {
        "bloques": bloques,
        "score": sum(1 for b in bloques if b["cumple"]),
        "bloques_fallidos": [b["numero"] for b in bloques if not b["cumple"]],
        "critico_fallido": any(
            b["numero"] in DOR_CRITICAL_BLOCKS for b in bloques if not b["cumple"]
        ),
    }


def test_all_blocks_pass():
    result = _parse_result(_all_pass_data())
    assert result.score == 12
    assert result.pasa is True
    assert result.critico_fallido is False
    assert result.bloques_fallidos == []


def test_one_non_critical_fails():
    # Block 2 is non-critical: score 11, no critical fail → should PASS
    data = _all_pass_data({2: {"cumple": False, "gap": "Falta el rol", "accion": "Añadir rol"}})
    result = _parse_result(data)
    assert result.score == 11
    assert result.pasa is True
    assert result.critico_fallido is False
    assert 2 in result.bloques_fallidos


def test_two_non_critical_fail():
    # Score 10, no critical fail → should FAIL (< 11)
    data = _all_pass_data({
        2: {"cumple": False, "gap": "Gap B2", "accion": "Fix B2"},
        4: {"cumple": False, "gap": "Gap B4", "accion": "Fix B4"},
    })
    result = _parse_result(data)
    assert result.score == 10
    assert result.pasa is False
    assert result.critico_fallido is False


def test_critical_block_fails_with_high_score():
    # Block 1 is critical. Score 11 but critical fails → KO
    data = _all_pass_data({1: {"cumple": False, "gap": "No describe problema", "accion": "Reformular"}})
    result = _parse_result(data)
    assert result.score == 11
    assert result.pasa is False
    assert result.critico_fallido is True
    assert 1 in result.bloques_fallidos


def test_critical_blocks_are_correctly_identified():
    for num in DOR_CRITICAL_BLOCKS:
        data = _all_pass_data({num: {"cumple": False, "gap": "gap", "accion": "fix"}})
        result = _parse_result(data)
        assert result.critico_fallido is True, f"Block {num} should be critical"


def test_block_names_completeness():
    assert len(DOR_BLOCK_NAMES) == 12
    for i in range(1, 13):
        assert i in DOR_BLOCK_NAMES


def test_comment_jira_ok():
    result = _parse_result(_all_pass_data())
    comment = result.comentario_jira()
    assert "DOR GATE OK" in comment
    assert "12/12" in comment


def test_comment_jira_ko():
    data = _all_pass_data({
        1: {"cumple": False, "gap": "Formulado como solución", "accion": "Reformular el problema"},
        9: {"cumple": False, "gap": "Falta happy path", "accion": "Añadir casuística"},
    })
    result = _parse_result(data)
    comment = result.comentario_jira()
    assert "DOR GATE KO" in comment
    assert "DEFINICIÓN" in comment
    assert "Formulado como solución" in comment
