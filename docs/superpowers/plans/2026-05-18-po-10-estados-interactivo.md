# po-assistant — Asistente interactivo para los 10 estados del flujo PO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender po-assistant para asistir al PO en los 10 estados del flujo (INTAKE→RELEASE), con Q&A interactivo guiado por las plantillas de Flexicar, contenido acumulativo en el ticket Jira, y IA que estructura sin inventar.

**Architecture:** Cada estado tiene su propio módulo `workflow/<state>.py` que hace Q&A interactivo, llama a la IA para formatear las respuestas según la plantilla correspondiente, y añade un bloque `## ESTADO — YYYY-MM-DD` al final de la descripción del ticket Jira (acumulativo). La infraestructura compartida vive en `workflow/qa.py` (`ask()`, `append_section()`). El flujo de definición existente se actualiza para usar el mismo patrón acumulativo.

**Tech Stack:** Python 3.11+, Typer, Rich, Anthropic SDK (`claude-sonnet-4-6`), Jira REST API v3 (ADF descriptions), `unittest.mock` para tests, `pytest`.

---

## File Structure

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `src/po_assistant/workflow/qa.py` | Crear | `ask()`, `ask_multiline()`, `ask_choice()`, `append_section()` |
| `src/po_assistant/workflow/triage.py` | Crear | Flujo TRIAGE: árbol de decisión |
| `src/po_assistant/workflow/discovery.py` | Crear | Flujo DISCOVERY: Q&A ficha previa |
| `src/po_assistant/workflow/signoff.py` | Crear | Flujo SIGN-OFF SH: documento sign-off |
| `src/po_assistant/workflow/handshake.py` | Crear | Flujo HANDSHAKE: acta handshake |
| `src/po_assistant/workflow/uat.py` | Crear | Flujo UAT: acta UAT |
| `src/po_assistant/workflow/release.py` | Crear | Flujo RELEASE: checklist release |
| `src/po_assistant/prompts/triage_decide.md` | Crear | Prompt IA: formatear decisión de triage |
| `src/po_assistant/prompts/discovery_ficha.md` | Crear | Prompt IA: formatear ficha previa |
| `src/po_assistant/prompts/signoff_doc.md` | Crear | Prompt IA: generar documento sign-off |
| `src/po_assistant/prompts/handshake_acta.md` | Crear | Prompt IA: generar acta handshake |
| `src/po_assistant/prompts/uat_acta.md` | Crear | Prompt IA: generar acta UAT |
| `src/po_assistant/prompts/release_check.md` | Crear | Prompt IA: generar checklist release |
| `src/po_assistant/main.py` | Modificar | Añadir 6 nuevos comandos |
| `src/po_assistant/workflow/intake.py` | Modificar | Cambiar hint "siguiente paso" a `po triage` |
| `src/po_assistant/workflow/definition.py` | Modificar | Usar `append_section()` en lugar de reemplazar la descripción |
| `tests/test_qa_helpers.py` | Crear | Tests para `append_section()` y helpers puros |
| `tests/test_triage.py` | Crear | Tests para lógica de decisión de triage |

---

## Task 1: Infraestructura Q&A compartida (`workflow/qa.py`)

**Files:**
- Create: `src/po_assistant/workflow/qa.py`
- Create: `tests/test_qa_helpers.py`

- [ ] **Step 1: Escribir tests que fallan**

```python
# tests/test_qa_helpers.py
from unittest.mock import MagicMock, patch
from po_assistant.workflow.qa import append_section, _build_section_header


def _make_issue(description: str) -> MagicMock:
    issue = MagicMock()
    issue.description = description
    return issue


def test_append_section_empty_description():
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue("")
    
    append_section(jira, "FP-1", "TRIAGE", "Decisión: entra a Discovery.")
    
    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    # Verify description ADF was passed
    assert "description" in fields
    # The ADF content node text should contain our section
    adf = fields["description"]
    import json
    adf_text = json.dumps(adf)
    assert "TRIAGE" in adf_text
    assert "Decisión: entra a Discovery." in adf_text


def test_append_section_adds_to_existing():
    existing = "## INTAKE — 2026-05-18\n\nPetición original aquí."
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue(existing)
    
    append_section(jira, "FP-1", "TRIAGE", "Entra a Discovery.")
    
    call_args = jira.update_issue.call_args
    fields = call_args[0][1]
    adf = fields["description"]
    import json
    adf_text = json.dumps(adf)
    assert "INTAKE" in adf_text
    assert "TRIAGE" in adf_text


def test_build_section_header_format():
    header = _build_section_header("DISCOVERY", "2026-05-20")
    assert header == "## DISCOVERY — 2026-05-20"


def test_append_section_date_in_header():
    jira = MagicMock()
    jira.get_issue.return_value = _make_issue("")
    
    with patch("po_assistant.workflow.qa.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-05-20"
        append_section(jira, "FP-1", "DISCOVERY", "Ficha aquí.")
    
    call_args = jira.update_issue.call_args
    adf_text = str(call_args)
    assert "2026-05-20" in adf_text
```

- [ ] **Step 2: Verificar que los tests fallan**

```
cd C:\ggpGithub\Flexicar\po-assistant
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_qa_helpers.py -v
```

Expected: `ModuleNotFoundError: No module named 'po_assistant.workflow.qa'`

- [ ] **Step 3: Implementar `workflow/qa.py`**

