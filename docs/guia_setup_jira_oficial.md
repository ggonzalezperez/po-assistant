# Guía de configuración — Jira oficial Flexicar

> Esta guía reproduce en el Jira corporativo exactamente lo que el
> prototipo tiene en `gerx97.atlassian.net`. La mayor parte se automatiza
> con `po setup`; hay un paso manual para las columnas del tablero.

---

## Requisitos previos

| Requisito | Detalle |
|-----------|---------|
| Rol en Jira | **Administrador de proyecto** como mínimo; para crear campos globales y esquemas de workflow se necesita **Administrador Jira** (o que el admin lo ejecute) |
| Python | 3.11+ con el repo `po-assistant` instalado (`uv sync`) |
| API token | Generado en `https://id.atlassian.com/manage-profile/security/api-tokens` con el usuario corporativo |
| Clave de proyecto | La clave exacta del proyecto Jira de producto (p.ej. `FLX`, `PROD`, `FLEX`…) |

---

## Paso 1 — Configurar `.env`

Copia `.env.example` a `.env` y rellena estos valores con los datos del entorno oficial:

```dotenv
# ── Jira corporativo ────────────────────────────────────────
JIRA_BASE_URL=https://<empresa>.atlassian.net
JIRA_EMAIL=<tu-usuario>@flexicar.es
JIRA_API_TOKEN=<token-generado-en-atlassian>

JIRA_PO_PROJECT_KEY=<CLAVE_PROYECTO>    # ej: FLX
JIRA_DEV_PROJECT_KEY=<CLAVE_DEV>        # ej: FDV

# ── Claude API ───────────────────────────────────────────────
ANTHROPIC_API_KEY=<sk-ant-api03-...>
CLAUDE_MODEL=claude-sonnet-4-6

# ── Equipo PO (formato Nombre:email separados por coma) ──────
PO_TEAM=Ester Carrasco:ecarrasco@flexicar.es,Daniel Luengo:dluengo@flexicar.es,Jorge Ye Fu:jorge.ye@flexicar.es,César Herredero:cesar.herredero@flexicar.es
PE_EMAIL=<product-engineer>@flexicar.es

# ── Docs ─────────────────────────────────────────────────────
DOCS_PATH=<ruta-local-a-Modelo_Operativo_PO>
ENVIRONMENT=production
DRY_RUN=false
PYTHONUTF8=1
```

Los campos `JIRA_FIELD_*` se rellenan **automáticamente** durante el paso 2.

---

## Paso 2 — Ejecutar `po setup`

```bash
po setup
```

Este comando crea o verifica automáticamente:

| Qué | Cómo | Idempotente |
|-----|------|-------------|
| Proyecto Jira | `POST /rest/api/3/project` | Sí — detecta si ya existe |
| 5 campos custom | `POST /rest/api/3/field` | Sí — detecta por nombre (case-insensitive) |
| IDs de campos → `.env` | `dotenv.set_key()` | Sí — solo escribe si cambia |
| 10 estados globales | `POST /rest/api/3/statuses` | Sí — detecta existentes |
| Workflow "PO Workflow — Flexicar" | `POST /rest/api/3/workflows/create` | Sí — comprueba antes de crear |
| Asignación workflow al proyecto | `PUT /rest/api/2/workflowscheme/{id}/draft` + publish | Aplica solo si no asignado |
| Tablero Kanban | `POST /rest/agile/1.0/board` | Sí — detecta si ya existe |
| Filtros rápidos (uno por estado PO) | `POST /rest/agile/1.0/board/{id}/quickfilter` | No crítico si falla |
| Componentes (uno por PO del equipo) | `POST /rest/api/3/component` | Sí — detecta existentes |

### Campos custom que crea

| Campo | Tipo | Uso |
|-------|------|-----|
| `DoR Score` | Número | Puntuación 0-12 del DoR Gate automático |
| `DoR Gaps` | Texto | Lista de gaps detectados por la IA |
| `IA Asistida` | Texto | Si la HU fue asistida por IA |
| `Tipo Peticion` | Texto | problema / idea / urgencia / mejora / incidencia |
| `Validador UAT` | Texto | Nombre y rol del validador funcional |

