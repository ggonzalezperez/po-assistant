"""
KPI computation engine, terminal dashboard, and Markdown export for po-assistant.
Command: po kpis
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from rich import box
from rich.padding import Padding
from rich.table import Table

from ..config import Config
from ..display import console, section_rule, C_MUTED, C_ACCENT, C_SUCCESS
from ..jira_client import JiraClient
from ..models import JiraIssue, POEstado

# ── Regex for section-date lines (em dash / en dash / hyphen) ────────────────

_SECTION_RE = re.compile(
    r'(INTAKE|TRIAGE|DISCOVERY|DEFINICION|SIGN-OFF SH|DOR GATE|HANDSHAKE|'
    r'EN DESARROLLO|UAT|RELEASE)[\s]*[—\-–][\s]*(\d{4}-\d{2}-\d{2})'
)

# ── Estado orderings ─────────────────────────────────────────────────────────

_AT_OR_AFTER_DOR_GATE = {
    POEstado.DOR_GATE.value,
    POEstado.HANDSHAKE.value,
    POEstado.EN_DESARROLLO.value,
    POEstado.UAT.value,
    POEstado.RELEASE.value,
    POEstado.CERRADO.value,
}

_AT_OR_AFTER_HANDSHAKE = {
    POEstado.HANDSHAKE.value,
    POEstado.EN_DESARROLLO.value,
    POEstado.UAT.value,
    POEstado.RELEASE.value,
    POEstado.CERRADO.value,
}

_AT_OR_AFTER_DEFINICION = {
    POEstado.DEFINICION.value,
    POEstado.SIGN_OFF_SH.value,
    POEstado.DOR_GATE.value,
    POEstado.HANDSHAKE.value,
    POEstado.EN_DESARROLLO.value,
    POEstado.UAT.value,
    POEstado.RELEASE.value,
    POEstado.CERRADO.value,
}

_RELEASED_OR_CLOSED = {
    POEstado.RELEASE.value,
    POEstado.CERRADO.value,
}

_OPEN_STATES = {e.value for e in POEstado} - {
    POEstado.CERRADO.value,
    POEstado.RECHAZADO.value,
    POEstado.APLAZADO.value,
}

# ── KPI data model ────────────────────────────────────────────────────────────

KPI_STATUS = ("ok", "warning", "alert", "info", "no_data")


@dataclass
class KPIResult:
    kpi_id: str        # "F1.1"
    name: str          # short display name
    family: str        # "F1" – "F6"
    value: str         # formatted value string, "" if no_data
    target: str        # M3 target string
    n: int             # sample size (0 if no_data)
    status: str        # one of KPI_STATUS
    note: str = ""     # for no_data KPIs — explanation


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_section_date(text: str, section: str) -> Optional[date]:
    """Return the first date found for the given section name in plain-text description."""
    for m in _SECTION_RE.finditer(text):
        if m.group(1) == section:
            try:
                return date.fromisoformat(m.group(2))
            except ValueError:
                pass
    return None


def _parse_created(iso: str) -> Optional[date]:
    """Parse ISO timestamp from Jira → date."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.date()
    except Exception:
        return None


def _get_cf_value(issue: JiraIssue, field_id: str) -> Optional[object]:
    """Get raw custom field value; handles dict-with-value pattern."""
    if not field_id:
        return None
    raw = issue.custom_fields.get(field_id)
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("value")
    return raw


def _estado_value(issue: JiraIssue) -> Optional[str]:
    estado = issue.po_estado
    return estado.value if estado else None


# ── Individual KPI computations ───────────────────────────────────────────────

