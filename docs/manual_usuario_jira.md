# Manual de usuario — `po-assistant`

> Para Product Owners de Flexicar. Explica qué hace cada comando, por qué existe cada paso,
> qué verás en el terminal y qué queda guardado en Jira.

---

## Antes de empezar

### La idea central

Cada HU en Jira tiene una **descripción acumulativa**. Cuando ejecutas un comando del CLI, no sobreescribe lo que había — añade un nuevo bloque al final. Al final del ciclo completo, la descripción del ticket es la historia completa de esa HU:

```
## INTAKE — 2026-05-18
(clasificación IA de la petición original)

---

## TRIAGE — 2026-05-19
(decisión del comité y justificación)

---

## DISCOVERY — 2026-05-20
(ficha de contexto, stakeholders, viabilidad)

---

## DEFINICION — 2026-05-21
(HU completa generada con IA)

---

## SIGN-OFF SH — 2026-05-22
(documento de alcance firmado por el stakeholder)

---

## DOR GATE — 2026-05-22
(score 11/12, gaps detectados)

---

## HANDSHAKE — 2026-05-23
(acta de traspaso: estimación, riesgos, dependencias)

---

## EN DESARROLLO — 2026-05-24
(leads de desarrollo)

---

## UAT — 2026-05-30
(acta de validación funcional)

---

## RELEASE — 2026-05-31
(checklist de release)
```

Esto significa que cualquier persona del equipo puede abrir el ticket y ver toda la historia: por qué se hizo, quién participó, qué se decidió y cuándo.

### Cómo responder en el terminal

Todos los comandos guiados (triage, discovery, define, signoff, etc.) hacen preguntas una a una. El CLI usa `;;` como terminador universal:

```
¿Cuál es el problema real detrás de esta petición?
  (;; en línea nueva para terminar)
→ Los agentes no saben cómo cancelar una reserva en el CRM.
→ Tienen que llamar a un técnico, lo que genera esperas y errores.
→ ;;
```

Funciona igual para respuestas cortas (una línea) que para respuestas largas con párrafos o listas. Cuando hayas terminado de escribir, escribe `;;` en una línea nueva y pulsa Enter.

---

## El flujo completo: de la petición al release

Una HU normal pasa por 10 pasos. Cada paso tiene un comando:

```
1. po intake "texto"     →  Recibe la petición, la clasifica con IA, crea el ticket
2. po triage FP-12       →  Comité decide si avanza, se aplaza o se rechaza
3. po discovery FP-12    →  PO recoge contexto con el stakeholder
4. po define FP-12       →  IA genera la HU completa
5. po signoff FP-12      →  Stakeholder firma el alcance
6. po dor-gate FP-12     →  IA valida que la HU está lista para desarrollo
7. po handshake FP-12    →  Sesión de traspaso al equipo dev
8. po start-dev FP-12    →  Se registran los leads y empieza el sprint
9. po uat FP-12          →  Validación funcional con el negocio
10. po release FP-12     →  Checklist de release y cierre
```

---

## La semana tipo del PO

```
Lunes — Comité Semanal de Triage
  po dashboard             → revisar el pipeline completo antes del comité
  po triage FP-XX          → decidir qué peticiones avanzan esta semana

Durante la semana — Discovery y Definición
  po intake "petición"     → capturar peticiones nuevas que vayan llegando
  po discovery FP-XX       → ficha de discovery con el stakeholder
  po define FP-XX          → HU completa con IA tras el discovery
  po dor-gate FP-XX        → validar que la HU está completa antes del sign-off

Jueves — Sign-offs y Handshakes
  po signoff FP-XX         → documento formal de alcance para el stakeholder
  (stakeholder confirma en el ticket de Jira)
  po handshake FP-XX       → traspaso técnico al equipo dev
  po start-dev FP-XX       → mover a EN DESARROLLO cuando el sprint arranque

Fin de sprint
  po uat FP-XX             → registrar el acta de validación UAT
  po release FP-XX         → checklist de release y cierre del ciclo

Viernes — KPIs
  po kpis                  → dashboard en terminal
  po kpis --export         → exportar informe semanal a Markdown
```

---

## Comandos — guía detallada

---

### Paso 1 — `po intake "descripción"`

**Por qué existe este paso**

Las peticiones llegan por todos los canales: Slack, email, reuniones, llamadas. Sin un punto de entrada unificado, algunas se pierden y las que llegan no tienen formato ni prioridad. `po intake` convierte cualquier petición en texto en un ticket de Jira estructurado y clasificado.

