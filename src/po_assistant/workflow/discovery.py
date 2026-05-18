from datetime import datetime
from pathlib import Path

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, append_section


def _extract_intake_text(description: str) -> str:
    return description[:800] if description else ""


def _build_answers_text(answers: dict) -> str:
    fields = [
        ("Problema real", "problema_real"),
        ("Frecuencia y volumen", "frecuencia"),
        ("Usuario directo (rol)", "usuario_directo"),
        ("Stakeholder solicitante", "solicitante"),
        ("Validador UAT", "validador_uat"),
        ("Cómo se resuelve hoy", "situacion_actual"),
        ("Qué duele del proceso actual", "que_duele"),
        ("Por qué importa (objetivo estratégico)", "por_que_importa"),
        ("Consecuencia de no hacer nada", "consecuencia"),
        ("Restricciones / reglas de negocio", "restricciones"),
        ("Riesgos y dudas abiertas", "riesgos"),
    ]
    lines = []
    for label, key in fields:
        value = answers.get(key, "").strip()
        lines.append(f"{label}: {value if value else '[sin respuesta]'}")
    return "\n".join(lines)


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Discovery — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]")
    console.print(f"  [{C_MUTED}]Vamos a completar la Ficha Previa de Análisis.[/{C_MUTED}]\n")

    if len((issue.description or "").strip()) < 30:
        notify_warning("El ticket tiene poca información.", "Se recomienda haber completado el intake primero.")

    console.print(f"  [{C_ACCENT}]Sección 1 — Problema real[/{C_ACCENT}]")
    problema_real = ask(
        "¿Cuál es el problema real detrás de esta petición?",
        "Descríbelo sin mencionar la solución. Ej: 'Los agentes pierden tiempo buscando cómo cancelar reservas.'"
    )
    frecuencia = ask(
        "¿Con qué frecuencia ocurre y a cuántos usuarios afecta?",
        "Ej: '10-15 veces al día en tiendas grandes, ~50 agentes afectados'"
    )

    console.print()
    console.print(f"  [{C_ACCENT}]Sección 2 — Personas[/{C_ACCENT}]")
    usuario_directo = ask("¿Quién sufre este problema día a día? (rol, no nombre)", "Ej: agente comercial de tienda")
    solicitante = ask("¿Quién lo solicitó? (nombre, rol, área)", "Ej: María Ruiz, Responsable de Operaciones")
    validador_uat = ask(
        "¿Quién puede validar en UAT cuando esté listo?",
        "Ej: Luis Pérez, encargado de tienda piloto"
    )

    console.print()
    console.print(f"  [{C_ACCENT}]Sección 3 — Situación actual[/{C_ACCENT}]")
    situacion_actual = ask_multiline(
        "¿Cómo se resuelve hoy este problema?",
        "Describe el flujo actual paso a paso"
    )
    que_duele = ask("¿Qué duele específicamente del proceso actual?")

    console.print()
    console.print(f"  [{C_ACCENT}]Sección 4 — Por qué importa[/{C_ACCENT}]")
    por_que_importa = ask(
        "¿Qué objetivo estratégico conecta con esta petición?",
        "Ej: reducción de carga de soporte, mejora NPS agentes, eficiencia operativa"
    )
    consecuencia = ask("¿Qué pasa si no hacemos nada?")

    console.print()
    console.print(f"  [{C_ACCENT}]Sección 5 — Restricciones y riesgos[/{C_ACCENT}]")
    restricciones = ask(
        "¿Hay reglas de negocio o limitaciones técnicas mencionadas?",
        "Ej: no puede tocar contratos, depende de integración con JATO. Si no hay, escribe 'ninguna'"
    )
    riesgos = ask(
        "¿Qué dudas o riesgos quedan abiertos?",
        "Ej: no sabemos si el validador UAT estará disponible en junio"
    )

    answers = {
        "problema_real": problema_real,
        "frecuencia": frecuencia,
        "usuario_directo": usuario_directo,
        "solicitante": solicitante,
        "validador_uat": validador_uat,
        "situacion_actual": situacion_actual,
        "que_duele": que_duele,
        "por_que_importa": por_que_importa,
        "consecuencia": consecuencia,
        "restricciones": restricciones,
        "riesgos": riesgos,
    }

    console.print()
    ficha_md = ai.call(
        "discovery_ficha.md",
        {
            "USER_INPUT": "Genera la ficha previa de análisis.",
            "TITULO": issue.summary,
            "INTAKE_TEXT": _extract_intake_text(issue.description or ""),
            "RESPUESTAS_PO": _build_answers_text(answers),
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "PO_AUTOR": config.jira_email,
            "ISSUE_KEY": issue_key,
            "PETICION_ORIGINAL": issue.description[:300] if issue.description else "",
            "SOLICITANTE": solicitante,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=4000,
    )

    section_rule("Vista previa — Ficha Previa de Análisis")
    for line in ficha_md.splitlines()[:40]:
        console.print(f"  {line}")
    if len(ficha_md.splitlines()) > 40:
        console.print(f"  [{C_MUTED}]... (ver completo en Jira)[/{C_MUTED}]")
    console.print()
    console.print(f"  [{C_MUTED}]Podrás editar la ficha directamente en el ticket Jira.[/{C_MUTED}]\n")

    if not confirm("¿Guardar la ficha previa en Jira?", default=True):
        filename = f"{issue_key}-ficha-previa.md"
        Path(filename).write_text(ficha_md, encoding="utf-8")
        console.print(f"  [{C_MUTED}]Guardado localmente en {filename}[/{C_MUTED}]\n")
        raise typer.Abort()

    append_section(jira, issue_key, "DISCOVERY — Ficha Previa", ficha_md)
    jira.transition_po_state(issue_key, POEstado.DISCOVERY)
    jira.add_comment(
        issue_key,
        f"## Ficha Previa — po-assistant\n\n"
        f"- Modelo: `{config.claude_model}`\n"
        f"- **Revisor humano: [PENDIENTE — añade tu nombre en Trazabilidad IA]**\n\n"
        f"Siguiente: `po define {issue_key}`"
    )

    notify_success(
        f"Ficha Previa guardada en {issue_key}. Estado → DISCOVERY.",
        f"Siguiente: [{C_ACCENT}]po define {issue_key}[/{C_ACCENT}]",
    )
    console.print()
