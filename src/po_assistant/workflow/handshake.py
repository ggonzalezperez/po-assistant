from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, ask_choice, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Handshake — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a levantar el Acta de Handshake entre PO y Desarrollo.[/{C_MUTED}]\n"
    )

    asistentes = ask_multiline(
        "¿Quiénes asistieron al Handshake?",
        "Una persona por línea: Nombre — Rol"
    )
    dor_score = ask("¿Cuál fue el score del DoR Gate?", "Ej: 11/12")
    dudas = ask_multiline(
        "¿Qué dudas planteó desarrollo y cómo se respondieron?",
        "Formato: Pregunta | Respuesta. Una por línea. Si no hubo: escribe 'ninguna'"
    )
    supuestos = ask_multiline(
        "¿Qué supuestos se validaron?",
        "Uno por línea. Si no hubo: escribe 'ninguno'"
    )
    riesgos_tecnicos = ask(
        "¿Qué riesgos técnicos se identificaron?",
        "Ej: 'integración con JATO puede dar problemas de latencia'. Si no hay: 'ninguno'"
    )
    estimacion = ask("¿Cuál es la estimación inicial?", "Ej: 5 puntos / 3 días")
    dependencias = ask(
        "¿Hay dependencias confirmadas (FE, BE, Data, UX, externas)?",
        "Si no hay: 'ninguna'"
    )

    decision = ask_choice(
        "¿Cuál es la decisión del Handshake?",
        [
            ("OK para arrancar dev", "El equipo tiene todo lo necesario para empezar"),
            ("Vuelve a Definición", "Hay gaps que necesitan resolverse primero"),
        ]
    )

    gaps_def = ""
    if decision == 2:
        gaps_def = ask_multiline("¿Cuáles son los gaps que impiden arrancar?", "Uno por línea")

    answers_text = "\n".join(filter(None, [
        f"Asistentes:\n{asistentes}",
        f"DoR Gate previo: {dor_score}",
        f"Dudas y respuestas:\n{dudas}",
        f"Supuestos validados:\n{supuestos}",
        f"Riesgos técnicos: {riesgos_tecnicos}",
        f"Estimación: {estimacion}",
        f"Dependencias: {dependencias}",
        f"Decisión: {'OK para arrancar dev' if decision == 1 else 'Vuelve a Definición'}",
        f"Gaps:\n{gaps_def}" if gaps_def else "",
    ]))

    acta_md = ai.call(
        "handshake_acta.md",
        {
            "USER_INPUT": "Genera el acta de handshake.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "TICKET_TEXT": issue.description[:600] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Acta de Handshake")
    for line in acta_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Acta de Handshake en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "HANDSHAKE", acta_md)
    jira.transition_po_state(issue_key, POEstado.HANDSHAKE)

    if decision == 1:
        jira.add_comment(
            issue_key,
            f"## Handshake OK\n\n"
            f"Estimación: {estimacion}\n\n"
            f"**El equipo puede arrancar desarrollo.**\n\n"
            f"Siguiente: `po uat {issue_key}` (cuando dev termine)"
        )
        notify_success(
            f"Acta de Handshake guardada en {issue_key}. Estado → HANDSHAKE.",
            "El equipo puede arrancar desarrollo.",
        )
    else:
        jira.add_comment(
            issue_key,
            f"## Handshake KO\n\nGaps identificados:\n{gaps_def}\n\n"
            f"La HU vuelve a Definición."
        )
        notify_warning(
            f"Handshake KO — la HU vuelve a Definición.",
            f"Resuelve los gaps y ejecuta de nuevo `po handshake {issue_key}`.",
        )

    console.print()
