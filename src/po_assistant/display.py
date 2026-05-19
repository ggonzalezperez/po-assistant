"""
Shared UI components for po-assistant.
Single source of truth for all terminal design: colors, panels, step tracker, cards.
"""

import time
from typing import Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console(force_terminal=True)

# ── Design tokens ────────────────────────────────────────────────────────────

VERSION = "0.1"
TAGLINE = "Asistente IA para Product Owners · Flexicar"

# Colors
C_PRIMARY   = "bright_blue"
C_SUCCESS   = "green"
C_WARNING   = "yellow"
C_ERROR     = "red"
C_CRITICAL  = "bold red"
C_ACCENT    = "cyan"
C_MUTED     = "dim"
C_WHITE     = "white"

# Semantic icons (consistent throughout)
ICON_OK       = "●"
ICON_FAIL     = "○"
ICON_CRITICAL = "◆"
ICON_CURRENT  = "◉"
ICON_ARROW    = "→"
ICON_CHECK    = "✓"
ICON_CROSS    = "✗"
ICON_WARN     = "!"
ICON_SPARK    = "✦"
ICON_DOT      = "·"

PRIORITY_META = {
    "Alta":  ("red",    "▲ ALTA"),
    "Media": ("yellow", "● MEDIA"),
    "Baja":  ("green",  "▼ BAJA"),
}

TYPE_META = {
    "problema":  ("red",          "PROBLEMA"),
    "idea":      ("cyan",         "IDEA"),
    "urgencia":  ("bold red",     "URGENCIA"),
    "mejora":    ("bright_blue",  "MEJORA"),
    "incidencia":("yellow",       "INCIDENCIA"),
}

DOR_CRITICAL_SET = {1, 5, 7, 9, 10, 12}


# ── App chrome ───────────────────────────────────────────────────────────────

def app_header(subtitle: str = "") -> None:
    """Top-of-screen header. Call once per command."""
    console.print()
    _rule_thin()
    name = Text()
    name.append("  po", style=f"bold {C_PRIMARY}")
    name.append("-assistant", style=f"bold {C_WHITE}")
    name.append(f"  v{VERSION}", style=C_MUTED)
    console.print(Align.center(name))
    console.print(Align.center(Text(TAGLINE, style=C_MUTED)))
    if subtitle:
        console.print(Align.center(Text(f"{ICON_SPARK} {subtitle} {ICON_SPARK}", style=f"bold {C_ACCENT}")))
    _rule_thin()
    console.print()


def step_bar(steps: list[str], current: int) -> None:
    """
    Horizontal step tracker. current is 0-based index of the active step.

    Example (3 steps, current=1):
      ● INTAKE  →  ◉ DEFINICIÓN  →  ○ DOR GATE
    """
    parts: list[str] = []
    for i, name in enumerate(steps):
        if i < current:
            parts.append(f"[{C_SUCCESS}]{ICON_CHECK} {name}[/{C_SUCCESS}]")
        elif i == current:
            parts.append(f"[bold {C_PRIMARY}]{ICON_CURRENT} {name}[/bold {C_PRIMARY}]")
        else:
            parts.append(f"[{C_MUTED}]{ICON_FAIL} {name}[/{C_MUTED}]")
    line = f"  [{C_MUTED}]{ICON_ARROW}[/{C_MUTED}]  ".join(parts)
    console.print(Padding(line, (0, 4)))
    console.print()


def section_rule(title: str, icon: str = ICON_DOT) -> None:
    """Thin section divider with label."""
    console.print()
    console.print(Rule(f"[{C_MUTED}]{icon}  {title}  {icon}[/{C_MUTED}]", style=C_MUTED))
    console.print()


# ── Notification banners ─────────────────────────────────────────────────────

def notify_success(message: str, detail: str = "") -> None:
    body = f"[{C_SUCCESS}]{ICON_CHECK}  {message}[/{C_SUCCESS}]"
    if detail:
        body += f"\n[{C_MUTED}]   {detail}[/{C_MUTED}]"
    console.print(Panel(body, border_style=C_SUCCESS, padding=(0, 2), box=box.ROUNDED))


def notify_warning(message: str, detail: str = "") -> None:
    body = f"[{C_WARNING}]{ICON_WARN}  {message}[/{C_WARNING}]"
    if detail:
        body += f"\n[{C_MUTED}]   {detail}[/{C_MUTED}]"
    console.print(Panel(body, border_style=C_WARNING, padding=(0, 2), box=box.ROUNDED))


