import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, intake_card, notify_success,
    notify_warning, confirm, C_MUTED, C_ACCENT, ICON_ARROW,
)
from ..jira_client import JiraClient
from ..models import IntakeResult, POEstado, TipoPeticion


def run(text: str, ai: AIClient, jira: JiraClient, config: Config) -> str:
    """
    Classifies a free-text request with IA, shows a structured preview,
    confirms with the PO, creates the Jira issue. Returns the issue key.
    """
    section_rule("Analizando petición con IA")

    data = ai.call_json("intake_classify.md", {"USER_INPUT": text})

    result = IntakeResult(
        titulo=data["titulo"],
        tipo_peticion=TipoPeticion(data["tipo_peticion"]),
        descripcion=data["descripcion"],
        prioridad_sugerida=data["prioridad_sugerida"],
        razon_prioridad=data["razon_prioridad"],
        alerta_urgencia=data.get("alerta_urgencia", False),
        dudas_para_el_po=data.get("dudas_para_el_po", []),
    )

    intake_card(
        titulo=result.titulo,
        tipo=result.tipo_peticion.value,
        prioridad=result.prioridad_sugerida,
        descripcion=result.descripcion,
        razon_prioridad=result.razon_prioridad,
        dudas=result.dudas_para_el_po,
    )

    if result.alerta_urgencia:
        notify_warning(
            "La IA detecta posible urgencia.",
            f"Si es así, usa [{C_ACCENT}]po urgencia[/{C_ACCENT}] para el flujo abreviado.",
        )

    if not confirm("¿Crear este ticket en Jira?", default=True):
        console.print(f"  [{C_MUTED}]Cancelado.[/{C_MUTED}]\n")
        raise typer.Abort()

    description = _build_description(result, text)
    labels = [
        POEstado.INTAKE.value,
        f"tipo:{result.tipo_peticion.value}",
        f"prio:{result.prioridad_sugerida.lower()}",
    ]

    issue = jira.create_issue(
        summary=result.titulo,
        description_md=description,
        issue_type="Story",
        labels=labels,
    )

    key = issue.get("key", "FP-DRY")
    jira_url = f"{config.jira_base_url}/browse/{key}"

    notify_success(
        f"Ticket creado: {key}",
        f"[link={jira_url}]{jira_url}[/link]",
    )

    console.print(
        f"  [{C_MUTED}]Siguiente paso:[/{C_MUTED}]  "
        f"[bold {C_ACCENT}]po triage {key}[/bold {C_ACCENT}]\n"
    )
    return key


def _build_description(result: IntakeResult, original_text: str) -> str:
    lines = [
        "## Petición original",
        original_text,
        "",
        "---",
        "",
        "## Análisis IA",
        f"**Tipo de petición:** {result.tipo_peticion.value}",
        f"**Prioridad sugerida:** {result.prioridad_sugerida}",
        f"**Justificación:** {result.razon_prioridad}",
        "",
        "**Descripción estructurada:**",
        result.descripcion,
    ]
    if result.dudas_para_el_po:
        lines += ["", "**Preguntas para el PO (resolver en discovery):"]
        for d in result.dudas_para_el_po:
            lines.append(f"- {d}")
    lines += [
        "",
        "---",
        "_Creado con po-assistant · Siguiente: `po triage <KEY>`_",
    ]
    return "\n".join(lines)