**Cuándo usarlo**

Cada vez que recibes una petición nueva que puede ser una funcionalidad, un problema o una mejora. Cuanto antes, mejor — aunque sea al final del día después de una llamada.

**Cómo usarlo**

```bash
po intake "Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM"
```

**Qué ocurre en el terminal**

La IA analiza el texto, decide el tipo de petición (problema / mejora / nueva funcionalidad), asigna prioridad y crea el ticket. Verás algo así:

```
─────── Nuevo intake ──────────────────────────────
  Clasificando con IA...

  Tipo:      problema
  Prioridad: alta
  Título:    [PROBLEMA] Los agentes no pueden cancelar reservas en CRM

  Preguntas para el triage:
  - ¿Afecta a todas las tiendas o solo algunas?
  - ¿Existe workaround actual? ¿Cuánto tarda?
  - ¿Hay un caso de negocio claro (KPI afectado)?

  ✓ Ticket FP-12 creado en Jira → estado INTAKE
  Siguiente: po triage FP-12
```

**Qué queda en Jira**

Se crea el ticket `FP-12` con:
- Título estructurado `[TIPO] Descripción`
- Campo `Tipo Peticion` = problema
- Estado = INTAKE
- Sección `## INTAKE — YYYY-MM-DD` en la descripción con la clasificación IA y las preguntas para el triage

---

### Paso 2 — `po triage FP-12`

**Por qué existe este paso**

No todas las peticiones merecen el mismo tratamiento. Algunas son incidencias técnicas (no son del PO), otras son urgencias que requieren un canal especial, y muchas son ideas válidas pero sin suficiente contexto para avanzar. El triage del lunes filtra y prioriza antes de invertir tiempo en el discovery.

**Cuándo usarlo**

En el Comité Semanal de Triage (lunes), para cada ticket que esté en estado INTAKE.

**Cómo usarlo**

```bash
po triage FP-12
```

**Qué ocurre en el terminal**

El CLI muestra el contexto del ticket y te presenta 5 opciones:

```
─────── Triage — FP-12 ──────────────────────────────
  Los agentes de tienda no encuentran cómo cancelar una reserva en el CRM
  Tipo: problema · Prioridad: alta

  ¿Cuál es la naturaleza de esta petición?

  1. Incidencia técnica → redirigir a soporte / equipo dev
  2. Urgencia real → vía urgencias (fuera del pipeline normal)
  3. Idea sin problema claro → devolver al stakeholder con preguntas
  4. Mejora/problema con prioridad clara → avanzar a Discovery
  5. Mejora/problema con prioridad dudosa → aplazar al Comité siguiente

  Opción [1-5]:
```

Después de elegir, el CLI pregunta la justificación y el PO asignado (si avanza a Discovery).

**Qué queda en Jira**

Se añade la sección `## TRIAGE — YYYY-MM-DD` con:
- La decisión tomada y la justificación
- PO asignado (si avanza)
- Estado actualizado (TRIAGE, APLAZADO o RECHAZADO)

**Casos especiales**

- Si eliges opción 1 (incidencia técnica) o 3 (idea sin contexto) → estado RECHAZADO, el ticket queda documentado pero fuera del pipeline
- Si eliges opción 5 → estado APLAZADO, aparecerá de nuevo en el tablero el próximo lunes

---

### Paso 3 — `po discovery FP-12`

**Por qué existe este paso**

Antes de escribir la HU, el PO necesita entender bien el problema. Sin discovery estructurado, es habitual llegar a la definición con información incompleta y tener que volver atrás. El discovery guiado garantiza que se recogen todos los datos necesarios antes de que la IA genere la HU.

**Cuándo usarlo**

Después del triage, cuando el PO asignado se sienta con el stakeholder (o en la reunión de discovery). Puedes hacerlo durante la reunión, respondiendo las preguntas en tiempo real.

**Cómo usarlo**

```bash
po discovery FP-12
```

**Qué ocurre en el terminal**

El CLI hace 11 preguntas guiadas, una a una. Ejemplos:

```
─────── Discovery — FP-12 ──────────────────────────────
  Los agentes de tienda no pueden cancelar reservas en CRM

  1/11 ¿Cuál es el problema real (no la solución)?
    (;; en línea nueva para terminar)
  → Los agentes tienen que llamar al técnico para cancelar.
  → Genera esperas de 10-15 min y a veces el cliente ya se fue.
  → ;;

  2/11 ¿Con qué frecuencia ocurre? ¿Cuántos usuarios afectados?
    (;; en línea nueva para terminar)
  → ...
```

**Las 11 preguntas cubren:**
1. Problema real (no la solución propuesta)
2. Frecuencia y volumen de impacto
3. Usuarios afectados y su perfil
4. Solución actual y sus problemas
5. Solución propuesta y cómo encaja con el negocio
6. Dependencias técnicas y de otros equipos
7. Riesgos y restricciones conocidas
8. KPIs de éxito (cómo sabremos que funcionó)
9. Stakeholder principal y validador UAT
10. Contexto adicional relevante
11. Preguntas que han quedado abiertas

**Qué queda en Jira**

La IA genera una ficha de discovery estructurada con todo lo recogido y la añade como sección `## DISCOVERY — YYYY-MM-DD`. El estado pasa a DISCOVERY.

**Fallback sin conexión**

Si Jira no está disponible, la ficha se guarda localmente en `FP-12-discovery.md`. Cuando recuperes la conexión, puedes añadirla manualmente a Jira o reejecutar el comando.

---

### Paso 4 — `po define FP-12`

**Por qué existe este paso**

Redactar una HU completa y bien estructurada lleva tiempo. La IA puede hacerlo en 30 segundos usando toda la información que ya está en el ticket (el intake, el discovery). El PO revisa, completa los `[PENDIENTE:]` y la adapta. Es mucho más rápido que escribir desde cero.

**Cuándo usarlo**

Después de completar el discovery y tener suficiente contexto. Si tienes notas adicionales de la reunión, puedes pasarlas con `--notes`.

**Cómo usarlo**

```bash
po define FP-12

# Si tienes notas extra de la reunión:
po define FP-12 --notes notas_reunion_maria.txt
```

**Qué ocurre en el terminal**

El comando lee el contexto acumulado del ticket y llama a Claude. Tarda unos 30-45 segundos:

```
─────── Definición — FP-12 ──────────────────────────────
  Leyendo contexto del ticket...
  Generando HU con IA (claude-sonnet-4-6)...

  ✓ HU generada — 6 bloques

  Revisa los [PENDIENTE:] antes del DOR GATE.
  Siguiente: po dor-gate FP-12
```

**Qué queda en Jira**

La IA genera la HU en 6 bloques y la añade como sección `## DEFINICION — YYYY-MM-DD`:

```
## Contexto y problema
...

## Descripción funcional
...

## Criterios de aceptación
- [ ] CA1: ...
- [ ] CA2: ...

## Plan UAT
...

## Operativa
Prioridad: Alta
Dependencias: ...

## Trazabilidad IA
Modelo: claude-sonnet-4-6 | Fecha: ...
```

**Importante**

La HU generada es un borrador. Es normal que tenga algunos `[PENDIENTE: ...]`. El PO debe revisarla, completar los pendientes y adaptarla a la realidad antes de ejecutar el DOR GATE.

---

### Paso 5 — `po signoff FP-12`

**Por qué existe este paso**

Antes de involucrar al equipo técnico, el stakeholder debe confirmar formalmente que el alcance es correcto. Sin este paso, es habitual que en el handshake o en la UAT aparezca "eso no era lo que pedíamos". El sign-off documenta el acuerdo explícito y evita malentendidos.

**Cuándo usarlo**

Cuando la HU está redactada y el DOR GATE ha pasado (o mientras se resuelven los gaps menores). Requiere una reunión o llamada con el stakeholder firmante.

**Cómo usarlo**

```bash
po signoff FP-12
```

**Qué ocurre en el terminal**

El CLI recoge los datos del sign-off con preguntas guiadas:

```
─────── Sign-off — FP-12 ──────────────────────────────

  Firmante (nombre y cargo):
  → María Ruiz — Responsable Operaciones Comerciales
  → ;;

  Funcionalidades acordadas (alcance positivo):
  → Botón "Cancelar reserva" visible en la ficha del cliente.
  → Cancela la reserva y envía confirmación al cliente por email.
  → ;;

  Exclusiones explícitas (qué NO entra):
  → No incluye devolución de señal en este MVP.
  → ;;

  MVP acordado:
  → Cancelación manual desde CRM en 1 clic.
  → ;;

  ...
```

