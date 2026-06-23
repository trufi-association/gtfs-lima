# Análisis del KML fuente — `aemus mapa 2.kml`

> Análisis técnico previo a cualquier transformación. **No se ha modificado el KML.**
> Fecha: 2026-06-23 · Autor: Leonardo + Claude

## 1. Qué es el archivo

- Export de **Google My Maps** (`<name>Mapa sin nombre</name>`), 842 KB, UTF-8.
- Sistema de coordenadas **WGS84 (EPSG:4326)**, lon/lat. Altitud siempre 0.
- **Bounding box:** Lon −77.143 .. −76.912 · Lat −12.241 .. −11.846 → ✅ corresponde a **Lima Metropolitana** (norte: Los Olivos/Callao; sur: Villa El Salvador).

## 2. Contenido: 6 capas = 6 rutas

> ⚠️ El alcance comercial vigente cotiza **4 rutas** (ítem GTFS €1.953). El KML trae **6**. A aclarar con el cliente (ver §5).

| # | Capa (ruta) | Trazados (LineString) | Paradas (Point) | Esquema de atributos | Estado |
|---|---|---|---|---|---|
| 1 | **R-9605 URBANITO** | 1 — `AV OSCAR BENAVIDES-AV. UNIVERS` (87v) | 47 | `rp_numero`, `rp_codigo_alfanumerico`, `latitud`, `longitud` | ⚠️ Solo **un sentido** trazado |
| 2 | **R-1066 LA 50** | 2 — `MERCADO MONTENEGRO` (121v), `DULANTO` (90v) | 94 | `N°`, **`SENTIDO`** (IDA/VUELTA), `LATITUD`, `LONGITUD` | ✅ Más completa — única con SENTIDO explícito |
| 3 | **R-1702 NUEVA AMERICA** | 2 — `Pdro. Pocitos` (242v), `Pdro. Inicial Torreblanca` (136v) | 315 | `Número`, `Codigo_alfanumerico` | ✅ OK (muchas paradas) |
| 4 | **R-1802 ETUCHISA-A** | 4 — `A6 Av. Lomas c/Sep` (432v) + **3 fragmentos de 3 vértices** | 264 | `Numero`, `Codigo` | 🔴 Trazado **roto en fragmentos** (solo A6 es real) |
| 5 | **R-1132B AERODIRECTO CENTRO** | 2 — `IDA_AERODIRECTO` (256v), `RETORNO_AERODIRECTO` (244v) | **0** | — | 🔴 **Sin paradas** |
| 6 | **R-1435XS AERODIRECTO NORTE** | 2 — `IDA` (546v), `RETORNO` (435v) | 22 | `Latitud`/`Longitud` genérico | ⚠️ Pocas paradas + 1 `Polígono sin título` suelto |

**Totales:** 13 LineStrings · 742 Points · 1 Polygon · 756 placemarks.

## 3. Hallazgo clave: las paradas traen `ExtendedData` estructurada

Cada parada (Point) incluye atributos en `<ExtendedData>`, lo que adelanta gran parte del GTFS:
secuencia, código de parada y coordenadas propias. **Pero el esquema NO es homogéneo** — cada
capa fue digitalizada por separado, con nombres de campo distintos:

| Capa | Campo nº orden | Campo código | Campo coords | ¿Sentido? |
|---|---|---|---|---|
| R-9605 URBANITO | `rp_numero` | `rp_codigo_alfanumerico` | `latitud`/`longitud` | No |
| R-1066 LA 50 | `N°` | — | `LATITUD`/`LONGITUD` | **`SENTIDO`** ✅ |
| R-1702 NUEVA AMERICA | `Número` | `Codigo_alfanumerico` | (genérico) | No |
| R-1802 ETUCHISA-A | `Numero` | `Codigo` | (genérico) | No |
| R-1435XS / genérico | — | — | `Latitud`/`Longitud` | No |

→ **Requiere una capa de normalización** que mapee los 5 esquemas a un modelo único antes de generar GTFS.

## 4. Problemas de calidad detectados

1. 🔴 **Esquemas de atributos heterogéneos** (5 variantes entre 6 capas). Normalizar.
2. 🟡 **Mojibake / doble-UTF8** en **53 nombres** (`CAÃ‘ETE`→CAÑETE, `PollerÃ­a`→Pollería, `HuascarÃ¡n`→Huascarán). Limpieza de encoding.
3. 🔴 **R-1802 ETUCHISA-A**: 3 de 4 trazados son fragmentos de 3 vértices → el recorrido real está incompleto/partido. Reconstruir o pedir trazado completo.
4. 🔴 **R-1132B AERODIRECTO CENTRO**: 0 paradas. Pedir paradas al cliente o derivarlas.
5. 🟡 **R-9605 URBANITO**: un solo sentido trazado. Falta el retorno.
6. 🟡 **Sentido (ida/vuelta)** solo explícito en LA 50; en el resto hay que inferirlo por asignación parada↔trazado u orden de secuencia.
7. 🟡 **Polígono "sin título"** suelto en AERODIRECTO NORTE — ¿zona de cobertura? ¿error de dibujo? Aclarar.

## 5. Qué falta para un GTFS válido (no está en el KML)

El KML aporta **geometría + paradas**. Para un feed GTFS válido aún falta información que **solo el cliente tiene**:

- **`agency.txt`**: operador(es), URL, zona horaria (`America/Lima`), idioma, teléfono.
- **`calendar.txt` / `calendar_dates.txt`**: días de operación de cada ruta.
- **Horarios o frecuencias** (`stop_times.txt` o `frequencies.txt`): headways por franja, hora de inicio/fin de servicio. **Nada temporal viene en el KML.**
- **Asignación confirmada** parada → ruta → sentido → secuencia (parcialmente derivable de `ExtendedData`, a validar).
- **Trazados faltantes/incompletos** (retorno de URBANITO, recorrido completo de ETUCHISA, paradas de AERODIRECTO CENTRO).
- (Opcional) Tarifas (`fare_attributes`/`fare_rules`).

## 6. Discrepancia comercial a resolver

- **Cotizado:** 4 rutas (€1.953).
- **Entregado en KML:** 6 rutas.
- **Acción:** confirmar con Edgardo/Juan Prado cuáles 4 son del MVP, o renegociar alcance/precio por las 2 adicionales.

## 7. Conclusión

El KML es una **base sólida pero heterogénea**: buena geometría y paradas con metadatos, pero
con 5 esquemas distintos, errores de encoding y vacíos (sentidos/paradas/trazados faltantes).
El camino **KML → OpenStreetMap → GTFS** es viable; OSM nos sirve para **homogeneizar, corregir
trazados y validar** antes de generar el feed. Ver plan de tareas en `docs/01_pipeline.md`.
