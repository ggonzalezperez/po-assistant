"""po-assistant — CLI para Product Owners · Flexicar"""

import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import typer
from dotenv import find_dotenv, set_key
from rich.padding import Padding

from .config import load_config
from .display import (
    console, app_header, step_bar, section_rule,
    notify_success, notify_warning, notify_error,
    pipeline_table, demo_welcome, demo_scenario_card, demo_summary,
    _help_row, C_MUTED, C_ACCENT, C_PRIMARY, C_SUCCESS, C_ERROR,
    ICON_ARROW,
)
from .jira_client import JiraClient, JiraError
from .ai_client import AIClient
from .models import POEstado

app = typer.Typer(
    name="po",
    help="Asistente IA para Product Owners — Flexicar",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)

ESTADO_ORDER = [
    POEstado.INTAKE, POEstado.TRIAGE, POEstado.DISCOVERY, POEstado.DEFINICION,
    POEstado.SIGN_OFF_SH, POEstado.DOR_GATE, POEstado.HANDSHAKE,
    POEstado.EN_DESARROLLO, POEstado.UAT, POEstado.RELEASE,
]

ESTADO_COLOR = {
    POEstado.INTAKE:       "white",
    POEstado.TRIAGE:       "cyan",
    POEstado.DISCOVERY:    "bright_blue",
    POEstado.DEFINICION:   "blue",
    POEstado.SIGN_OFF_SH:  "yellow",
    POEstado.DOR_GATE:     "orange3",
    POEstado.HANDSHAKE:    "magenta",
    POEstado.EN_DESARROLLO:"green",
    POEstado.UAT:          "bright_green",
    POEstado.RELEASE:      "cyan",
    POEstado.CERRADO:      "dim",
    POEstado.RECHAZADO:    "red",
    POEstado.APLAZADO:     "dark_orange",
}

DEMO_STEPS = ["INTAKE", "DEFINICIÓN", "DOR GATE"]

DEMO_TEXT = (
    "Los agentes comerciales de tienda tardan demasiado en encontrar la opción "
    "de cancelar una reserva desde el CRM. Cuando un cliente llama para cancelar, "
    "el agente tiene que navegar por tres menús distintos y muchas veces llama al "
    "soporte interno porque no lo encuentra. Ocurre unas 10-15 veces al día en las "
    "tiendas grandes. Lo pide María Ruiz, responsable de operaciones comerciales."
)


def _clients():
    config = load_config()
    return config, JiraClient(config), AIClient(config)


# ── SETUP ────────────────────────────────────────────────────────────────────

