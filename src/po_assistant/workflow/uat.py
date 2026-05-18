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
    section_rule(f"UAT — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a registrar el Acta de UAT. "
        f"El PO acompaña, el validador de negocio firma.[/{C_MUTED}]\n"
    )

    validador = ask("¿Quién es el validador funcional? (nombre, rol)")
    entorno = ask("¿En qué entorno se realizó la UAT?", "Normalmente: PRE")
    casos_ok = ask_multiline(
        "¿Qué casuísticas se validaron y con qué resultado?",
        "Una por línea. Ej: 'Happy path — cancelación desde CRM ✅ OK'"
    )
    defectos = ask(
        "¿Se detectaron defectos?",
        "Si no hay: 'ninguno'. Si hay: descríbelos con su severidad"
    )

    decision = ask_choice(
        "¿Cuál es la decisión del validador?",
        [
            ("UAT OK", "La HU pasa a sign-off de release"),
            ("UAT KO con observaciones", "La HU vuelve a desarrollo"),
            ("UAT OK condicional", "Pasa con defectos menores que se trackean aparte"),
        ]
    )

    observaciones = ""
    if decision in (2, 3):
        observaciones = ask_multiline("¿Cuáles son las observaciones / defectos?")

    answers_text = "\n".join(filter(None, [
        f"Validador funcional: {validador}",
        f"Entorno: {entorno}",
        f"Casuísticas validadas:\n{casos_ok}",
        f"Defectos detectados: {defectos}",
        f"Decisión: {['UAT OK', 'UAT KO con observaciones', 'UAT OK condicional'][decision - 1]}",
        f"Observaciones:\n{observaciones}" if observaciones else "",
    ]))

    acta_md = ai.call(
        "uat_acta.md",
        {
            "USER_INPUT": "Genera el acta de UAT.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "PO_AUTOR": config.jira_email,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Acta UAT")
    for line in acta_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Acta UAT en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "UAT", acta_md)
    jira.transition_po_state(issue_key, POEstado.UAT)

    if decision == 1:
        jira.add_comment(issue_key,
            f"## UAT OK ✅\n\nValidador: **{validador}**\n\n"
            f"Siguiente: `po release {issue_key}`")
        notify_success(
            f"Acta UAT guardada en {issue_key}. Estado → UAT.",
            f"Siguiente: [{C_ACCENT}]po release {issue_key}[/{C_ACCENT}]",
        )
    elif decision == 2:
        jira.add_comment(issue_key,
            f"## UAT KO ❌\n\nDefectos: {defectos}\n\n"
            f"La HU vuelve a desarrollo. Lead FE/BE a cargo de la corrección.")
        notify_warning(f"UAT KO — la HU vuelve a desarrollo.", f"Defectos: {defectos}")
    else:
        jira.add_comment(issue_key,
            f"## UAT OK condicional ⚠️\n\nObservaciones: {observaciones}\n\n"
            f"Siguiente: `po release {issue_key}`")
        notify_success(f"UAT OK condicional. Estado → UAT.", "Observaciones trackadas en Jira.")

    console.print()
