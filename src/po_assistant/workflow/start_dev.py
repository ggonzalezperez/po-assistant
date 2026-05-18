import typer

from ..config import Config
from ..display import console, section_rule, notify_success, confirm, C_MUTED, C_ACCENT
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask_multiline, append_section


def run(issue_key: str, jira: JiraClient, config: Config) -> None:
    section_rule(f"Arrancar desarrollo — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")

    leads = ask_multiline(
        "¿Quiénes lideran el desarrollo?",
        "Uno por línea: Nombre — Rol. Ej: Carlos López — Backend"
    )

    section_content = f"**Leads:** {leads}\n\n*(HU completa en la sección DEFINICION de esta tarjeta)*"

    if not confirm("¿Mover a EN DESARROLLO?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "EN DESARROLLO", section_content)
    jira.transition_po_state(issue_key, POEstado.EN_DESARROLLO)

    notify_success(
        f"HU {issue_key} en marcha. Estado → EN DESARROLLO.",
        f"Siguiente cuando termine dev: [bold {C_ACCENT}]po uat {issue_key}[/bold {C_ACCENT}]",
    )
    console.print()
