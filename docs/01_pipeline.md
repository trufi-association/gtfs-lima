# Pipeline KML → OpenStreetMap → GTFS

> Plan de trabajo para producir el GTFS estático de Lima (jurisdicción ATU) a partir
> del KML del cliente. Cliente: AEMUS / INTERNATIONAL PARTNERS S.A.

## Visión general

```
  data/source/*.kml          OpenStreetMap                 data/gtfs/
 (fuente del cliente)   →   (homogenizar, corregir,   →   (feed GTFS
  INTOCABLE                  validar geometría +            estático validado)
                             relaciones de rutas)
        │                          │                            │
        └── data/osm/ (trabajo intermedio: GeoJSON/OSM, normalización) ──┘
```

**Por qué pasar por OSM:** el KML tiene 5 esquemas de atributos, encoding roto y trazados
incompletos. OSM nos da un modelo de datos único (rutas como `relations`, paradas como `nodes`),
herramientas de edición/validación y una fuente reutilizable y abierta. De OSM a GTFS hay
conversores maduros.

## Fases

### Fase 0 — Análisis (✅ hecho)
- [x] Inventariar capas, geometrías, atributos, calidad → `docs/00_analisis_kml.md`.

### Fase 1 — Normalización del KML (✅ hecho — `scripts/normalize.py`, ver `02_normalizacion.md`)
- [x] Corregir encoding (mojibake doble-UTF8) en los 53 nombres afectados.
- [x] Mapear los 5 esquemas de `ExtendedData` a un modelo único: `route_ref`, `route_name`, `stop_id`, `stop_name`, `stop_seq`, `direction`, `lat`, `lon`.
- [x] Separar por ruta; `stop_id` únicos garantizados.
- [x] Exportar a GeoJSON limpio en `data/osm/`.
- [~] Inferir sentido donde no es explícito → se hará por proximidad al trazado en Fase 3.

### Fase 2 — Resolver vacíos con el cliente
- [ ] Aclarar las **4 rutas del alcance** (vs. 6 entregadas).
- [ ] Pedir: retorno de URBANITO, recorrido completo de ETUCHISA, paradas de AERODIRECTO CENTRO.
- [ ] Pedir datos no-geográficos: operador(es), horarios/frecuencias, días de servicio.
- [ ] Aclarar el polígono "sin título" de AERODIRECTO NORTE.

### Fase 3 — Mapeo en OpenStreetMap
- [ ] Cargar trazados como `relations` tipo `route=bus` + `route_master`.
- [ ] Paradas como nodes `highway=bus_stop` / `public_transport=platform`.
- [ ] Tags: `ref`, `name`, `operator`, `network=ATU`, `from`/`to`.
- [ ] Validar geometría (continuidad, sentido, cobertura) contra calles reales.

### Fase 4 — Generación del GTFS
- [ ] Construir `agency`, `routes`, `trips`, `stops`, `stop_times`, `shapes`, `calendar`, `frequencies`.
- [ ] Validar con MobilityData GTFS Validator (canonical).
- [ ] Entregar feed en `data/gtfs/` + reporte de validación.

## Herramientas candidatas
- **Conversión/geo:** `ogr2ogr` (GDAL), Python (`lxml`, `shapely`).
- **OSM:** JOSM (edición manual), Overpass (consulta).
- **GTFS:** generadores OSM→GTFS, `gtfstidy`, **MobilityData GTFS Validator**.

> Estado de herramientas locales (2026-06-23): `node` y `python3` ✅ · `ogr2ogr`/`gtfstidy` por instalar.