def notify_error(message: str, detail: str = "") -> None:
    body = f"[{C_ERROR}]{ICON_CROSS}  {message}[/{C_ERROR}]"
    if detail:
        body += f"\n[{C_MUTED}]   {detail}[/{C_MUTED}]"
    console.print(Panel(body, border_style=C_ERROR, padding=(0, 2), box=box.ROUNDED))


# ── Intake card ──────────────────────────────────────────────────────────────

def intake_card(
    titulo: str,
    tipo: str,
    prioridad: str,
    descripcion: str,
    razon_prioridad: str,
    dudas: list[str],
    issue_key: str = "",
) -> None:
    """Full-width card showing the structured result of an intake analysis."""
    type_color, type_label = TYPE_META.get(tipo, (C_WHITE, tipo.upper()))
    prio_color, prio_label = PRIORITY_META.get(prioridad, (C_WHITE, prioridad.upper()))

    # Header row: type badge + priority
    badges = Text()
    badges.append(f"  {type_label}  ", style=f"bold {type_color} on grey15")
    badges.append("   ")
    badges.append(f"  {prio_label}  ", style=f"bold {prio_color} on grey15")
    if issue_key:
        badges.append(f"   [{C_MUTED}]{issue_key}[/{C_MUTED}]")

    # Title
    title_text = Text(f"\n  {titulo}\n", style="bold white")

    # Description
    desc_lines = _wrap(descripcion, 70)
    desc_text = Text("\n".join(f"  {l}" for l in desc_lines), style=C_WHITE)
    desc_text.append(f"\n\n  [{C_MUTED}]{ICON_ARROW} {razon_prioridad}[/{C_MUTED}]")

    content = Group(badges, title_text, desc_text)
    console.print(Panel(content, border_style=C_PRIMARY, box=box.ROUNDED, padding=(1, 1)))

    if dudas:
        console.print(f"  [{C_ACCENT}]{ICON_SPARK} Preguntas abiertas para el PO:[/{C_ACCENT}]")
        for i, d in enumerate(dudas, 1):
            console.print(f"  [{C_MUTED}]  {i}.[/{C_MUTED}] {d}")
    console.print()


def urgencia_card(
    titulo: str,
    descripcion: str,
    impacto: str,
    causa_probable: str,
    accion_correctiva: str,
    rollback: str,
    checks: list[str],
    issue_key: str = "",
) -> None:
    """Full-width card for a production urgency AI brief."""
    badges = Text()
    badges.append("  URGENCIA  ", style="bold white on red")
    badges.append("   ")
    badges.append("  ▲ ALTA  ", style=f"bold {C_ERROR} on grey15")
    if issue_key:
        badges.append(f"   [{C_MUTED}]{issue_key}[/{C_MUTED}]")

    title_text = Text(f"\n  {titulo}\n", style="bold white")

    brief = Table(box=None, show_header=False, padding=(0, 1), expand=True)
    brief.add_column(style=C_MUTED, width=28)
    brief.add_column()
    brief.add_row("Impacto:",           impacto)
    brief.add_row("Causa probable:",    causa_probable)
    brief.add_row("Acción correctiva:", accion_correctiva)
    brief.add_row("Plan de rollback:",  rollback)

    content = Group(badges, title_text, brief)
    console.print(Panel(content, border_style=C_ERROR, box=box.ROUNDED, padding=(1, 1)))

    if checks:
        console.print(f"  [{C_ACCENT}]{ICON_SPARK} Checks de verificación:[/{C_ACCENT}]")
        for i, check in enumerate(checks, 1):
            console.print(f"  [{C_MUTED}]  {i}.[/{C_MUTED}] {check}")
    console.print()


# ── HU preview ───────────────────────────────────────────────────────────────

