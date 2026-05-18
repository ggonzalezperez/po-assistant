from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Sign-off Stakeholder — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a generar el documento de Sign-off del alcance "
        f"para que el stakeholder lo confirme.[/{C_MUTED}]\n"
    )

    firmante = ask("¿Quién firma el sign-off? (nombre, rol)", "Ej: María Ruiz, Responsable de Operaciones")
    fecha_discovery = ask("¿Cuándo fue la reunión de discovery?", "Ej: 2026-05-15")
    funcionalidades = ask_multiline(
        "¿Qué funcionalidades entran en el alcance que firmamos?",
        "Una por línea"
    )
    exclusiones = ask_multiline(
        "¿Qué exclusiones explícitas hay? (qué NO entra)",
        "Una por línea. Si no hay, escribe 'ninguna'"
    )
    mvp = ask("¿Cuál es el MVP acordado? (unidad mínima de valor)")
    validador_uat = ask("¿Quién es el validador de UAT y cuándo está disponible?")
    tiene_fecha = ask("¿Hay una fecha objetivo? (s/n)", "")
    fecha_objetivo = ""
    if tiene_fecha.strip().lower() in ("s", "si", "sí", "y", "yes"):
        fecha_objetivo = ask("¿Cuál es la fecha objetivo?", "Ej: 2026-06-30")
    limitaciones = ask(
        "¿El stakeholder declara alguna limitación por su parte?",
        "Ej: no disponible en julio. Si no hay, escribe 'ninguna'"
    )

    answers_text = "\n".join([
        f"Firmante: {firmante}",
        f"Fecha reunión discovery: {fecha_discovery}",
        f"Funcionalidades acordadas:\n{funcionalidades}",
        f"Exclusiones explícitas:\n{exclusiones}",
        f"MVP: {mvp}",
        f"Validador UAT: {validador_uat}",
        f"Fecha objetivo: {fecha_objetivo if fecha_objetivo else 'No aplica'}",
        f"Limitaciones del stakeholder: {limitaciones}",
    ])

    signoff_md = ai.call(
        "signoff_doc.md",
        {
            "USER_INPUT": "Genera el documento de sign-off.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "TICKET_TEXT": issue.description[:600] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "FIRMANTE": firmante,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Sign-off")
    for line in signoff_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()
    console.print(f"  [{C_MUTED}]Comparte este documento con el stakeholder para que lo confirme en Jira.[/{C_MUTED}]\n")

    if not confirm("¿Guardar el Sign-off en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "SIGN-OFF SH", signoff_md)
    jira.transition_po_state(issue_key, POEstado.SIGN_OFF_SH)
    jira.add_comment(
        issue_key,
        f"## Sign-off pendiente de confirmación\n\n"
        f"Documento generado. Stakeholder: **{firmante}**.\n\n"
        f"_Pendiente: {firmante} debe confirmar en un comentario de este ticket._\n\n"
        f"Siguiente: `po dor-gate {issue_key}` (tras recibir confirmación)"
    )

    notify_success(
        f"Sign-off guardado en {issue_key}. Estado → SIGN-OFF SH.",
        f"Comparte la URL del ticket con {firmante} para su confirmación.",
    )
    console.print()
