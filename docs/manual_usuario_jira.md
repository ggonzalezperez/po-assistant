# Manual de usuario — Flujo PO en Jira

> Para Product Owners de Flexicar. Cómo usar el tablero, los estados y
> el CLI `po` en el día a día.

---

## El tablero Kanban

Abre el tablero desde:
`https://<empresa>.atlassian.net/jira/software/projects/<CLAVE>/boards/<ID>`

El tablero tiene **10 columnas** que representan los 10 pasos del flujo PO.
Cada ticket de producto pasa de izquierda a derecha. El CLI `po` es quien
mueve los tickets — no los arrastres manualmente.

```
INTAKE → TRIAGE → DISCOVERY → DEFINICION → SIGN-OFF SH
    → DOR GATE → HANDSHAKE → EN DESARROLLO → UAT → RELEASE
```

---

## Los 10 estados y qué ocurre en cada uno

| Estado | Responsable | Qué significa | Siguiente acción |
|--------|-------------|---------------|-----------------|
| **INTAKE** | PE / PO | Petición recibida y clasificada por IA | Llevar al Comité Semanal de Triage |
| **TRIAGE** | Comité Semanal | Petición revisada, se decide si avanza | Asignar PO y pasar a Discovery |
| **DISCOVERY** | PO asignado | PO investiga contexto, stakeholders y viabilidad | Reunión con stakeholder → `po define` |
| **DEFINICION** | PO asignado | HU siendo redactada (con o sin IA) | `po dor-gate` para validar |
| **SIGN-OFF SH** | Stakeholder | Stakeholder revisa y aprueba la HU | Aprobación verbal o escrita |
| **DOR GATE** | IA + PO | Validación automática de los 12 bloques DoR | Si pasa (≥11/12 sin críticos): `po handshake` |
| **HANDSHAKE** | PO + Tech Lead | Sesión de traspaso técnico al equipo dev | Crear issue en proyecto DEV |
| **EN DESARROLLO** | Equipo dev | Feature en sprint | Esperar a QA/UAT |
| **UAT** | Validador designado | Pruebas funcionales con datos reales | Sign-off final |
| **RELEASE** | PO | Feature desplegada, pendiente sign-off PO | Cerrar ticket |

### Estados especiales

| Estado | Cuándo se usa |
|--------|--------------|
| **CERRADO** | Feature entregada y confirmada por el negocio |
| **RECHAZADO** | Petición descartada (duplicada, fuera de alcance, etc.) |
| **APLAZADO** | Revisión aplazada al próximo Comité Semanal |

---

## Cómo usar el CLI `po` — comandos del día a día

### `po intake "descripción"`

**Cuándo usarlo:** Cuando recibes una petición nueva (llamada, email, reunión, Slack).

```bash
po intake "Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM"
```

**Qué hace:**
1. La IA clasifica la petición (tipo, prioridad, stakeholder)
2. Redacta una descripción estructurada
3. Crea el ticket en Jira en estado **INTAKE**
4. Te muestra preguntas abiertas para el discovery

**Resultado en Jira:** ticket `FP-XX` con etiquetas `tipo:problema` (o el tipo detectado), `prio:alta/media/baja`.

---

### `po define FP-XX`

**Cuándo usarlo:** Después de completar el discovery, cuando tienes suficiente información para escribir la HU.

```bash
po define FP-12
# Con notas de una reunión:
po define FP-12 --notes notas_reunion_maria.txt
```

**Qué hace:**
1. Lee el contexto del ticket de Jira
2. La IA genera la HU completa en 6 bloques:
   - Contexto y problema
   - Descripción funcional
   - Criterios de aceptación
   - Plan UAT
   - Operativa (prioridad, dependencias)
   - Trazabilidad IA
3. Actualiza la descripción del ticket en Jira
4. Mueve el ticket a estado **DEFINICION**

**Duración:** ~30-45 segundos (llamada a Claude API).

---

### `po dor-gate FP-XX`

**Cuándo usarlo:** Cuando la HU está escrita y quieres validar si está lista para el Handshake.

```bash
po dor-gate FP-12
```

**Qué hace:**
1. La IA evalúa los 12 bloques del DoR (Definition of Ready)
2. Muestra un informe con score y gaps por bloque
3. Guarda el resultado como comentario en Jira
4. Actualiza los campos `DoR Score` y `DoR Gaps`
5. Mueve el ticket:
   - Si pasa (≥11/12 sin bloques críticos fallidos) → **DOR GATE**
   - Si no pasa → **DEFINICION** (vuelve a completar los gaps)

**Los 6 bloques críticos** (deben cumplir siempre):
- B1: Problema definido (no solución)
- B5: Alcance + exclusiones explícitas
- B7: Reglas de negocio críticas
- B9: Casuística completa
- B10: Criterios de aceptación verificables
- B12: Validador UAT designado