```python
# src/po_assistant/workflow/qa.py
from datetime import datetime

import typer

from ..display import console, C_ACCENT, C_MUTED, C_PRIMARY
from ..jira_client import JiraClient, md_to_adf


def ask(question: str, hint: str = "") -> str:
    """Display a question and return the PO's one-line answer."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    if hint:
        console.print(f"  [{C_MUTED}]{hint}[/{C_MUTED}]")
    console.print(f"  [{C_ACCENT}]→[/{C_ACCENT}] ", end="")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        raise typer.Abort()


def ask_multiline(question: str, hint: str = "") -> str:
    """Display a question expecting multiline input; blank line ends input."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    if hint:
        console.print(f"  [{C_MUTED}]{hint}[/{C_MUTED}]")
    console.print(f"  [{C_MUTED}](línea en blanco para terminar)[/{C_MUTED}]")
    lines: list[str] = []
    while True:
        console.print(f"  [{C_ACCENT}]·[/{C_ACCENT}] ", end="")
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def ask_choice(question: str, options: list[tuple[str, str]]) -> int:
    """Show numbered options, return chosen index (1-based)."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    for i, (short, desc) in enumerate(options, 1):
        console.print(f"  [{C_ACCENT}]{i}.[/{C_ACCENT}] {short}")
        if desc:
            console.print(f"     [{C_MUTED}]{desc}[/{C_MUTED}]")
    while True:
        console.print(f"  [{C_ACCENT}]→[/{C_ACCENT}] ", end="")
        try:
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            raise typer.Abort()
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx
        except ValueError:
            pass
        console.print(f"  [{C_MUTED}]Elige un número del 1 al {len(options)}[/{C_MUTED}]")


def _build_section_header(state: str, date_str: str) -> str:
    return f"## {state} — {date_str}"


def append_section(jira: JiraClient, issue_key: str, section_title: str, content: str) -> None:
    """Append a markdown section to the Jira ticket description (cumulative)."""
    issue = jira.get_issue(issue_key)
    current_text = issue.description or ""
    date_str = datetime.now().strftime("%Y-%m-%d")
    header = _build_section_header(section_title, date_str)
    new_section = f"{header}\n\n{content}"
    separator = "\n\n---\n\n"
    full_text = (current_text + separator + new_section) if current_text.strip() else new_section
    jira.update_issue(issue_key, {"description": md_to_adf(full_text)})
```

- [ ] **Step 4: Verificar que los tests pasan**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_qa_helpers.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```
git add src/po_assistant/workflow/qa.py tests/test_qa_helpers.py
git commit -m "feat: add shared Q&A infrastructure (ask, append_section)"
```

---

## Task 2: AI Prompts para los nuevos estados

**Files:**
- Create: `src/po_assistant/prompts/triage_decide.md`
- Create: `src/po_assistant/prompts/discovery_ficha.md`
- Create: `src/po_assistant/prompts/signoff_doc.md`
- Create: `src/po_assistant/prompts/handshake_acta.md`
- Create: `src/po_assistant/prompts/uat_acta.md`
- Create: `src/po_assistant/prompts/release_check.md`

- [ ] **Step 1: Crear `prompts/triage_decide.md`**

```markdown
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es formatear la decisión de triage del PO en un comentario claro y trazable para el ticket Jira.

## Reglas
1. NO inventes información. Usa solo lo que el PO ha aportado.
2. Si falta justificación, escribe `[PENDIENTE: justificación]`.
3. El output debe ser markdown limpio, sin texto introductorio.
4. La decisión debe quedar inequívoca: qué pasa con este ticket y por qué.

## Contexto del ticket
**Título:** {{TITULO}}
**Descripción (intake):**
{{INTAKE_TEXT}}

## Respuestas del PO en el triage
{{RESPUESTAS_PO}}

## Formato de salida

Genera SOLO este bloque markdown (sin texto extra):

```
**Decisión de Triage** — {{DECISION_LABEL}}

**Justificación:** <1-2 frases con el razonamiento del PO>

**Acción:** <qué ocurre ahora con este ticket>

**Asignado a:** <PO responsable del siguiente paso, si aplica>

**Fecha triage:** {{FECHA}}
```

Si la decisión es "aplazado", añade:
**Próximo Comité de Priorización:** <fecha si fue mencionada, si no: [PENDIENTE: fecha]>

Si la decisión es "devuelto al stakeholder", añade las preguntas pendientes como lista con guiones.
```

Contenido del archivo (sin los backticks externos):

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es formatear la decisión de triage del PO en un comentario claro y trazable para el ticket Jira.

## Reglas
1. NO inventes información. Usa solo lo que el PO ha aportado.
2. Si falta justificación, escribe `[PENDIENTE: justificación]`.
3. El output debe ser markdown limpio, sin texto introductorio.
4. La decisión debe quedar inequívoca: qué pasa con este ticket y por qué.

## Contexto del ticket
**Título:** {{TITULO}}
**Descripción (intake):**
{{INTAKE_TEXT}}

## Respuestas del PO en el triage
{{RESPUESTAS_PO}}

## Formato de salida

Genera SOLO este bloque markdown (sin texto extra):

**Decisión de Triage** — {{DECISION_LABEL}}

**Justificación:** <1-2 frases con el razonamiento del PO>

**Acción:** <qué ocurre ahora con este ticket>

**Asignado a:** <PO responsable del siguiente paso, si aplica>

**Fecha triage:** {{FECHA}}
```

- [ ] **Step 2: Crear `prompts/discovery_ficha.md`**

Archivo `src/po_assistant/prompts/discovery_ficha.md`:

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es formatear las respuestas del PO en una Ficha Previa de Análisis completa.

## Reglas críticas
1. NO inventes datos. Si el PO no aportó información, escribe `[PENDIENTE: descripción breve del campo]`.
2. Sigue exactamente la estructura de secciones numeradas de abajo.
3. Mejora la redacción del PO (claridad, precisión) sin cambiar el significado.
4. El "problema real" debe estar en lenguaje de problema, no de solución.
5. Output SOLO el markdown, sin texto introductorio.

## Contexto del ticket
**Título:** {{TITULO}}
**Petición original (intake):** {{INTAKE_TEXT}}

## Respuestas del PO
{{RESPUESTAS_PO}}

## Formato de salida

### Ficha Previa de Análisis

**Fecha:** {{FECHA}}
**PO autor:** {{PO_AUTOR}}
**Origen:** Jira {{ISSUE_KEY}}
**Estado:** Borrador

---

#### 1. Petición original
**Tal como llegó:**
> {{PETICION_ORIGINAL}}

**Quién la planteó:** {{SOLICITANTE}}

---

#### 2. Problema real
**El problema (lenguaje de problema, no de solución):**
<usa las respuestas del PO — si no hay suficiente info, marca [PENDIENTE: reformular el problema real]>

**Frecuencia y volumen:** <usa las respuestas>

---

#### 3. Personas
**Usuario directo:** <rol>
**Stakeholder solicitante:** <nombre, rol, área>
**Validador UAT:** <nombre, rol>

---

#### 4. Situación actual
**Cómo se resuelve hoy:** <usa las respuestas>

**Qué duele:** <usa las respuestas>

---

#### 5. Por qué importa
**Objetivo estratégico:** <usa las respuestas>
**Consecuencia de no hacer nada:** <usa las respuestas>

---

#### 6. Restricciones identificadas
<usa las respuestas; si no hay: [PENDIENTE: confirmar en discovery]>

---

#### 7. Riesgos y dudas abiertas
<usa las respuestas; añade dudas abiertas identificadas>

---

#### 8. Trazabilidad IA
**Generada con IA:** Sí
**Modelo:** {{CLAUDE_MODEL}}
**Revisor humano:** [PENDIENTE: añadir nombre del PO]
```