**Qué queda en Jira**

La IA genera el documento formal de sign-off y lo añade como sección `## SIGN-OFF SH — YYYY-MM-DD`. El estado pasa a SIGN-OFF SH.

**Acción requerida**

Comparte la URL del ticket con el firmante para que añada un comentario confirmando el alcance. Cuando lo haga, ya puedes avanzar al DOR GATE o directamente al Handshake.

---

### Paso 6 — `po dor-gate FP-12`

**Por qué existe este paso**

El DoR (Definition of Ready) es el conjunto de condiciones que debe cumplir una HU antes de entrar en desarrollo. Sin validación sistemática, es habitual que el equipo técnico reciba HUs incompletas y tenga que parar el sprint para pedir aclaraciones. El DOR GATE valida 12 bloques automáticamente con IA.

**Cuándo usarlo**

Cuando la HU está redactada (después de `po define`) y antes del Handshake. Puedes ejecutarlo varias veces hasta que pase.

**Cómo usarlo**

```bash
po dor-gate FP-12
```

**Qué ocurre en el terminal**

La IA evalúa la HU contra los 12 bloques del DoR y muestra el resultado:

```
─────── DOR Gate — FP-12 ──────────────────────────────

  Evaluando 12 bloques DoR con IA...

  B1  Problema definido (no solución)        ✓
  B2  Contexto de negocio                    ✓
  B3  Usuarios afectados                     ✓
  B4  Frecuencia / volumen                   ✓
  B5  Alcance + exclusiones explícitas       ✓
  B6  Diagrama / mockup                      ~ (recomendado, no bloqueante)
  B7  Reglas de negocio críticas             ✓
  B8  Dependencias externas                  ✓
  B9  Casuística completa                    ✗ FALTA: casos de error no documentados
  B10 Criterios de aceptación verificables   ✓
  B11 Estimación orientativa                 ~ (sin estimación)
  B12 Validador UAT designado                ✓

  Score: 10/12 — KO (B9 es bloque crítico)

  Acción: Completa B9 en la sección DEFINICION de Jira y vuelve a ejecutar po dor-gate.
```

**Resultados posibles**

- **≥ 11/12 sin bloques críticos fallidos** → pasa a estado DOR GATE. Siguiente: `po handshake FP-12`
- **< 11/12 o algún crítico fallido** → vuelve a DEFINICION. Corrige los gaps indicados en la descripción de Jira y vuelve a ejecutar `po dor-gate`

**Los 6 bloques críticos** (deben cumplir siempre):
B1 · B5 · B7 · B9 · B10 · B12

**Qué queda en Jira**

El resultado del DOR GATE se añade como comentario al ticket, y los campos `DoR Score` y `DoR Gaps` se actualizan con el score y la lista de gaps.

---

### Paso 7 — `po handshake FP-12`

**Por qué existe este paso**

El handshake es la reunión donde el PO traspasa la HU al equipo técnico. Sin un acta estructurada, las decisiones tomadas en esa reunión se pierden. El handshake documenta: quién asistió, qué preguntas hizo el equipo, qué riesgos se identificaron, la estimación y si hay algún gap que impida arrancar.

**Cuándo usarlo**

En la sesión de traspaso técnico, con el PO y el equipo de desarrollo presentes.

**Cómo usarlo**

```bash
po handshake FP-12
```

**Qué ocurre en el terminal**

El CLI recoge los datos con preguntas guiadas:

```
─────── Handshake — FP-12 ──────────────────────────────
  Los agentes no pueden cancelar reservas en CRM · Score DoR: 11/12

  Asistentes (nombre — rol, uno por línea, ;; para terminar):
  → Carlos López — Backend
  → Sara Martín — Frontend
  → ;;

  Dudas de desarrollo y respuestas (;; para terminar):
  → P: ¿El botón cancela también en JATO o solo en CRM?
  → R: Solo en CRM en este MVP. JATO queda para v2.
  → ;;

  Riesgos técnicos identificados:
  → ...

  Estimación inicial:
  → 5 puntos (1 sprint)
  → ;;

  Decisión final:
    1. OK para arrancar dev
    2. Vuelve a Definición (hay gaps)
  Opción [1/2]:
```

**Qué queda en Jira**

La IA genera el acta de handshake y la añade como sección `## HANDSHAKE — YYYY-MM-DD` con asistentes, preguntas/respuestas, riesgos, estimación y decisión. El estado pasa a HANDSHAKE (si OK) o vuelve a DEFINICION.

