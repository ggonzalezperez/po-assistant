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

| Estado | Responsable | Qué significa | Siguiente acción CLI |
|--------|-------------|---------------|----------------------|
| **INTAKE** | PE / PO | Petición recibida y clasificada por IA | `po triage FP-X` |
| **TRIAGE** | Comité Semanal | Petición revisada, se decide si avanza | `po discovery FP-X` |
| **DISCOVERY** | PO asignado | PO investiga contexto, stakeholders y viabilidad | `po define FP-X` |
| **DEFINICION** | PO asignado | HU siendo redactada (con o sin IA) | `po dor-gate FP-X` |
| **SIGN-OFF SH** | Stakeholder | Stakeholder revisa y aprueba el alcance | Confirmar en Jira → `po dor-gate FP-X` |
| **DOR GATE** | IA + PO | Validación automática de los 12 bloques DoR | Si pasa (≥11/12 sin críticos): `po handshake FP-X` |
| **HANDSHAKE** | PO + Tech Lead | Sesión de traspaso técnico al equipo dev | Esperar sprint → `po uat FP-X` |
| **EN DESARROLLO** | Equipo dev | Feature en sprint | Esperar a QA/UAT → `po uat FP-X` |
| **UAT** | Validador designado | Pruebas funcionales con datos reales | `po release FP-X` |
| **RELEASE** | PO | Feature desplegada, pendiente confirmación negocio | Cerrar ticket en Jira |

### Estados especiales

| Estado | Cuándo se usa |
|--------|--------------|
| **CERRADO** | Feature entregada y confirmada por el negocio |
| **RECHAZADO** | Petición descartada en triage (incidencia técnica, urgencia, devuelta al stakeholder) |
| **APLAZADO** | Revisión aplazada al próximo Comité Semanal |

---

## Cómo funciona la descripción del ticket

Cada comando del CLI **añade** un bloque al final de la descripción de Jira — nunca sobreescribe. La historia completa del ticket queda visible:

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
[HU completa]
…
```

---

## Cómo introducir respuestas en el CLI

Los comandos guiados (triage, discovery, signoff, handshake, uat, release) hacen preguntas
una a una. Para cada pregunta:

- **Respuesta corta** — escríbela y pulsa Enter. Después escribe `;;` y pulsa Enter para confirmar.
- **Respuesta larga o pegada** — pega el texto (puede tener saltos de línea, listas, párrafos en blanco). Cuando hayas terminado, escribe `;;` en una nueva línea y pulsa Enter.

```
¿Cuál es el problema real detrás de esta petición?
  (;; en línea nueva para terminar)