- [ ] **Step 3: Crear `prompts/signoff_doc.md`**

Archivo `src/po_assistant/prompts/signoff_doc.md`:

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es generar el documento de Sign-off del alcance basado en las respuestas del PO.

## Reglas
1. NO inventes información. Campos sin datos → `[PENDIENTE: ...]`.
2. El documento debe ser formal y claro. Lenguaje directo.
3. Output SOLO el markdown del documento.

## Contexto
**HU:** {{TITULO}}
**Issue:** {{ISSUE_KEY}}
**Contenido actual del ticket:**
{{TICKET_TEXT}}

## Respuestas del PO
{{RESPUESTAS_PO}}

## Formato de salida

### Sign-off del alcance — {{ISSUE_KEY}}

**HU:** {{TITULO}}
**Fecha:** {{FECHA}}
**Persona que firma:** {{FIRMANTE}}

---

#### Confirmación
Confirmo que la HU {{ISSUE_KEY}} refleja el alcance acordado.

**Reunión de discovery:** <fecha si fue mencionada>
**Ficha previa:** validada el <fecha o [PENDIENTE]>

---

#### Alcance que firmo
<lista de funcionalidades acordadas — usa las respuestas del PO>

---

#### Exclusiones explícitas
<lo que NO entra — usa las respuestas del PO; si no hay: [PENDIENTE: confirmar exclusiones]>

---

#### MVP acordado
<unidad mínima de valor — usa las respuestas del PO>

---

#### Validador de UAT
**Persona:** <usa las respuestas>
**Disponibilidad:** <usa las respuestas o [PENDIENTE: confirmar disponibilidad]>

---

#### Para uso del PO
**Forma de firma:** Comentario Jira
**Estado:** Pendiente confirmación del stakeholder

---

#### Trazabilidad IA
**Generado con IA:** Sí
**Modelo:** {{CLAUDE_MODEL}}
**Revisor humano:** [PENDIENTE: añadir nombre del PO]
```

- [ ] **Step 4: Crear `prompts/handshake_acta.md`**

Archivo `src/po_assistant/prompts/handshake_acta.md`:

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es generar el Acta de Handshake basada en las respuestas del PO.

## Reglas
1. NO inventes información. Campos sin datos → `[PENDIENTE: ...]`.
2. El acta debe reflejar exactamente lo que el PO reportó.
3. Output SOLO el markdown del acta.

## Contexto
**HU:** {{TITULO}}
**Issue:** {{ISSUE_KEY}}
**DoR Gate anterior:**
{{TICKET_TEXT}}

## Respuestas del PO
{{RESPUESTAS_PO}}

## Formato de salida

### Acta — Handshake {{ISSUE_KEY}}

**Fecha:** {{FECHA}}
**HU:** {{TITULO}}

---

#### Asistentes
<lista de asistentes con rol — usa las respuestas>

---

#### Pre-condiciones
- DoR Gate: <score y fecha — usa las respuestas o [PENDIENTE]>
- Sign-off stakeholder: <fecha o [PENDIENTE]>

---

#### Dudas planteadas y respuestas
| # | Pregunta | Respuesta | ¿Cierra? |
|---|---|---|---|
<rellena con las respuestas del PO; si no hay dudas: | 1 | Sin dudas pendientes | — | Sí |>

---

#### Supuestos validados
<usa las respuestas; si no hay: [PENDIENTE: confirmar supuestos en sesión]>

---

#### Riesgos técnicos
<usa las respuestas; si no hay: Sin riesgos identificados>

---

#### Dependencias confirmadas
<usa las respuestas; si no hay: [PENDIENTE: confirmar con leads FE/BE]>

---

#### Estimación
**Puntos/días:** <usa las respuestas o [PENDIENTE]>

---

#### Decisión
<OK para arrancar dev o Vuelve a Definición — usa las respuestas>

---

#### Trazabilidad IA
**Generado con IA:** Sí
**Modelo:** {{CLAUDE_MODEL}}
**Revisor humano:** [PENDIENTE: añadir nombre del PO]
```

- [ ] **Step 5: Crear `prompts/uat_acta.md`**

Archivo `src/po_assistant/prompts/uat_acta.md`:

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es generar el Acta de UAT basada en las respuestas del PO.

## Reglas
1. NO inventes. Campos sin datos → `[PENDIENTE: ...]`.
2. Los casos de prueba deben estar en el formato estándar.
3. Output SOLO el markdown del acta.

## Contexto
**HU:** {{TITULO}}
**Issue:** {{ISSUE_KEY}}

## Respuestas del PO
{{RESPUESTAS_PO}}

## Formato de salida

### Acta — UAT {{ISSUE_KEY}}

**Fecha:** {{FECHA}}
**HU:** {{TITULO}}
**Validador funcional:** <usa las respuestas>
**PO acompañante:** {{PO_AUTOR}}
**Entorno:** PRE

---

#### Pre-condiciones de la UAT
- [ ] DoR Gate OK
- [ ] Sign-off del qué registrado
- [ ] Desarrollo finalizado
- [ ] Tests automáticos en verde
- [ ] Entorno PRE accesible
- [ ] Datos de prueba cargados

---

#### Casuísticas validadas
<usa las respuestas — un caso por párrafo con: descripción, resultado esperado, resultado real OK/KO>

---

#### Defectos detectados
<usa las respuestas; si no hay: Sin defectos detectados>

---

#### Decisión del validador
<UAT OK / UAT KO con observaciones — usa las respuestas>

---

#### Próximos pasos
<usa las respuestas>

---

#### Trazabilidad IA
**Generado con IA:** Sí
**Modelo:** {{CLAUDE_MODEL}}
**Revisor humano:** [PENDIENTE: añadir nombre del PO]
```

- [ ] **Step 6: Crear `prompts/release_check.md`**

Archivo `src/po_assistant/prompts/release_check.md`:

```
Eres el asistente de un Product Owner en Flexicar.

Tu trabajo es generar el Checklist de Release basado en las respuestas del PO.

## Reglas
1. NO inventes. Campos sin datos → `[PENDIENTE: ...]`.
2. Los checkboxes deben estar marcados si el PO confirmó el ítem, sin marcar si no.
3. Output SOLO el markdown del checklist.