**Siguiente**

Si el handshake es OK: `po start-dev FP-12` para registrar los leads y mover a EN DESARROLLO.

---

### Paso 8 — `po start-dev FP-12`

**Por qué existe este paso**

Después del handshake, el ticket está en estado HANDSHAKE pero el equipo todavía no ha arrancado. `po start-dev` formaliza el arranque del sprint: registra quién lidera el desarrollo y mueve el ticket a EN DESARROLLO. También deja un enlace a la HU completa para que el equipo la tenga a mano.

**Cuándo usarlo**

Justo cuando el equipo va a empezar a desarrollar (normalmente al inicio del sprint, después del handshake).

**Cómo usarlo**

```bash
po start-dev FP-12
```

**Qué ocurre en el terminal**

```
─────── Arrancar desarrollo — FP-12 ──────────────────────────────

  ¿Quiénes lideran el desarrollo?
  (Uno por línea: Nombre — Rol. Ej: Carlos López — Backend)
  → Carlos López — Backend
  → Sara Martín — Frontend
  → ;;

  ¿Mover a EN DESARROLLO? [S/n]: S

  ✓ HU FP-12 en marcha. Estado → EN DESARROLLO.
  Siguiente cuando termine dev: po uat FP-12
```

**Qué queda en Jira**

Se añade la sección `## EN DESARROLLO — YYYY-MM-DD` con los leads de desarrollo y un enlace a la sección DEFINICION (donde está la HU completa). El estado pasa a EN DESARROLLO.

---

### Paso 9 — `po uat FP-12`

**Por qué existe este paso**

La UAT (User Acceptance Testing) es la validación funcional con el negocio antes del release. Sin un acta formal, es habitual que después del deploy aparezca "esto no funciona como esperábamos" sin que quede claro qué se validó y quién lo validó. El acta de UAT deja constancia de qué se probó, qué falló y quién dio el OK.

**Cuándo usarlo**

Cuando el equipo de desarrollo ha terminado y el validador designado ha hecho las pruebas en el entorno de PRE.

**Cómo usarlo**

```bash
po uat FP-12
```

**Qué ocurre en el terminal**

El CLI recoge los datos de la UAT:

```
─────── UAT — FP-12 ──────────────────────────────

  Validador funcional (nombre y rol):
  → María Ruiz — Responsable Operaciones Comerciales
  → ;;

  Entorno de validación:
  → PRE
  → ;;

  Casuísticas validadas y resultado (;; para terminar):
  → CA1: Cancelar reserva desde ficha de cliente → OK
  → CA2: Email de confirmación al cliente → OK
  → CA3: Intentar cancelar reserva ya cancelada → OK, mensaje de error correcto
  → ;;

  Defectos detectados:
  → Ninguno
  → ;;

  Decisión final:
    1. UAT OK — todo correcto
    2. UAT KO — hay defectos bloqueantes (vuelve a desarrollo)
    3. UAT OK condicional — defectos menores trackeados aparte
  Opción [1-3]:
```

**Resultados posibles**

- **UAT OK** → estado UAT. Siguiente: `po release FP-12`
- **UAT KO** → vuelve a EN DESARROLLO. Los defectos quedan documentados para el equipo técnico
- **UAT OK condicional** → estado UAT. Los defectos menores se documentan y trackean en tickets separados

**Qué queda en Jira**

La IA genera el acta de UAT y la añade como sección `## UAT — YYYY-MM-DD` con validador, entorno, resultados por casuística y decisión.

---

### Paso 10 — `po release FP-12`

**Por qué existe este paso**

El checklist de release es el último filtro antes del despliegue a producción. Verifica que todo está en orden: UAT firmada, PR mergeado, tests en verde, rollback preparado, comunicación al negocio lista. Si algo falta, es mejor saberlo antes de desplegar.

**Cuándo usarlo**

Cuando el equipo va a hacer el despliegue a producción.

**Cómo usarlo**

```bash
po release FP-12
```

**Qué ocurre en el terminal**

El CLI recoge los datos del release con un checklist:

