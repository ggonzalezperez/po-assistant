# Prompt IA — Setup automático del flujo PO en Jira

> Pega este prompt en Claude Code (o cualquier agente con acceso a terminal)
> desde la raíz del repo `po-assistant` con el `.env` ya configurado.
> El agente ejecutará todos los pasos, verificará el resultado y configurará
> las columnas del tablero.

---

## Prompt

```
Configura el flujo PO completo en Jira usando el CLI po-assistant.

CONTEXTO:
- Estás en el repo po-assistant (po-assistant/)
- El fichero .env ya está configurado con las credenciales de Jira y Anthropic
- El entorno Python está en .venv/ (usa .venv/Scripts/po.exe en Windows o .venv/bin/po en Linux/Mac)
- Variable de entorno PYTHONUTF8=1 obligatoria en Windows

OBJETIVO:
Dejar el Jira completamente configurado con:
1. Los 5 campos custom del flujo PO
2. El workflow "PO Workflow — Flexicar" con 10 estados y transiciones globales
3. El tablero Kanban "Pipeline PO — <CLAVE>" con las 10 columnas asignadas a sus estados
4. Los componentes del equipo PO
5. Verificación end-to-end con po demo --offline

PASOS A EJECUTAR:

Paso 1 — Verificar entorno
  - Comprueba que .env existe y tiene JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, ANTHROPIC_API_KEY
  - Si falta alguno, detente y avisa

Paso 2 — Ejecutar po setup
  Ejecuta: PYTHONUTF8=1 .venv/Scripts/po.exe setup  (Windows)
           PYTHONUTF8=1 .venv/bin/po setup           (Linux/Mac)
  Responde "Y" a todas las confirmaciones.
  Verifica que el output muestra:
  - "Conexión Jira OK"
  - Campos custom creados o "ya configurado"
  - "Workflow PO ya existe" o "✓ Workflow creado"
  - Tablero Kanban creado o "ya existe"

Paso 3 — Configurar columnas del tablero via MCP Playwright
  
  CONTEXTO IMPORTANTE: La API pública PUT /rest/agile/1.0/board/{id}/configuration
  devuelve 405 en Jira Cloud. Jira usa internamente el endpoint
  PUT /rest/greenhopper/1.0/rapidviewconfig/columns (API legacy de Greenhopper),
  que SOLO acepta autenticación por cookie de sesión, no por API token.
  Por eso hay que ejecutarlo desde dentro de una sesión activa del navegador.
  
  Usa las herramientas MCP Playwright siguiendo exactamente estos pasos:

  3a. Obtén los IDs de estado via API (esto SÍ funciona con API token):
      Ejecuta en terminal:
      curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_BASE_URL/rest/api/3/status"
      Filtra los 10 estados PO y anota sus IDs numéricos.

  3b. Obtén el ID del tablero:
      curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
        "$JIRA_BASE_URL/rest/agile/1.0/board?projectKeyOrId=$JIRA_PO_PROJECT_KEY&type=kanban"
      Anota el campo "id" del primer resultado.

  3c. Navega a la página de configuración de columnas:
      browser_navigate → $JIRA_BASE_URL/jira/software/projects/$JIRA_PO_PROJECT_KEY/boards/<BOARD_ID>/settings/columns
      (Si pide login, usa browser_fill_form con las credenciales.)

  3d. Crea las 10 columnas. Para cada nombre en
      [INTAKE, TRIAGE, DISCOVERY, DEFINICION, SIGN-OFF SH, DOR GATE, HANDSHAKE, EN DESARROLLO, UAT, RELEASE]:
      - browser_snapshot → localiza el botón "Add column" o campo de texto de nueva columna
      - browser_click → click en "Add column"
      - browser_type → escribe el nombre
      - browser_press_key → Enter para confirmar
      Repite hasta tener las 10 columnas.

  3e. Obtén los IDs de columna capturando el tráfico de red:
      - browser_network_requests → activa la captura
      - browser_drag → arrastra cualquier estado a cualquier columna (para disparar la petición)
      - browser_network_requests → busca la petición a "rapidviewconfig/columns"
      - En el payload verás los IDs actuales de todas las columnas (campo "id" de cada mappedColumn)
      Anota los IDs de columna para las 10 columnas que creaste.

  3f. Llama al endpoint de configuración desde dentro de la sesión del navegador:
      browser_evaluate → ejecuta este JavaScript (sustituye los IDs con los reales):

      const body = {
        currentStatisticsField: { id: "issueCount_" },
        rapidViewId: <BOARD_ID>,
        mappedColumns: [
          { id: <COL_BACKLOG>,     name: "Backlog",        isKanPlanColumn: true,  mappedStatuses: [], min: "", max: "" },
          { id: <COL_INTAKE>,      name: "INTAKE",         isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_INTAKE>" }],       min: "", max: "" },
          { id: <COL_TRIAGE>,      name: "TRIAGE",         isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_TRIAGE>" }],       min: "", max: "" },
          { id: <COL_DISCOVERY>,   name: "DISCOVERY",      isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DISCOVERY>" }],    min: "", max: "" },
          { id: <COL_DEFINICION>,  name: "DEFINICION",     isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DEFINICION>" }],   min: "", max: "" },
          { id: <COL_SIGNOFF>,     name: "SIGN-OFF SH",    isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_SIGNOFF>" }],      min: "", max: "" },
          { id: <COL_DOR>,         name: "DOR GATE",       isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DOR>" }],          min: "", max: "" },
          { id: <COL_HANDSHAKE>,   name: "HANDSHAKE",      isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_HANDSHAKE>" }],    min: "", max: "" },
          { id: <COL_DESARROLLO>,  name: "EN DESARROLLO",  isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_DESARROLLO>" }],  min: "", max: "" },
          { id: <COL_UAT>,         name: "UAT",            isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_UAT>" }],          min: "", max: "" },
          { id: <COL_RELEASE>,     name: "RELEASE",        isKanPlanColumn: false, mappedStatuses: [{ id: "<STATUS_RELEASE>" }],     min: "", max: "" },
        ]
      };
      const r = await fetch('/rest/greenhopper/1.0/rapidviewconfig/columns', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Atlassian-Token': 'no-check' },
        body: JSON.stringify(body)
      });
      const res = await r.json();
      `STATUS: ${r.status} — ${JSON.stringify(res).slice(0,200)}`;
      // Resultado esperado: 200

  3g. Verifica el resultado:
      browser_navigate → $JIRA_BASE_URL/jira/software/projects/$JIRA_PO_PROJECT_KEY/boards/<BOARD_ID>
      browser_take_screenshot → confirma que las 10 columnas están visibles con issues en INTAKE

Paso 4 — Verificar
  Ejecuta: PYTHONUTF8=1 .venv/Scripts/po.exe setup
  → Todo debe mostrar "ya configurado" / "ya existe"
  
  Ejecuta: PYTHONUTF8=1 .venv/Scripts/po.exe dashboard
  → Debe mostrar el pipeline vacío sin errores
  
  Ejecuta: PYTHONUTF8=1 .venv/Scripts/po.exe demo --offline
  → Debe completar el flujo INTAKE→DEFINICIÓN→DOR GATE sin errores

CRITERIO DE ÉXITO:
- po setup termina con exit 0 y "Setup completado"
- po dashboard muestra las 10 filas del pipeline
- po demo --offline completa con DoR score visible
- El tablero Jira muestra las 10 columnas en el navegador

Si cualquier paso falla, muestra el error completo y sugiere la corrección
antes de continuar.
```

---

## Notas de uso

- El prompt asume que `.env` ya está rellenado. Si no, ajusta el Paso 1 para
  guiar la creación del token y la configuración del fichero.
- En Windows, sustituye `.venv/bin/po` por `.venv\Scripts\po.exe`.
- El Paso 3 requiere **MCP Playwright activo** en Claude Code. Sin él, el
  tablero queda sin columnas y hay que configurarlas a mano desde el navegador
  (ver `docs/guia_setup_jira_oficial.md` Opción B).
- Las herramientas MCP Playwright usadas en el Paso 3 son:
  `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`,
  `browser_press_key`, `browser_network_requests`, `browser_evaluate`,
  `browser_take_screenshot`.
- El endpoint `PUT /rest/greenhopper/1.0/rapidviewconfig/columns` solo acepta
  cookies de sesión, nunca API token. Por eso el `browser_evaluate` funciona
  (ejecuta dentro de la sesión del navegador logado) y `curl` con API token no.