## Contexto
**HU:** {{TITULO}}
**Issue:** {{ISSUE_KEY}}

## Respuestas del PO
{{RESPUESTAS_PO}}

## Formato de salida

### Checklist de Release — {{ISSUE_KEY}}

**HU:** {{TITULO}}
**Fecha de release:** <usa las respuestas o [PENDIENTE]>
**PO:** {{PO_AUTOR}}

---

#### Pre-condiciones funcionales
- [x] UAT OK firmada por validador funcional
- [x] Sign-off del qué consistente con lo entregado
<marca con [x] solo los ítems confirmados por el PO>

---

#### Pre-condiciones técnicas
<marca con [x] los ítems confirmados; deja [ ] los pendientes>
- [ ] PR mergeado a rama de release
- [ ] Tests automáticos en verde
- [ ] Code review completada
- [ ] Plan de rollback técnico preparado

---

#### Comunicación
<usa las respuestas del PO>

---

#### Ventana de release
**Inicio programado:** <usa las respuestas o [PENDIENTE]>
**Plan de comunicación si hay incidencia:** <usa las respuestas>

---

#### Sign-off de release
**PO:** [PENDIENTE: firma del PO]
**Lead FE/BE:** [PENDIENTE: firma del Lead]
**Fecha:** {{FECHA}}

---

#### Trazabilidad IA
**Generado con IA:** Sí
**Modelo:** {{CLAUDE_MODEL}}
**Revisor humano:** [PENDIENTE: añadir nombre del PO]
```

- [ ] **Step 7: Commit**

```
git add src/po_assistant/prompts/
git commit -m "feat: add AI prompts for triage, discovery, signoff, handshake, UAT, release"
```

---

## Task 3: Flujo TRIAGE (`workflow/triage.py`)

**Files:**
- Create: `src/po_assistant/workflow/triage.py`
- Create: `tests/test_triage.py`
- Modify: `src/po_assistant/main.py` (añadir comando `triage`)

- [ ] **Step 1: Escribir test que falla**

```python
# tests/test_triage.py
from po_assistant.workflow.triage import _decision_label, _build_answers_text


def test_decision_label_discovery():
    assert _decision_label(4) == "Entra a Discovery"


def test_decision_label_aplazado():
    assert _decision_label(5) == "Aplazado — Comité Semanal"


def test_decision_label_incidencia():
    assert _decision_label(1) == "Redirigido — Incidencia técnica"


def test_decision_label_urgencia():
    assert _decision_label(2) == "Urgencia — Vía urgencias"


def test_decision_label_devuelto():
    assert _decision_label(3) == "Devuelto — Clarificación necesaria"


def test_build_answers_text():
    answers = {
        "decision": 4,
        "justificacion": "La petición tiene un problema claro.",
        "asignado_a": "Ana García",
    }
    text = _build_answers_text(answers)
    assert "Entra a Discovery" in text
    assert "La petición tiene un problema claro." in text
    assert "Ana García" in text
```

- [ ] **Step 2: Verificar que los tests fallan**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_triage.py -v
```

Expected: `ModuleNotFoundError: No module named 'po_assistant.workflow.triage'`

- [ ] **Step 3: Implementar `workflow/triage.py`**

```python
# src/po_assistant/workflow/triage.py
from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT, C_PRIMARY,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_choice, append_section

_DECISIONS = [
    ("Incidencia técnica", "No es una HU — redirigir a soporte o dev"),
    ("Urgencia real", "Producción afectada ahora — usar `po urgencia`"),
    ("Idea sin problema claro", "Devolver al stakeholder con preguntas"),
    ("Mejora con prioridad clara", "Entra a Discovery"),
    ("Mejora con prioridad dudosa", "Aplazar al Comité Semanal de Priorización"),
]


def _decision_label(choice: int) -> str:
    labels = {
        1: "Redirigido — Incidencia técnica",
        2: "Urgencia — Vía urgencias",
        3: "Devuelto — Clarificación necesaria",
        4: "Entra a Discovery",
        5: "Aplazado — Comité Semanal",
    }
    return labels.get(choice, "Desconocido")


def _build_answers_text(answers: dict) -> str:
    lines = [
        f"Decisión elegida: {_decision_label(answers['decision'])}",
        f"Justificación: {answers.get('justificacion', '[sin justificación]')}",
    ]
    if answers.get("asignado_a"):
        lines.append(f"Asignado a: {answers['asignado_a']}")
    if answers.get("comite_fecha"):
        lines.append(f"Próximo Comité: {answers['comite_fecha']}")
    if answers.get("preguntas"):
        lines.append(f"Preguntas para el stakeholder: {answers['preguntas']}")
    if answers.get("destino"):
        lines.append(f"Destino de redirección: {answers['destino']}")
    return "\n".join(lines)


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Triage — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")

    if issue.description:
        console.print(f"  [{C_MUTED}]Descripción actual:[/{C_MUTED}]")
        for line in issue.description.splitlines()[:12]:
            console.print(f"  [{C_MUTED}]{line}[/{C_MUTED}]")
        console.print()

    choice = ask_choice("¿Cuál es la decisión de triage?", _DECISIONS)
    justificacion = ask("¿Cuál es tu justificación? (1-2 frases)")
    answers: dict = {"decision": choice, "justificacion": justificacion}

    if choice == 4:
        asignado = ask("¿A qué PO se asigna el Discovery?", "ej: Ana García")
        answers["asignado_a"] = asignado
    elif choice == 5:
        fecha = ask("¿Fecha del próximo Comité de Priorización?", "ej: 2026-05-26 o 'próximo lunes'")
        answers["comite_fecha"] = fecha
    elif choice == 3:
        preguntas = ask("¿Qué preguntas le devuelves al stakeholder?",
                        "escribe las preguntas separadas por punto y coma")
        answers["preguntas"] = preguntas
    elif choice == 1:
        destino = ask("¿A quién/dónde se redirige?", "ej: soporte N2, dev backend, etc.")
        answers["destino"] = destino

    answers_text = _build_answers_text(answers)
    fecha = datetime.now().strftime("%Y-%m-%d")

    triage_md = ai.call(
        "triage_decide.md",
        {
            "USER_INPUT": "Formatea la decisión de triage.",
            "TITULO": issue.summary,
            "INTAKE_TEXT": issue.description[:800] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "DECISION_LABEL": _decision_label(choice),
            "FECHA": fecha,
        },
    )

    console.print()
    section_rule("Vista previa — Triage")
    for line in triage_md.splitlines():
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar esta decisión en Jira?", default=True):
        console.print(f"  [{C_MUTED}]Cancelado.[/{C_MUTED}]\n")
        raise typer.Abort()

    append_section(jira, issue_key, "TRIAGE", triage_md)

    if choice == 4:
        jira.transition_po_state(issue_key, POEstado.TRIAGE)
    elif choice == 5:
        jira.transition_po_state(issue_key, POEstado.APLAZADO)

    jira.add_comment(issue_key, f"**Triage completado** — {_decision_label(choice)}\n\n_{fecha}_")

    next_cmd = f"po discovery {issue_key}" if choice == 4 else ""
    notify_success(
        f"Triage guardado en {issue_key}.",
        f"Siguiente: [{C_ACCENT}]{next_cmd}[/{C_ACCENT}]" if next_cmd else "",
    )
    console.print()
```

