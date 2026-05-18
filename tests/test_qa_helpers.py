import json
from unittest.mock import MagicMock, patch
from po_assistant.workflow.qa import append_section, _build_section_header, ask_multiline


def _empty_adf() -> dict:
    return {"type": "doc", "version": 1, "content": []}


def _adf_with_heading(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "heading", "attrs": {"level": 2},
             "content": [{"type": "text", "text": text}]},
        ],
    }


def test_append_section_empty_description():
    jira = MagicMock()
    jira.get_description_adf.return_value = _empty_adf()

    append_section(jira, "FP-1", "TRIAGE", "Decisión: entra a Discovery.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf_text = json.dumps(fields["description"], ensure_ascii=False)
    assert "TRIAGE" in adf_text
    assert "Decisión: entra a Discovery." in adf_text


def test_append_section_adds_to_existing():
    jira = MagicMock()
    jira.get_description_adf.return_value = _adf_with_heading("INTAKE — 2026-05-18")

    append_section(jira, "FP-1", "TRIAGE", "Entra a Discovery.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf_text = json.dumps(fields["description"])
    assert "INTAKE" in adf_text
    assert "TRIAGE" in adf_text
    assert '"rule"' in adf_text  # separator between sections


def test_append_section_no_separator_when_empty():
    jira = MagicMock()
    jira.get_description_adf.return_value = _empty_adf()

    append_section(jira, "FP-1", "INTAKE", "Primera sección.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf_text = json.dumps(fields["description"])
    assert '"rule"' not in adf_text  # no separator when description was empty


def test_build_section_header_format():
    header = _build_section_header("DISCOVERY", "2026-05-20")
    assert header == "## DISCOVERY — 2026-05-20"


def test_append_section_date_in_header():
    jira = MagicMock()
    jira.get_description_adf.return_value = _empty_adf()

    with patch("po_assistant.workflow.qa.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-05-20"
        append_section(jira, "FP-1", "DISCOVERY", "Ficha aquí.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf_text = json.dumps(fields["description"], ensure_ascii=False)
    assert "2026-05-20" in adf_text


def test_ask_multiline_joins_lines_until_terminator():
    inputs = iter(["línea uno", "línea dos", ";;"])
    with patch("builtins.input", side_effect=lambda: next(inputs)):
        with patch("po_assistant.workflow.qa.console"):
            result = ask_multiline("¿Cuéntame?")
    assert result == "línea uno\nlínea dos"


def test_ask_multiline_allows_blank_lines_within_input():
    inputs = iter(["párrafo uno", "", "párrafo dos", ";;"])
    with patch("builtins.input", side_effect=lambda: next(inputs)):
        with patch("po_assistant.workflow.qa.console"):
            result = ask_multiline("¿Cuéntame?")
    assert result == "párrafo uno\n\npárrafo dos"
