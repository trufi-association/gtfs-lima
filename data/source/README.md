# `data/source/` — Fuente original (INTOCABLE)

Esta carpeta contiene los datos **crudos tal como los entregó el cliente**.
Nunca se editan ni se sobrescriben. Todo procesamiento se hace sobre copias en
`data/osm/` o `data/gtfs/`.

## Inventario

| Archivo | Origen | Recibido | Notas |
|---|---|---|---|
| `aemus mapa 2.kml` | Cliente (Edgardo / SIMA-ITS) vía Google My Maps | 2026-06-23 | Export de Google My Maps. 6 capas = 6 rutas. Ver `docs/00_analisis_kml.md`. |

## Procedencia

- **Cliente:** INTERNATIONAL PARTNERS S.A. / AEMUS (Lima).
- **Contacto técnico:** Juan Prado — SIMA-ITS.
- **Herramienta de origen:** Google My Maps (export KML).
- **Sistema de coordenadas:** WGS84 (EPSG:4326), lon/lat. Altitud = 0 (no usada).