def hu_preview(hu_text: str, issue_key: str) -> None:
    """Render the HU draft with markdown syntax highlighting inside a panel."""
    console.print(Panel(
        Syntax(hu_text, "markdown", theme="nord", word_wrap=True, background_color="default"),
        title=f"[bold {C_WHITE}]HU Borrador — {issue_key}[/bold {C_WHITE}]",
        subtitle=f"[{C_MUTED}]Revisa y confirma antes de guardar[/{C_MUTED}]",
        border_style=C_PRIMARY,
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()


# ── DoR Gate ─────────────────────────────────────────────────────────────────

def dor_score_bar(score: int, total: int = 12, pasa: bool = True, critico: bool = False) -> None:
    """Visual score bar with pass/fail verdict."""
    BAR_WIDTH = 24
    filled = round((score / total) * BAR_WIDTH)
    empty  = BAR_WIDTH - filled

    if pasa:
        color = C_SUCCESS
    elif critico:
        color = C_ERROR
    else:
        color = C_WARNING

    bar  = f"[{color}]{'█' * filled}[/{color}]"
    bar += f"[{C_MUTED}]{'░' * empty}[/{C_MUTED}]"

    verdict = (
        f"[bold {C_SUCCESS}]{ICON_CHECK} DOR GATE OK[/bold {C_SUCCESS}]" if pasa
        else f"[bold {C_ERROR}]{ICON_CROSS} DOR GATE KO[/bold {C_ERROR}]"
        + (f"  [{C_MUTED}]— bloque crítico fallido[/{C_MUTED}]" if critico else "")
    )

    console.print(f"  {bar}  [{color}]{score}/{total} bloques[/{color}]")
    console.print(f"  {verdict}")
    console.print()


def dor_blocks_table(bloques: list) -> None:
    """Render the DoR block evaluation as a structured table."""
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style=f"bold {C_MUTED}",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("#",     style=C_MUTED, width=4, justify="right")
    table.add_column("Bloque",               min_width=32)
    table.add_column("Estado",               width=14)
    table.add_column("Gap detectado / Acción sugerida")

    for b in bloques:
        num_str = str(b.numero).zfill(2)
        crit_tag = f" [{C_MUTED}]C[/{C_MUTED}]" if b.critico else ""  # C = crítico

        if b.cumple:
            status = f"[{C_SUCCESS}]{ICON_CHECK} OK[/{C_SUCCESS}]"
            detail = f"[{C_MUTED}]—[/{C_MUTED}]"
        elif b.critico:
            status = f"[bold {C_ERROR}]{ICON_CROSS} CRÍTICO[/bold {C_ERROR}]"
            gap    = b.gap or ""
            accion = b.accion or ""
            detail = f"[{C_ERROR}]{gap}[/{C_ERROR}]"
            if accion:
                detail += f"\n[{C_MUTED}]  {ICON_ARROW} {accion}[/{C_MUTED}]"
        else:
            status = f"[{C_WARNING}]{ICON_WARN} Gap[/{C_WARNING}]"
            gap    = b.gap or ""
            accion = b.accion or ""
            detail = gap
            if accion:
                detail += f"\n[{C_MUTED}]  {ICON_ARROW} {accion}[/{C_MUTED}]"

        table.add_row(f"{num_str}{crit_tag}", b.nombre, status, detail)

    console.print(Padding(table, (0, 2)))


def dor_gate_card(issue_key: str, summary: str, bloques: list, score: int, pasa: bool, critico: bool) -> None:
    """Full DoR Gate result card."""
    title_color = C_SUCCESS if pasa else C_ERROR
    title = f"[bold {title_color}]DoR Gate — {issue_key}[/bold {title_color}]"
    subtitle = Text(summary[:70], style=C_MUTED)

    console.print(Panel(
        Group(
            Padding("", (0, 0)),
            Padding(_dor_score_group(score, 12, pasa, critico), (0, 2)),
            Padding(_dor_legend(), (0, 2)),
        ),
        title=title,
        subtitle=subtitle,
        border_style=C_SUCCESS if pasa else C_ERROR,
        box=box.ROUNDED,
        padding=(0, 1),
    ))
    console.print()
    dor_blocks_table(bloques)


def _dor_score_group(score: int, total: int, pasa: bool, critico: bool):
    BAR_WIDTH = 24
    filled = round((score / total) * BAR_WIDTH)
    empty  = BAR_WIDTH - filled
    color  = C_SUCCESS if pasa else (C_ERROR if critico else C_WARNING)

    bar  = f"[{color}]{'█' * filled}[/{color}]"
    bar += f"[{C_MUTED}]{'░' * empty}[/{C_MUTED}]"

    verdict = (
        f"  [{C_SUCCESS}]{ICON_CHECK} PASA — listo para HANDSHAKE[/{C_SUCCESS}]" if pasa
        else f"  [{C_ERROR}]{ICON_CROSS} NO PASA — vuelve a DEFINICIÓN[/{C_ERROR}]"
    )
    return Text.from_markup(
        f"  {bar}  [{color}]{score}/{total}[/{color}]\n{verdict}"
    )


def _dor_legend() -> Text:
    return Text.from_markup(
        f"  [{C_MUTED}][C] = bloque crítico (01, 05, 07, 09, 10, 12) — si falla, KO aunque score ≥ 11[/{C_MUTED}]"
    )


# ── Demo-specific components ─────────────────────────────────────────────────

def demo_welcome() -> None:
    """Full-screen welcome for the CTO demo."""
    console.print()
    _rule_primary()
    console.print()
    console.print(Align.center(Text("po-assistant", style=f"bold {C_PRIMARY}")))
    console.print(Align.center(Text(TAGLINE, style=C_MUTED)))
    console.print()
    console.print(Align.center(Text("Demo — Prototipo Fase 0", style=f"bold {C_ACCENT}")))
    console.print()
    _rule_primary()
    console.print()

    story = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    story.add_column(width=3)
    story.add_column()
    story.add_row(f"[{C_MUTED}]1.[/{C_MUTED}]", f"[{C_WHITE}]María Ruiz (responsable de operaciones) llama al PO y describe un problema en el CRM.[/{C_WHITE}]")
    story.add_row(f"[{C_MUTED}]2.[/{C_MUTED}]", f"[{C_WHITE}]El PO usa [bold]po intake[/bold] — la IA clasifica, estructura y crea el ticket en Jira.[/{C_WHITE}]")
    story.add_row(f"[{C_MUTED}]3.[/{C_MUTED}]", f"[{C_WHITE}]El PO usa [bold]po define[/bold] — la IA genera la HU completa (6 bloques + criterios de aceptación).[/{C_WHITE}]")
    story.add_row(f"[{C_MUTED}]4.[/{C_MUTED}]", f"[{C_WHITE}]El PO usa [bold]po dor-gate[/bold] — la IA valida los 12 bloques del DoR automáticamente.[/{C_WHITE}]")

    console.print(Panel(
        story,
        title=f"[bold {C_WHITE}]Escenario de la demo[/bold {C_WHITE}]",
        border_style=C_MUTED,
        box=box.ROUNDED,
        padding=(1, 0),
    ))
    console.print()


def demo_scenario_card(text: str) -> None:
    """Show the raw request that triggered the demo."""
    console.print(Panel(
        Padding(Text(f'"{text}"', style="italic white"), (1, 2)),
        title=f"[{C_MUTED}]Petición recibida de María Ruiz[/{C_MUTED}]",
        border_style=C_MUTED,
        box=box.ROUNDED,
    ))
    console.print()


def demo_summary(issue_key: str, jira_url: str, score: int, elapsed: float) -> None:
    """Final summary card after the demo completes."""
    console.print()
    _rule_primary()
    console.print()

    elapsed_str = f"{elapsed:.0f}s" if elapsed < 60 else f"{elapsed/60:.1f}min"

    summary = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    summary.add_column(width=22, style=C_MUTED)
    summary.add_column()
    summary.add_row("Issue creado",     f"[bold {C_WHITE}]{issue_key}[/bold {C_WHITE}]")
    summary.add_row("HU generada",      f"[{C_SUCCESS}]{ICON_CHECK} 6 bloques completos[/{C_SUCCESS}]")
    summary.add_row("DoR Gate",         f"[{C_SUCCESS}]{ICON_CHECK} {score}/12 bloques OK[/{C_SUCCESS}]")
    summary.add_row("Tiempo total",     f"[bold {C_WHITE}]{elapsed_str}[/bold {C_WHITE}]")
    summary.add_row("Siguiente paso",   f"[{C_ACCENT}]po handshake {issue_key}[/{C_ACCENT}]")

    console.print(Panel(
        Group(
            Padding(summary, (1, 0)),
            Padding(Text.from_markup(
                f"  [{C_MUTED}]Jira → [link={jira_url}]{jira_url}[/link][/{C_MUTED}]"
            ), (0, 0)),
        ),
        title=f"[bold {C_SUCCESS}]{ICON_SPARK} Demo completada[/bold {C_SUCCESS}]",
        border_style=C_SUCCESS,
        box=box.ROUNDED,
        padding=(0, 0),
    ))

    console.print()
    _help_row([
        ("po dashboard", "ver el pipeline"),
        ("po dor-gate " + issue_key, "re-evaluar DoR"),
        ("po define " + issue_key, "regenerar HU"),
    ])
    console.print()


def _help_row(commands: list[tuple[str, str]]) -> None:
    """Compact command hint row at the bottom of a screen."""
    parts = "   ".join(
        f"[bold {C_ACCENT}]{cmd}[/bold {C_ACCENT}] [{C_MUTED}]{desc}[/{C_MUTED}]"
        for cmd, desc in commands
    )
    console.print(Padding(parts, (0, 2)))


# ── Dashboard components ──────────────────────────────────────────────────────

def pipeline_table(rows: list[dict], project_key: str, now_str: str) -> None:
    """
    rows: list of {label, display, count, oldest, color, alerts}
    'oldest' is the age of the oldest issue currently in that state (e.g. "3d", "2w").
    """
    table = Table(
        title=f"[bold {C_WHITE}]Pipeline — {project_key}[/bold {C_WHITE}]   [{C_MUTED}]{now_str}[/{C_MUTED}]",
        caption=f"[{C_MUTED}]'Issue más viejo' = antigüedad del ticket más antiguo en ese estado · SLA: INTAKE >48h · SIGN-OFF >5d · DOR GATE >2d[/{C_MUTED}]",
        box=box.ROUNDED,
        show_lines=False,
        header_style=f"bold {C_MUTED}",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Estado",         min_width=18)
    table.add_column("Issues",         justify="right", width=8)
    table.add_column("Issue más viejo", width=16)
    table.add_column("Alertas SLA")

    for row in rows:
        color = row["color"]
        count = row["count"]
        oldest_cell = f"[{C_MUTED}]{row['oldest']}[/{C_MUTED}]" if row["oldest"] else f"[{C_MUTED}]—[/{C_MUTED}]"
        table.add_row(
            f"[{color}]{row['display']}[/{color}]",
            f"[bold]{count}[/bold]" if count > 0 else f"[{C_MUTED}]—[/{C_MUTED}]",
            oldest_cell,
            row["alerts"],
        )

    console.print()
    console.print(Padding(table, (0, 2)))


def dashboard_summary_panel(
    project_key: str,
    now_str: str,
    total: int,
    active: int,
    in_dev: int,
    sla_alerts: int,
    unassigned: int,
    pipeline_counts: list[tuple[str, str, int]],  # (display_name, color, count)
) -> None:
    """Render the top-of-dashboard summary panel with key metrics and mini pipeline."""
    # ── Key metrics: número grande + etiqueta debajo ───────────────────────────
    metrics = Table(box=None, show_header=False, padding=(0, 3), expand=True)
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")
    metrics.add_column(justify="center")

    sla_style   = "bold red"    if sla_alerts > 0 else "bold white"
    unas_style  = "bold yellow" if unassigned > 0 else "bold white"
    sla_prefix  = "⚠ "         if sla_alerts > 0 else ""
    unas_prefix = "! "          if unassigned > 0 else ""

    metrics.add_row(
        f"[bold white]{active}[/bold white]",
        f"[bold white]{in_dev}[/bold white]",
        f"[{sla_style}]{sla_prefix}{sla_alerts}[/{sla_style}]",
        f"[{unas_style}]{unas_prefix}{unassigned}[/{unas_style}]",
    )
    metrics.add_row(
        f"[{C_MUTED}]activos en pipeline[/{C_MUTED}]",
        f"[{C_MUTED}]en desarrollo[/{C_MUTED}]",
        f"[{C_MUTED}]SLA en alerta[/{C_MUTED}]",
        f"[{C_MUTED}]sin asignar[/{C_MUTED}]",
    )

    # ── Mini pipeline: dos filas de 5 estados ─────────────────────────────────
    def _state_cell(name: str, color: str, count: int) -> str:
        if count > 0:
            return f"[{color}]{name}[/{color}] [bold {color}]{count}[/bold {color}]"
        return f"[{C_MUTED}]{name} —[/{C_MUTED}]"

    row1 = pipeline_counts[:5]
    row2 = pipeline_counts[5:]

    pipeline_table_inner = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    for _ in range(5):
        pipeline_table_inner.add_column(justify="left")
    pipeline_table_inner.add_row(*[_state_cell(n, c, v) for n, c, v in row1])
    pipeline_table_inner.add_row(*[_state_cell(n, c, v) for n, c, v in row2])

    content = Group(
        Padding(metrics, (0, 0)),
        Padding(Rule(style=C_MUTED), (1, 0, 0, 0)),
        Padding(pipeline_table_inner, (1, 0)),
    )

    console.print(Panel(
        content,
        title=f"[bold {C_WHITE}]Pipeline {project_key}[/bold {C_WHITE}]   [{C_MUTED}]{now_str}[/{C_MUTED}]",
        border_style=C_PRIMARY,
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()


def dashboard_estado_block(
    display_name: str,
    color: str,
    issues: list[dict],
    sla_label: str = "",
) -> None:
    """
    Render one Kanban state block for the expanded dashboard view.

    Each dict in `issues` has:
        key, tipo, summary, age, assignee, reporter (all str), sla_alert (bool)
    """
    n = len(issues)
    issue_word = "issue" if n == 1 else "issues"
    header = f"  [{color}]{display_name}[/{color}]  [{C_MUTED}]·  {n} {issue_word}[/{C_MUTED}]"
    if sla_label:
        header += f"  [{C_MUTED}]·  SLA {sla_label}[/{C_MUTED}]"
    console.print(header)

    if n == 0:
        console.print(f"  [{C_MUTED}]──── vacío[/{C_MUTED}]")
        console.print()
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
        expand=True,
    )
    table.add_column("Ticket",      style=C_ACCENT, width=9)
    table.add_column("Tipo",        width=14)
    table.add_column("Descripción", min_width=38)
    table.add_column("Edad",        justify="right", width=14)
    table.add_column("Asignado",    style=C_MUTED,   width=20)
    table.add_column("Informador",  style=C_MUTED,   width=20)

    for issue in issues:
        tipo_raw = issue.get("tipo", "")
        if tipo_raw:
            type_color, type_label = TYPE_META.get(tipo_raw, (None, tipo_raw.upper()))
            if type_color:
                tipo_cell = f"[{type_color}][{type_label}][/{type_color}]"
            else:
                tipo_cell = f"[{C_MUTED}][{type_label}][/{C_MUTED}]"
        else:
            tipo_cell = f"[{C_MUTED}]—[/{C_MUTED}]"

        summary_raw = issue.get("summary", "")
        summary_cell = summary_raw[:58] + "…" if len(summary_raw) > 58 else summary_raw

        age_raw = issue.get("age", "")
        age_cell = (
            f"[red]{age_raw} ⚠ SLA[/red]" if issue.get("sla_alert")
            else f"[{C_MUTED}]{age_raw}[/{C_MUTED}]"
        )

        assignee_raw = issue.get("assignee", "")
        assignee_cell = assignee_raw if assignee_raw else f"[{C_MUTED}]sin asignar[/{C_MUTED}]"

        reporter_raw = issue.get("reporter", "")
        reporter_cell = reporter_raw if reporter_raw else f"[{C_MUTED}]—[/{C_MUTED}]"

        table.add_row(issue["key"], tipo_cell, summary_cell, age_cell, assignee_cell, reporter_cell)

    console.print(Padding(table, (0, 4)))
    console.print()


# ── Internal helpers ─────────────────────────────────────────────────────────

def _rule_thin() -> None:
    console.print(Rule(style=C_MUTED))


def _rule_primary() -> None:
    console.print(Rule(style=C_PRIMARY))


def _wrap(text: str, width: int) -> list[str]:
    """Simple word-wrap."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).lstrip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def confirm(prompt: str, default: bool = True) -> bool:
    """Styled confirmation prompt. Accepts s/y (yes) or n (no), both languages."""
    import typer
    hint = "S/n" if default else "s/N"
    console.print(f"  [{C_ACCENT}]{ICON_ARROW}[/{C_ACCENT}] {prompt} [{C_MUTED}][{hint}][/{C_MUTED}]: ", end="")
    try:
        answer = input().strip().strip("﻿").lower()
    except (EOFError, KeyboardInterrupt):
        raise typer.Abort()
    if not answer:
        return default
    return answer in ("s", "si", "sí", "y", "yes")
