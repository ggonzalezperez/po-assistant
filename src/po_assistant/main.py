"""po-assistant — CLI para Product Owners · Flexicar"""

from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .config import load_config
from .jira_client import JiraClient, JiraError
from .ai_client import AIClient
from .models import POEstado

app = typer.Typer(
    name="po",
    help="Asistente IA para Product Owners — Flexicar",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

ESTADO_ORDER = [
    POEstado.INTAKE, POEstado.TRIAGE, POEstado.DISCOVERY, POEstado.DEFINICION,
    POEstado.SIGN_OFF_SH, POEstado.DOR_GATE, POEstado.HANDSHAKE,
    POEstado.EN_DESARROLLO, POEstado.UAT, POEstado.RELEASE,
]
ESTADO_COLOR = {
    POEstado.INTAKE: "white",
    POEstado.TRIAGE: "cyan",
    POEstado.DISCOVERY: "blue",
    POEstado.DEFINICION: "magenta",
    POEstado.SIGN_OFF_SH: "yellow",
    POEstado.DOR_GATE: "orange3",
    POEstado.HANDSHAKE: "bright_magenta",
    POEstado.EN_DESARROLLO: "green",
    POEstado.UAT: "bright_green",
    POEstado.RELEASE: "bright_cyan",
    POEstado.CERRADO: "dim",
    POEstado.RECHAZADO: "red",
    POEstado.APLAZADO: "dark_orange",
}


def _clients():
    config = load_config()
    return config, JiraClient(config), AIClient(config)


# ── SETUP ────────────────────────────────────────────────────────────────────

@app.command()
def setup():
    """Crea el proyecto FP en Jira y los campos custom necesarios."""
    config, jira, _ = _clients()

    console.print(Panel(
        "[bold]po-assistant Setup[/bold]\n"
        f"Instancia Jira: [cyan]{config.jira_base_url}[/cyan]\n"
        f"Email: [cyan]{config.jira_email}[/cyan]\n"
        f"Proyecto PO: [cyan]{config.jira_po_project_key}[/cyan]",
        border_style="blue"
    ))

    # Verify connection
    try:
        me = jira.get_myself()
        account_id = me["accountId"]
        console.print(f"✅ Conexión Jira OK — {me.get('displayName', config.jira_email)}")
    except JiraError as e:
        console.print(f"[red]❌ Error conectando a Jira: {e}[/red]")
        console.print("\n[yellow]Verifica JIRA_BASE_URL, JIRA_EMAIL y JIRA_API_TOKEN en tu .env[/yellow]")
        raise typer.Exit(1)

    # Create project if it doesn't exist
    key = config.jira_po_project_key
    if jira.project_exists(key):
        console.print(f"ℹ️  Proyecto [bold]{key}[/bold] ya existe.")
    else:
        if not typer.confirm(f"\n¿Crear proyecto '{key}' — Flexicar Producto en Jira?", default=True):
            raise typer.Abort()
        try:
            project = jira.create_project(key, "Flexicar Producto", account_id)
            console.print(f"✅ Proyecto [bold]{key}[/bold] creado. ID: {project.get('id')}")
        except JiraError as e:
            console.print(f"[red]❌ Error creando proyecto: {e}[/red]")
            console.print("\n[yellow]En Jira Free puedes crearlo manualmente:[/yellow]")
            console.print("   Jira → Projects → Create Project → Scrum / Kanban")
            console.print(f"   Clave: [bold]{key}[/bold] · Nombre: Flexicar Producto")
            raise typer.Exit(1)

    # Create custom fields
    console.print("\n[bold]Creando campos custom…[/bold]")
    fields_to_create = [
        ("DoR Score", "number", "Score de 0-12 del DoR Gate automático"),
        ("DoR Gaps", "text", "Gaps detectados por el linter DoR"),
        ("IA Asistida", "text", "Si/No — indica si la HU fue generada con IA"),
        ("Tipo Peticion", "text", "problema|idea|urgencia|mejora|incidencia"),
        ("Validador UAT", "text", "Nombre y rol del validador funcional de UAT"),
    ]

    created_ids: dict[str, str] = {}
    for name, ftype, desc in fields_to_create:
        try:
            if ftype == "number":
                result = jira.create_number_field(name, desc)
            else:
                result = jira.create_text_field(name, desc)
            field_id = result.get("id", "?")
            created_ids[name] = field_id
            console.print(f"  ✅ {name} → [dim]{field_id}[/dim]")
        except JiraError as e:
            console.print(f"  [yellow]⚠️  {name}: {e} (puede que ya exista)[/yellow]")

    # Check for existing fields with same names
    if not created_ids:
        all_fields = jira.get_all_fields()
        for f in all_fields:
            for name, _, _ in fields_to_create:
                if f.get("name") == name:
                    created_ids[name] = f["id"]

    console.print("\n[bold green]Setup completado.[/bold green]")
    console.print("\nAñade estos IDs a tu [bold].env[/bold]:\n")

    env_map = {
        "DoR Score": "JIRA_FIELD_DOR_SCORE",
        "DoR Gaps": "JIRA_FIELD_DOR_GAPS",
        "IA Asistida": "JIRA_FIELD_IA_ASISTIDA",
        "Tipo Peticion": "JIRA_FIELD_TIPO_PETICION",
        "Validador UAT": "JIRA_FIELD_VALIDADOR_UAT",
    }
    for name, env_key in env_map.items():
        field_id = created_ids.get(name, "customfield_XXXXX")
        console.print(f"  {env_key}={field_id}")

    console.print(f"\nJira: [link={config.jira_base_url}/jira/software/projects/{key}/boards]"
                  f"{config.jira_base_url}/jira/software/projects/{key}/boards[/link]")


# ── INTAKE ───────────────────────────────────────────────────────────────────

@app.command()
def intake(
    text: str = typer.Argument(..., help="Descripción libre de la petición (entre comillas)"),
):
    """
    [bold]Paso 1[/bold] — Clasifica una petición con IA y crea el ticket en Jira.

    [dim]Ejemplo: po intake "Los agentes no saben cómo cancelar una reserva desde el CRM"[/dim]
    """
    config, jira, ai = _clients()
    from .workflow import intake as intake_workflow
    intake_workflow.run(text, ai, jira, config)


# ── DEFINE ───────────────────────────────────────────────────────────────────

@app.command()
def define(
    issue_key: str = typer.Argument(..., help="Clave del issue Jira (ej: FP-12)"),
    notes: Optional[Path] = typer.Option(None, "--notes", "-n",
                                          help="Archivo .txt con notas de discovery"),
):
    """
    [bold]Paso 4[/bold] — Genera un borrador completo de HU con IA.

    Lee el issue de Jira, genera los 6 bloques de la HU y actualiza la descripción.
    [dim]Ejemplo: po define FP-12[/dim]
    [dim]Con notas: po define FP-12 --notes discovery_notas.txt[/dim]
    """
    config, jira, ai = _clients()
    from .workflow import definition as definition_workflow
    definition_workflow.run(issue_key, ai, jira, config, notes_file=notes)


# ── DOR-GATE ─────────────────────────────────────────────────────────────────

@app.command(name="dor-gate")
def dor_gate(
    issue_key: str = typer.Argument(..., help="Clave del issue Jira (ej: FP-12)"),
):
    """
    [bold]Paso 6[/bold] — Valida los 12 bloques del DoR con IA.

    Puntúa de 0-12, lista los gaps, actualiza Jira y decide OK/KO.
    [dim]Ejemplo: po dor-gate FP-12[/dim]
    """
    config, jira, ai = _clients()
    from .workflow import dor_gate as dor_gate_workflow
    dor_gate_workflow.run(issue_key, ai, jira, config)


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@app.command()
def dashboard(
    po: Optional[str] = typer.Option(None, "--po", help="Filtrar por assignee (parte del nombre)"),
    show_closed: bool = typer.Option(False, "--all", "-a", help="Incluir CERRADO y RECHAZADO"),
):
    """
    [bold]Vista de pipeline[/bold] — Estado de todos los issues del proyecto FP.

    [dim]po dashboard             → todos los POs
    po dashboard --po ester   → solo Ester
    po dashboard --all        → incluye cerrados[/dim]
    """
    config, jira, _ = _clients()

    console.print(f"\n[dim]Cargando issues de {config.jira_po_project_key}…[/dim]")
    try:
        issues = jira.get_project_issues()
    except JiraError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if po:
        issues = [i for i in issues if i.assignee and po.lower() in i.assignee.lower()]

    # Group by PO estado
    by_estado: dict[str, list] = {e.value: [] for e in ESTADO_ORDER}
    by_estado[POEstado.CERRADO.value] = []
    by_estado[POEstado.RECHAZADO.value] = []
    by_estado[POEstado.APLAZADO.value] = []

    no_estado = []
    for issue in issues:
        estado = issue.po_estado
        if estado:
            by_estado[estado.value].append(issue)
        else:
            no_estado.append(issue)

    table = Table(
        title=f"Pipeline PO — {config.jira_po_project_key}   "
              f"[dim]{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}[/dim]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Estado", min_width=16)
    table.add_column("Issues", justify="right", width=7)
    table.add_column("Más antiguo", width=12)
    table.add_column("Alertas / Detalles")

    for estado in ESTADO_ORDER:
        if not show_closed and estado in (POEstado.CERRADO, POEstado.RECHAZADO):
            continue
        issues_in = by_estado.get(estado.value, [])
        count = len(issues_in)
        color = ESTADO_COLOR.get(estado, "white")

        oldest = ""
        if issues_in:
            sorted_issues = sorted(issues_in, key=lambda x: x.created)
            oldest_dt = _parse_jira_date(sorted_issues[0].created)
            if oldest_dt:
                age = datetime.now(timezone.utc) - oldest_dt
                oldest = _fmt_age(age)

        alerts = _build_alerts(estado, issues_in)
        label = estado.display if hasattr(estado, "display") else estado.value.upper()

        table.add_row(
            f"[{color}]{label}[/{color}]",
            f"[bold]{count}[/bold]" if count > 0 else "[dim]0[/dim]",
            f"[dim]{oldest}[/dim]",
            alerts,
        )

    console.print()
    console.print(table)

    if no_estado:
        console.print(f"\n[dim]{len(no_estado)} issue(s) sin etiqueta po-*[/dim]")

    total = len(issues)
    done = len(by_estado.get(POEstado.CERRADO.value, []))
    console.print(f"\n[dim]Total: {total} issues | Cerrados: {done}[/dim]\n")


# ── DEMO ─────────────────────────────────────────────────────────────────────

@app.command()
def demo(
    offline: bool = typer.Option(False, "--offline", help="No crea issues en Jira (solo muestra el flujo)"),
):
    """
    [bold]Demo para el CTO[/bold] — Recorre el flujo completo con un caso real de Flexicar.

    Muestra: intake → definición → dor-gate con un ejemplo de CRM.
    """
    console.print(Panel(
        "[bold blue]po-assistant · Demo para el CTO[/bold blue]\n\n"
        "Vamos a simular que un agente comercial pide mejorar el CRM.\n"
        "El flujo completo: [bold]INTAKE → DEFINE → DOR GATE[/bold]",
        border_style="blue",
    ))

    demo_input = (
        "Los agentes comerciales de tienda tardan mucho en encontrar la opción de cancelar "
        "una reserva en el CRM. Cuando un cliente llama para cancelar, el agente tiene que "
        "buscar en tres menús distintos y a veces llama al soporte interno porque no lo "
        "encuentra. Ocurre unas 10-15 veces al día en las tiendas grandes. "
        "Lo pide María Ruiz, responsable de operaciones comerciales."
    )

    console.print("\n[bold]Petición recibida:[/bold]")
    console.print(Panel(demo_input, border_style="dim"))
    typer.echo("")

    if not typer.confirm("¿Ejecutar INTAKE con IA?", default=True):
        raise typer.Abort()

    config = load_config()
    if offline:
        config.dry_run = True  # type: ignore
    jira = JiraClient(config)
    ai = AIClient(config)

    from .workflow import intake as intake_workflow
    from .workflow import definition as definition_workflow
    from .workflow import dor_gate as dor_gate_workflow

    issue_key = intake_workflow.run(demo_input, ai, jira, config)

    if not typer.confirm(f"\n¿Generar la HU completa para {issue_key}?", default=True):
        raise typer.Abort()

    definition_workflow.run(issue_key, ai, jira, config)

    if not typer.confirm(f"\n¿Ejecutar DoR Gate para {issue_key}?", default=True):
        raise typer.Abort()

    dor_gate_workflow.run(issue_key, ai, jira, config)

    jira_url = f"{config.jira_base_url}/browse/{issue_key}"
    console.print(Panel(
        f"[bold green]Demo completado.[/bold green]\n\n"
        f"Issue en Jira: [link={jira_url}]{issue_key}[/link]\n\n"
        f"Comandos disponibles:\n"
        f"  [bold]po dashboard[/bold]      → ver pipeline completo\n"
        f"  [bold]po dor-gate FP-X[/bold]  → re-evaluar el DoR\n"
        f"  [bold]po define FP-X[/bold]    → re-generar la HU\n",
        border_style="green",
    ))


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _parse_jira_date(date_str: str):
    try:
        from datetime import datetime
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _fmt_age(delta: timedelta) -> str:
    hours = int(delta.total_seconds() / 3600)
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    if days < 7:
        return f"{days}d"
    return f"{days // 7}w"


def _build_alerts(estado: POEstado, issues: list) -> str:
    alerts: list[str] = []
    now = datetime.now(timezone.utc)

    sla_hours = {
        POEstado.INTAKE: 48,
        POEstado.SIGN_OFF_SH: 5 * 24,
        POEstado.DOR_GATE: 2 * 24,
    }

    max_h = sla_hours.get(estado)
    if max_h:
        for issue in issues:
            dt = _parse_jira_date(issue.created)
            if dt:
                age_h = (now - dt).total_seconds() / 3600
                if age_h > max_h:
                    alerts.append(f"[red]⚠ {issue.key} SLA vencido ({_fmt_age(now - dt)})[/red]")

    return "\n".join(alerts) if alerts else ""


if __name__ == "__main__":
    app()