- [ ] **Step 4: Añadir comando `triage` a `main.py`**

En `src/po_assistant/main.py`, después del bloque `# ── INTAKE` (línea ~267), añadir:

```python
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
```

- [ ] **Step 5: Verificar que los tests de triage pasan**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_triage.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Smoke test manual**

```
$env:PYTHONUTF8=1; .venv\Scripts\po.exe --help
```

Expected: Ver `triage` en la lista de comandos.

- [ ] **Step 7: Commit**

```
git add src/po_assistant/workflow/triage.py src/po_assistant/main.py tests/test_triage.py
git commit -m "feat: add po triage command with decision tree and cumulative Jira content"
```

---

## Task 4: Flujo DISCOVERY (`workflow/discovery.py`)

**Files:**
- Create: `src/po_assistant/workflow/discovery.py`
- Create: `tests/test_discovery.py`
- Modify: `src/po_assistant/main.py` (añadir comando `discovery`)

- [ ] **Step 1: Escribir test que falla**

```python
# tests/test_discovery.py
from po_assistant.workflow.discovery import _build_answers_text, _extract_intake_text


def test_build_answers_text_all_fields():
    answers = {
        "problema_real": "Los agentes no encuentran cómo cancelar una reserva.",
        "frecuencia": "10-15 veces al día en tiendas grandes.",
        "usuario_directo": "Agente comercial de tienda.",
        "solicitante": "María Ruiz, Responsable de operaciones.",
        "validador_uat": "Luis Pérez, encargado de tienda piloto.",
        "situacion_actual": "El agente navega por tres menús distintos.",
        "que_duele": "Pierde tiempo y llama a soporte.",
        "por_que_importa": "Reduce carga del soporte y mejora NPS agentes.",
        "consecuencia": "Seguirá habiendo llamadas innecesarias al soporte.",
        "restricciones": "No puede tocar el módulo de contratos.",
        "riesgos": "Podría afectar al flujo de cancelación si hay errores.",
    }
    text = _build_answers_text(answers)
    assert "Los agentes no encuentran" in text
    assert "María Ruiz" in text
    assert "10-15 veces" in text


def test_extract_intake_text_trims_to_800():
    long_text = "a" * 1500
    result = _extract_intake_text(long_text)
    assert len(result) <= 800


def test_extract_intake_text_short_passthrough():
    short_text = "Petición corta."
    result = _extract_intake_text(short_text)
    assert result == short_text
```

- [ ] **Step 2: Verificar que los tests fallan**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_discovery.py -v
```

Expected: `ModuleNotFoundError: No module named 'po_assistant.workflow.discovery'`

- [ ] **Step 3: Implementar `workflow/discovery.py`**

```python
# src/po_assistant/workflow/discovery.py
from datetime import datetime

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
        from pathlib import Path
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
```

- [ ] **Step 4: Añadir comando `discovery` a `main.py`**

En `src/po_assistant/main.py`, después del bloque `# ── TRIAGE`:

```python
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
```

- [ ] **Step 5: Verificar tests**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\test_discovery.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```
git add src/po_assistant/workflow/discovery.py src/po_assistant/main.py tests/test_discovery.py
git commit -m "feat: add po discovery command with guided Q&A for ficha previa"
```

---

## Task 5: Flujo SIGN-OFF SH (`workflow/signoff.py`)

**Files:**
- Create: `src/po_assistant/workflow/signoff.py`
- Modify: `src/po_assistant/main.py` (añadir comando `signoff`)

- [ ] **Step 1: Implementar `workflow/signoff.py`**

```python
# src/po_assistant/workflow/signoff.py
from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, confirm, C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Sign-off Stakeholder — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a generar el documento de Sign-off del alcance "
        f"para que el stakeholder lo confirme.[/{C_MUTED}]\n"
    )

    firmante = ask("¿Quién firma el sign-off? (nombre, rol)", "Ej: María Ruiz, Responsable de Operaciones")
    fecha_discovery = ask("¿Cuándo fue la reunión de discovery?", "Ej: 2026-05-15")
    funcionalidades = ask_multiline(
        "¿Qué funcionalidades entran en el alcance que firmamos?",
        "Una por línea"
    )
    exclusiones = ask_multiline(
        "¿Qué exclusiones explícitas hay? (qué NO entra)",
        "Una por línea. Si no hay, escribe 'ninguna'"
    )
    mvp = ask("¿Cuál es el MVP acordado? (unidad mínima de valor)")
    validador_uat = ask("¿Quién es el validador de UAT y cuándo está disponible?")
    tiene_fecha = ask("¿Hay una fecha objetivo? (S/n, si S: escribe la fecha)", "")
    fecha_objetivo = ""
    if tiene_fecha.strip().lower() in ("s", "si", "sí", "y", "yes"):
        fecha_objetivo = ask("¿Cuál es la fecha objetivo?", "Ej: 2026-06-30")
    limitaciones = ask(
        "¿El stakeholder declara alguna limitación por su parte?",
        "Ej: no disponible en julio. Si no hay, escribe 'ninguna'"
    )

    answers_text = "\n".join([
        f"Firmante: {firmante}",
        f"Fecha reunión discovery: {fecha_discovery}",
        f"Funcionalidades acordadas:\n{funcionalidades}",
        f"Exclusiones explícitas:\n{exclusiones}",
        f"MVP: {mvp}",
        f"Validador UAT: {validador_uat}",
        f"Fecha objetivo: {fecha_objetivo if fecha_objetivo else 'No aplica'}",
        f"Limitaciones del stakeholder: {limitaciones}",
    ])

    signoff_md = ai.call(
        "signoff_doc.md",
        {
            "USER_INPUT": "Genera el documento de sign-off.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "TICKET_TEXT": issue.description[:600] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "FIRMANTE": firmante,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Sign-off")
    for line in signoff_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()
    console.print(f"  [{C_MUTED}]Comparte este documento con el stakeholder para que lo confirme en Jira.[/{C_MUTED}]\n")

    if not confirm("¿Guardar el Sign-off en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "SIGN-OFF SH", signoff_md)
    jira.transition_po_state(issue_key, POEstado.SIGN_OFF_SH)
    jira.add_comment(
        issue_key,
        f"## Sign-off pendiente de confirmación\n\n"
        f"Documento generado. Stakeholder: **{firmante}**.\n\n"
        f"_Pendiente: {firmante} debe confirmar en un comentario de este ticket._\n\n"
        f"Siguiente: `po dor-gate {issue_key}` (tras recibir confirmación)"
    )

    notify_success(
        f"Sign-off guardado en {issue_key}. Estado → SIGN-OFF SH.",
        f"Comparte la URL del ticket con {firmante} para su confirmación.",
    )
    console.print()
```

