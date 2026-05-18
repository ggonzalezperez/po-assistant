# po-assistant

> Asistente IA para Product Owners — Flexicar
> Automatiza el flujo end-to-end en Jira con Claude API.

---

## Qué hace

| Comando | Paso del flujo | Qué hace la IA |
|---|---|---|
| `po setup` | — | Crea el proyecto FP en Jira y los campos custom |
| `po intake "texto"` | Paso 1 — Intake | Clasifica la petición y crea el ticket en Jira |
| `po define FP-12` | Paso 4 — Definición | Genera la HU completa (6 bloques) a partir del discovery |
| `po dor-gate FP-12` | Paso 6 — DoR Gate | Valida los 12 bloques del DoR, da score y lista los gaps |
| `po dashboard` | — | Muestra el pipeline completo por estado |
| `po demo` | — | Demo guiada con un caso real de Flexicar (para el CTO) |

---

## Setup rápido (5 minutos)

### 1. Prerrequisitos

- Python 3.12+
- Cuenta Jira Cloud (gratuita o de pago)
- API Key de Anthropic (console.anthropic.com)

### 2. Instalar

```bash
# Clonar el repo
git clone https://github.com/ggonzalezperez/po-assistant.git
cd po-assistant

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# Instalar dependencias
pip install -e .
```

### 3. Configurar

```bash
cp .env.example .env
# Edita .env con tu editor y rellena:
# - JIRA_BASE_URL  (ej: https://gerx97.atlassian.net)
# - JIRA_EMAIL     (tu email de Atlassian)
# - JIRA_API_TOKEN (desde https://id.atlassian.com/manage-profile/security/api-tokens)
# - ANTHROPIC_API_KEY (desde https://console.anthropic.com/settings/keys)
```

### 4. Crear el proyecto en Jira

```bash
po setup
```

Sigue las instrucciones en pantalla. Si hay problemas, consulta [JIRA_SETUP.md](JIRA_SETUP.md).

### 5. Probar

```bash
# Demo completa (recomendado para ver el flujo)
po demo

# O paso a paso:
po intake "Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM"
po define FP-1
po dor-gate FP-1
po dashboard
```

---

## Uso avanzado

```bash
# Generar HU desde un archivo de notas de discovery
po define FP-12 --notes notas_reunion.txt

# Dashboard filtrado por PO
po dashboard --po ester

# Dashboard con issues cerrados
po dashboard --all

# Demo sin crear issues en Jira
po demo --offline

# Modo dry-run (simula sin escribir en Jira)
DRY_RUN=true po intake "Prueba sin crear issue"
```

---

## Estructura del proyecto

```
po-assistant/
├── src/po_assistant/
│   ├── main.py              # CLI — comandos typer
│   ├── config.py            # Config desde .env
│   ├── jira_client.py       # Jira REST API v3
│   ├── ai_client.py         # Anthropic SDK (Claude)
│   ├── models.py            # Tipos: POEstado, DorGateResult, etc.
│   ├── workflow/
│   │   ├── intake.py        # Clasificación + creación de issue
│   │   ├── definition.py    # Borrador HU completo
│   │   └── dor_gate.py      # Linter de 12 bloques DoR
│   ├── prompts/             # System prompts para Claude (archivos .md)
│   │   ├── intake_classify.md
│   │   ├── definition_draft_hu.md
│   │   └── dor_validate.md
│   └── templates/
│       └── hu_template.md   # Plantilla de HU (referencia)
├── tests/
│   └── test_dor_gate.py
├── .env.example
├── JIRA_SETUP.md            # Guía de configuración Jira
└── pyproject.toml
```

---

## Entornos: prototipo vs Flexicar

```bash
# Prototipo (tu Jira personal)
cp .env.example .env
# → edita con datos de gerx97.atlassian.net

# Producción Flexicar
cp .env.example .env.flexicar
# → edita con datos de flexicar.atlassian.net
# → para usar: edita .env con los datos de .env.flexicar
```

---

## Checklists vivas

Los prompts de IA y las checklists del flujo se cargan desde archivos `.md` del repositorio
de documentación (`DOCS_PATH` en `.env`). Si se actualiza `14_Checklist_Maestra.md`
o el DoR, el tool usa la versión actualizada automáticamente en la siguiente ejecución.

---

## Tests

```bash
pip install -e ".[dev]"   # instala pytest
pytest tests/ -v
```

---

## Roadmap

- [ ] `po triage FP-X` — árbol de decisión asistido
- [ ] `po discovery FP-X` — checklist guiada de discovery
- [ ] `po signoff FP-X` — email de sign-off para stakeholder
- [ ] `po handshake FP-X` — agenda para la sesión con dev + crea issue FI
- [ ] `po uat FP-X` — paquete de validación UAT
- [ ] `po urgencia "texto"` — flujo abreviado para urgencias
- [ ] `po audit --week` — auditoría DoR semanal (10 issues aleatorios)
- [ ] Integración con `flexicar-po-dashboard` (M7/M8)

---

## Documentación relacionada

- `04_Flujo_End_to_End_PO.md` — flujo de los 10 pasos
- `05_DoR_y_Plantilla_HU.md` — DoR v1 y plantilla de HU
- `11_KPIs_Cuadro_Mando.md` — KPIs que este tool ayuda a medir
- `14_Checklist_Maestra.md` — checklists de cada paso
