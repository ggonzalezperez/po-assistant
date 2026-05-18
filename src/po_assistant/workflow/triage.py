from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT, C_PRIMARY,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_choice, append_section

_DECISIONS = [
    ("Incidencia técnica", "No es una HU — redirigir a soporte o dev"),
    ("Urgencia real", "Producción afectada ahora — usar `po urgencia`"),
    ("Idea sin problema claro", "Devolver al stakeholder con preguntas"),
    ("Mejora con prioridad clara", "Entra a Discovery"),
    ("Mejora con prioridad dudosa", "Aplazar al Comité Semanal de Priorización"),
]


def _decision_label(choice: int) -> str:
    labels = {
        1: "Redirigido — Incidencia técnica",
        2: "Urgencia — Vía urgencias",
        3: "Devuelto — Clarificación necesaria",
        4: "Entra a Discovery",
        5: "Aplazado — Comité Semanal",
    }
    return labels.get(choice, "Desconocido")


def _build_answers_text(answers: dict) -> str:
    lines = [
        f"Decisión elegida: {_decision_label(answers['decision'])}",
        f"Justificación: {answers.get('justificacion', '[sin justificación]')}",
    ]
    if answers.get("asignado_a"):
        lines.append(f"Asignado a: {answers['asignado_a']}")
    if answers.get("comite_fecha"):
        lines.append(f"Próximo Comité: {answers['comite_fecha']}")
    if answers.get("preguntas"):
        lines.append(f"Preguntas para el stakeholder: {answers['preguntas']}")
    if answers.get("destino"):
        lines.append(f"Destino de redirección: {answers['destino']}")
    return "\n".join(lines)


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Triage — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")

    if issue.description:
        console.print(f"  [{C_MUTED}]Descripción actual:[/{C_MUTED}]")
        for line in issue.description.splitlines()[:12]:
            console.print(f"  [{C_MUTED}]{line}[/{C_MUTED}]")
        console.print()

    choice = ask_choice("¿Cuál es la decisión de triage?", _DECISIONS)
    justificacion = ask("¿Cuál es tu justificación? (1-2 frases)")
    answers: dict = {"decision": choice, "justificacion": justificacion}

    if choice == 4:
        asignado = ask("¿A qué PO se asigna el Discovery?", "ej: Ana García")
        answers["asignado_a"] = asignado
    elif choice == 5:
        fecha = ask("¿Fecha del próximo Comité de Priorización?", "ej: 2026-05-26 o 'próximo lunes'")
        answers["comite_fecha"] = fecha
    elif choice == 3:
        preguntas = ask("¿Qué preguntas le devuelves al stakeholder?",
                        "escribe las preguntas separadas por punto y coma")
        answers["preguntas"] = preguntas
    elif choice == 1:
        destino = ask("¿A quién/dónde se redirige?", "ej: soporte N2, dev backend, etc.")
        answers["destino"] = destino

    answers_text = _build_answers_text(answers)
    fecha = datetime.now().strftime("%Y-%m-%d")

    triage_md = ai.call(
        "triage_decide.md",
        {
            "USER_INPUT": "Formatea la decisión de triage.",
            "TITULO": issue.summary,
            "INTAKE_TEXT": issue.description[:800] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "DECISION_LABEL": _decision_label(choice),
            "FECHA": fecha,
        },
    )

    console.print()
    section_rule("Vista previa — Triage")
    for line in triage_md.splitlines():
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar esta decisión en Jira?", default=True):
        console.print(f"  [{C_MUTED}]Cancelado.[/{C_MUTED}]\n")
        raise typer.Abort()

    append_section(jira, issue_key, "TRIAGE", triage_md)

    if choice == 4:
        jira.transition_po_state(issue_key, POEstado.TRIAGE)
    elif choice == 5:
        jira.transition_po_state(issue_key, POEstado.APLAZADO)

    jira.add_comment(issue_key, f"**Triage completado** — {_decision_label(choice)}\n\n_{fecha}_")

    next_cmd = f"po discovery {issue_key}" if choice == 4 else ""
    notify_success(
        f"Triage guardado en {issue_key}.",
        f"Siguiente: [{C_ACCENT}]{next_cmd}[/{C_ACCENT}]" if next_cmd else "",
    )
    console.print()