@app.command()
def setup():
    """
    Crea el proyecto [bold]FP[/bold] en Jira y los campos custom necesarios.
    """
    app_header("Configuración inicial")
    config, jira, _ = _clients()

    console.print(f"  [{C_MUTED}]Instancia:[/{C_MUTED}] {config.jira_base_url}")
    console.print(f"  [{C_MUTED}]Email:    [/{C_MUTED}] {config.jira_email}")
    console.print(f"  [{C_MUTED}]Proyecto: [/{C_MUTED}] {config.jira_po_project_key}\n")

    try:
        me = jira.get_myself()
        account_id = me["accountId"]
        notify_success(f"Conexión Jira OK — {me.get('displayName', config.jira_email)}")
    except JiraError as e:
        notify_error("Error conectando a Jira.", str(e))
        console.print(f"\n  [{C_MUTED}]Revisa JIRA_BASE_URL, JIRA_EMAIL y JIRA_API_TOKEN en .env[/{C_MUTED}]\n")
        raise typer.Exit(1)

    key = config.jira_po_project_key
    if jira.project_exists(key):
        notify_warning(f"El proyecto '{key}' ya existe.", "Se omite la creación.")
    else:
        if not typer.confirm(f"\n  ¿Crear proyecto '{key}' — Flexicar Producto?", default=True):
            raise typer.Abort()
        try:
            jira.create_project(key, "Flexicar Producto", account_id)
            notify_success(f"Proyecto '{key}' creado.")
        except JiraError as e:
            notify_error("Error creando proyecto.", str(e))
            console.print(f"\n  [{C_MUTED}]Créalo manualmente en Jira → Projects → Create Project[/{C_MUTED}]")
            console.print(f"  [{C_MUTED}]Clave: {key}  Nombre: Flexicar Producto[/{C_MUTED}]\n")
            raise typer.Exit(1)

    section_rule("Campos custom")
    fields_spec = [
        ("DoR Score",      "number", "Score 0-12 del DoR Gate automático",      config.fields.dor_score),
        ("DoR Gaps",       "text",   "Gaps detectados por el linter DoR",        config.fields.dor_gaps),
        ("IA Asistida",    "text",   "Si/No",                                    config.fields.ia_asistida),
        ("Tipo Peticion",  "text",   "problema|idea|urgencia|mejora|incidencia", config.fields.tipo_peticion),
        ("Validador UAT",  "text",   "Nombre y rol del validador funcional de UAT", config.fields.validador_uat),
    ]
    env_map = {
        "DoR Score":     "JIRA_FIELD_DOR_SCORE",
        "DoR Gaps":      "JIRA_FIELD_DOR_GAPS",
        "IA Asistida":   "JIRA_FIELD_IA_ASISTIDA",
        "Tipo Peticion": "JIRA_FIELD_TIPO_PETICION",
        "Validador UAT": "JIRA_FIELD_VALIDADOR_UAT",
    }

    # Skip Jira lookup entirely if all IDs are already in .env
    all_preconfigured = all(existing_id for _, _, _, existing_id in fields_spec)
    if all_preconfigured:
        existing_lower: dict[str, str] = {}
    else:
        jira_fields = jira.get_all_fields()
        existing_lower = {f.get("name", "").lower(): f["id"] for f in jira_fields}

    created: dict[str, str] = {}
    for name, ftype, desc, env_id in fields_spec:
        if env_id:
            # Already set in .env — nothing to do
            created[name] = env_id
            console.print(f"  [{C_MUTED}]— {name:<22} ya configurado  {env_id}[/{C_MUTED}]")
        elif name.lower() in existing_lower:
            # Exists in Jira but missing from .env (e.g. after manual field creation)
            fid = existing_lower[name.lower()]
            created[name] = fid
            console.print(f"  [{C_MUTED}]— {name:<22} ya existe  {fid}[/{C_MUTED}]")
        else:
            try:
                result = jira.create_number_field(name, desc) if ftype == "number" \
                    else jira.create_text_field(name, desc)
                fid = result.get("id", "?")
                created[name] = fid
                console.print(f"  [{C_SUCCESS}]✓[/{C_SUCCESS}] {name:<22} [{C_MUTED}]{fid}[/{C_MUTED}]")
            except JiraError as e:
                console.print(f"  [{C_MUTED}]— {name:<22} error: {e}[/{C_MUTED}]")

    # Auto-update .env so IDs persist without manual copy-paste
    dotenv_path = find_dotenv(usecwd=True) or ""
    env_updated = False
    for name, env_key in env_map.items():
        fid = created.get(name, "")
        if fid and fid != "?" and os.getenv(env_key, "") != fid:
            if dotenv_path:
                set_key(dotenv_path, env_key, fid)
            env_updated = True

    if env_updated:
        section_rule(".env actualizado automáticamente")
        for name, env_key in env_map.items():
            fid = created.get(name, "")
            if fid:
                console.print(f"  [{C_SUCCESS}]✓[/{C_SUCCESS}] {env_key}={fid}")
    else:
        section_rule("Campos custom — IDs")
        for name, env_key in env_map.items():
            fid = created.get(name, "")
            console.print(f"  [{C_MUTED}]{env_key}={fid or '—'}[/{C_MUTED}]")

    # ── Workflow Kanban con 10 estados ────────────────────────────────────────
    section_rule("Workflow PO — 10 estados")
    if jira.po_workflow_exists():
        console.print(f"  [{C_MUTED}]— Workflow PO ya existe[/{C_MUTED}]")
    else:
        try:
            console.print(f"  [{C_MUTED}]Creando statuses y workflow…[/{C_MUTED}]")
            status_ids = jira.get_or_create_po_statuses()
            jira.create_po_workflow(status_ids)

            proj_data = jira._get(f"/project/{key}")
            scheme_id = jira.get_project_scheme_id(proj_data["id"])
            old_statuses = ["10000", "3", "10001"]
            task_id = jira.assign_workflow_to_project(
                scheme_id, "PO Workflow — Flexicar", old_statuses, status_ids
            )
            if task_id:
                console.print(f"  [{C_MUTED}]Esperando migración…[/{C_MUTED}]")
                jira.wait_for_task(task_id)

            console.print(f"  [{C_SUCCESS}]✓[/{C_SUCCESS}] Workflow creado: 10 estados + transiciones globales")
        except JiraError as e:
            console.print(f"  [{C_MUTED}]— Workflow: {e}[/{C_MUTED}]")

    # ── Tablero Kanban ────────────────────────────────────────────────────────
    section_rule("Tablero Kanban")
    board_id = jira.get_board(key)
    if board_id:
        console.print(f"  [{C_MUTED}]— Tablero Kanban ya existe  (ID: {board_id})[/{C_MUTED}]")
    else:
        try:
            board_id = jira.create_board(f"Pipeline PO — {key}", key)
            for estado in ESTADO_ORDER:
                jira.create_quick_filter(board_id, estado.display, f"labels = \"{estado.value}\"")
            console.print(
                f"  [{C_SUCCESS}]✓[/{C_SUCCESS}] Tablero Kanban creado   "
                f"[{C_MUTED}]ID: {board_id}[/{C_MUTED}]"
            )
        except JiraError as e:
            board_id = 0
            console.print(f"  [{C_MUTED}]— Tablero: {e}[/{C_MUTED}]")

    # ── Instrucciones columnas del board (una vez manual en UI) ───────────────
    if board_id:
        board_settings_url = (
            f"{config.jira_base_url}/jira/software/projects/{key}/boards/{board_id}?config=columns"
        )
        section_rule("Configurar columnas del tablero (1 vez)")
        console.print(
            f"  [{C_MUTED}]El board Kanban necesita 10 columnas. Abre:[/{C_MUTED}]\n"
            f"  [{C_ACCENT}]{board_settings_url}[/{C_ACCENT}]\n"
            f"  [{C_MUTED}]Board settings → Columns → Añade estas columnas:[/{C_MUTED}]"
        )
        for i, estado in enumerate(ESTADO_ORDER, 1):
            console.print(f"  [{C_MUTED}]  {i:>2}. {estado.display}[/{C_MUTED}]")

    # ── Equipo PO — Componentes ───────────────────────────────────────────────
    if config.po_team:
        section_rule("Equipo PO — Componentes")
        for po_name, po_email in config.po_team.items():
            try:
                jira.create_component(key, po_name, po_email)
                console.print(
                    f"  [{C_SUCCESS}]✓[/{C_SUCCESS}] {po_name:<26} [{C_MUTED}]{po_email}[/{C_MUTED}]"
                )
            except JiraError:
                console.print(f"  [{C_MUTED}]— {po_name:<26} ya existe[/{C_MUTED}]")

    console.print()
    board_url = (
        f"{config.jira_base_url}/jira/software/projects/{key}/boards/{board_id}"
        if board_id else
        f"{config.jira_base_url}/jira/software/projects/{key}/boards"
    )
    notify_success("Setup completado.", f"[link={board_url}]Abrir tablero →[/link]")
    console.print()