def _kpi_f1_1(issues: list[JiraIssue], config: Config) -> KPIResult:
    """F1.1 — % HUs con DoR >= 11/12"""
    dor_field = config.fields.dor_score
    eligible = [
        i for i in issues
        if _estado_value(i) in _AT_OR_AFTER_DOR_GATE and dor_field
        and _get_cf_value(i, dor_field) is not None
    ]
    n = len(eligible)
    if n == 0:
        return KPIResult("F1.1", "% HUs DoR >= 11/12", "F1", "", ">=90%", 0, "no_data",
                         note="Requiere campo DoR Score en issues con estado >= DOR GATE")
    passed = 0
    for i in eligible:
        raw = _get_cf_value(i, dor_field)
        try:
            if float(raw) >= 11:
                passed += 1
        except (TypeError, ValueError):
            pass
    pct = round(100 * passed / n) if n else 0
    status = "ok" if pct >= 90 else ("warning" if pct >= 72 else "alert")
    return KPIResult("F1.1", "% HUs DoR >= 11/12", "F1", f"{pct}%", ">=90%", n, status)


def _kpi_f1_3(issues: list[JiraIssue]) -> KPIResult:
    """F1.3 — Tiempo medio Intake → Sign-off (días)"""
    deltas: list[int] = []
    for i in issues:
        signoff_date = _parse_section_date(i.description, "SIGN-OFF SH")
        created_date = _parse_created(i.created)
        if signoff_date and created_date:
            deltas.append((signoff_date - created_date).days)
    n = len(deltas)
    if n == 0:
        return KPIResult("F1.3", "Lead time Intake->Sign-off", "F1", "", "<=10 dias", 0, "no_data",
                         note="Requiere sección SIGN-OFF SH en descripción")
    avg = round(sum(deltas) / n, 1)
    status = "ok" if avg <= 10 else ("warning" if avg <= 15 else "alert")
    return KPIResult("F1.3", "Lead time Intake->Sign-off", "F1", f"{avg}d", "<=10d", n, status)


def _kpi_f1_4(issues: list[JiraIssue]) -> KPIResult:
    """F1.4 — % HUs con sign-off escrito"""
    eligible = [i for i in issues if _estado_value(i) in _AT_OR_AFTER_DOR_GATE]
    n = len(eligible)
    if n == 0:
        return KPIResult("F1.4", "% HUs con sign-off escrito", "F1", "", "100%", 0, "no_data",
                         note="Sin issues en estado >= DOR GATE")
    with_signoff = sum(1 for i in eligible if "SIGN-OFF SH" in i.description)
    pct = round(100 * with_signoff / n)
    status = "ok" if pct == 100 else ("warning" if pct >= 80 else "alert")
    return KPIResult("F1.4", "% HUs con sign-off escrito", "F1", f"{pct}%", "100%", n, status)


def _kpi_f1_5(issues: list[JiraIssue]) -> KPIResult:
    """F1.5 — % HUs con handshake formal"""
    eligible = [i for i in issues if _estado_value(i) in _AT_OR_AFTER_HANDSHAKE]
    n = len(eligible)
    if n == 0:
        return KPIResult("F1.5", "% HUs con handshake formal", "F1", "", "100%", 0, "no_data",
                         note="Sin issues en estado >= HANDSHAKE")
    with_hsk = sum(1 for i in eligible if "HANDSHAKE" in i.description)
    pct = round(100 * with_hsk / n)
    status = "ok" if pct == 100 else ("warning" if pct >= 80 else "alert")
    return KPIResult("F1.5", "% HUs con handshake formal", "F1", f"{pct}%", "100%", n, status)


def _kpi_f2_1(issues: list[JiraIssue]) -> KPIResult:
    """F2.1 — Lead time medio Intake → Producción (días)"""
    released = [i for i in issues if _estado_value(i) in _RELEASED_OR_CLOSED]
    deltas: list[int] = []
    for i in released:
        created_date = _parse_created(i.created)
        if not created_date:
            continue
        release_date = _parse_section_date(i.description, "RELEASE")
        if release_date is None:
            # fallback: updated date
            release_date = _parse_created(i.updated)
        if release_date:
            deltas.append((release_date - created_date).days)
    n = len(deltas)
    if n == 0:
        return KPIResult("F2.1", "Lead time Intake->Produccion", "F2", "", "Tendencia estable", 0, "info")
    avg = round(sum(deltas) / n, 1)
    return KPIResult("F2.1", "Lead time Intake->Produccion", "F2", f"{avg}d", "Tendencia estable", n, "info")


