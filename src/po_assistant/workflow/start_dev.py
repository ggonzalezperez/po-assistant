import typer

from ..config import Config
from ..display import console, section_rule, notify_success, confirm, C_MUTED, C_ACCENT
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, append_section


def run(issue_key: str, jira: JiraClient, config: Config) -> None:
    section_rule(f"Arrancar desarrollo — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a mover la HU a EN DESARROLLO y dejar constancia en Jira.[/{C_MUTED}]\n"
    )

    sprint = ask("¿En qué sprint entra?", "Ej: Sprint 42 · Q2-2026. Si no aplica: 'flujo continuo'")
    dev_lead = ask("¿Quién lidera el desarrollo?", "Nombre — Rol. Ej: Carlos López — Backend")
    equipo = ask_multiline(
        "¿Quiénes más participan en el desarrollo?",
        "Uno por línea: Nombre — Rol. Si no hay más: escribe 'solo el lead'"
    )
    notas = ask_multiline(
        "¿Hay algo que el equipo debe tener en cuenta al arrancar?",
        "Ej: dependencias, riesgos, decisiones técnicas previas. Si no hay: escribe 'ninguno'"
    )

    lines = [
        f"- **Sprint:** {sprint}",
        f"- **Lead de desarrollo:** {dev_lead}",
    ]
    if equipo.strip().lower() not in ("solo el lead", ""):
        lines.append(f"- **Equipo:** {equipo}")
    if notas.strip().lower() not in ("ninguno", ""):
        lines.append(f"\n**Notas de arranque:**\n\n{notas}")

    section_content = "\n".join(lines)

    if not confirm("¿Guardar el inicio de desarrollo en Jira y mover a EN DESARROLLO?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "EN DESARROLLO", section_content)
    jira.transition_po_state(issue_key, POEstado.EN_DESARROLLO)

    jira.add_comment(
        issue_key,
        f"## Desarrollo arrancado\n\n"
        f"- Sprint: {sprint}\n"
        f"- Lead: {dev_lead}\n\n"
        f"Siguiente: `po uat {issue_key}` (cuando dev termine y esté listo para validación)"
    )

    notify_success(
        f"HU {issue_key} en marcha. Estado → EN DESARROLLO.",
        f"Siguiente cuando termine dev: [bold {C_ACCENT}]po uat {issue_key}[/bold {C_ACCENT}]",
    )
    console.print()
