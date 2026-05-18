from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from ..ai_client import AIClient
from ..config import Config
from ..jira_client import JiraClient
from ..models import IntakeResult, POEstado, TipoPeticion

console = Console()

PRIORITY_COLOR = {"Alta": "red", "Media": "yellow", "Baja": "green"}
TYPE_ICON = {
    "problema": "🔴",
    "idea": "💡",
    "urgencia": "🚨",
    "mejora": "🔧",
    "incidencia": "⚠️",
}


def run(text: str, ai: AIClient, jira: JiraClient, config: Config) -> str:
    """
    Classifies a free-text request with IA, shows a preview, confirms with the PO,
    and creates the Jira issue. Returns the created issue key.
    """
    console.print("\n[bold]Analizando petición con IA…[/bold]")

    data = ai.call_json(
        "intake_classify.md",
        {"USER_INPUT": text},
    )

    result = IntakeResult(
        titulo=data["titulo"],
        tipo_peticion=TipoPeticion(data["tipo_peticion"]),
        descripcion=data["descripcion"],
        prioridad_sugerida=data["prioridad_sugerida"],
        razon_prioridad=data["razon_prioridad"],
        alerta_urgencia=data.get("alerta_urgencia", False),
        dudas_para_el_po=data.get("dudas_para_el_po", []),
    )

    _display_intake_result(result)

    if result.alerta_urgencia:
        console.print(Panel(
            "⚠️  La IA ha detectado que esto puede ser una [bold red]URGENCIA[/bold red].\n"
            "Si es así, usa [bold]po urgencia[/bold] para el flujo abreviado.",
            title="Alerta", border_style="yellow"
        ))

    if not typer.confirm("\n¿Crear este ticket en Jira?", default=True):
        console.print("[yellow]Cancelado.[/yellow]")
        raise typer.Abort()

    description = _build_description(result, text)
    labels = [POEstado.INTAKE.value, f"tipo:{result.tipo_peticion.value}",
              f"prio:{result.prioridad_sugerida.lower()}"]

    issue = jira.create_issue(
        summary=result.titulo,
        description_md=description,
        issue_type="Story",
        labels=labels,
    )

    key = issue.get("key", "FP-DRY")
    jira_url = f"{config.jira_base_url}/browse/{key}"
    console.print(f"\n[bold green]✅ Ticket creado: {key}[/bold green]")
    console.print(f"[link={jira_url}]{jira_url}[/link]\n")

    if result.dudas_para_el_po:
        console.print("[bold yellow]⚡ Preguntas abiertas para el PO:[/bold yellow]")
        for i, duda in enumerate(result.dudas_para_el_po, 1):
            console.print(f"  {i}. {duda}")
        console.print()

    return key


def _display_intake_result(result: IntakeResult) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="dim", width=22)
    table.add_column()

    icon = TYPE_ICON.get(result.tipo_peticion.value, "")
    color = PRIORITY_COLOR.get(result.prioridad_sugerida, "white")

    table.add_row("Título", f"[bold]{result.titulo}[/bold]")
    table.add_row("Tipo", f"{icon} {result.tipo_peticion.value}")
    table.add_row("Prioridad", f"[{color}]{result.prioridad_sugerida}[/{color}] — {result.razon_prioridad}")
    table.add_row("Descripción", result.descripcion)

    console.print(Panel(table, title="[bold]Resultado del análisis IA[/bold]", border_style="blue"))


def _build_description(result: IntakeResult, original_text: str) -> str:
    lines = [
        f"## Petición original",
        f"{original_text}",
        "",
        "---",
        "",
        f"## Análisis IA",
        f"**Tipo de petición:** {result.tipo_peticion.value}",
        f"**Prioridad sugerida:** {result.prioridad_sugerida}",
        f"**Justificación:** {result.razon_prioridad}",
        "",
        f"**Descripción estructurada:**",
        result.descripcion,
    ]
    if result.dudas_para_el_po:
        lines += ["", "**Dudas para el PO (a resolver en discovery):**"]
        for d in result.dudas_para_el_po:
            lines.append(f"- {d}")
    lines += [
        "",
        "---",
        "_Ticket creado con po-assistant. Siguiente paso: `po triage <KEY>`_",
    ]
    return "\n".join(lines)
