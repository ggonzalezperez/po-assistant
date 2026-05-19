from pathlib import Path

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, hu_preview, notify_success, notify_warning,
    confirm, C_MUTED, C_ACCENT, C_WARNING,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import append_section


def run(
    issue_key: str,
    ai: AIClient,
    jira: JiraClient,
    config: Config,
    notes_file: Path | None = None,
) -> None:
    """
    Generates a complete HU draft from issue content or a notes file.
    Updates Jira description and transitions to DEFINICIÓN.
    """
    section_rule(f"Generando HU — {issue_key}")

    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")

    if notes_file:
        if not notes_file.exists():
            console.print(f"  [{C_WARNING}]Archivo no encontrado: {notes_file}[/{C_WARNING}]\n")
            raise typer.Exit(1)
        discovery_notes = notes_file.read_text(encoding="utf-8")
        console.print(f"  [{C_MUTED}]Usando notas desde {notes_file}[/{C_MUTED}]")
    else:
        discovery_notes = f"Título: {issue.summary}\n\n{issue.description}"
        console.print(f"  [{C_MUTED}]Usando la descripción actual del issue[/{C_MUTED}]")

    if len(discovery_notes.strip()) < 50:
        notify_warning(
            "El issue tiene poca información.",
            f"Considera hacer el discovery primero o usa [{C_ACCENT}]--notes archivo.txt[/{C_ACCENT}].",
        )
        if not confirm("¿Continuar de todas formas?", default=False):
            raise typer.Abort()

    console.print()
    hu_text = ai.call(
        "definition_draft_hu.md",
        {
            "USER_INPUT": "Genera la HU completa según las instrucciones del sistema.",
            "TITULO": issue.summary,
            "DISCOVERY_NOTES": discovery_notes,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=6000,
    )

    hu_preview(hu_text, issue_key)

    console.print(
        f"  [{C_MUTED}]Revisa el Bloque 6 — añade tu nombre como revisor humano antes de guardar.[/{C_MUTED}]\n"
    )

    if not confirm("¿Guardar esta HU en Jira?", default=True):
        _offer_local_save(issue_key, hu_text)
        raise typer.Abort()

    append_section(jira, issue_key, "DEFINICION", hu_text)
    jira.transition_po_state(issue_key, POEstado.DEFINICION)

    if config.fields.ia_asistida:
        jira.update_issue(issue_key, {config.fields.ia_asistida: "Sí"})

    comment = (
        "## HU borrador — po-assistant\n\n"
        f"- Modelo: `{config.claude_model}`\n"
        "- Prompt: `po-assistant/prompts/definition_draft_hu.md`\n"
        "- **Revisor humano: [PENDIENTE — añade tu nombre en Bloque 6]**\n\n"
        f"Siguiente: `po dor-gate {issue_key}`"
    )
    jira.add_comment(issue_key, comment)

    notify_success(
        f"HU guardada en {issue_key}. Estado → DEFINICIÓN.",
        f"Siguiente: [bold {C_ACCENT}]po dor-gate {issue_key}[/bold {C_ACCENT}]",
    )
    console.print()


def _offer_local_save(issue_key: str, hu_text: str) -> None:
    filename = f"{issue_key}-hu-borrador.md"
    if confirm(f"¿Guardar localmente como {filename}?", default=True):
        Path(filename).write_text(hu_text, encoding="utf-8")
        console.print(f"  [{C_MUTED}]Guardado en {filename}[/{C_MUTED}]\n")