```
─────── Release — FP-12 ──────────────────────────────

  Fecha de release (YYYY-MM-DD):
  → 2026-05-31
  → ;;

  ¿UAT OK firmado?     [S/n]: S
  ¿Sign-off PO?        [S/n]: S
  ¿PR mergeado?        [S/n]: S
  ¿Tests en verde?     [S/n]: S
  ¿Rollback preparado? [S/n]: S

  Comunicación al negocio (;; para terminar):
  → Comunicado enviado por email a María Ruiz y a todo el equipo de tiendas.
  → ;;

  ✓ Checklist completo. Estado → RELEASE.
  Siguiente: cuando el negocio confirme → cierra el ticket en Jira.
```

**Qué queda en Jira**

La IA genera el documento de release y lo añade como sección `## RELEASE — YYYY-MM-DD` con el checklist completo, fecha de deploy y responsable de post-deploy.

**Última acción**

Cuando el negocio confirme que todo va bien en producción, cierra el ticket manualmente en Jira (estado CERRADO).

---

## Funciones de análisis

---

### `po kpis` — Dashboard de KPIs

**Por qué existe**

El pipeline de HUs genera datos valiosos que están dispersos en Jira: tiempos de ciclo, tasa de éxito del DOR GATE, throughput, aging del backlog... `po kpis` extrae esos datos automáticamente y los presenta como un cuadro de mando. Útil para el Comité Semanal, para el reporting mensual y para detectar cuellos de botella.

**Cuándo usarlo**

- Viernes, para la publicación semanal de KPIs
- Primer lunes de mes, para el reporting mensual
- Cuando algo no funciona y quieres datos concretos

**Cómo usarlo**

```bash
po kpis                        # dashboard en terminal
po kpis --export               # + exportar a Markdown (YYYY-MM-DD-kpis-FP.md)
po kpis --out informe.md       # nombre de archivo personalizado
po kpis --weeks 12             # throughput de las últimas 12 semanas (defecto: 4)
```

**Qué muestra**

Los KPIs se agrupan en 6 familias. Los que pueden calcularse directamente de Jira se muestran con valor real; los demás muestran `N/A` con la fuente donde buscarlos:

| Familia | KPI | Fuente |
|---------|-----|--------|
| F1 — Calidad de entrada | % HUs con DoR ≥ 11/12 | Jira |
| F1 — Calidad de entrada | Tiempo medio Intake → Sign-off | Jira |
| F1 — Calidad de entrada | % HUs con sign-off formal | Jira |
| F1 — Calidad de entrada | % HUs con handshake formal | Jira |
| F2 — Delivery | Lead time medio (Intake → Release) | Jira |
| F2 — Delivery | Throughput semanal | Jira |
| F2 — Delivery | Aging del backlog (issues > 30 días sin avanzar) | Jira |
| F3 — Calidad de salida | % releases con UAT formal | Jira |
| F4 — IA aplicada al PO | % HUs con IA asistida | Jira |
| F5 — Gobernanza | Urgencias declaradas (último mes) | Jira |
| F6 — Salud organizativa | Satisfaction score POs | Encuesta manual |

Los 13 KPIs que requieren fuentes externas (GitHub, Sentry, encuestas) aparecen como `N/A` con la fuente indicada.

**Exportación Markdown**

Con `--export` genera un archivo `YYYY-MM-DD-kpis-FP.md` con:
- Resumen ejecutivo con alertas
- Tablas por familia (valor, objetivo, estado)
- Sección de KPIs sin datos y sus fuentes
- Checklist de próximas acciones

Útil para compartir en Confluence o en el Comité Semanal.

---

### `po dashboard` — Pipeline Kanban en terminal

**Por qué existe**

Antes del Comité Semanal, el PO necesita una visión rápida de qué hay en cada estado del pipeline sin tener que abrir Jira. El dashboard muestra el estado completo con alertas de SLA (tickets que llevan demasiado tiempo en un estado).

**Cuándo usarlo**

Al inicio del Comité Semanal, o cuando quieras revisar el estado del pipeline rápidamente.

**Cómo usarlo**

```bash
po dashboard               # pipeline completo
po dashboard --po ester    # filtrar solo los tickets de Ester
po dashboard --all         # incluir también los cerrados y rechazados
```

**Qué muestra**

- Pipeline con el número de issues en cada estado
- Antigüedad del issue más viejo en cada estado
- Alertas de SLA cuando un issue lleva demasiado tiempo parado:
  - INTAKE > 48 h sin triage
  - SIGN-OFF SH > 5 días sin confirmar
  - DOR GATE > 2 días sin avanzar

---

### `po setup` — Configuración inicial de Jira