- [ ] **Step 2: Añadir comando `signoff` a `main.py`**

```python
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
```

- [ ] **Step 3: Smoke test**

```
$env:PYTHONUTF8=1; .venv\Scripts\po.exe --help
```

Expected: Ver `signoff` en la lista.

- [ ] **Step 4: Commit**

```
git add src/po_assistant/workflow/signoff.py src/po_assistant/main.py
git commit -m "feat: add po signoff command for stakeholder sign-off document"
```

---

## Task 6: Flujo HANDSHAKE (`workflow/handshake.py`)

**Files:**
- Create: `src/po_assistant/workflow/handshake.py`
- Modify: `src/po_assistant/main.py` (añadir comando `handshake`)

- [ ] **Step 1: Implementar `workflow/handshake.py`**

```python
# src/po_assistant/workflow/handshake.py
from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, ask_choice, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Handshake — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a levantar el Acta de Handshake entre PO y Desarrollo.[/{C_MUTED}]\n"
    )

    asistentes = ask_multiline(
        "¿Quiénes asistieron al Handshake?",
        "Una persona por línea: Nombre — Rol"
    )
    dor_score = ask("¿Cuál fue el score del DoR Gate?", "Ej: 11/12")
    dudas = ask_multiline(
        "¿Qué dudas planteó desarrollo y cómo se respondieron?",
        "Formato: Pregunta | Respuesta. Una por línea. Si no hubo: escribe 'ninguna'"
    )
    supuestos = ask_multiline(
        "¿Qué supuestos se validaron?",
        "Uno por línea. Si no hubo: escribe 'ninguno'"
    )
    riesgos_tecnicos = ask(
        "¿Qué riesgos técnicos se identificaron?",
        "Ej: 'integración con JATO puede dar problemas de latencia'. Si no hay: 'ninguno'"
    )
    estimacion = ask("¿Cuál es la estimación inicial?", "Ej: 5 puntos / 3 días")
    dependencias = ask(
        "¿Hay dependencias confirmadas (FE, BE, Data, UX, externas)?",
        "Si no hay: 'ninguna'"
    )

    decision = ask_choice(
        "¿Cuál es la decisión del Handshake?",
        [
            ("OK para arrancar dev", "El equipo tiene todo lo necesario para empezar"),
            ("Vuelve a Definición", "Hay gaps que necesitan resolverse primero"),
        ]
    )

    gaps_def = ""
    if decision == 2:
        gaps_def = ask_multiline("¿Cuáles son los gaps que impiden arrancar?", "Uno por línea")

    answers_text = "\n".join([
        f"Asistentes:\n{asistentes}",
        f"DoR Gate previo: {dor_score}",
        f"Dudas y respuestas:\n{dudas}",
        f"Supuestos validados:\n{supuestos}",
        f"Riesgos técnicos: {riesgos_tecnicos}",
        f"Estimación: {estimacion}",
        f"Dependencias: {dependencias}",
        f"Decisión: {'OK para arrancar dev' if decision == 1 else 'Vuelve a Definición'}",
        f"Gaps (si vuelve a Definición):\n{gaps_def}" if gaps_def else "",
    ])

    acta_md = ai.call(
        "handshake_acta.md",
        {
            "USER_INPUT": "Genera el acta de handshake.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "TICKET_TEXT": issue.description[:600] if issue.description else "",
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Acta de Handshake")
    for line in acta_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Acta de Handshake en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "HANDSHAKE", acta_md)
    jira.transition_po_state(issue_key, POEstado.HANDSHAKE)

    if decision == 1:
        jira.add_comment(
            issue_key,
            f"## Handshake OK\n\n"
            f"Estimación: {estimacion}\n\n"
            f"**El equipo puede arrancar desarrollo.**\n\n"
            f"Siguiente: `po uat {issue_key}` (cuando dev termine)"
        )
        notify_success(
            f"Acta de Handshake guardada en {issue_key}. Estado → HANDSHAKE.",
            f"El equipo puede arrancar desarrollo.",
        )
    else:
        notify_warning(
            f"Handshake KO — la HU vuelve a Definición.",
            f"Resuelve los gaps y ejecuta de nuevo `po handshake {issue_key}`.",
        )

    console.print()
```

- [ ] **Step 2: Añadir comando `handshake` a `main.py`**

```python
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
```

- [ ] **Step 3: Commit**

```
git add src/po_assistant/workflow/handshake.py src/po_assistant/main.py
git commit -m "feat: add po handshake command with Q&A-driven acta handshake"
```

---

## Task 7: Flujo UAT (`workflow/uat.py`)

**Files:**
- Create: `src/po_assistant/workflow/uat.py`
- Modify: `src/po_assistant/main.py` (añadir comando `uat`)

- [ ] **Step 1: Implementar `workflow/uat.py`**

