import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..ai_client import AIClient
from ..config import Config
from ..jira_client import JiraClient
from ..models import (
    DOR_BLOCK_NAMES, DOR_CRITICAL_BLOCKS, DorBlockResult, DorGateResult, POEstado
)

console = Console()


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> DorGateResult:
    """
    Validates the 12 DoR blocks for the given issue using AI.
    Updates Jira with the result (comment + label transition).
    Returns the DorGateResult.
    """
    console.print(f"\n[bold]Cargando issue {issue_key} para DoR Gate…[/bold]")
    issue = jira.get_issue(issue_key)

    if not issue.description or len(issue.description.strip()) < 100:
        console.print(
            "[red]❌ El issue no tiene descripción suficiente para evaluar el DoR.\n"
            "Ejecuta primero `po define " + issue_key + "` para generar la HU.[/red]"
        )
        raise typer.Exit(1)

    hu_text = f"Título: {issue.summary}\n\n{issue.description}"

    console.print("[bold]Validando 12 bloques del DoR con IA…[/bold]")
    data = ai.call_json(
        "dor_validate.md",
        {
            "USER_INPUT": "Evalúa la HU según las instrucciones del sistema.",
            "HU_TEXT": hu_text,
        },
        max_tokens=4096,
    )

    result = _parse_result(data)
    _display_result(issue_key, issue.summary, result)

    if not typer.confirm(
        "\n¿Registrar este resultado en Jira?", default=True
    ):
        console.print("[yellow]Resultado no guardado.[/yellow]")
        return result

    comment = result.comentario_jira()
    jira.add_comment(issue_key, comment)

    extra_fields: dict = {}
    if config.fields.dor_score:
        extra_fields[config.fields.dor_score] = float(result.score)
    if config.fields.dor_gaps and not result.pasa:
        gaps_text = "; ".join(
            f"B{b.numero}: {b.gap}" for b in result.bloques if not b.cumple and b.gap
        )
        extra_fields[config.fields.dor_gaps] = gaps_text[:255]
    if extra_fields:
        jira.update_issue(issue_key, extra_fields)

    if result.pasa:
        jira.transition_po_state(issue_key, POEstado.DOR_GATE)
        console.print(f"\n[bold green]✅ DoR Gate OK ({result.score}/12). "
                      f"Estado → DOR GATE.[/bold green]")
        console.print(f"Siguiente: [bold]po handshake {issue_key}[/bold]\n")
    else:
        jira.transition_po_state(issue_key, POEstado.DEFINICION)
        console.print(f"\n[bold red]❌ DoR Gate KO ({result.score}/12). "
                      f"Estado → DEFINICIÓN.[/bold red]")
        console.print("[yellow]Sin reproche. La HU vuelve cuando estén cerrados los gaps.[/yellow]\n")

    return result


def _parse_result(data: dict) -> DorGateResult:
    bloques: list[DorBlockResult] = []
    for b in data.get("bloques", []):
        num = int(b["numero"])
        bloques.append(DorBlockResult(
            numero=num,
            nombre=DOR_BLOCK_NAMES.get(num, f"Bloque {num}"),
            cumple=bool(b["cumple"]),
            critico=num in DOR_CRITICAL_BLOCKS,
            gap=b.get("gap"),
            accion=b.get("accion"),
        ))

    # Sort by block number in case AI returns out of order
    bloques.sort(key=lambda x: x.numero)

    score = int(data.get("score", sum(1 for b in bloques if b.cumple)))
    bloques_fallidos = [b.numero for b in bloques if not b.cumple]
    critico_fallido = any(b.numero in DOR_CRITICAL_BLOCKS for b in bloques if not b.cumple)
    pasa = score >= 11 and not critico_fallido

    return DorGateResult(
        score=score,
        bloques=bloques,
        pasa=pasa,
        critico_fallido=critico_fallido,
        bloques_fallidos=bloques_fallidos,
    )


def _display_result(issue_key: str, summary: str, result: DorGateResult) -> None:
    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("Bloque", width=40)
    table.add_column("Estado", width=14)
    table.add_column("Gap / Acción")

    for b in result.bloques:
        if b.cumple:
            status = "[green]✅ OK[/green]"
            detail = ""
        elif b.critico:
            status = "[bold red]❌ CRÍTICO[/bold red]"
            detail = f"[red]{b.gap or ''}[/red]\n[dim]{b.accion or ''}[/dim]"
        else:
            status = "[yellow]⚠️  Gap[/yellow]"
            detail = f"{b.gap or ''}\n[dim]{b.accion or ''}[/dim]"

        table.add_row(str(b.numero).zfill(2), b.nombre, status, detail)

    score_color = "green" if result.pasa else "red"
    verdict = (
        f"[bold green]DOR GATE OK ✅ ({result.score}/12)[/bold green]"
        if result.pasa else
        f"[bold red]DOR GATE KO ❌ ({result.score}/12)[/bold red]"
    )
    if result.critico_fallido:
        verdict += " [red]— bloque crítico fallido[/red]"

    console.print(Panel(
        table,
        title=f"[bold]DoR Gate — {issue_key}[/bold] · {summary[:60]}",
        subtitle=verdict,
        border_style=score_color,
    ))