def _kpi_f2_2(issues: list[JiraIssue], weeks: int) -> KPIResult:
    """F2.2 — Throughput semanal (HUs/semana) over last `weeks` weeks"""
    today = date.today()
    cutoff = today - timedelta(weeks=weeks)
    released = [
        i for i in issues
        if _estado_value(i) in _RELEASED_OR_CLOSED
    ]
    # Count per week bucket
    weekly: dict[int, int] = {}
    for i in released:
        release_date = _parse_section_date(i.description, "RELEASE")
        if release_date is None:
            release_date = _parse_created(i.updated)
        if release_date and release_date >= cutoff:
            iso_week = release_date.isocalendar()[1]
            # Use (year * 100 + week) as key to avoid year-boundary collisions
            key = release_date.isocalendar()[0] * 100 + iso_week
            weekly[key] = weekly.get(key, 0) + 1
    non_zero = [v for v in weekly.values() if v > 0]
    n_issues = sum(non_zero)
    if not non_zero:
        return KPIResult("F2.2", "Throughput semanal", "F2", "0 HUs/sem", "Tendencia creciente", 0, "info")
    avg = round(sum(non_zero) / len(non_zero), 1)
    return KPIResult("F2.2", "Throughput semanal", "F2", f"{avg} HUs/sem", "Tendencia creciente", n_issues, "info")


def _kpi_f2_3(issues: list[JiraIssue]) -> KPIResult:
    """F2.3 — Aging medio backlog (días)"""
    today = date.today()
    open_issues = [i for i in issues if _estado_value(i) in _OPEN_STATES]
    ages: list[int] = []
    for i in open_issues:
        cd = _parse_created(i.created)
        if cd:
            ages.append((today - cd).days)
    n = len(ages)
    if n == 0:
        return KPIResult("F2.3", "Aging medio backlog", "F2", "", "Descendente", 0, "info")
    avg = round(sum(ages) / n, 1)
    return KPIResult("F2.3", "Aging medio backlog", "F2", f"{avg}d", "Descendente", n, "info")


def _kpi_f3_3(issues: list[JiraIssue]) -> KPIResult:
    """F3.3 — % releases con UAT formal"""
    released = [i for i in issues if _estado_value(i) in _RELEASED_OR_CLOSED]
    n = len(released)
    if n == 0:
        return KPIResult("F3.3", "% releases con UAT formal", "F3", "", ">=95%", 0, "no_data",
                         note="Sin issues en estado RELEASE o CERRADO")
    with_uat = sum(1 for i in released if "UAT" in i.description)
    pct = round(100 * with_uat / n)
    status = "ok" if pct >= 95 else ("warning" if pct >= 80 else "alert")
    return KPIResult("F3.3", "% releases con UAT formal", "F3", f"{pct}%", ">=95%", n, status)


def _kpi_f4_1(issues: list[JiraIssue], config: Config) -> KPIResult:
    """F4.1 — % HUs IA asistida.

    Primary source: custom field ia_asistida = "Sí".
    Fallback for older issues: presence of a DEFINICION section in description,
    which only po define (IA) can create.
    """
    ia_field = config.fields.ia_asistida
    eligible = [i for i in issues if _estado_value(i) in _AT_OR_AFTER_DEFINICION]
    n = len(eligible)
    if n == 0:
        return KPIResult("F4.1", "% HUs IA asistida", "F4", "", "100%", 0, "no_data",
                         note="Sin issues en estado >= DEFINICION")
    ia_ok = {"sí", "si", "yes", "true"}
    ia_count = 0
    for i in eligible:
        raw = _get_cf_value(i, ia_field) if ia_field else None
        if raw is not None and str(raw).strip().lower() in ia_ok:
            ia_count += 1
        elif raw is None and "DEFINICION" in i.description:
            # po define always uses IA — treat DEFINICION section as retroactive proxy
            ia_count += 1
    pct = round(100 * ia_count / n)
    status = "ok" if pct == 100 else ("warning" if pct >= 80 else "alert")
    return KPIResult("F4.1", "% HUs IA asistida", "F4", f"{pct}%", "100%", n, status)


