from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..ai_client import AIClient
from ..config import Config
from ..jira_client import JiraClient
from ..models import POEstado

console = Console()


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config,
        notes_file: Path | None = None) -> None:
    """
    Generates a complete HU draft from the issue's current content (or from a notes file).
    Updates the Jira issue description and transitions to DEFINICIÓN.
    """
    console.print(f"\n[bold]Cargando issue {issue_key}…[/bold]")
    issue = jira.get_issue(issue_key)

    if notes_file:
        if not notes_file.exists():
            console.print(f"[red]Archivo no encontrado: {notes_file}[/red]")
            raise typer.Exit(1)
        discovery_notes = notes_file.read_text(encoding="utf-8")
        console.print(f"[dim]Usando notas desde {notes_file}[/dim]")
    else:
        discovery_notes = f"Título: {issue.summary}\n\n{issue.description}"
        console.print(f"[dim]Usando la descripción actual del issue[/dim]")

    if len(discovery_notes.strip()) < 50:
        console.print(
            "[yellow]⚠️  El issue tiene muy poca información. "
            "Considera hacer el discovery primero o pasa las notas con --notes.[/yellow]"
        )
        if not typer.confirm("¿Continuar de todas formas?", default=False):
            raise typer.Abort()

    console.print("\n[bold]Generando HU con IA…[/bold]")
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

    console.print("\n")
    console.print(Panel(
        Syntax(hu_text, "markdown", theme="monokai", word_wrap=True),
        title=f"[bold]HU Borrador — {issue_key}[/bold]",
        border_style="green",
        expand=False,
    ))

    console.print("\n[yellow]Revisa la HU antes de guardarla.[/yellow]")
    console.print("El campo [bold]'Revisor humano'[/bold] (Bloque 6) debe rellenarse con tu nombre.\n")

    if not typer.confirm("¿Guardar esta HU en Jira?", default=True):
        _offer_local_save(issue_key, hu_text)
        raise typer.Abort()

    jira.update_issue(issue_key, {"description": _build_adf_from_hu(hu_text, jira)})
    jira.transition_po_state(issue_key, POEstado.DEFINICION)

    comment = (
        f"## HU borrador generada con po-assistant\n\n"
        f"- Modelo: {config.claude_model}\n"
        f"- Prompt: `po-assistant/prompts/definition_draft_hu.md`\n"
        f"- **Revisor humano: [PENDIENTE — el PO debe añadir su nombre en Bloque 6]**\n\n"
        f"Siguiente paso: `po dor-gate {issue_key}`"
    )
    jira.add_comment(issue_key, comment)

    console.print(f"\n[bold green]✅ HU guardada en {issue_key}. Estado → DEFINICIÓN[/bold green]")
    console.print(f"Siguiente: [bold]po dor-gate {issue_key}[/bold]\n")


def _build_adf_from_hu(hu_text: str, jira: JiraClient) -> dict:
    from ..jira_client import md_to_adf
    return md_to_adf(hu_text)


def _offer_local_save(issue_key: str, hu_text: str) -> None:
    filename = f"{issue_key}-hu-borrador.md"
    if typer.confirm(f"¿Guardar localmente como {filename}?", default=True):
        Path(filename).write_text(hu_text, encoding="utf-8")
        console.print(f"[dim]Guardado en {filename}[/dim]")
