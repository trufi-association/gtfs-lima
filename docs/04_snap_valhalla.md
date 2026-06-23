# Fase 2.5 — Snap-to-roads con Valhalla

> Convierte los trazados del KML en geometría limpia pegada a las calles reales de OpenStreetMap,
> usando el motor **Valhalla** de Trufi/BusBoy (`VALHALLA_URL`, sin Mapbox). Fecha: 2026-06-23.

## Enfoque: map-match del trazado (no routing entre paradas)

El primer intento conectaba las **paradas** con `/route` (costing auto). Resultado: Valhalla rutea
"como un carro" y mete **rodeos y vueltas en U** (ej. URBANITO se iba por Av. Guillermo Dansey en un
rectángulo que no existe en la ruta). Ver `img/urbanito-snap.jpeg` (azul, con el rodeo).

**Corrección** — hacer **map-matching del trazado dibujado** (`/trace_route`, `shape_match: map_snap`,
`costing: bus`): pega la *forma* del KML a las calles **sin inventar desvíos**. Bonus: cada LineString
del KML ya es un **sentido** (ida/vuelta), así que esto **resuelve también el sentido** sin depender
del campo `direction` (que solo traía LA 50).

Comparación en URBANITO (`img/urbanito-fix.jpeg`, verde = corregido):

| Método | Puntos | Longitud | Vueltas en U |
|---|---|---|---|
| KML original | 87 | 18.60 km | 0 |
| Snap por paradas (auto) | 540 | 16.93 km (−9%) | 1 ⚠️ |
| **Map-match + bus** | 591 | 19.00 km (+2%) | **0** ✅ |

## Script: `scripts/snap_valhalla.py`

Para cada trazado del KML: `/trace_route` (bus→auto) → geometría limpia; respaldo a routing por
paradas si el trazado es muy corto/roto; `/trace_attributes` → `osm_way_ids` + `osm_streets`.
**Auto-marca para revisión** (campo `review`) cuando detecta vueltas en U, diferencia de longitud
>20 % con el KML, o trazado roto.

```
VALHALLA_URL=https://valhalla.busboy.app python3 scripts/snap_valhalla.py        # todas
VALHALLA_URL=https://valhalla.busboy.app python3 scripts/snap_valhalla.py R-9605 # una
```
Salida: `data/osm/shapes_snapped.geojson` (LineString por trazado + `method`, `distance_km`,
`uturns`, `review`, `osm_way_ids`, `osm_streets`).

## Resultado (13 trazados, 2026-06-23)

- ✅ **Limpios:** URBANITO · NUEVA AMERICA (ida/vuelta) · AERODIRECTO NORTE retorno.
- ⚠️ **A revisar (datos de origen incompletos, no fallo del algoritmo):**
  - **ETUCHISA A1/A3/A4** — fragmentos de 3 vértices en el KML → el respaldo por paradas mezcla
    sentidos (150 km, 26 U-turns). **Pedir trazado completo al cliente.**
  - **AERODIRECTO CENTRO/NORTE IDA, LA 50** — trazados cortos/incompletos en el KML (Δlongitud alta).

## Las 3 palancas de corrección

1. **Map-match + `bus`** (automático) — corrige rodeos y vueltas en U del algoritmo. ✅ aplicado.
2. **Marcado automático** — el script señala qué revisar y por qué. ✅
3. **Corrección manual / pedir datos** — trazados rotos en el KML no se arreglan solos: o se dibujan
   a mano en un editor (tp-routes / GTFS·X, ver `03_evaluacion_editor_gtfs.md`) o se piden a Juan Prado.

## Cuidados

- `costing: bus` respeta lógica de bus y sentidos de calle. Si el server no lo soporta, cae a `auto`.
- Valhalla **propone**, nosotros **validamos**: revisar siempre los trazados marcados ⚠️.

## Próximo

- [ ] Mejorar el respaldo de ETUCHISA: separar paradas por sentido antes del fallback (no mezclar).
- [ ] Pedir a Juan Prado: trazado completo de ETUCHISA y los IDA de AERODIRECTO; retorno de URBANITO.
- [ ] Asignar cada parada a su trazado (sentido) por proximidad — Fase 3 (OSM).
- [ ] Revisar/corregir a mano los trazados ⚠️ en un editor visual.
