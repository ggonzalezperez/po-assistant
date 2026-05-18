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

Paso 3 — Configurar columnas del tablero (via navegador si disponible)
  Si tienes acceso a herramientas de navegador (Playwright u otras):
  
  3a. Obtén los IDs de estado ejecutando:
      curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
        "$JIRA_BASE_URL/rest/api/3/status" \
        | python -c "import json,sys; s=json.load(sys.stdin); [print(x['name'], x['id']) for x in s if x['name'] in ['INTAKE','TRIAGE','DISCOVERY','DEFINICION','SIGN-OFF SH','DOR GATE','HANDSHAKE','EN DESARROLLO','UAT','RELEASE']]"
  
  3b. Obtén el ID del tablero:
      curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
        "$JIRA_BASE_URL/rest/agile/1.0/board?projectKeyOrId=$JIRA_PO_PROJECT_KEY&type=kanban" \
        | python -c "import json,sys; b=json.load(sys.stdin); print('Board ID:', b['values'][0]['id'])"
  
  3c. Abre en navegador: $JIRA_BASE_URL/jira/software/projects/$JIRA_PO_PROJECT_KEY/boards/<ID_BOARD>/settings/columns
  
  3d. Crea manualmente las 10 columnas: INTAKE, TRIAGE, DISCOVERY, DEFINICION,
      SIGN-OFF SH, DOR GATE, HANDSHAKE, EN DESARROLLO, UAT, RELEASE
  
  3e. Obtén los IDs de columna inspeccionando el tráfico de red al hacer drag-and-drop
      (F12 → Network → filtrar "rapidviewconfig")
  
  3f. Ejecuta en consola del navegador (estando logado en Jira):
  
      const STATUS = {
        "INTAKE": "<ID>", "TRIAGE": "<ID>", "DISCOVERY": "<ID>",
        "DEFINICION": "<ID>", "SIGN-OFF SH": "<ID>", "DOR GATE": "<ID>",
        "HANDSHAKE": "<ID>", "EN DESARROLLO": "<ID>", "UAT": "<ID>", "RELEASE": "<ID>"
      };
      const COLS = {
        "Backlog": <COL_ID>, "INTAKE": <COL_ID>, "TRIAGE": <COL_ID>,
        "DISCOVERY": <COL_ID>, "DEFINICION": <COL_ID>, "SIGN-OFF SH": <COL_ID>,
        "DOR GATE": <COL_ID>, "HANDSHAKE": <COL_ID>, "EN DESARROLLO": <COL_ID>,
        "UAT": <COL_ID>, "RELEASE": <COL_ID>
      };
      const body = {
        currentStatisticsField: { id: "issueCount_" },
        rapidViewId: <BOARD_ID>,
        mappedColumns: [
          { id: COLS["Backlog"], name: "Backlog", isKanPlanColumn: true, mappedStatuses: [], min: "", max: "" },
          ...Object.entries(STATUS).map(([name, sid]) => ({
            id: COLS[name], name, isKanPlanColumn: false,
            mappedStatuses: [{ id: sid }], min: "", max: ""
          }))
        ]
      };
      const r = await fetch('/rest/greenhopper/1.0/rapidviewconfig/columns', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Atlassian-Token': 'no-check' },
        body: JSON.stringify(body)
      });
      console.log(r.status, await r.json()); // debe ser 200

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
- El Paso 3 (columnas) requiere sesión activa en el navegador — la API
  `PUT /rest/greenhopper/1.0/rapidviewconfig/columns` no acepta autenticación
  Basic, solo cookies de sesión. Es la única operación que no se puede hacer
  puramente via API token.
- Si el agente tiene MCP Playwright disponible, puede automatizar el Paso 3
  completo incluyendo la creación de columnas y la llamada al endpoint.