# ── INTAKE ───────────────────────────────────────────────────────────────────

@app.command()
def intake(
    text: str = typer.Argument(..., help="Descripción libre de la petición"),
):
    """
    [bold]Paso 1[/bold] — Clasifica la petición con IA y crea el ticket en Jira.
    """
    app_header("Paso 1 — Intake")
    config, jira, ai = _clients()
    from .workflow import intake as wf
    wf.run(text, ai, jira, config)


# ── TRIAGE ───────────────────────────────────────────────────────────────────

@app.command()
def triage(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 2[/bold] — Árbol de decisión de triage con comentario documentado.
    """
    app_header("Paso 2 — Triage")
    config, jira, ai = _clients()
    from .workflow import triage as wf
    wf.run(issue_key, ai, jira, config)


# ── DISCOVERY ────────────────────────────────────────────────────────────────

@app.command()
def discovery(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 3[/bold] — Q&A guiado para completar la Ficha Previa de Análisis.
    """
    app_header("Paso 3 — Discovery")
    config, jira, ai = _clients()
    from .workflow import discovery as wf
    wf.run(issue_key, ai, jira, config)


# ── DEFINE ───────────────────────────────────────────────────────────────────

@app.command()
def define(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
    notes: Optional[Path] = typer.Option(None, "--notes", "-n",
                                          help="Archivo .txt con notas de discovery"),
):
    """
    [bold]Paso 4[/bold] — Genera la HU completa (6 bloques) con IA.
    """
    app_header("Paso 4 — Definición")
    config, jira, ai = _clients()
    from .workflow import definition as wf
    wf.run(issue_key, ai, jira, config, notes_file=notes)


# ── DOR-GATE ─────────────────────────────────────────────────────────────────

@app.command(name="dor-gate")
def dor_gate(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 6[/bold] — Valida los 12 bloques del DoR con IA.
    """
    app_header("Paso 6 — DoR Gate")
    config, jira, ai = _clients()
    from .workflow import dor_gate as wf
    wf.run(issue_key, ai, jira, config)


# ── SIGN-OFF SH ───────────────────────────────────────────────────────────────

@app.command()
def signoff(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 5[/bold] — Genera el documento de Sign-off del alcance con el stakeholder.
    """
    app_header("Paso 5 — Sign-off Stakeholder")
    config, jira, ai = _clients()
    from .workflow import signoff as wf
    wf.run(issue_key, ai, jira, config)


# ── HANDSHAKE ─────────────────────────────────────────────────────────────────

@app.command()
def handshake(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 7[/bold] — Genera el Acta de Handshake PO ↔ Desarrollo.
    """
    app_header("Paso 7 — Handshake")
    config, jira, ai = _clients()
    from .workflow import handshake as wf
    wf.run(issue_key, ai, jira, config)


# ── UAT ───────────────────────────────────────────────────────────────────────

@app.command()
def uat(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 9[/bold] — Registra el Acta de UAT con el validador funcional.
    """
    app_header("Paso 9 — UAT")
    config, jira, ai = _clients()
    from .workflow import uat as wf
    wf.run(issue_key, ai, jira, config)


# ── RELEASE ───────────────────────────────────────────────────────────────────

@app.command()
def release(
    issue_key: str = typer.Argument(..., help="Clave del issue (ej: FP-12)"),
):
    """
    [bold]Paso 10[/bold] — Completa el Checklist de Release y autoriza la entrada a producción.
    """
    app_header("Paso 10 — Release")
    config, jira, ai = _clients()
    from .workflow import release as wf
    wf.run(issue_key, ai, jira, config)


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@app.command()
def dashboard(
    po: Optional[str] = typer.Option(None, "--po", help="Filtrar por PO (parte del nombre)"),
    show_closed: bool = typer.Option(False, "--all", "-a", help="Incluir CERRADO y RECHAZADO"),
):
    """
    [bold]Pipeline[/bold] — Estado de todos los issues del proyecto FP.
    """
    app_header("Dashboard — Pipeline PO")
    config, jira, _ = _clients()

    console.print(f"  [{C_MUTED}]Cargando {config.jira_po_project_key}…[/{C_MUTED}]\n")
    try:
        issues = jira.get_project_issues()
    except JiraError as e:
        notify_error("Error cargando issues.", str(e))
        raise typer.Exit(1)

    if po:
        issues = [i for i in issues if i.assignee and po.lower() in i.assignee.lower()]

    by_estado: dict[str, list] = {e.value: [] for e in list(ESTADO_ORDER) + [
        POEstado.CERRADO, POEstado.RECHAZADO, POEstado.APLAZADO
    ]}
    no_estado: list = []
    for issue in issues:
        estado = issue.po_estado
        if estado:
            by_estado.setdefault(estado.value, []).append(issue)
        else:
            no_estado.append(issue)

    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    visible_estados = ESTADO_ORDER + ([POEstado.CERRADO, POEstado.RECHAZADO] if show_closed else [])

    for estado in visible_estados:
        issues_in = by_estado.get(estado.value, [])
        color = ESTADO_COLOR.get(estado, "white")

        oldest = ""
        if issues_in:
            sorted_i = sorted(issues_in, key=lambda x: x.created)
            dt = _parse_date(sorted_i[0].created)
            if dt:
                oldest = _fmt_age(now - dt)

        alerts = _build_alerts(estado, issues_in, now)
        label = estado.display if hasattr(estado, "display") else estado.value.upper()

        rows.append({
            "label":   estado.value,
            "display": label,
            "count":   len(issues_in),
            "oldest":  oldest,
            "color":   color,
            "alerts":  alerts,
        })

    pipeline_table(rows, config.jira_po_project_key,
                   now.strftime("%Y-%m-%d %H:%M UTC"))

    total = len(issues)
    done  = len(by_estado.get(POEstado.CERRADO.value, []))
    console.print(f"  [{C_MUTED}]Total: {total}  ·  Cerrados: {done}[/{C_MUTED}]")
    if no_estado:
        console.print(f"  [{C_MUTED}]{len(no_estado)} issue(s) sin etiqueta po-*[/{C_MUTED}]")
    console.print()

    _help_row([
        ("po intake \"texto\"", "crear ticket"),
        ("po define FP-X", "generar HU"),
        ("po dor-gate FP-X", "validar DoR"),
    ])
    console.print()


# ── DEMO ─────────────────────────────────────────────────────────────────────

@app.command()
def demo(
    offline: bool = typer.Option(False, "--offline",
                                  help="Simula sin crear issues en Jira (DRY_RUN)"),
):
    """
    [bold]Demo para el CTO[/bold] — Flujo completo con un caso real de Flexicar.

    INTAKE → DEFINICIÓN → DOR GATE · Tiempo estimado: 2-3 minutos.
    """
    start_time = time.time()

    demo_welcome()

    # Show the scenario
    demo_scenario_card(DEMO_TEXT)

    if not typer.confirm("  ¿Empezar la demo?", default=True):
        raise typer.Abort()

    config = load_config()
    if offline:
        config.dry_run = True  # type: ignore
        console.print(f"\n  [{C_MUTED}]Modo offline activado — no se crean issues en Jira.[/{C_MUTED}]\n")

    jira = JiraClient(config)
    ai   = AIClient(config)

    from .workflow import intake as wf_intake
    from .workflow import definition as wf_def
    from .workflow import dor_gate as wf_dor

    # ── Paso 1: INTAKE ───────────────────────────────────────────────────────
    console.print()
    step_bar(DEMO_STEPS, current=0)
    issue_key = wf_intake.run(DEMO_TEXT, ai, jira, config)

    if not typer.confirm(f"\n  ¿Continuar con DEFINICIÓN para {issue_key}?", default=True):
        raise typer.Abort()

    # ── Paso 2: DEFINICIÓN ──────────────────────────────────────────────────
    console.print()
    step_bar(DEMO_STEPS, current=1)
    wf_def.run(issue_key, ai, jira, config)

    if not typer.confirm(f"\n  ¿Continuar con DOR GATE para {issue_key}?", default=True):
        raise typer.Abort()

    # ── Paso 3: DOR GATE ────────────────────────────────────────────────────
    console.print()
    step_bar(DEMO_STEPS, current=2)
    result = wf_dor.run(issue_key, ai, jira, config)

    # ── Summary ─────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    jira_url = f"{config.jira_base_url}/browse/{issue_key}"
    demo_summary(issue_key, jira_url, result.score, elapsed)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _fmt_age(delta: timedelta) -> str:
    h = int(delta.total_seconds() / 3600)
    if h < 24:
        return f"{h}h"
    d = h // 24
    return f"{d}d" if d < 14 else f"{d // 7}w"


SLA_HOURS = {
    POEstado.INTAKE:      48,
    POEstado.SIGN_OFF_SH: 5 * 24,
    POEstado.DOR_GATE:    2 * 24,
}


def _build_alerts(estado: POEstado, issues: list, now: datetime) -> str:
    alerts: list[str] = []
    max_h = SLA_HOURS.get(estado)
    if max_h:
        for issue in issues:
            dt = _parse_date(issue.created)
            if dt and (now - dt).total_seconds() / 3600 > max_h:
                age = _fmt_age(now - dt)
                alerts.append(f"[red]⚠ {issue.key} SLA ({age})[/red]")
    return "  ".join(alerts)


if __name__ == "__main__":
    app()