### Estados del workflow

| Estado | Categoría Jira |
|--------|---------------|
| INTAKE | Por hacer (TODO) |
| TRIAGE | Por hacer (TODO) |
| DISCOVERY | En curso (IN_PROGRESS) |
| DEFINICION | En curso |
| SIGN-OFF SH | En curso |
| DOR GATE | En curso |
| HANDSHAKE | En curso |
| EN DESARROLLO | En curso |
| UAT | En curso |
| RELEASE | Hecho (DONE) |

---

## Paso 3 — Configurar columnas del tablero (una sola vez)

Este es el único paso que **no se puede hacer con la API pública de Jira**:
`PUT /rest/agile/1.0/board/{id}/configuration` devuelve **405** en Jira Cloud.

Jira usa internamente el endpoint `PUT /rest/greenhopper/1.0/rapidviewconfig/columns`
(API legacy de Greenhopper), que **solo acepta autenticación por cookie de sesión**,
no por API token. Por eso se ejecuta desde dentro de una sesión activa del navegador.

Hay tres formas de hacerlo, de más a menos automática:

### Opción A — Claude Code con MCP Playwright (recomendado si usas IA)

Esta es la forma en que se configuró el tablero del prototipo. Claude Code tiene
acceso al plugin MCP Playwright que controla un navegador real, mantiene la sesión
y puede llamar a la API interna de Jira.

Cuando ejecutes el `prompt_setup_jira.md` con Claude Code (con el plugin Playwright
activo), el agente hará automáticamente:

1. `browser_navigate` → abre la página de configuración de columnas del tablero
2. `browser_snapshot` → lee el estado actual de la UI
3. Crea las columnas faltantes con `browser_type` + `browser_click` (o renombra las existentes)
4. `browser_network_requests` → intercepta el tráfico para capturar los IDs reales
   de columnas y estados del payload de `rapidviewconfig`
5. `browser_evaluate` → ejecuta `fetch('PUT /rest/greenhopper/1.0/rapidviewconfig/columns', ...)`
   dentro de la sesión del navegador, con el cuerpo correcto para mapear los 10 estados

El resultado es HTTP 200 y el tablero queda configurado sin intervención humana.

**Requisito:** tener el plugin MCP Playwright instalado en Claude Code.
En el `claude_desktop_config.json` o `.claude/settings.json`:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"]
    }
  }
}
```

### Opción B — Script en consola del navegador (manual rápido)

1. Abre el tablero: `https://<empresa>.atlassian.net/jira/software/projects/<CLAVE>/boards/<ID_BOARD>`
2. Abre las DevTools del navegador (F12) → consola
3. Ejecuta el script siguiente **sustituyendo los IDs** de columnas y estados por los reales de tu instancia:

```javascript
// ── INSTRUCCIONES ────────────────────────────────────────────────────────────
// 1. Abre: Jira → Tablero → Configuración → Columnas
// 2. Crea las 10 columnas manualmente (solo los nombres) si no existen ya
// 3. Inspecciona la red (F12 → Network) al mover una columna y captura el
//    payload de PUT /rest/greenhopper/1.0/rapidviewconfig/columns
//    para obtener los IDs reales de columnas y estados
// 4. Sustituye los valores de mappedColumns por los de tu instancia
// ─────────────────────────────────────────────────────────────────────────────

const body = {
  currentStatisticsField: { id: "issueCount_" },
  rapidViewId: <ID_BOARD>,                    // ← ID del tablero (ver URL)
  mappedColumns: [
    // Backlog — columna especial de Kanban, no mapear a estado
    { id: <COL_BACKLOG>,  name: "Backlog",        isKanPlanColumn: true,  mappedStatuses: [], min: "", max: "" },
    // Columnas del flujo PO — sustituir id de columna y id de estado
    { id: <COL_INTAKE>,       name: "INTAKE",        isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_INTAKE>" }],        min: "", max: "" },
    { id: <COL_TRIAGE>,       name: "TRIAGE",        isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_TRIAGE>" }],        min: "", max: "" },
    { id: <COL_DISCOVERY>,    name: "DISCOVERY",     isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DISCOVERY>" }],     min: "", max: "" },
    { id: <COL_DEFINICION>,   name: "DEFINICION",    isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DEFINICION>" }],    min: "", max: "" },
    { id: <COL_SIGNOFF>,      name: "SIGN-OFF SH",   isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_SIGNOFF>" }],       min: "", max: "" },
    { id: <COL_DOR>,          name: "DOR GATE",      isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DOR>" }],           min: "", max: "" },
    { id: <COL_HANDSHAKE>,    name: "HANDSHAKE",     isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_HANDSHAKE>" }],     min: "", max: "" },
    { id: <COL_DESARROLLO>,   name: "EN DESARROLLO", isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DESARROLLO>" }],   min: "", max: "" },
    { id: <COL_UAT>,          name: "UAT",           isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_UAT>" }],           min: "", max: "" },
    { id: <COL_RELEASE>,      name: "RELEASE",       isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_RELEASE>" }],      min: "", max: "" },
  ]
};

const resp = await fetch('/rest/greenhopper/1.0/rapidviewconfig/columns', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json', 'X-Atlassian-Token': 'no-check' },
  body: JSON.stringify(body)
});
console.log(resp.status, await resp.json());
// Resultado esperado: 200 OK
```

#### Cómo obtener los IDs de columnas y estados

**IDs de columnas** — después de crearlas manualmente en Configuración → Columnas,
inspecciona el payload de cualquier drag-and-drop en la red (F12 → Network →
filtrar por `rapidviewconfig`) para ver los IDs asignados.

**IDs de estados** — ejecuta en consola estando logado:
```javascript
const r = await fetch('/rest/api/3/status'); const s = await r.json();
console.table(s.filter(x => ["INTAKE","TRIAGE","DISCOVERY","DEFINICION","SIGN-OFF SH","DOR GATE","HANDSHAKE","EN DESARROLLO","UAT","RELEASE"].includes(x.name)).map(x => ({name: x.name, id: x.id})));
```

### Opción B — UI manual

Jira → Tablero → Configuración de tablero → Columnas → arrastra cada estado
desde "Estados sin asignar" a su columna correspondiente.

---

## Paso 4 — Verificar

```bash
po setup          # debe imprimir "ya configurado" / "ya existe" en todo
po dashboard      # debe mostrar el pipeline vacío sin errores
po demo --offline # valida el flujo completo sin crear tickets reales
```

---

## Permisos necesarios en Jira corporativo

Si el usuario que ejecuta `po setup` no tiene permisos de administrador global,
el administrador de Jira debe hacer previamente:

1. **Crear los 10 estados globales** en Jira → Administración → Estados
2. **Crear el esquema de workflow** y asignarlo al proyecto
3. **Crear los 5 campos custom** en Jira → Administración → Campos personalizados
   y añadirlos a la pantalla del proyecto
4. Dar al usuario PO permisos de **Administrador de proyecto** para el tablero

Una vez hecho, el PO puede ejecutar `po setup` sin privilegios globales (el
comando detectará los elementos existentes y no intentará recrearlos).

---

## Referencia rápida — valores del prototipo

> Solo como referencia. En el Jira oficial los IDs serán distintos.

| Elemento | Prototipo (`gerx97.atlassian.net`) |
|----------|------------------------------------|
| Proyecto PO | `FP` — Flexicar Producto |
| Board ID | `1` |
| Status INTAKE | `10005` |
| Status TRIAGE | `10006` |
| Status DISCOVERY | `10007` |
| Status DEFINICION | `10008` |
| Status SIGN-OFF SH | `10009` |
| Status DOR GATE | `10010` |
| Status HANDSHAKE | `10011` |
| Status EN DESARROLLO | `10012` |
| Status UAT | `10013` |
| Status RELEASE | `10014` |
| DoR Score field | `customfield_10087` |
| DoR Gaps field | `customfield_10088` |
| IA Asistida field | `customfield_10089` |
| Tipo Peticion field | `customfield_10090` |
| Validador UAT field | `customfield_10091` |