```python
# src/po_assistant/workflow/uat.py
from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, notify_warning, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_multiline, ask_choice, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"UAT — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(
        f"  [{C_MUTED}]Vamos a registrar el Acta de UAT. "
        f"El PO acompaña, el validador de negocio firma.[/{C_MUTED}]\n"
    )

    validador = ask("¿Quién es el validador funcional? (nombre, rol)")
    entorno = ask("¿En qué entorno se realizó la UAT?", "Normalmente: PRE")
    casos_ok = ask_multiline(
        "¿Qué casuísticas se validaron y con qué resultado?",
        "Una por línea. Ej: 'Happy path — cancelación desde CRM ✅ OK'"
    )
    defectos = ask(
        "¿Se detectaron defectos?",
        "Si no hay: 'ninguno'. Si hay: descríbelos con su severidad"
    )

    decision = ask_choice(
        "¿Cuál es la decisión del validador?",
        [
            ("UAT OK", "La HU pasa a sign-off de release"),
            ("UAT KO con observaciones", "La HU vuelve a desarrollo"),
            ("UAT OK condicional", "Pasa con defectos menores que se trackean aparte"),
        ]
    )

    observaciones = ""
    if decision in (2, 3):
        observaciones = ask_multiline("¿Cuáles son las observaciones / defectos?")

    answers_text = "\n".join([
        f"Validador funcional: {validador}",
        f"Entorno: {entorno}",
        f"Casuísticas validadas:\n{casos_ok}",
        f"Defectos detectados: {defectos}",
        f"Decisión: {['UAT OK', 'UAT KO con observaciones', 'UAT OK condicional'][decision - 1]}",
        f"Observaciones:\n{observaciones}" if observaciones else "",
    ])

    acta_md = ai.call(
        "uat_acta.md",
        {
            "USER_INPUT": "Genera el acta de UAT.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "PO_AUTOR": config.jira_email,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Acta UAT")
    for line in acta_md.splitlines()[:35]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Acta UAT en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "UAT", acta_md)
    jira.transition_po_state(issue_key, POEstado.UAT)

    if decision == 1:
        jira.add_comment(issue_key,
            f"## UAT OK ✅\n\nValidador: **{validador}**\n\n"
            f"Siguiente: `po release {issue_key}`")
        notify_success(
            f"Acta UAT guardada en {issue_key}. Estado → UAT.",
            f"Siguiente: [{C_ACCENT}]po release {issue_key}[/{C_ACCENT}]",
        )
    elif decision == 2:
        jira.add_comment(issue_key,
            f"## UAT KO ❌\n\nDefectos: {defectos}\n\n"
            f"La HU vuelve a desarrollo. Lead FE/BE a cargo de la corrección.")
        notify_warning(f"UAT KO — la HU vuelve a desarrollo.", f"Defectos: {defectos}")
    else:
        jira.add_comment(issue_key,
            f"## UAT OK condicional ⚠️\n\nPasa con observaciones: {observaciones}\n\n"
            f"Siguiente: `po release {issue_key}`")
        notify_success(f"UAT OK condicional. Estado → UAT.", f"Observaciones trackadas en Jira.")

    console.print()
```

- [ ] **Step 2: Añadir comando `uat` a `main.py`**

```python
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
```

- [ ] **Step 3: Commit**

```
git add src/po_assistant/workflow/uat.py src/po_assistant/main.py
git commit -m "feat: add po uat command with Q&A-driven acta UAT"
```

---

## Task 8: Flujo RELEASE (`workflow/release.py`)

**Files:**
- Create: `src/po_assistant/workflow/release.py`
- Modify: `src/po_assistant/main.py` (añadir comando `release`)

- [ ] **Step 1: Implementar `workflow/release.py`**

```python
# src/po_assistant/workflow/release.py
from datetime import datetime

import typer

from ..ai_client import AIClient
from ..config import Config
from ..display import (
    console, section_rule, notify_success, confirm,
    C_MUTED, C_ACCENT,
)
from ..jira_client import JiraClient
from ..models import POEstado
from .qa import ask, ask_choice, append_section


def run(issue_key: str, ai: AIClient, jira: JiraClient, config: Config) -> None:
    section_rule(f"Release — {issue_key}")
    issue = jira.get_issue(issue_key)
    console.print(f"  [{C_MUTED}]{issue.summary[:80]}[/{C_MUTED}]\n")
    console.print(f"  [{C_MUTED}]Checklist de release final.[/{C_MUTED}]\n")

    fecha_release = ask("¿Cuándo está programado el release?", "Ej: 2026-06-10 18:00")
    tipo_release = ask_choice(
        "¿Qué tipo de release es?",
        [("Release planificado", ""), ("Hotfix", "")]
    )
    lead_tecnico = ask("¿Quién es el Lead técnico responsable del release?")

    console.print(f"\n  [{C_ACCENT}]Pre-condiciones funcionales[/{C_ACCENT}]")
    uat_ok = ask("¿El Acta UAT está firmada? (S/n)")
    signoff_ok = ask("¿El sign-off del alcance está en Jira? (S/n)")

    console.print(f"\n  [{C_ACCENT}]Pre-condiciones técnicas[/{C_ACCENT}]")
    pr_mergeado = ask("¿El PR está mergeado a la rama de release? (S/n)")
    tests_verde = ask("¿Los tests automáticos están en verde? (S/n)")
    rollback_plan = ask("¿Hay plan de rollback técnico preparado?",
                         "Describe el plan brevemente")

    console.print(f"\n  [{C_ACCENT}]Comunicación[/{C_ACCENT}]")
    comunicacion = ask("¿A quién hay que comunicar el release?",
                        "Ej: stakeholder + área de soporte. Si no aplica: 'N/A'")

    console.print(f"\n  [{C_ACCENT}]Post-deploy[/{C_ACCENT}]")
    responsable_postdeploy = ask("¿Quién monitoriza las 24-48h post-deploy?")

    yes_set = {"s", "si", "sí", "y", "yes"}

    def check(val: str) -> str:
        return "[x]" if val.strip().lower() in yes_set else "[ ]"

    answers_text = "\n".join([
        f"Fecha de release: {fecha_release}",
        f"Tipo: {['Release planificado', 'Hotfix'][tipo_release - 1]}",
        f"Lead técnico: {lead_tecnico}",
        f"UAT firmada: {uat_ok}",
        f"Sign-off en Jira: {signoff_ok}",
        f"PR mergeado: {pr_mergeado}",
        f"Tests en verde: {tests_verde}",
        f"Plan de rollback: {rollback_plan}",
        f"Comunicación: {comunicacion}",
        f"Responsable post-deploy: {responsable_postdeploy}",
        f"UAT OK checkbox: {check(uat_ok)}",
        f"PR mergeado checkbox: {check(pr_mergeado)}",
        f"Tests en verde checkbox: {check(tests_verde)}",
    ])

    checklist_md = ai.call(
        "release_check.md",
        {
            "USER_INPUT": "Genera el checklist de release.",
            "TITULO": issue.summary,
            "ISSUE_KEY": issue_key,
            "RESPUESTAS_PO": answers_text,
            "FECHA": datetime.now().strftime("%Y-%m-%d"),
            "PO_AUTOR": config.jira_email,
            "CLAUDE_MODEL": config.claude_model,
        },
        max_tokens=3000,
    )

    section_rule("Vista previa — Checklist de Release")
    for line in checklist_md.splitlines()[:40]:
        console.print(f"  {line}")
    console.print()

    if not confirm("¿Guardar el Checklist de Release en Jira?", default=True):
        raise typer.Abort()

    append_section(jira, issue_key, "RELEASE", checklist_md)
    jira.transition_po_state(issue_key, POEstado.RELEASE)
    jira.add_comment(
        issue_key,
        f"## Checklist de Release completado ✅\n\n"
        f"Fecha programada: **{fecha_release}**\n"
        f"Lead técnico: **{lead_tecnico}**\n\n"
        f"_Tras el release: marcar ticket como CERRADO._"
    )

    notify_success(
        f"Checklist de Release guardado en {issue_key}. Estado → RELEASE.",
        f"Tras el release: transiciona el ticket a CERRADO desde Jira.",
    )
    console.print()
```

