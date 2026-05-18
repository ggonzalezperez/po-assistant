from unittest.mock import MagicMock, patch
from po_assistant.workflow.qa import append_section, _build_section_header


def _make_issue(description: str) -> MagicMock:
    issue = MagicMock()
    issue.description = description
    return issue


def test_append_section_empty_description():
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue("")

    append_section(jira, "FP-1", "TRIAGE", "Decisión: entra a Discovery.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    assert "description" in fields
    adf = fields["description"]
    import json
    adf_text = json.dumps(adf, ensure_ascii=False)
    assert "TRIAGE" in adf_text
    assert "Decisión: entra a Discovery." in adf_text


def test_append_section_adds_to_existing():
    existing = "## INTAKE — 2026-05-18\n\nPetición original aquí."
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue(existing)

    append_section(jira, "FP-1", "TRIAGE", "Entra a Discovery.")

    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf = fields["description"]
    import json
    adf_text = json.dumps(adf)
    assert "INTAKE" in adf_text
    assert "TRIAGE" in adf_text


def test_build_section_header_format():
    header = _build_section_header("DISCOVERY", "2026-05-20")
    assert header == "## DISCOVERY — 2026-05-20"


def test_append_section_date_in_header():
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue("")

    with patch("po_assistant.workflow.qa.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-05-20"
        append_section(jira, "FP-1", "DISCOVERY", "Ficha aquí.")

    call_args = jira.update_issue.call_args
    adf_text = str(call_args)
    assert "2026-05-20" in adf_text
