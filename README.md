# po-assistant

> Asistente IA para Product Owners — Flexicar  
> Automatiza el flujo end-to-end de definición de HUs con Claude + Jira.

---

## Qué hace

```
Petición bruta  →  INTAKE  →  TRIAGE  →  DISCOVERY  →  DEFINICION
    →  SIGN-OFF SH  →  DOR GATE  →  HANDSHAKE  →  EN DESARROLLO  →  UAT  →  RELEASE
```

| Comando | Paso | Qué hace |
|---------|------|----------|
| `po intake "texto"` | 1 — Intake | Clasifica tipo y prioridad con IA, crea ticket en Jira |
| `po triage FP-12` | 2 — Triage | Árbol de decisión asistido: avanza, aplaza, redirige o rechaza |
| `po discovery FP-12` | 3 — Discovery | Genera ficha de discovery guiada por preguntas del PO |
| `po define FP-12` | 4 — Definición | Genera HU completa (6 bloques + criterios de aceptación) |
| `po dor-gate FP-12` | 6 — DoR Gate | Valida los 12 bloques del DoR, score 0-12, gaps accionables |
| `po signoff FP-12` | 5 — Sign-off SH | Genera documento de sign-off para el stakeholder |
| `po handshake FP-12` | 7 — Handshake | Acta de traspaso PO → desarrollo; KO devuelve a DEFINICION |
| `po uat FP-12` | 9 — UAT | Registra acta de UAT; KO devuelve a EN DESARROLLO |
| `po release FP-12` | 10 — Release | Checklist de release y cierre del ciclo |
| `po dashboard` | — | Pipeline Kanban con SLA alerts por estado |
| `po setup` | — | Configura proyecto Jira, campos custom, workflow y tablero |
| `po demo` | — | Demo guiada con caso real Flexicar |

---

## Instalación rápida

### Prerrequisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes) — o pip
- Cuenta Jira Cloud con permisos de administrador
- API Key de Anthropic — [console.anthropic.com](https://console.anthropic.com/settings/keys)

### Instalar

```bash
git clone https://github.com/ggonzalezperez/po-assistant.git
cd po-assistant

# Con uv (recomendado)
uv sync

# Con pip
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
```

### Configurar

```bash
cp .env.example .env
```

Edita `.env` con los valores reales:

```dotenv
JIRA_BASE_URL=https://<dominio>.atlassian.net
JIRA_EMAIL=<tu-email>@flexicar.es
JIRA_API_TOKEN=<token de id.atlassian.com>
ANTHROPIC_API_KEY=<sk-ant-api03-...>
JIRA_PO_PROJECT_KEY=FP
PO_TEAM=Ester Carrasco:ecarrasco@flexicar.es,...
PYTHONUTF8=1
```

### Inicializar Jira

```bash
po setup
```

Crea o verifica: proyecto, 5 campos custom, workflow de 10 estados, tablero Kanban y componentes del equipo.
Los IDs de campos se escriben automáticamente en `.env`.

Para el paso adicional de configurar las columnas del tablero, consulta
[`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md).

### Probar

```bash
po demo               # demo guiada con caso real (~2 min)
po demo --offline     # sin crear issues en Jira
```

---

## Uso diario

```bash
# Nueva petición recibida
po intake "Los agentes no encuentran cómo cancelar una reserva en el CRM"
# → Crea FP-12 en INTAKE con clasificación IA

# Comité de Triage — decidir qué avanza
po triage FP-12
# → 5 opciones: redirigir, urgencia, devolver, discovery, aplazar
# → Transitions: discovery → TRIAGE | aplazar → APLAZADO | resto → RECHAZADO

# Discovery con el stakeholder — ficha guiada
po discovery FP-12
# → 11 preguntas guiadas; genera ficha de contexto en Jira

# Tras el discovery, generar HU
po define FP-12
po define FP-12 --notes notas_reunion.txt  # con notas de la reunión

# Validar si la HU está lista para desarrollo
po dor-gate FP-12
# → Score 11/12 OK → pasa a DOR GATE
# → Score 8/12 KO  → vuelve a DEFINICION con gaps detallados

# Sign-off del stakeholder — documento formal de alcance
po signoff FP-12
# → Genera documento de sign-off; stakeholder confirma en Jira

# Handshake con el equipo de desarrollo
po handshake FP-12
# → Acta de traspaso: estimación, riesgos, dependencias
# → OK → HANDSHAKE | KO (gaps) → vuelve a DEFINICION

# Registro de UAT
po uat FP-12
# → Acta de validación funcional
# → OK/condicional → UAT | KO → vuelve a EN DESARROLLO

# Release y cierre del ciclo
po release FP-12
# → Checklist de release; transitions a RELEASE

# Revisar el pipeline
po dashboard
po dashboard --po ester   # filtrar por PO
po dashboard --all        # incluir cerrados
```

---

## Estructura del proyecto

```
po-assistant/
├── src/po_assistant/
│   ├── main.py              # CLI — comandos Typer
│   ├── config.py            # Configuración desde .env
│   ├── jira_client.py       # Jira REST API v3 + Agile API
│   ├── ai_client.py         # Anthropic SDK (Claude)
│   ├── models.py            # Tipos: POEstado, DorGateResult…
│   ├── display.py           # UI terminal con Rich
│   ├── workflow/
│   │   ├── qa.py            # Q&A helpers compartidos (ask, append_section…)
│   │   ├── intake.py        # Clasificación + creación de issue
│   │   ├── triage.py        # Árbol de decisión de triage
│   │   ├── discovery.py     # Ficha de discovery guiada
│   │   ├── definition.py    # Generación HU 6 bloques
│   │   ├── dor_gate.py      # Validación 12 bloques DoR
│   │   ├── signoff.py       # Documento de sign-off stakeholder
│   │   ├── handshake.py     # Acta de handshake PO → dev
│   │   ├── uat.py           # Acta de UAT
│   │   └── release.py       # Checklist de release
│   ├── prompts/             # System prompts para Claude (.md)
│   │   ├── intake_classify.md
│   │   ├── triage_decide.md
│   │   ├── discovery_ficha.md
│   │   ├── definition_draft_hu.md
│   │   ├── dor_validate.md
│   │   ├── signoff_doc.md
│   │   ├── handshake_acta.md
│   │   ├── uat_acta.md
│   │   └── release_check.md
│   └── templates/
│       └── hu_template.md   # Plantilla de referencia
├── docs/
│   ├── guia_setup_jira_oficial.md   # Setup Jira corporativo paso a paso
│   ├── prompt_setup_jira.md         # Prompt IA para automatizar el setup
│   └── manual_usuario_jira.md       # Manual de uso diario para POs
├── tests/
│   ├── test_qa_helpers.py
│   ├── test_triage.py
│   ├── test_discovery.py
│   └── test_dor_gate.py
├── JIRA_SETUP.md            # Referencia rápida de configuración Jira
├── .env.example
└── pyproject.toml
```

---

## Cómo funciona internamente — descripción acumulativa

Cada comando añade un bloque `## ESTADO — YYYY-MM-DD` a la descripción del ticket
en Jira, separado por `---`. La descripción nunca se sobreescribe: la historia
completa del ticket queda visible.

```
## INTAKE — 2026-05-18
[análisis IA de la petición original]

---

## TRIAGE — 2026-05-19
[decisión del comité + justificación]

---

## DISCOVERY — 2026-05-20
[ficha de contexto, stakeholders, viabilidad]

---

## DEFINICION — 2026-05-21
[HU completa: 6 bloques + criterios de aceptación]
…
```

---

## Configuración Jira — resumen técnico

`po setup` configura automáticamente:

| Qué | API usada |
|-----|-----------|
| Proyecto Kanban | `POST /rest/api/3/project` |
| 10 estados globales (INTAKE → RELEASE) | `POST /rest/api/3/statuses` |
| Workflow con transiciones globales | `POST /rest/api/3/workflows/create` |
| Asignación workflow al proyecto | `PUT /rest/api/2/workflowscheme/{id}/draft` |
| 5 campos custom (DoR Score, DoR Gaps…) | `POST /rest/api/3/field` |
| Tablero Kanban + filtros rápidos | `POST /rest/agile/1.0/board` |
| Componentes del equipo PO | `POST /rest/api/3/component` |

Las columnas del tablero requieren un paso manual (ver
[`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md)) porque
la API pública de Jira Free devuelve 405 en ese endpoint. Se usan las DevTools
del navegador con el API interno de Greenhopper.

---

## Entornos

```bash
# Prototipo personal
cp .env.example .env
# → JIRA_BASE_URL=https://gerx97.atlassian.net

# Producción Flexicar
cp .env.example .env
# → JIRA_BASE_URL=https://flexicar.atlassian.net
# → JIRA_PO_PROJECT_KEY=<CLAVE_CORPORATIVA>
```

---

## Tests

```bash
uv run pytest tests/ -v
# o: pip install -e ".[dev]" && pytest tests/ -v
```

---

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md) | Guía completa para configurar el Jira corporativo |
| [`docs/prompt_setup_jira.md`](docs/prompt_setup_jira.md) | Prompt para que una IA ejecute el setup automáticamente |
| [`docs/manual_usuario_jira.md`](docs/manual_usuario_jira.md) | Manual de uso diario para Product Owners |
| [`JIRA_SETUP.md`](JIRA_SETUP.md) | Referencia rápida de campos, estados y troubleshooting |

---

## Roadmap

- [ ] `po urgencia "texto"` — flujo abreviado para urgencias en producción
- [ ] `po audit --week` — auditoría DoR semanal automatizada
- [ ] Integración con `flexicar-po-dashboard` (M7/M8)
