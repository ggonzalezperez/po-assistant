import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, dor_gate_card, notify_success, notify_error,
    confirm, C_MUTED, C_ACCENT, C_WARNING,
)
from ..jira_client import JiraClient
from ..models import (
    DOR_BLOCK_NAMES, DOR_CRITICAL_BLOCKS, DorBlockResult, DorGateResult, POEstado,
)


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> DorGateResult:
    """
    Validates the 12 DoR blocks for the given issue using AI.
    Updates Jira with the result and transitions the PO state.
    Returns the DorGateResult.
    """
    section_rule(f"DoR Gate — {issue_key}")

    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")

    if not issue.description or len(issue.description.strip()) < 100:
        notify_error(
            "Descripción insuficiente para evaluar el DoR.",
            f"Ejecuta primero [{C_ACCENT}]po define {issue_key}[/{C_ACCENT}].",
        )
        raise typer.Exit(1)

    hu_text = f"Título: {issue.summary}\n\n{issue.description}"

    data = ai.call_json(
        "dor_validate.md",
        {
            "USER_INPUT": "Evalúa la HU según las instrucciones del sistema.",
            "HU_TEXT": hu_text,
        },
        max_tokens=4096,
    )

    result = _parse_result(data)

    dor_gate_card(
        issue_key=issue_key,
        summary=issue.summary,
        bloques=result.bloques,
        score=result.score,
        pasa=result.pasa,
        critico=result.critico_fallido,
    )

    if not confirm("¿Registrar este resultado en Jira?", default=True):
        console.print(f"  [{C_MUTED}]Resultado no guardado.[/{C_MUTED}]\n")
        return result

    jira.add_comment(issue_key, result.comentario_jira())

    extra_fields: dict = {}
    if config.fields.dor_score:
        extra_fields[config.fields.dor_score] = float(result.score)
    if config.fields.dor_gaps and not result.pasa:
        gaps = "; ".join(
            f"B{b.numero}: {b.gap}" for b in result.bloques if not b.cumple and b.gap
        )
        extra_fields[config.fields.dor_gaps] = gaps[:255]
    if extra_fields:
        try:
            jira.update_issue(issue_key, extra_fields)
        except Exception:
            pass  # custom fields not on screen in Jira Free — non-blocking

    if result.pasa:
        jira.transition_po_state(issue_key, POEstado.DOR_GATE)
        notify_success(
            f"DoR Gate OK ({result.score}/12). Estado → DOR GATE.",
            f"Siguiente: [bold {C_ACCENT}]po handshake {issue_key}[/bold {C_ACCENT}]",
        )
    else:
        jira.transition_po_state(issue_key, POEstado.DEFINICION)
        notify_error(
            f"DoR Gate KO ({result.score}/12). Estado → DEFINICIÓN.",
            f"[{C_MUTED}]Sin reproche. La HU vuelve cuando estén cerrados los gaps.[/{C_MUTED}]",
        )

    console.print()
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
