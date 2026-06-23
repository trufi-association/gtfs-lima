# Fase 2.5 — Snap-to-roads con Valhalla

> Cómo usamos el motor **Valhalla** (servicio de Trufi/BusBoy) para convertir las paradas y
> trazados del KML en geometría limpia pegada a las calles reales de OpenStreetMap.
> Fecha: 2026-06-23.

## Para qué sirve

El KML traía trazados con problemas (ETUCHISA roto en fragmentos, URBANITO sin retorno, geometría
imprecisa). Valhalla resuelve esto: dadas las **paradas en orden**, calcula el recorrido **siguiendo
las calles reales** y nos devuelve dos cosas a la vez:

1. **Geometría pegada a la calle** → futura `shapes.txt` del GTFS.
2. **Los `way_id` de OpenStreetMap** por donde pasa la ruta → insumo para mapear en OSM PTv2 (Fase 3).

Reutilizamos el **mismo motor que tp-routes/BusBoy** (`VALHALLA_URL`), no dependemos de Mapbox.

## Endpoint

`VALHALLA_URL=https://valhalla.busboy.app` (ver `.env.example`). Cobertura: **Colombia, Bolivia y
Lima (Perú)**. Lima se añadió el 2026-06-23 (recorte OSM del bbox de las rutas).

> La administración del servidor (cómo se actualizan los mapas, rollback) está documentada en la
> carpeta privada de gestión, no en este repo público.

## Receta (dos pasos, igual que `tp-routes/js/valhalla.js`)

**Paso 1 — `/route`**: trazado siguiendo calles entre los puntos.
```json
POST /route
{ "locations": [{"lat":-12.0502,"lon":-77.0776}, {"lat":-12.0476,"lon":-77.0410}],
  "costing": "auto",
  "directions_options": {"units":"kilometers"} }
```
La geometría viene como **polilínea codificada (precisión 6)** en `trip.legs[].shape` → hay que
decodificarla. Si hay >~20 puntos, se trocea en chunks solapados (1 punto de solape).

**Paso 2 — `/trace_attributes`** (`shape_match: map_snap`): pega la geometría a OSM y devuelve los
`way_id` + nombres de calle.
```json
POST /trace_attributes
{ "shape": [...muestreo de la geometría del paso 1...],
  "costing": "auto", "shape_match": "map_snap",
  "filters": {"attributes":["edge.way_id","edge.names","edge.length"],"action":"include"} }
```

**Verificado en Lima (2026-06-23):** una traza sobre Av. Óscar Benavides devolvió 7 edges y Valhalla
reconoció la calle real *"Avenida Óscar Raimundo Benavides"* — justo el corredor de la ruta URBANITO.

## Notas / cuidados

- `costing: "auto"` respeta sentidos de calle (one-way), correcto para buses. Valhalla también tiene
  `costing: "bus"` si hiciera falta afinar.
- Valhalla **propone**, nosotros **validamos**: siempre comparar el trazado snapped contra el
  LineString del KML; donde difieran mucho, revisar a mano (puede haber corredores exclusivos o
  giros que el routing automático no adivina).
- Para rutas con trazado roto/faltante en el KML, el recorrido se reconstruye **desde las paradas**.

## Próximo

- [ ] `scripts/snap_valhalla.py`: por ruta+sentido, paradas en orden → `/route` + `/trace_attributes`
      → `data/osm/shapes_snapped.geojson` (geometría) + `way_ids` por ruta.
- [ ] Resolver el sentido de las paradas donde no es explícito (solo LA 50 lo trae) — asignación por
      proximidad al trazado, en la Fase 3 (OSM).
