# Evaluación: editor de GTFS para clientes — tp-routes vs GTFS·X vs alternativas

> **Encargo de Leonardo (2026-06-23):** evaluar cómo dar al cliente una interfaz para que
> **edite su propio GTFS con apoyo de Trufi**; comparar nuestra plataforma **tp-routes** (alias
> "tprutas" / BusBoy) con el proyecto nuevo **gtfsx.com**, ver si hay compatibilidad y si
> podemos aprender de él o usarlo, y proponer integración con el pipeline de Lima.
>
> Investigación: análisis estático + **prueba en vivo** de gtfsx.com, lectura del código de
> `leoguti/tp-routes`, del ecosistema GTFS de Trufi (`trufi-gtfs-builder`, `trufi-gtfs-simulator`,
> etc.) y un barrido del panorama competitivo 2026.

---

## 0. TL;DR (recomendación)

1. **Para el objetivo concreto "el cliente edita un GTFS existente", GTFS·X es hoy muy superior
   a tp-routes** — y lo confirmé en vivo: importa un GTFS, lo edita en mapa y lo exporta validado.
   tp-routes **todavía no importa ni exporta GTFS** (es su "Fase 5" pendiente).
2. **Pero GTFS·X y tp-routes no compiten en lo mismo.** GTFS·X edita feeds; tp-routes **captura y
   construye** datos desde cero (trabajo de campo offline, trazado por calles, OSM-first, multi-región
   LatAm). Son **piezas complementarias**, no sustitutas.
3. **GTFS·X es open source (AGPL-3.0) y muy activo.** Eso abre la puerta a **self-hostarlo,
   forkearlo o contribuirle** — no solo a usarlo como SaaS. Es la noticia estratégica más importante.
4. **Recomendación:** no reconstruir un editor GTFS completo desde cero en tp-routes (duplicaríamos
   años de trabajo que GTFS·X ya tiene). En su lugar, **adoptar GTFS·X como capa de edición/validación/
   export de GTFS** (self-hosted con marca Trufi o vía su SaaS), y **mantener tp-routes/builder como
   nuestro diferenciador** en lo que GTFS·X no hace: **OSM→GTFS automático y captura de campo**.
5. **Para Lima:** el pipeline `KML→OSM→GTFS` produce el feed; el cliente (AEMUS) lo **edita y
   mantiene en una instancia de GTFS·X** con Trufi acompañando. Es la vía más rápida y barata a
   "el cliente edita su propio GTFS".

> Dicho de frente, Leonardo: tu intuición de que "el cliente edite su GTFS con apoyo nuestro" es
> exactamente el hueco de mercado correcto. Pero el camino más corto **no** es terminar tp-routes
> como editor GTFS — es **pararnos sobre GTFS·X** (que es libre) y poner nuestro valor donde somos
> únicos. Detalle abajo.

---

## 1. La pregunta de negocio

¿Qué opciones hay para que un operador/cliente **no técnico** edite su propio feed GTFS desde una
interfaz web, con un consultor (Trufi) que acompaña, revisa y publica? El panorama 2026 deja un
**hueco claro** entre dos extremos:

- **"Excel gratis + soporte humano"** (National RTAP, EE.UU.): buen modelo de servicio, herramienta pobre.
- **"Enterprise caro"** (Optibus, que absorbió a Trillium): potente pero fuera del alcance del operador pequeño.

En medio casi no hay nada **asequible, web, multilingüe y pensado para LatAm/África/Asia** — los
mercados de Trufi. Ahí es donde encaja la jugada.

---

## 2. GTFS·X (gtfsx.com) — el proyecto nuevo

