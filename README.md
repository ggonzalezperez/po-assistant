# po-assistant

> CLI con IA para Product Owners de Flexicar.  
> Guía el flujo completo de definición de HUs: desde la petición bruta hasta el release.

---

## El problema que resuelve

Sin una herramienta así, el trabajo del PO es manual, inconsistente y difícil de medir:
- Las peticiones llegan por Slack, email, llamadas y Excel, no por Jira.
- Las HUs no siguen una plantilla, cada PO escribe lo que puede.
- No hay registro de por qué se tomaron las decisiones.
- Nadie sabe en qué estado está cada HU ni cuánto tiempo lleva atascada.

`po-assistant` convierte ese caos en un flujo guiado de 10 pasos, con IA para las partes que consumen más tiempo (clasificar, redactar, validar) y con todo documentado en Jira automáticamente.

---

## Cómo funciona — los 10 pasos

```
1. INTAKE        →  po intake "texto"     Clasifica y crea el ticket en Jira
2. TRIAGE        →  po triage FP-12       Decide si avanza, aplaza o se rechaza
3. DISCOVERY     →  po discovery FP-12    Ficha de contexto con el stakeholder
4. DEFINICION    →  po define FP-12       Genera la HU completa con IA
5. SIGN-OFF SH   →  po signoff FP-12      Documento de alcance firmado
6. DOR GATE      →  po dor-gate FP-12     Valida los 12 bloques del DoR con IA
7. HANDSHAKE     →  po handshake FP-12    Acta de traspaso al equipo de dev
8. EN DESARROLLO →  po start-dev FP-12    Registra el arranque y los leads
9. UAT           →  po uat FP-12          Acta de validación funcional
10. RELEASE      →  po release FP-12      Checklist de release y cierre
```

> **Flujo de urgencia:** `po urgencia "texto"` — salta los pasos 2-7 y crea el ticket directamente en EN DESARROLLO (paso 8). Continúa normalmente con `po uat` y `po release`.

Cada paso añade un bloque fechado a la descripción del ticket en Jira. Al final, el ticket contiene la historia completa de la HU: decisiones, quién participó, qué cambió y por qué.

---

## Instalación

### Prerrequisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recomendado) — o pip
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

### Configurar `.env`

```bash
cp .env.example .env
```

```dotenv
JIRA_BASE_URL=https://<dominio>.atlassian.net
JIRA_EMAIL=<tu-email>@flexicar.es
JIRA_API_TOKEN=<token de id.atlassian.com>
ANTHROPIC_API_KEY=<sk-ant-api03-...>
JIRA_PO_PROJECT_KEY=FP
PO_TEAM=Ester Carrasco:ecarrasco@flexicar.es,...
PYTHONUTF8=1
```

### Inicializar Jira (una vez)

```bash
po setup
```

Crea el proyecto FP, los 5 campos custom, el workflow de 10 estados y el tablero Kanban.
Los IDs de campos se guardan automáticamente en `.env`.

