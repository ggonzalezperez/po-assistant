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
from .qa import ask, ask_choice, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Release — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(f"  [{C_MUTED}]Checklist de release final.[/{C_MUTED}]\n")

    fecha_release = ask("¿Cuándo está programado el release?", "Ej: 2026-06-10 18:00")
    tipo_release = ask_choice(
        "¿Qué tipo de release es?",
        [("Release planificado", ""), ("Hotfix", "")]
    )
    lead_tecnico = ask("¿Quién es el Lead técnico responsable del release?")

    console.print(f"\n  [{C_ACCENT}]Pre-condiciones funcionales[/{C_ACCENT}]")
    uat_ok = ask("¿El Acta UAT está firmada? (s/n)")
    signoff_ok = ask("¿El sign-off del alcance está en Jira? (s/n)")

    console.print(f"\n  [{C_ACCENT}]Pre-condiciones técnicas[/{C_ACCENT}]")
    pr_mergeado = ask("¿El PR está mergeado a la rama de release? (s/n)")
    tests_verde = ask("¿Los tests automáticos están en verde? (s/n)")
    rollback_plan = ask("¿Hay plan de rollback técnico preparado?",
                         "Describe el plan brevemente")

    console.print(f"\n  [{C_ACCENT}]Comunicación[/{C_ACCENT}]")
    comunicacion = ask("¿A quién hay que comunicar el release?",
                        "Ej: stakeholder + área de soporte. Si no aplica: 'N/A'")

    console.print(f"\n  [{C_ACCENT}]Post-deploy[/{C_ACCENT}]")
    responsable_postdeploy = ask("¿Quién monitoriza las 24-48h post-deploy?")

    yes_set = {"s", "si", "sí", "y", "yes"}

    def _check(val: str) -> str:
        return "[x]" if val.strip().lower() in yes_set else "[ ]"

    answers_text = "\n".join([
        f"Fecha de release: {fecha_release}",
        f"Tipo: {['Release planificado', 'Hotfix'][tipo_release - 1]}",
        f"Lead técnico: {lead_tecnico}",
        f"UAT firmada: {uat_ok} {_check(uat_ok)}",
        f"Sign-off en Jira: {signoff_ok} {_check(signoff_ok)}",
        f"PR mergeado: {pr_mergeado} {_check(pr_mergeado)}",
        f"Tests en verde: {tests_verde} {_check(tests_verde)}",
        f"Plan de rollback: {rollback_plan}",
        f"Comunicación: {comunicacion}",
        f"Responsable post-deploy: {responsable_postdeploy}",
    ])

    checklist_md = ai.call(
        "release_check.md",
        {
            "USER_INPUT": "Genera el checklist de release.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "PO_AUTOR": config.jira_email,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Checklist de Release")
    for line in checklist_md.splitlines()[:40]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Checklist de Release en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "RELEASE", checklist_md)
    jira.transition_po_state(issue_key, POEstado.RELEASE)
    jira.add_comment(
        issue_key,
        f"## Checklist de Release completado ✅\n\n"
        f"Fecha programada: **{fecha_release}**\n"
        f"Lead técnico: **{lead_tecnico}**\n\n"
        f"_Tras el release: marcar ticket como CERRADO._"
    )

    notify_success(
        f"Checklist de Release guardado en {issue_key}. Estado → RELEASE.",
        f"Tras el release: transiciona el ticket a CERRADO desde Jira.",
    )
    console.print()
