# GTFS Lima — AEMUS

Generación del **GTFS estático de Lima** (jurisdicción ATU) a partir del KML entregado
por el cliente, pasando por **OpenStreetMap** como capa intermedia de homogeneización y
validación.

- **Cliente:** INTERNATIONAL PARTNERS S.A. / AEMUS (Lima, Perú).
- **Operación / marca:** Trufi Association e.V.
- **Pipeline:** `KML (Google My Maps) → OpenStreetMap → GTFS`.
- **Alcance comercial:** GTFS de 4 rutas (a conciliar — el KML trae 6). Ver `docs/00_analisis_kml.md`.

## Estructura

```
gtfs_lima/
├── README.md                 ← este archivo
├── data/
│   ├── source/               ← fuente cruda del cliente (KML) — INTOCABLE
│   ├── osm/                  ← trabajo intermedio (GeoJSON/OSM, normalización)
│   └── gtfs/                 ← feed GTFS generado (salida)
├── docs/
│   ├── 00_analisis_kml.md    ← análisis del KML fuente
│   ├── 01_pipeline.md        ← plan de trabajo KML → OSM → GTFS
│   └── 02_normalizacion.md   ← resultado de la Fase 1
└── scripts/
    └── normalize.py          ← Fase 1: KML → modelo único (GeoJSON/CSV)
```

## Estado

| Fase | Estado |
|---|---|
| 0 · Análisis del KML | ✅ Completo |
| 1 · Normalización | ✅ Completo — ver `docs/02_normalizacion.md` |
| 2 · Resolver vacíos con cliente | ⬜ Pendiente |
| 3 · Mapeo en OSM | ⬜ Pendiente |
| 4 · Generación GTFS | ⬜ Pendiente |

## Datos del KML (resumen)

6 rutas · 13 trazados · 742 paradas con metadatos · WGS84 · Lima Metropolitana.
Detalle y problemas de calidad en [`docs/00_analisis_kml.md`](docs/00_analisis_kml.md).