Ver [`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md) para configurar las columnas del tablero (paso manual).

---

## Uso rápido — flujo completo de ejemplo

```bash
# Una petición llega por Slack: "los agentes no encuentran cómo cancelar una reserva"
po intake "Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM"
# → Crea FP-12 en Jira con clasificación IA (tipo: problema, prio: alta)

# Comité de Triage del lunes
po triage FP-12
# → Decide avanzar a Discovery; documenta la decisión en Jira

# PO hace discovery con María Ruiz (operaciones)
po discovery FP-12
# → 11 preguntas guiadas; genera ficha de contexto en Jira

# PO redacta la HU con IA
po define FP-12
# → HU completa en 6 bloques; queda en la descripción de FP-12

# Sign-off formal del alcance con María
po signoff FP-12
# → Documento de alcance; María confirma en Jira

# Validar que la HU está lista para desarrollo
po dor-gate FP-12
# → Score 11/12 OK → estado DOR GATE

# Reunión de traspaso con el equipo técnico
po handshake FP-12
# → Acta con estimación, riesgos y dependencias; estado HANDSHAKE

# El sprint arranca
po start-dev FP-12
# → Registra los leads y mueve a EN DESARROLLO

# Validación funcional con el negocio
po uat FP-12
# → Acta de UAT firmada; estado UAT

# Deploy a producción
po release FP-12
# → Checklist de release; estado RELEASE

# Alternativa para urgencias en producción
po urgencia "El proceso de compra online devuelve 500 desde las 14:30"
# → Crea FP-13 directamente en EN DESARROLLO con brief IA y skip de 6 pasos
```

---

## Comandos de análisis y gestión

```bash
# Visión global del pipeline
po dashboard               # panel de resumen + tickets por estado con SLA alerts
po dashboard --po ester    # filtrar por PO
po dashboard --all         # incluir cerrados y rechazados
po dashboard --export      # exportar a reports/YYYY-MM-DD-dashboard-FP.md

# KPIs del pipeline (extraídos de Jira automáticamente)
po kpis                    # dashboard en terminal
po kpis --export           # exportar a reports/YYYY-MM-DD-kpis-FP.md
po kpis --weeks 12         # throughput de las últimas 12 semanas
```

`po dashboard` muestra dos secciones:

1. **Panel de resumen** — métricas clave (activos, en desarrollo, SLA en alerta, sin asignar) y una vista rápida de los 10 estados con sus conteos.
2. **Bloques por estado** — cada estado Kanban con su lista de tickets: clave, tipo, descripción, antigüedad, asignado e **informador**. Los tickets que superan el SLA aparecen en rojo.

---

## Todos los comandos

| Paso | Comando | Qué hace |
|------|---------|----------|
| 1 | `po intake "texto"` | Clasifica la petición con IA y crea el ticket |
| — | `po urgencia "texto"` | Flujo abreviado para urgencias: brief IA + ticket directo a EN DESARROLLO |
| 2 | `po triage FP-12` | Árbol de decisión: avanza, aplaza, redirige o rechaza |
| 3 | `po discovery FP-12` | 11 preguntas guiadas para completar el contexto |
| 4 | `po define FP-12` | Genera la HU completa (6 bloques) con IA |
| 5 | `po signoff FP-12` | Documento formal de alcance para el stakeholder |
| 6 | `po dor-gate FP-12` | Valida 12 bloques DoR con IA; score y gaps accionables |
| 7 | `po handshake FP-12` | Acta de traspaso PO → dev; si hay gaps, vuelve a Definición |
| 8 | `po start-dev FP-12` | Registra leads y mueve a EN DESARROLLO |
| 9 | `po uat FP-12` | Acta de UAT; si falla, vuelve a EN DESARROLLO |
| 10 | `po release FP-12` | Checklist de release y cierre del ciclo |
| — | `po kpis` | Dashboard de KPIs extraídos de Jira; `--export` → `reports/` |
| — | `po dashboard` | Panel de resumen + tickets por estado con informador y SLA; `--export` → `reports/` |
| — | `po setup` | Configura Jira: proyecto, campos, workflow, tablero |
| — | `po demo` | Demo guiada con caso real Flexicar (~2 min) |

---

## Cómo crece la descripción del ticket

Ningún comando sobreescribe la descripción. Cada uno añade un bloque al final,
separado por una línea horizontal. Al final del ciclo, el ticket es un registro
completo de todo lo que pasó:

```
## INTAKE — 2026-05-18
Clasificación IA: problema · prioridad alta
Preguntas para el triage: ¿Afecta a todas las tiendas?...

---

## TRIAGE — 2026-05-19
Decisión: avanza a Discovery. PO asignado: Ester Carrasco.

---

## DISCOVERY — 2026-05-20
Ficha de contexto: stakeholder, frecuencia, solución actual...

---

## DEFINICION — 2026-05-21
HU completa: contexto, criterios de aceptación, plan UAT...

---

## SIGN-OFF SH — 2026-05-22
Alcance acordado con María Ruiz. MVP: cancelación en 1 clic.

---

## HANDSHAKE — 2026-05-23
Estimación: 5 puntos. Riesgos: integración con JATO.

---

## EN DESARROLLO — 2026-05-24
Lead: Carlos López — Backend.

---

## UAT — 2026-05-30
Validador: María Ruiz. Resultado: OK sin defectos.

---

## RELEASE — 2026-05-31
Deploy: 2026-05-31. Checklist completo. Comunicado al negocio.
```

---

## Estructura del proyecto

```
po-assistant/
├── src/po_assistant/
│   ├── main.py              # CLI — registro de comandos Typer
│   ├── config.py            # Configuración desde .env
│   ├── jira_client.py       # Jira REST API v3 + Agile API
│   ├── ai_client.py         # Anthropic SDK (Claude)
│   ├── models.py            # Tipos: POEstado, DorGateResult…
│   ├── display.py           # UI terminal con Rich
│   ├── workflow/
│   │   ├── qa.py            # Helpers compartidos: ask(), append_section()…
│   │   ├── intake.py        # Paso 1 — Clasificación + creación
│   │   ├── triage.py        # Paso 2 — Árbol de decisión
│   │   ├── discovery.py     # Paso 3 — Ficha de discovery
│   │   ├── definition.py    # Paso 4 — Generación HU con IA
│   │   ├── signoff.py       # Paso 5 — Documento de sign-off
│   │   ├── dor_gate.py      # Paso 6 — Validación DoR con IA
│   │   ├── handshake.py     # Paso 7 — Acta de handshake
│   │   ├── start_dev.py     # Paso 8 — Arranque de desarrollo
│   │   ├── uat.py           # Paso 9 — Acta de UAT
│   │   ├── release.py       # Paso 10 — Checklist de release
│   │   └── kpis.py          # Dashboard KPIs + exportación Markdown
│   └── prompts/             # System prompts para Claude (.md)
├── docs/
│   ├── manual_usuario_jira.md       # Manual de uso diario para POs
│   ├── guia_setup_jira_oficial.md   # Configuración Jira corporativo
│   └── prompt_setup_jira.md         # Prompt IA para automatizar el setup
├── tests/
├── .env.example
└── pyproject.toml
```

---

## Tests

```bash
uv run pytest tests/ -v
```

---

## Documentación completa

| Documento | Para quién | Contenido |
|-----------|-----------|-----------|
| [`docs/manual_usuario_jira.md`](docs/manual_usuario_jira.md) | POs | Guía de uso día a día con todos los comandos |
| [`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md) | Admin Jira | Configuración paso a paso del entorno corporativo |
| [`JIRA_SETUP.md`](JIRA_SETUP.md) | Técnico | Referencia rápida de campos, estados y troubleshooting |

---

## Roadmap

- [ ] `po audit --week` — auditoría DoR semanal automatizada
- [ ] Integración con `flexicar-po-dashboard` (M7/M8)
