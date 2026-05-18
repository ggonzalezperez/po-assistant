# Jira Setup — Proyecto FP (Flexicar Producto)

> Guía paso a paso para configurar el proyecto Jira del flujo PO.
> Tiempo estimado: 20-30 minutos.

---

## 1. Crear la API Token de Jira

1. Ve a: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Nombre: `po-assistant`
4. Copia el token y ponlo en `.env` → `JIRA_API_TOKEN`

---

## 2. Obtener tu dominio Jira

Tu URL de Jira tiene el formato: `https://TU-DOMINIO.atlassian.net`

Ponla en `.env` → `JIRA_BASE_URL=https://TU-DOMINIO.atlassian.net`

---

## 3. Crear el proyecto FP (automático o manual)

### Opción A — Con el CLI (recomendado)

```bash
po setup
```

Esto crea el proyecto y los campos custom automáticamente.

### Opción B — Manual desde la UI

1. Jira → Projects → "Create project"
2. Tipo: **Scrum** (o Kanban)
3. Project name: `Flexicar Producto`
4. Project key: `FP`
5. Click "Create"

---

## 4. Añadir columnas al tablero (UI)

Para que el tablero refleje el flujo PO de los 10 pasos:

1. Ve al proyecto FP → Board → "..." → "Board settings"
2. En "Columns", añade las siguientes columnas:

| Columna del tablero | Categoría Jira |
|---|---|
| INTAKE | To Do |
| TRIAGE / DISCOVERY | In Progress |
| DEFINICIÓN / SIGN-OFF | In Progress |
| DOR GATE / HANDSHAKE | In Progress |
| EN DESARROLLO | In Progress |
| UAT / RELEASE | In Progress |
| CERRADO | Done |

**Nota:** en Jira Free, las columnas del tablero se mapean a las categorías TO DO / IN PROGRESS / DONE.
El estado preciso del flujo PO se guarda como etiqueta (`po-intake`, `po-triage`, etc.) gestionada por el CLI.

---

## 5. Crear campos custom (si `po setup` no los creó)

Ve a Jira → Project settings → Fields → "Add custom field":

| Nombre del campo | Tipo | Para qué |
|---|---|---|
| DoR Score | Number | Score 0-12 del DoR Gate automático |
| DoR Gaps | Text Field (short) | Gaps detectados en el DoR Gate |
| IA Asistida | Text Field (short) | "Si" o "No" |
| Tipo Peticion | Text Field (short) | problema/idea/urgencia/mejora/incidencia |
| Validador UAT | Text Field (short) | Nombre del validador funcional |

Después de crear cada campo, anota el ID (formato `customfield_XXXXX`) y ponlo en `.env`:

```
JIRA_FIELD_DOR_SCORE=customfield_10100
JIRA_FIELD_DOR_GAPS=customfield_10101
JIRA_FIELD_IA_ASISTIDA=customfield_10102
JIRA_FIELD_TIPO_PETICION=customfield_10103
JIRA_FIELD_VALIDADOR_UAT=customfield_10104
```

**Cómo encontrar el ID de un campo:**
Jira → Project settings → Fields → Click en el campo → La URL contiene el ID.

---

## 6. Verificar que todo funciona

```bash
# Test de conexión
po setup

# Crear un issue de prueba
po intake "Prueba de configuración — por favor ignorar"

# Ver el tablero
po dashboard
```

---

## 7. Etiquetas del flujo PO

El CLI usa estas etiquetas para rastrear el estado de cada issue:

| Etiqueta | Estado del flujo |
|---|---|
| `po-intake` | Paso 1 — Intake |
| `po-triage` | Paso 2 — Triage |
| `po-discovery` | Paso 3 — Discovery |
| `po-definicion` | Paso 4 — Definición |
| `po-signoff-sh` | Paso 5 — Sign-off Stakeholder |
| `po-dor-gate` | Paso 6 — DoR Gate |
| `po-handshake` | Paso 7 — Handshake |
| `po-en-desarrollo` | Paso 8 — Desarrollo |
| `po-uat` | Paso 9 — UAT |
| `po-release` | Paso 10 — Release Sign-off |
| `po-cerrado` | Cerrado |
| `po-rechazado` | Rechazado |
| `po-aplazado` | Aplazado al Comité Semanal |

---

## 8. Migrar a Flexicar (producción)

Cuando estés listo para pasar de tu cuenta personal a flexicar.atlassian.net:

1. Copia `.env` → `.env.flexicar`
2. Cambia en `.env.flexicar`:
   ```
   JIRA_BASE_URL=https://flexicar.atlassian.net
   JIRA_EMAIL=german@flexicar.es
   JIRA_API_TOKEN=<token de la cuenta Flexicar>
   ```
3. Para usar la config de Flexicar:
   ```bash
   po --env .env.flexicar setup
   po --env .env.flexicar dashboard
   ```

---

## Troubleshooting frecuente

| Error | Causa | Solución |
|---|---|---|
| `HTTP 401` | Token inválido o email incorrecto | Regenera el token en Atlassian |
| `HTTP 403` | Sin permisos de admin en el proyecto | Verifica que eres admin del proyecto |
| `HTTP 404` | Proyecto no existe | Ejecuta `po setup` o créalo manualmente |
| `La IA no devolvió JSON válido` | Límite de tokens o modelo lento | Reintenta o cambia `CLAUDE_MODEL` |
| `Variable obligatoria no configurada` | `.env` incompleto | Copia `.env.example` → `.env` |