def _kpi_f5_4(issues: list[JiraIssue], config: Config) -> KPIResult:
    """F5.4 — Urgencias declaradas (mes actual)"""
    tipo_field = config.fields.tipo_peticion
    today = date.today()
    this_month_issues = [
        i for i in issues
        if _parse_created(i.created) and _parse_created(i.created).year == today.year
        and _parse_created(i.created).month == today.month
    ]
    total_month = len(this_month_issues)
    if not tipo_field:
        return KPIResult("F5.4", "Urgencias (mes actual)", "F5",
                         f"N/A / {total_month}", "Tendencia descendente", total_month, "info")
    urgencias = sum(
        1 for i in this_month_issues
        if str(_get_cf_value(i, tipo_field) or "").strip().lower() == "urgencia"
    )
    return KPIResult("F5.4", "Urgencias (mes actual)", "F5",
                     f"{urgencias} / {total_month}", "Tendencia descendente", total_month, "info")


# ── Placeholder KPIs (no Jira data) ──────────────────────────────────────────

_NO_DATA_KPIS: list[tuple[str, str, str, str]] = [
    ("F1.2", "% HUs devueltas",          "F1", "Requiere campo 'Motivo devolucion'    | Obj: -40% rel"),
    ("F2.4", "Aging medio PRs",           "F2", "Fuente: GitHub/GitLab                 | Obj: Descendente"),
    ("F3.1", "Rollbacks en produccion",   "F3", "Fuente: registro de releases          | Obj: -50%"),
    ("F3.2", "Defectos en produccion",    "F3", "Fuente: Sentry                        | Obj: Descendente"),
    ("F4.2", "KPI piloto IA",             "F4", "Requiere auditoria manual             | Obj: -25% rel"),
    ("F4.3", "Prompts validados en repo", "F4", "Fuente: repositorio compartido        | Obj: >=20"),
    ("F4.4", "% IA con revisor humano",   "F4", "Requiere campo 'Revisor humano'       | Obj: 100%"),
    ("F5.1", "% peticiones por Jira",     "F5", "Requiere auditoria + encuesta         | Obj: 100%"),
    ("F5.2", "% SLA respuesta <=48h",     "F5", "Requiere historial de comentarios     | Obj: >=95%"),
    ("F5.3", "Asistencia Comite Semanal", "F5", "Fuente: actas de reunion              | Obj: >=90%"),
    ("F6.1", "Pulse check (5 dims)",      "F6", "Fuente: encuesta trimestral           | Obj: >=3.5"),
    ("F6.2", "% tiempo en discovery",     "F6", "Fuente: auto-reporte                  | Obj: >=30%"),
    ("F6.3", "Propuestas resueltas",      "F6", "Requiere auditoria manual             | Obj: >=90%"),
]


def _placeholder_kpis() -> list[KPIResult]:
    results = []
    for kpi_id, name, family, note_target in _NO_DATA_KPIS:
        # Split note | target
        parts = note_target.split("|")
        note = parts[0].strip()
        target = parts[1].replace("Obj:", "").strip() if len(parts) > 1 else ""
        results.append(KPIResult(kpi_id, name, family, "", target, 0, "no_data", note=note))
    return results


# ── Main compute function ─────────────────────────────────────────────────────

def compute_kpis(issues: list[JiraIssue], config: Config, weeks: int = 8) -> list[KPIResult]:
    """Compute all 10 Jira-based KPIs + 13 placeholder KPIs."""
    jira_kpis = [
        _kpi_f1_1(issues, config),
        _kpi_f1_3(issues),
        _kpi_f1_4(issues),
        _kpi_f1_5(issues),
        _kpi_f2_1(issues),
        _kpi_f2_2(issues, weeks),
        _kpi_f2_3(issues),
        _kpi_f3_3(issues),
        _kpi_f4_1(issues, config),
        _kpi_f5_4(issues, config),
    ]
    return jira_kpis + _placeholder_kpis()


# ── Status display ────────────────────────────────────────────────────────────