### Qué es
Editor de GTFS **basado en navegador**, "rápido y gratis", para crear/editar/analizar/**publicar**
feeds GTFS y GTFS-Flex. Autor: **Mark Egge** (consultor GTFS reconocido en EE.UU., ex-High Street).
Repo: **`markegge/gtfsx`**, **licencia AGPL-3.0**, TypeScript, **muy activo** (último push 2026-06-22).

### Evidencia en vivo (lo probé yo)
- El **editor carga sin cuenta** (modo anónimo, guarda en IndexedDB como "Local draft").
- **Importé un GTFS de muestra** (feed de ejemplo público) → parseó correctamente
  **5 routes · 9 stops · 11 trips**, reposicionó el mapa y **habilitó "Export GTFS"**.
- El panel de **Routes** lista cada ruta (`Bus · N stops · N trips`), con detalle, filtro y "Add Route".
- Capturas: `docs/img/gtfsx-editor.jpeg`, `gtfsx-import-ok.jpeg`, `gtfsx-routes.jpeg`.

→ **Round-trip GTFS confirmado** (importar → editar → exportar validado).

### Capacidades (del README + verificación)
- **Editor completo:** Agencia/Feed Info, Calendarios (con festivos, excepciones), **Rutas** (dibujo de
  polilíneas, **snap-to-road** vía Mapbox, freehand, simplify, variantes de shape), **Paradas**
  (colocar sobre ruta, offset de acera, reordenar, compartir entre rutas, **import CSV**), **Trips &
  Timetables** (grid tipo hoja de cálculo, auto-interpolación de tiempos), **Tarifas**, **GTFS-Flex**
  (zonas poligonales, booking rules).
- **Validación en tiempo real** (errores bloquean export, warnings se marcan; click-para-navegar al
  problema; auto-fix en el diálogo de export). Usa el **gtfs-validator canónico de MobilityData**.
- **Import/Export GTFS ZIP** con `shape_dist_traveled` y `feed_info.txt` automáticos.
- **Análisis (EE.UU.):** mapa de demanda nacional, cobertura demográfica (Census/ACS), **Title VI**,
  estimación de **costos** operativos. ⚠️ *Estas funciones son específicas de EE.UU. — no aplican a Lima.*
- **Tier backend (de pago):** cuentas, organizaciones con roles, **publicación a URL estable**
  (`feeds.gtfsx.com/<slug>/gtfs.zip`), mini-sitio para pasajeros, submission a Mobility Database/Google.

### Stack
React 18/19 + TypeScript + Vite · **Mapbox GL JS** (react-map-gl + mapbox-gl-draw) · Zustand · Tailwind v4
· Radix UI · TanStack Table · Turf.js · JSZip + PapaParse · Dexie (IndexedDB). **Backend:** un único
Cloudflare Worker (Hono) + D1 + R2 + KV + Resend + Turnstile + Stripe.

### Modelo de negocio (freemium)
- **Free $0** — editar/validar/exportar en el navegador, 3 feeds en la nube, GTFS-Flex.
- **Pro $49/mes** — hosting/publicación, mini-sitio de horarios, submission a catálogos.
- **Agency $299/mes** — planificación, costos, cobertura, Title VI, RT Service Alerts, white-label,
  "**cross-org membership for consultants**" (pensado para que un consultor gestione varios clientes).
- **Enterprise** — DOTs/consorcios, SLA. Y un servicio "**Fix my feed for me**" (done-for-you).

### Fortalezas
Madurez y completitud muy altas; round-trip GTFS real; validación canónica; GTFS-Flex (estado del
arte); **open source y self-hostable**; UX pulida; pensado para que **consultores gestionen clientes**.

### Límites / riesgos para Trufi
- **Dependencia de Mapbox** (token de pago por uso) para tiles y snap-to-road → costo recurrente.
- **Backend acoplado a Cloudflare** (Workers/D1/R2) → self-hosting fuera de Cloudflare exige reescritura.
- **Sesgo EE.UU.** (Title VI, ACS, RTAP, demand map) → relleno inútil para LatAm; el editor núcleo sí sirve.
- **AGPL-3.0** (ver §6) → copyleft de red: condiciona cómo lo ofreceríamos como servicio.
- Proyecto **muy nuevo** (1 star) y de **un solo autor** → riesgo de continuidad; mitigable porque es libre.

---

## 3. tp-routes ("tprutas" / BusBoy) — nuestra plataforma

### Qué es realmente
Una **plataforma colaborativa para construir datos de transporte desde cero**, no un editor de un
GTFS existente. Desplegada y funcional (`tptasks.vercel.app` / `rutas.busboy.app`), en **piloto real
con el Terminal de Tunja**. ~5.500 líneas JS + ~8.300 HTML, desarrollo continuo mar–jun 2026.

### Stack
JavaScript **vanilla** (sin framework) + **Leaflet** · Backend **serverless Node en Vercel** ·
**Postgres (Neon)** · **Valhalla propio** (`valhalla.busboy.app`) para trazado por calles · Overpass/Photon ·
Google OAuth + OTP. Multi-región (Boyacá CO, Cochabamba BO).

### Lo que SÍ hace (y muy bien)
- **Captura de campo offline** (PWA `campo/`): tarifas, paradas y frecuencias con cola idempotente y
  bandeja aislada — pensada para usuarios **no técnicos en terreno**. Usada en piloto (mayo 2026).
- **Edición de paradas y rutas en mapa**, con **trazado real por calles (Valhalla)** y picking de
  coordenadas / Street View.
- **Export OSM PTv2** (`.osm` XML) + **validación PTv2** robusta (continuidad, gaps, orden de miembros).
- Modelo de datos **GTFS-aware** (operators=agency, routes, stops, shapes, fares, trips, **frequencies**),
  multi-usuario con roles, import tolerante desde Excel/CSV.

### Lo que NO hace (gaps decisivos para este caso)
- **No importa GTFS** y **no exporta GTFS** — cero código de generación de `routes.txt`/`stops.txt`/
  `stop_times.txt`/… Es la **Fase 5 pendiente**. Hoy un cliente con un feed **no puede cargarlo**.
- **No valida GTFS** (valida PTv2, que es otra cosa).
- **Multi-tenant inmaduro:** roles sin enforcement, sin aislamiento por cliente (una BD por región).
- UI de tarifas/horarios incompleta; sin tests; acoplado al caso **intermunicipal** de Tunja
  (urbano como Lima requiere adaptación).

### Aptitud para "cliente edita su GTFS con apoyo": **2.5 / 5**
Bloqueante: sin import/export GTFS, no cubre el caso. Pero el modelo de datos es GTFS-compatible y el
export sería trabajo **acotado**; con eso saltaría a ~4/5. Su valor único —**captura de campo + OSM +
Valhalla**— no lo tiene GTFS·X.

---

## 4. El ecosistema GTFS de Trufi (piezas de apoyo)

| Repo | Qué hace | Etapa pipeline | Madurez |
|---|---|---|---|
| **trufi-gtfs-builder** (TS) | Genera GTFS completo **desde OSM** (`osmToGtfs`) | Conversión/Generación | **Alta** (prod, v2.13.x, jun-2026) |
| **trufi-gtfs-simulator** (`trufi-gtfs-viewer`) | Carga, **valida** (ligero) y **visualiza** GTFS en mapa (React+MapLibre) | Validación/Visualización | Media-alta |
| gtfs2osm (Py) | GTFS→GPX/GeoJSON | Conversión inversa | Baja (2023) |
| osm-transport-kml-exporter (Py) | OSM→KML/SHP | Conversión | Media |
| gtfs-route-length-api (Py) | longitud de ruta OSM | Utilidad | Baja |

**Clave:** `trufi-gtfs-builder` es un **generador batch OSM→GTFS sin UI** — perfecto como **motor**
detrás de un editor, pero no es el editor. **El hueco del ecosistema es justo la edición interactiva.**

---

## 5. Panorama competitivo 2026 (resumen)

| Herramienta | Tipo | Web | Apto no-técnicos | GTFS-Flex | Precio | Estado |
|---|---|---|---|---|---|---|
| **GTFS·X** | OSS (AGPL) + SaaS | Sí | **Sí** | **Sí** | Free / $49 / $299 | **Activo** |
| Trillium → **Optibus** | SaaS enterprise | Sí | Parcial | Parcial | Contrato (alto) | Activo |
| **Arcadis/IBI datatools-ui** | OSS + hosted | Sí | Sí | Limitado | Gratis/host | Activo pero **estancado** (últ. release 2022) |
| **AddTransit** | SaaS | Sí | Sí | No claro | desde $15/ruta | Activo |
| National RTAP Builder | Gratis (gov, EE.UU.) | Excel | Sí + soporte | No | Gratis | Activo (solo EE.UU.) |
| Spare GTFS-Flex Builder | SaaS (free tool) | Sí | Sí | **Sí** | Gratis | Activo |
| **trufi-gtfs-builder** | OSS (librería) | No | No | No | Gratis | Activo |

**Hallazgos:** (1) el mercado SaaS se consolidó caro alrededor de Optibus; (2) el editor OSS de
referencia (datatools-ui) está vivo pero **estancado**; (3) **GTFS-Flex** es terreno nuevo donde GTFS·X
ya es estado del arte; (4) **nadie cubre bien** "operador edita + consultor acompaña" **fuera de EE.UU.**
→ ese es el espacio de Trufi.

---

## 6. La licencia AGPL-3.0 (decisiva para "¿podemos usarlo?")

GTFS·X es **AGPL-3.0**: copyleft fuerte **con cláusula de red**. Implicaciones si Trufi lo usa:

- **Usar el SaaS de gtfsx.com** (gratis o de pago): sin obligación legal; es solo ser cliente.
- **Self-hostar y/o forkear** y ofrecerlo a clientes por red: **debemos poner a disposición de esos
  usuarios el código fuente, incluidas nuestras modificaciones.** Para Trufi (open source por ADN) esto
  es **filosóficamente compatible** — incluso deseable — pero hay que asumirlo conscientemente: no
  podríamos hacer una versión propietaria cerrada "marca Trufi".
- **Contribuir upstream** (mejoras de i18n/español, MapLibre en vez de Mapbox, casos LatAm) es la vía
  más sana: reduce divergencia y nos da influencia sobre el rumbo del proyecto.

> ⚠️ Confirmar con un humano la lectura de AGPL antes de comprometer arquitectura. Es compatible con
> cómo trabaja Trufi, pero condiciona el modelo de negocio (no cabe "cerrar" el fork).

---

## 7. Comparación directa para el caso "cliente edita su GTFS"

| Criterio | **tp-routes** | **GTFS·X** |
|---|---|---|
| Importa GTFS existente | ❌ No | ✅ Sí (probado) |
| Exporta GTFS válido | ❌ No (Fase 5) | ✅ Sí (validado) |
| Validación GTFS canónica | ❌ (valida PTv2) | ✅ MobilityData |
| Edición en mapa (rutas/paradas) | ✅ Sí (Leaflet+Valhalla) | ✅ Sí (Mapbox) |
| Horarios/timetables UI | 🟡 Incompleta | ✅ Grid completo |
| GTFS-Flex | ❌ | ✅ |
| Captura de campo offline | ✅ **Único** | ❌ |
| OSM-first / PTv2 | ✅ **Único** | ❌ (es GTFS-first) |
| Generación automática desde OSM | ✅ (vía builder) | ❌ |
| Multi-tenant por cliente | 🟡 Débil | ✅ Orgs + roles |
| Publicación/hosting de feed | ❌ | ✅ (Pro) |
| Costo de mapas | ✅ Gratis (Leaflet/OSM) | 🟡 Mapbox (pago) |
| Licencia/control | ✅ Nuestro | ✅ AGPL (libre) |
| Madurez para ESTE caso | 🟡 2.5/5 | 🟢 ~4.5/5 |

**Lectura:** se complementan casi perfectamente. GTFS·X gana en todo el ciclo de vida del **feed GTFS**;
tp-routes gana en **captura/creación de datos** y en lo **OSM/LatAm**. Construir en tp-routes lo que
GTFS·X ya tiene sería reinventar la rueda; ignorar la fuerza de tp-routes sería tirar nuestro diferenciador.

---

## 8. Opciones estratégicas

**A. Terminar tp-routes como editor GTFS completo (import+export+validación+timetables+publish).**
Control total, gratis en mapas, marca Trufi. Pero es **mucho trabajo** (meses) para alcanzar lo que
GTFS·X ya hace; sin tests ni multi-tenant maduro. *Riesgo alto, lento.*

**B. Adoptar GTFS·X como SaaS + servicio Trufi encima.** Rápido y barato: el cliente usa gtfsx.com
(Free/Pro), Trufi acompaña ("cross-org membership for consultants" está hecho para esto). Cero
mantenimiento de software. *Contra:* dependemos de un tercero/su billing; datos del cliente en su nube;
sesgo EE.UU. visible.

**C. Self-hostar/forkear GTFS·X con marca e i18n Trufi.** Instancia propia (AGPL), español, MapLibre en
vez de Mapbox (ahorra costo y quita dependencia), ocultar funciones EE.UU. Nos da una plataforma de
edición GTFS madura **ya**, manteniendo control. *Contra:* asumir Cloudflare o reescribir backend;
obligación AGPL de publicar el fork; esfuerzo de adaptación (medio).

**D. Híbrido (recomendado).** **GTFS·X para editar/validar/publicar el feed** (opción B corto plazo → C
medio plazo) **+ tp-routes/builder para lo que somos únicos**: generar el GTFS inicial desde OSM
(`KML→OSM→GTFS`) y la **captura de campo**. Integración por el **artefacto GTFS** (un ZIP): nuestro
pipeline lo produce, GTFS·X lo edita, el cliente lo mantiene, Trufi revisa.

---

## 9. Recomendación y aplicación a Lima (AEMUS)

**Recomiendo la opción D (híbrido), arrancando por B y evolucionando a C.**

Flujo para Lima, encajado con lo que ya hicimos:

```
 KML cliente ──(Fase 1–4 de este repo)──► GTFS v0  ──► GTFS·X (edición/validación/publish)
   (hecho)        builder / OSM                          │
                                                         ├─ cliente AEMUS edita y mantiene su feed
   tp-routes (campo) ──► datos que faltan ───────────────┘   con acompañamiento de Trufi
   (paradas AERODIRECTO, retorno URBANITO, horarios…)
```

1. **Corto plazo (Lima ya):** terminar el pipeline `KML→OSM→GTFS` de este repo para producir el **GTFS v0**.
   Entregar al cliente la edición vía **GTFS·X SaaS** (Free para empezar), con Trufi como "consultor"
   gestionando su organización. Probar el round-trip con el feed real de Lima en una sesión con Juan Prado.
2. **Validar el modelo:** ¿el cliente realmente quiere autoeditar, o prefiere "fix my feed for me"
   (servicio gestionado por Trufi)? Esto define si invertimos en C.
3. **Medio plazo (producto Trufi):** si el modelo funciona, **self-hostar un fork de GTFS·X** con i18n
   español, MapLibre (sin costo Mapbox) y marca Trufi; **contribuir upstream** las mejoras. Conectar el
   **builder (OSM→GTFS)** como "nuevo proyecto desde OSM" dentro de esa interfaz.
4. **tp-routes** se reposiciona como **herramienta de captura de campo y creación OSM-first** (su
   fortaleza real), alimentando GTFS·X — no compitiendo con él.

### Lo que NO recomiendo
Invertir meses en construir import/export/validación/timetables GTFS dentro de tp-routes para empatar a
GTFS·X. Ese esfuerzo rinde más **contribuido a GTFS·X** (que es libre) o puesto en nuestro diferenciador.

---

## 10. Próximos pasos concretos

- [ ] **Decidir** entre opciones B/C/D (decisión de Leonardo/Trufi; este informe recomienda D).
- [ ] Revisar con criterio legal la **AGPL-3.0** antes de forkear/self-hostar.
- [ ] **Probar GTFS·X con el GTFS real de Lima** (cuando exista v0) en sesión con el cliente.
- [ ] Evaluar esfuerzo de **fork i18n + MapLibre** de GTFS·X (spike técnico, 2–3 días).
- [ ] Reposicionar el roadmap de **tp-routes** hacia captura de campo + OSM (no editor GTFS).
- [ ] Confirmar si AEMUS quiere **autoservicio** o **servicio gestionado** ("fix my feed").

---

## Fuentes y evidencia
- GTFS·X: https://www.gtfsx.com · repo `markegge/gtfsx` (AGPL-3.0) · prueba en vivo (capturas en `docs/img/`).
- tp-routes: `leoguti/tp-routes` (análisis de código).
- Ecosistema: `trufi-association/trufi-gtfs-builder`, `trufi-gtfs-simulator`, `leoguti/gtfs2osm`, etc.
- Panorama: Optibus/Trillium, Arcadis/IBI datatools-ui, AddTransit, National RTAP, Spare, MobilityData gtfs-validator.

*Informe generado el 2026-06-23. Investigación con análisis de código, web y prueba interactiva del editor.*
