from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, urgencia_card, notify_success,
    confirm, C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado, UrgenciaResult
from .qa import ask


def run(text: str, ai: AIClient, jira: JiraClient, config: Config) -> str:
    """
    Flujo abreviado de urgencia: AI brief + Q&A mínimo → ticket en EN DESARROLLO.
    Retorna la clave del issue creado.
    """
    section_rule("Analizando urgencia con IA")

    data = ai.call_json("urgencia_brief.md", {"USER_INPUT": text})
    result = _parse_result(data)

    urgencia_card(
        titulo=result.titulo,
        descripcion=result.descripcion,
        impacto=result.impacto,
        causa_probable=result.causa_probable,
        accion_correctiva=result.accion_correctiva,
        rollback=result.rollback,
        checks=result.checks_verificacion,
    )

    section_rule("Datos del incidente")

    aprobador = ask(
        "¿Quién aprueba este fix? (nombre y rol)",
        "Ej: María Ruiz — Responsable Operaciones"
    )
    dev_lead = ask(
        "¿Quién es el dev lead técnico?",
        "Ej: Carlos López — Backend Lead"
    )
    eta = ask(
        "¿Cuál es el tiempo estimado de resolución?",
        "Ej: 2 horas / esta tarde / EOD"
    )

    if not confirm("¿Crear ticket urgente en Jira y mover a EN DESARROLLO?", default=True):
        console.print(f"  [{C_MUTED}]Cancelado.[/{C_MUTED}]\n")
        raise typer.Abort()

    description = _build_description(result, text, aprobador, dev_lead, eta)
    labels = [
        POEstado.EN_DESARROLLO.value,
        "tipo:urgencia",
        "prio:alta",
        "flujo:urgencia",
    ]

    issue = jira.create_issue(
        summary=result.titulo,
        description_md=description,
        issue_type="Story",
        labels=labels,
    )

    key = issue.get("key", "FP-DRY")

    if config.fields.ia_asistida:
        jira.update_issue(key, {config.fields.ia_asistida: "Sí"})

    jira.add_comment(
        key,
        f"## Urgencia creada — flujo abreviado\n\n"
        f"**Aprobado por:** {aprobador}\n"
        f"**Dev Lead:** {dev_lead}\n"
        f"**ETA:** {eta}\n\n"
        f"Siguiente cuando se resuelva: `po uat {key}`"
    )

    jira_url = f"{config.jira_base_url}/browse/{key}"
    notify_success(
        f"Ticket urgente creado: {key} → EN DESARROLLO",
        f"[link={jira_url}]{jira_url}[/link]",
    )
    console.print(
        f"  [{C_MUTED}]Siguiente paso:[/{C_MUTED}]  "
        f"[bold {C_ACCENT}]po uat {key}[/bold {C_ACCENT}]  "
        f"[{C_MUTED}](una vez resuelto el incidente)[/{C_MUTED}]\n"
    )
    return key


def _parse_result(data: dict) -> UrgenciaResult:
    return UrgenciaResult(
        titulo=data["titulo"],
        descripcion=data["descripcion"],
        prioridad_sugerida=data.get("prioridad_sugerida", "Alta"),
        razon_prioridad=data.get("razon_prioridad", ""),
        impacto=data.get("impacto", ""),
        causa_probable=data.get("causa_probable", ""),
        accion_correctiva=data.get("accion_correctiva", ""),
        rollback=data.get("rollback", ""),
        checks_verificacion=data.get("checks_verificacion", []),
    )


def _build_description(
    result: UrgenciaResult,
    original_text: str,
    aprobador: str,
    dev_lead: str,
    eta: str,
) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"## URGENCIA — {date_str}",
        "",
        "**Petición original:**",
        original_text,
        "",
        "---",
        "",
        f"**Impacto:** {result.impacto}",
        "",
        f"**Causa probable:** {result.causa_probable}",
        "",
        "**Acción correctiva sugerida:**",
        result.accion_correctiva,
        "",
        "**Plan de rollback:**",
        result.rollback,
        "",
        "**Checks de verificación:**",
    ]
    for check in result.checks_verificacion:
        lines.append(f"- {check}")
    lines += [
        "",
        "---",
        "",
        f"**Aprobado por:** {aprobador}",
        f"**Dev Lead:** {dev_lead}",
        f"**ETA resolución:** {eta}",
        "",
        "*Flujo abreviado de urgencia — generado con po-assistant*",
    ]
    return "\n".join(lines)