def _status_markup(status: str) -> str:
    return {
        "ok":      "[green]✓ OK[/green]",
        "warning": "[yellow]! ATENCIÓN[/yellow]",
        "alert":   "[red]✗ ALERTA[/red]",
        "info":    "[cyan]INFO[/cyan]",
        "no_data": "[dim]N/A[/dim]",
    }.get(status, "[dim]?[/dim]")


# ── Terminal dashboard ────────────────────────────────────────────────────────

_FAMILY_LABELS = {
    "F1": "F1 — Calidad de entrada",
    "F2": "F2 — Delivery",
    "F3": "F3 — Calidad de salida",
    "F4": "F4 — IA aplicada al PO",
    "F5": "F5 — Gobernanza",
    "F6": "F6 — Salud organizativa",
}


def _build_family_table(kpis: list[KPIResult], family: str) -> Table:
    label = _FAMILY_LABELS.get(family, family)
    table = Table(
        title=f"[bold]{label}[/bold]",
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style=f"bold dim",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("ID",        width=6,  style="dim")
    table.add_column("KPI",      min_width=28)
    table.add_column("Valor",    width=16, justify="right")
    table.add_column("Objetivo", width=18)
    table.add_column("Muestra",  width=9,  justify="right", style="dim")
    table.add_column("Estado",   width=14, justify="center")

    for kpi in kpis:
        if kpi.family != family:
            continue
        name_cell = kpi.name
        if kpi.status == "no_data" and kpi.note:
            name_cell = f"{kpi.name}\n[dim]{kpi.note}[/dim]"
        value_cell = kpi.value if kpi.value else "[dim]—[/dim]"
        n_cell = str(kpi.n) if kpi.n > 0 else "[dim]—[/dim]"
        table.add_row(
            kpi.kpi_id,
            name_cell,
            value_cell,
            kpi.target,
            n_cell,
            _status_markup(kpi.status),
        )
    return table


def print_dashboard(kpis: list[KPIResult]) -> None:
    """Render the full KPI dashboard to the terminal."""
    from rich.rule import Rule

    families = ["F1", "F2", "F3", "F4", "F5", "F6"]
    for family in families:
        family_kpis = [k for k in kpis if k.family == family]
        if not family_kpis:
            continue
        table = _build_family_table(kpis, family)
        console.print()
        console.print(Padding(table, (0, 2)))

    # Compute groups
    total = len(kpis)
    with_data = [k for k in kpis if k.status != "no_data"]
    on_target = [k for k in with_data if k.status == "ok"]
    alerts = [k for k in with_data if k.status == "alert"]
    warnings = [k for k in with_data if k.status == "warning"]
    no_data_count = total - len(with_data)

    console.print()
    console.print(Rule(style="dim"))
    console.print()

    # Summary table
    summary = Table(box=None, show_header=False, padding=(0, 2))
    summary.add_column(width=26, style="dim")
    summary.add_column()
    summary.add_row("KPIs calculados de Jira", f"{len(with_data)}/{total}")
    summary.add_row("En objetivo", f"[green]{len(on_target)}[/green]")
    if alerts:
        names = ", ".join(k.kpi_id for k in alerts)
        summary.add_row("Con alerta  (ALERTA)", f"[red]{len(alerts)} — {names}[/red]")
    if warnings:
        names = ", ".join(k.kpi_id for k in warnings)
        summary.add_row("Requieren atención", f"[yellow]{len(warnings)} — {names}[/yellow]")
    summary.add_row("Sin datos Jira (N/A)", f"[dim]{no_data_count} — requieren otras fuentes[/dim]")
    console.print(Padding(summary, (0, 2)))

    # Legend
    console.print()
    console.print(Padding(
        "[dim]Leyenda:  [green]✓ OK[/green] en objetivo  "
        "[yellow]! ATENCIÓN[/yellow] por debajo del objetivo  "
        "[red]✗ ALERTA[/red] fuera de objetivo  "
        "[cyan]INFO[/cyan] sin objetivo fijo  "
        "N/A sin datos Jira[/dim]",
        (0, 4)
    ))
    console.print()


# ── Markdown export ───────────────────────────────────────────────────────────

def _status_md(status: str) -> str:
    return {
        "ok":      "✓ OK",
        "warning": "! ATENCIÓN",
        "alert":   "✗ ALERTA",
        "info":    "INFO",
        "no_data": "N/A",
    }.get(status, "?")


def export_markdown(kpis: list[KPIResult], project_key: str, output: Optional[Path] = None) -> Path:
    """Generate a Markdown KPI report and write it to disk. Returns the file path."""
    today_str = date.today().isoformat()
    if output is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output = reports_dir / f"{today_str}-kpis-{project_key}.md"

    with_data = [k for k in kpis if k.status != "no_data"]
    ok_count = sum(1 for k in with_data if k.status == "ok")
    alert_count = sum(1 for k in with_data if k.status == "alert")
    no_data_count = sum(1 for k in kpis if k.status == "no_data")

    lines: list[str] = [
        f"# KPI Dashboard — {project_key}",
        f"",
        f"> Fecha: {today_str}",
        f"",
        f"## Resumen ejecutivo",
        f"",
        f"| Indicador | Valor |",
        f"|---|---|",
        f"| KPIs con datos Jira | {len(with_data)}/23 |",
        f"| En objetivo (OK) | {ok_count}/{len(with_data)} |",
        f"| Con alerta (KO) | {alert_count}/{len(with_data)} |",
        f"| Sin datos Jira | {no_data_count}/23 |",
        f"",
    ]

    families = ["F1", "F2", "F3", "F4", "F5", "F6"]
    for family in families:
        label = _FAMILY_LABELS.get(family, family)
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| ID | KPI | Valor | Obj. M3 | n | Estado |")
        lines.append("|---|---|---|---|---|---|")
        for kpi in kpis:
            if kpi.family != family:
                continue
            note_suffix = f" _(_{kpi.note}_)_" if kpi.note and kpi.status == "no_data" else ""
            lines.append(
                f"| {kpi.kpi_id} | {kpi.name}{note_suffix} | {kpi.value or '—'} "
                f"| {kpi.target} | {kpi.n or '—'} | {_status_md(kpi.status)} |"
            )
        lines.append("")

    # Alertas section
    alerts = [k for k in kpis if k.status == "alert"]
    lines.append("## Alertas")
    lines.append("")
    if alerts:
        for k in alerts:
            lines.append(f"- **{k.kpi_id} — {k.name}**: {k.value} (obj: {k.target})")
    else:
        lines.append("_Sin alertas activas._")
    lines.append("")

    # Próximas acciones
    lines.append("## Proximas acciones")
    lines.append("")
    lines.append("- [ ] Revisar KPIs en alerta con el equipo")
    lines.append("- [ ] Identificar issues bloqueados en backlog (aging alto)")
    lines.append("- [ ] Completar campos custom Jira para KPIs sin datos")
    lines.append("- [ ] Planificar encuesta trimestral (F6.1)")
    lines.append("- [ ] Conectar fuentes externas (GitHub, Sentry) para F2.4, F3.1, F3.2")
    lines.append("")

    lines.append(f"---")
    lines.append(f"*Generado con po-assistant · {today_str}*")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


# ── Entry point ───────────────────────────────────────────────────────────────

def run(
    jira: JiraClient,
    config: Config,
    export: bool = False,
    output: Optional[Path] = None,
    weeks: int = 8,
) -> None:
    """Main entry point called from main.py kpis command."""
    section_rule(f"Cargando issues del proyecto {config.jira_po_project_key}...")
    try:
        issues = jira.get_project_issues()
    except Exception as e:
        console.print(f"  [red]Error cargando issues de Jira: {e}[/red]")
        return

    console.print(f"  [dim]{len(issues)} issues cargados · throughput calculado sobre las últimas {weeks} semanas[/dim]")
    console.print(f"  [dim]Los KPIs marcados N/A requieren fuentes externas (GitHub, Sentry, encuestas)[/dim]\n")

    kpis = compute_kpis(issues, config, weeks=weeks)
    print_dashboard(kpis)

    if export or output:
        md_path = export_markdown(kpis, config.jira_po_project_key, output)
        console.print(f"  [green]Informe exportado:[/green] [cyan]{md_path}[/cyan]\n")