---

### `po dashboard`

**Cuándo usarlo:** Al inicio del día, en el Comité Semanal, para revisar el estado del pipeline.

```bash
po dashboard
# Filtrar por PO:
po dashboard --po ester
# Ver también cerrados:
po dashboard --all
```

**Qué muestra:**
- Pipeline de los 10 estados con número de issues en cada uno
- Antigüedad del issue más viejo en cada estado
- Alertas de SLA (INTAKE > 48h, SIGN-OFF > 5 días, DOR GATE > 2 días)

---

## Anatomía de un ticket FP

Un ticket bien configurado tiene:

```
Título:   [TIPO] Descripción breve del problema/funcionalidad
Estado:   DEFINICION (columna actual en el tablero)
Etiquetas: po-definicion  tipo:problema  prio:alta

Campos custom:
  DoR Score:      8/12 (rellenado por po dor-gate)
  DoR Gaps:       "B9: Casuística incompleta; B12: Validador sin designar"
  IA Asistida:    Sí
  Tipo Peticion:  problema
  Validador UAT:  María Ruiz (Responsable Operaciones Comerciales)

Descripción:
  ## Contexto y Problema
  ## Descripción funcional
  ## Criterios de aceptación
  ## Plan de UAT
  ## Operativa
  ## Trazabilidad IA
```

---

## Filtros rápidos del tablero

El tablero tiene filtros por estado PO que aparecen como botones sobre el tablero.
Útiles para el Comité Semanal:

| Filtro | Para qué |
|--------|----------|
| INTAKE | Ver las peticiones nuevas de la semana |
| TRIAGE | Issues en espera de decisión del Comité |
| SIGN-OFF SH | Issues esperando aprobación de stakeholder |
| DOR GATE | Issues listos para pasar a desarrollo |

---

## Flujo semanal tipo (referencia)

```
Lunes — Comité Semanal de Triage
  po dashboard                        → revisar pipeline completo
  (revisar issues en INTAKE)          → decidir qué avanza, qué se aplaza
  (mover manualmente INTAKE → TRIAGE en Jira si el PO lo lleva)

Durante la semana — Discovery / Definición
  po intake "nueva petición"          → capturar peticiones nuevas
  po define FP-XX                     → generar HU tras discovery
  po dor-gate FP-XX                   → validar DoR antes del Handshake

Jueves/Viernes — Sign-offs y Handshakes
  (reunión con stakeholder)           → Sign-off SH manual en Jira
  (sesión de handshake con dev)       → crear issue en proyecto DEV
```

---

## Etiquetas del sistema (no modificar manualmente)

El CLI usa estas etiquetas para rastrear el estado. **No las edites a mano**
en Jira — usa siempre el CLI para mover tickets.

| Etiqueta | Estado visible en tablero |
|----------|--------------------------|
| `po-intake` | INTAKE |
| `po-triage` | TRIAGE |
| `po-discovery` | DISCOVERY |
| `po-definicion` | DEFINICION |
| `po-signoff-sh` | SIGN-OFF SH |
| `po-dor-gate` | DOR GATE |
| `po-handshake` | HANDSHAKE |
| `po-en-desarrollo` | EN DESARROLLO |
| `po-uat` | UAT |
| `po-release` | RELEASE |
| `po-cerrado` | — (cerrado) |
| `po-rechazado` | — (rechazado) |
| `po-aplazado` | — (aplazado) |

---

## Preguntas frecuentes

**¿Puedo editar la HU generada por la IA?**  
Sí, siempre. La HU es un borrador. El PO debe revisarla, completar los
[PENDIENTE:] y adaptarla al contexto real antes del DOR GATE.

**¿Qué pasa si el DOR GATE da KO?**  
El ticket vuelve a DEFINICION. La IA deja un comentario con los gaps concretos.
Completa los gaps, edita la descripción en Jira y vuelve a ejecutar `po dor-gate`.
No hay un número máximo de intentos.

**¿El CLI puede sobrescribir trabajo mío en Jira?**  
`po define` sobreescribe la descripción del ticket. Si ya tienes contenido
importante, exporta o copia antes de ejecutar. `po dor-gate` solo añade
comentarios, no modifica la descripción.

**¿Puedo usar el CLI sin conexión a internet?**  
`po demo --offline` simula el flujo sin crear nada en Jira ni llamar a la IA.
Para trabajo real necesitas conexión a Jira y a la API de Anthropic.

**¿Qué versión de Claude usa?**  
`claude-sonnet-4-6` por defecto (configurable en `.env` → `CLAUDE_MODEL`).
