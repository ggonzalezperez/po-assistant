# Jira Setup — Referencia rápida

> Para la guía completa de configuración en el Jira corporativo, consulta
> [`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md).

---

## Setup en 2 pasos

```bash
# 1. Configurar .env
cp .env.example .env
# → Rellena JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, ANTHROPIC_API_KEY

# 2. Inicializar
po setup
```

`po setup` crea automáticamente: proyecto, campos custom, workflow de 10 estados,
tablero Kanban y componentes del equipo. Los IDs de campos se guardan en `.env`.

El único paso manual es configurar las columnas del tablero (ver más abajo).

---

## Campos custom

Creados por `po setup`. IDs guardados automáticamente en `.env`.

| Campo | Variable `.env` | Tipo | Uso |
|-------|-----------------|------|-----|
| DoR Score | `JIRA_FIELD_DOR_SCORE` | Número | Score 0-12 del DoR Gate |
| DoR Gaps | `JIRA_FIELD_DOR_GAPS` | Texto | Gaps detectados por la IA |
| IA Asistida | `JIRA_FIELD_IA_ASISTIDA` | Texto | Si/No |
| Tipo Peticion | `JIRA_FIELD_TIPO_PETICION` | Texto | problema/idea/urgencia/mejora/incidencia |
| Validador UAT | `JIRA_FIELD_VALIDADOR_UAT` | Texto | Nombre y rol del validador funcional |

---

## Workflow — 10 estados

Workflow global "PO Workflow — Flexicar" con transiciones globales (cualquier
estado puede ir a cualquier otro).

| Estado | Categoría Jira | Etiqueta CLI |
|--------|---------------|-------------|
| INTAKE | Por hacer | `po-intake` |
| TRIAGE | Por hacer | `po-triage` |
| DISCOVERY | En curso | `po-discovery` |
| DEFINICION | En curso | `po-definicion` |
| SIGN-OFF SH | En curso | `po-signoff-sh` |
| DOR GATE | En curso | `po-dor-gate` |
| HANDSHAKE | En curso | `po-handshake` |
| EN DESARROLLO | En curso | `po-en-desarrollo` |
| UAT | En curso | `po-uat` |
| RELEASE | Hecho | `po-release` |

Las etiquetas `po-*` son mantenidas por el CLI en paralelo al estado Jira,
para compatibilidad con los filtros del dashboard.

---

## Columnas del tablero (configuración manual)

La API pública de Jira Cloud devuelve `405` al intentar configurar columnas.
Se usa la API interna de Greenhopper desde el navegador.

**Una vez creadas las 10 columnas en la UI**, ejecuta esto en la consola del
navegador estando logado en Jira:

```javascript
// Sustituye los IDs por los de tu instancia (ver docs/guia_setup_jira_oficial.md)
const resp = await fetch('/rest/greenhopper/1.0/rapidviewconfig/columns', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json', 'X-Atlassian-Token': 'no-check' },
  body: JSON.stringify({ rapidViewId: <BOARD_ID>, mappedColumns: [ /* ... */ ] })
});
console.log(resp.status); // 200 = OK
```

Para el payload completo con todos los IDs, consulta
[`docs/guia_setup_jira_oficial.md`](docs/guia_setup_jira_oficial.md).

---

## Obtener IDs de estado (para el script de columnas)

```javascript
// Ejecutar en consola del navegador en Jira
const r = await fetch('/rest/api/3/status');
const estados = await r.json();
const po = ["INTAKE","TRIAGE","DISCOVERY","DEFINICION","SIGN-OFF SH",
            "DOR GATE","HANDSHAKE","EN DESARROLLO","UAT","RELEASE"];
console.table(estados.filter(s => po.includes(s.name)).map(s => ({name: s.name, id: s.id})));
```

---

## Troubleshooting

| Error | Causa | Solución |
|-------|-------|----------|
| `HTTP 401` | Token inválido | Regenera en `id.atlassian.com` → Security → API tokens |
| `HTTP 403` | Sin permisos admin | Pide al admin que ejecute `po setup` o cree los elementos manualmente |
| `HTTP 404` proyecto | Proyecto no existe | `po setup` lo crea automáticamente |
| `HTTP 410` en search | API deprecated | Asegúrate de usar la versión actual del repo (usa `/search/jql`) |
| `HTTP 405` en columnas | Limitación Jira Cloud | Usa el script de consola de navegador (ver arriba) |
| `La IA no devolvió JSON válido` | Timeout o modelo | Reintenta; si persiste cambia `CLAUDE_MODEL` en `.env` |
| `Variable obligatoria no configurada` | `.env` incompleto | `cp .env.example .env` y rellena los valores |
| `UnicodeEncodeError` en Windows | Encoding de terminal | Añade `PYTHONUTF8=1` a `.env` |