→ Flexicar necesita ganar autonomía técnica sobre la Intranet
→ antes del traspaso de Minery. El equipo no conoce la arquitectura.
→
→ La tarea de onboarding cubre solo el uso básico, no el desarrollo.
→ ;;
```

El `;;` es el único terminador — funciona igual para respuestas cortas y largas,
y permite pegar texto con líneas en blanco sin que el CLI avance a la siguiente pregunta.

---

## Cómo usar el CLI `po` — comandos del día a día

### `po intake "descripción"`

**Cuándo usarlo:** Cuando recibes una petición nueva (llamada, email, reunión, Slack).

```bash
po intake "Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM"
```

**Qué hace:**
1. La IA clasifica la petición (tipo, prioridad)
2. Redacta una descripción estructurada
3. Crea el ticket en Jira en estado **INTAKE**
4. Muestra preguntas abiertas para el triage/discovery

**Siguiente:** `po triage FP-XX`

---

### `po triage FP-XX`

**Cuándo usarlo:** En el Comité Semanal de Triage, después del intake.

```bash
po triage FP-12
```

**Qué hace:**
1. Muestra el contexto actual del ticket
2. Presenta 5 opciones de decisión:
   - **Incidencia técnica** → redirige a soporte / dev (RECHAZADO)
   - **Urgencia real** → vía urgencias (RECHAZADO del pipeline normal)
   - **Idea sin problema claro** → devuelve al stakeholder con preguntas (RECHAZADO)
   - **Mejora con prioridad clara** → avanza a Discovery (TRIAGE)
   - **Mejora con prioridad dudosa** → aplaza al Comité siguiente (APLAZADO)
3. La IA formatea la decisión y la añade al ticket
4. Guarda en Jira y actualiza el estado

**Siguiente (opción 4):** `po discovery FP-XX`

---

### `po discovery FP-XX`

**Cuándo usarlo:** Tras el triage, cuando el PO asignado empieza el discovery.

```bash
po discovery FP-12
```

**Qué hace:**
1. Guía al PO por 11 preguntas de discovery:
   - Problema real vs. síntoma
   - Frecuencia y volumen de afectación
   - Usuarios afectados y perfil
   - Solución actual y sus problemas
   - Solución propuesta y viabilidad
   - Dependencias técnicas y de negocio
   - Riesgos y restricciones
   - KPIs de éxito
   - Stakeholder principal
   - Contexto adicional
2. La IA genera una ficha de discovery estructurada con todo lo recogido
3. La añade al ticket en Jira → estado **DISCOVERY**

**Fallback:** Si Jira no está disponible, guarda la ficha en `{ISSUE_KEY}-discovery.md` localmente.

**Siguiente:** `po define FP-XX`

---

### `po define FP-XX`

**Cuándo usarlo:** Después de completar el discovery, cuando tienes suficiente información para escribir la HU.

```bash
po define FP-12
# Con notas de una reunión:
po define FP-12 --notes notas_reunion_maria.txt
```

**Qué hace:**
1. Lee el contexto acumulado del ticket de Jira
2. La IA genera la HU completa en 6 bloques:
   - Contexto y problema
   - Descripción funcional
   - Criterios de aceptación
   - Plan UAT
   - Operativa (prioridad, dependencias)
   - Trazabilidad IA
3. Añade la HU como sección `## DEFINICION` al ticket
4. Mueve el ticket a estado **DEFINICION**

**Duración:** ~30-45 segundos (llamada a Claude API).

**Siguiente:** `po dor-gate FP-XX`

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

**Siguiente (si pasa):** `po signoff FP-XX`

---

### `po signoff FP-XX`

**Cuándo usarlo:** Tras el DoR Gate, antes del Handshake. Requiere confirmación formal del stakeholder.

```bash
po signoff FP-12
```

**Qué hace:**
1. Recoge los datos del sign-off:
   - Firmante (nombre y rol)
   - Fecha de la reunión de discovery
   - Funcionalidades acordadas (alcance positivo)
   - Exclusiones explícitas (alcance negativo)
   - MVP acordado
   - Validador UAT y disponibilidad
   - Fecha objetivo (opcional)
   - Limitaciones del stakeholder
2. La IA genera el documento formal de sign-off
3. Lo añade al ticket y mueve a **SIGN-OFF SH**

**Acción siguiente:** Comparte la URL del ticket con el firmante para que confirme en un comentario. Cuando confirme, ejecuta `po dor-gate FP-XX` de nuevo si es necesario, o `po handshake FP-XX`.

---

### `po handshake FP-XX`

**Cuándo usarlo:** En la sesión de traspaso técnico con el equipo de desarrollo.

```bash
po handshake FP-12
```

**Qué hace:**
1. Recoge los datos del handshake:
   - Asistentes
   - Score del DoR Gate previo
   - Dudas planteadas por desarrollo y respuestas
   - Supuestos validados
   - Riesgos técnicos identificados
   - Estimación inicial
   - Dependencias confirmadas
   - Decisión final (2 opciones)
2. La IA genera el acta de handshake
3. La guarda en Jira y actualiza el estado:
   - **OK para arrancar dev** → HANDSHAKE
   - **Vuelve a Definición** (gaps) → DEFINICION

**Siguiente (OK):** El equipo puede arrancar. Espera a que terminen → `po uat FP-XX`

---

### `po uat FP-XX`

**Cuándo usarlo:** Cuando desarrollo termina y el validador designado ha realizado las pruebas funcionales.

```bash
po uat FP-12
```

**Qué hace:**
1. Recoge los datos de la UAT:
   - Validador funcional (nombre, rol)
   - Entorno (normalmente PRE)
   - Casuísticas validadas y resultado
   - Defectos detectados
   - Decisión final (3 opciones)
2. La IA genera el acta de UAT
3. La guarda en Jira y actualiza el estado:
   - **UAT OK** → UAT
   - **UAT KO** (con observaciones) → EN DESARROLLO (vuelve a dev)
   - **UAT OK condicional** (defectos menores trackeados aparte) → UAT