**Por qué existe**

Solo hay que ejecutarlo una vez, cuando se configura el entorno por primera vez. Crea el proyecto FP en Jira, los 5 campos custom necesarios, el workflow de 10 estados y el tablero Kanban.

**Cuándo usarlo**

Solo una vez, al instalar `po-assistant` en un entorno nuevo. Ver el documento `docs/guia_setup_jira_oficial.md` para los detalles.

```bash
po setup
```

---

## Preguntas frecuentes

**¿Puedo editar la HU generada por la IA directamente en Jira?**

Sí, siempre. La HU es un borrador. Edita la sección `## DEFINICION` directamente en Jira si quieres corregir algo. El CLI respetará tu contenido — nunca sobreescribe.

**¿Qué hago cuando el DOR GATE da KO?**

El ticket vuelve a DEFINICION. La IA indica exactamente qué bloques fallan y por qué. Edita la sección `## DEFINICION` en Jira para completar los gaps y vuelve a ejecutar `po dor-gate FP-XX`. No hay límite de intentos.

**¿El CLI puede sobreescribir trabajo mío en Jira?**

No. Todos los comandos añaden secciones al final de la descripción existente — nunca la sobreescriben. Puedes editar Jira directamente y el CLI respetará tu contenido.

**¿Qué pasa si el Handshake da KO?**

El ticket vuelve a DEFINICION. El PO resuelve los gaps identificados por el equipo y vuelve a ejecutar `po handshake FP-XX`. En la sección `## HANDSHAKE` queda documentado qué gaps impidieron arrancar.

**¿Qué pasa si la UAT da KO?**

El ticket vuelve a EN DESARROLLO. El acta de UAT queda en la descripción con el detalle completo de defectos. Cuando dev corrija, se vuelve a ejecutar `po uat FP-XX`.

**¿Qué KPIs calcula `po kpis` automáticamente?**

Calcula 10 KPIs directamente de Jira: % DoR cumplido, tiempo Intake→Sign-off, cobertura de sign-off, cobertura de handshake, lead time, throughput semanal, aging del backlog, cobertura de UAT formal, % IA asistida y urgencias declaradas. Los 13 KPIs restantes (GitHub, Sentry, encuestas) aparecen como `N/A` con la fuente indicada.

**¿La IA puede inventar información?**

No. Todos los prompts tienen la instrucción explícita de no inventar. Cuando falta información, la IA escribe `[PENDIENTE: ...]` en lugar de rellenar con datos ficticios. El PO siempre aporta el conocimiento; la IA estructura y mejora la forma.

**¿Qué versión de Claude usa?**

`claude-sonnet-4-6` por defecto. Configurable en `.env` con la variable `CLAUDE_MODEL`.

**¿Puedo pegar texto largo con saltos de línea en las respuestas?**

Sí. Todos los comandos guiados usan `;;` como terminador. Pega el texto que quieras (con párrafos, listas, Markdown), y cuando hayas terminado escribe `;;` en una línea nueva y pulsa Enter.

---

## Referencia rápida

### Estados del ticket y su orden

| Estado | Paso | Comando que lo activa |
|--------|------|-----------------------|
| INTAKE | 1 | `po intake "texto"` |
| TRIAGE | 2 | `po triage FP-XX` (opción avanza) |
| DISCOVERY | 3 | `po discovery FP-XX` |
| DEFINICION | 4 | `po define FP-XX` |
| SIGN-OFF SH | 5 | `po signoff FP-XX` |
| DOR GATE | 6 | `po dor-gate FP-XX` (si pasa) |
| HANDSHAKE | 7 | `po handshake FP-XX` (si OK) |
| EN DESARROLLO | 8 | `po start-dev FP-XX` |
| UAT | 9 | `po uat FP-XX` (si OK) |
| RELEASE | 10 | `po release FP-XX` |
| CERRADO | — | Manual en Jira |
| RECHAZADO | — | `po triage` (opciones 1, 2, 3) |
| APLAZADO | — | `po triage` (opción 5) |

### Etiquetas del sistema

El CLI gestiona estas etiquetas automáticamente. **No las edites a mano en Jira** — usa siempre el CLI para mover tickets entre estados.

| Etiqueta | Estado |
|----------|--------|
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
| `po-cerrado` | CERRADO |
| `po-rechazado` | RECHAZADO |
| `po-aplazado` | APLAZADO |