- [ ] **Step 2: Añadir comando `release` a `main.py`**

```python
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
```

- [ ] **Step 3: Commit**

```
git add src/po_assistant/workflow/release.py src/po_assistant/main.py
git commit -m "feat: add po release command with release checklist"
```

---

## Task 9: Actualizar intake.py, definition.py y dashboard hints en main.py

**Files:**
- Modify: `src/po_assistant/workflow/intake.py` (cambiar hint "siguiente paso")
- Modify: `src/po_assistant/workflow/definition.py` (usar `append_section` en lugar de reemplazar)
- Modify: `src/po_assistant/main.py` (actualizar help hints en `dashboard`)

- [ ] **Step 1: Actualizar `intake.py` next-step hint**

En `src/po_assistant/workflow/intake.py`, línea 74 (`notify_success`), cambiar el hint:

```python
# Antes:
console.print(
    f"  [{C_MUTED}]Siguiente paso:[/{C_MUTED}]  "
    f"[bold {C_ACCENT}]po define {key}[/bold {C_ACCENT}]\n"
)

# Después:
console.print(
    f"  [{C_MUTED}]Siguiente paso:[/{C_MUTED}]  "
    f"[bold {C_ACCENT}]po triage {key}[/bold {C_ACCENT}]\n"
)
```

- [ ] **Step 2: Actualizar `definition.py` para usar `append_section`**

Reemplazar la función `run()` en `src/po_assistant/workflow/definition.py` para que use `append_section` en lugar de `update_issue`:

```python
# Línea 71 — reemplazar:
jira.update_issue(issue_key, {"description": md_to_adf(hu_text)})
jira.transition_po_state(issue_key, POEstado.DEFINICION)

# Con:
from .qa import append_section as _append_section
_append_section(jira, issue_key, "DEFINICION — HU Borrador", hu_text)
jira.transition_po_state(issue_key, POEstado.DEFINICION)
```

También actualizar el import al inicio del archivo — quitar `md_to_adf` del import de `jira_client` si ya no se usa directamente:

```python
# Antes:
from ..jira_client import JiraClient, md_to_adf

# Después:
from ..jira_client import JiraClient
```

- [ ] **Step 3: Actualizar hints del dashboard**

En `src/po_assistant/main.py`, función `dashboard()`, líneas 373-376:

```python
# Reemplazar:
_help_row([
    ("po intake \"texto\"", "crear ticket"),
    ("po define FP-X", "generar HU"),
    ("po dor-gate FP-X", "validar DoR"),
])

# Con:
_help_row([
    ("po intake \"texto\"", "crear ticket"),
    ("po triage FP-X", "triage"),
    ("po discovery FP-X", "discovery / ficha previa"),
    ("po define FP-X", "generar HU (definición)"),
])
```

- [ ] **Step 4: Verificar que todos los tests siguen pasando**

```
$env:PYTHONUTF8=1; .venv\Scripts\pytest tests\ -v
```

Expected: Todos los tests en verde (no deben haber regresos).

- [ ] **Step 5: Smoke test del flujo completo**

```
$env:PYTHONUTF8=1; .venv\Scripts\po.exe --help
```

Expected: Ver todos los comandos: `intake`, `triage`, `discovery`, `define`, `signoff`, `dor-gate`, `handshake`, `uat`, `release`, `dashboard`, `setup`, `demo`.

- [ ] **Step 6: Commit final**

```
git add src/po_assistant/workflow/intake.py src/po_assistant/workflow/definition.py src/po_assistant/main.py
git commit -m "feat: update intake/definition to use cumulative Jira content; update dashboard hints"
```

---

## Self-Review

### 1. Spec coverage

| Requisito | Cubierto en |
|---|---|
| INTAKE interactivo | intake.py (existente, hint actualizado) |
| TRIAGE con árbol de decisión | Task 3 |
| DISCOVERY con Q&A ficha previa | Task 4 |
| DEFINICION con contenido acumulativo | Task 9 |
| SIGN-OFF SH con documento sign-off | Task 5 |
| DOR GATE (ya implementado) | existente |
| HANDSHAKE con acta | Task 6 |
| EN DESARROLLO (no hay acción PO) | no aplica |
| UAT con acta | Task 7 |
| RELEASE con checklist | Task 8 |
| Contenido acumulativo en Jira | Task 1 (`append_section`) |
| IA estructura sin inventar | Tasks 2 (prompts con reglas) |
| PO puede editar en Jira | inherente al diseño |

**Sin gaps.**

### 2. Placeholder scan

✅ No hay TBD, TODO, "similar to Task N", ni steps sin código. Cada step incluye el código completo o el cambio exacto.

### 3. Type consistency

- `append_section(jira: JiraClient, issue_key: str, section_title: str, content: str)` — usada igual en todos los workflows (Tasks 3-9).
- `ask(question: str, hint: str = "") -> str` — usada igual en todos los workflows.
- `ask_choice(question: str, options: list[tuple[str, str]]) -> int` — devuelve índice 1-based, usado consistentemente.
- `wf.run(issue_key, ai, jira, config)` — firma estándar en todos los módulos.