**Siguiente (OK/condicional):** `po release FP-XX`

---

### `po release FP-XX`

**Cuándo usarlo:** Cuando el equipo va a hacer el despliegue a producción.

```bash
po release FP-12
```

**Qué hace:**
1. Recoge los datos del release:
   - Fecha de release
   - Tipo de release (hotfix / release normal)
   - Lead técnico
   - Confirmaciones de checklist: UAT OK, sign-off PO, PR mergeado, tests verde, rollback preparado
   - Comunicación al negocio
   - Responsable de post-deploy
2. La IA genera el documento de release con el checklist
3. Lo guarda en Jira y mueve a **RELEASE**

**Siguiente:** Confirmar en Jira cuando el negocio dé el visto bueno → cerrar el ticket.

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

Descripción (acumulativa):
  ## INTAKE — 2026-05-18
  ## TRIAGE — 2026-05-19
  ## DISCOVERY — 2026-05-20
  ## DEFINICION — 2026-05-21
  ## SIGN-OFF SH — 2026-05-22
  …
```

---

## Flujo semanal tipo (referencia)

```
Lunes — Comité Semanal de Triage
  po dashboard                        → revisar pipeline completo
  po triage FP-XX                     → clasificar peticiones en INTAKE
  (cada petición: avanza, aplaza o se rechaza)

Durante la semana — Discovery / Definición
  po intake "nueva petición"          → capturar peticiones nuevas
  po discovery FP-XX                  → ficha de discovery guiada
  po define FP-XX                     → generar HU tras discovery
  po dor-gate FP-XX                   → validar DoR antes del Sign-off

Jueves — Sign-offs y Handshakes
  po signoff FP-XX                    → documento de alcance para stakeholder
  (stakeholder confirma en Jira)
  po handshake FP-XX                  → traspaso técnico al equipo dev

Fin de sprint / Releases
  po uat FP-XX                        → registrar acta de validación UAT
  po release FP-XX                    → checklist de release y cierre
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
`[PENDIENTE:]` y adaptarla al contexto real antes del DOR GATE.

**¿Qué pasa si el DOR GATE da KO?**  
El ticket vuelve a DEFINICION. La IA deja un comentario con los gaps concretos.
Completa los gaps, edita la descripción en Jira y vuelve a ejecutar `po dor-gate`.
No hay un número máximo de intentos.

**¿El CLI puede sobrescribir trabajo mío en Jira?**  
No — todos los comandos añaden secciones al final de la descripción existente,
nunca la sobreescriben. Puedes editar Jira directamente y el CLI respetará tu contenido.

**¿Qué pasa si el Handshake da KO?**  
El ticket vuelve a DEFINICION. El PO resuelve los gaps identificados por el equipo
y vuelve a ejecutar `po handshake FP-XX` cuando estén resueltos.

**¿Qué pasa si la UAT da KO?**  
El ticket vuelve a EN DESARROLLO. El lead técnico recibe en Jira el detalle completo
de defectos y observaciones. Cuando dev corrija, se vuelve a ejecutar `po uat FP-XX`.

**¿Puedo usar el CLI sin conexión a internet?**  
`po demo --offline` simula el flujo sin crear nada en Jira ni llamar a la IA.
Para trabajo real necesitas conexión a Jira y a la API de Anthropic.

**¿Qué versión de Claude usa?**  
`claude-sonnet-4-6` por defecto (configurable en `.env` → `CLAUDE_MODEL`).

**¿La IA puede inventar información?**  
No. Todos los prompts tienen la regla explícita "NO inventes". Cuando falta
información, la IA deja `[PENDIENTE: ...]` en lugar de inventar. El PO siempre
aporta el conocimiento; la IA solo estructura y mejora la forma.

**¿Puedo pegar texto largo o con saltos de línea en las preguntas del CLI?**  
Sí. Todos los comandos guiados usan `;;` como terminador de respuesta. Pega el
texto que quieras (con párrafos, listas, Markdown), y cuando hayas terminado
escribe `;;` en una línea nueva y pulsa Enter. Ver la sección
[Cómo introducir respuestas en el CLI](#cómo-introducir-respuestas-en-el-cli).
