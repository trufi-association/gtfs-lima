# Fase 1 — Normalización (resultado)

> Generado por `scripts/normalize.py` a partir de `data/source/aemus mapa 2.kml`.
> Reproducible: `python3 scripts/normalize.py` borra y regenera `data/osm/`.
> Fecha: 2026-06-23.

## Qué se hizo

1. **Encoding corregido** — mojibake doble-UTF8 en **53 nombres**. Estrategia: `encode('cp1252')`
   (cubre la `Ñ`, que viene como `Ã` + comilla tipográfica) con fallback a `latin-1`
   (cubre `Á`/`Í`, cuyos bytes `0x81`/`0x8d` CP1252 no asigna). **0 ocurrencias** de mojibake restantes.
2. **Esquemas unificados** — los 5 esquemas de `ExtendedData` mapeados a un modelo canónico:
   `route_ref`, `route_name`, `stop_id`, `stop_code`, `stop_name`, `stop_seq`, `direction`, `lon`, `lat`.
3. **Coordenadas** — tomadas de la **geometría** del Point (fuente más confiable), no de los
   campos lat/lon de `ExtendedData` (que variaban de nombre por capa).
4. **`stop_id` únicos garantizados** — código si existe; si no, `REF[_DIR]_S<seq>`, con
   desambiguación `-2/-3` ante colisiones. Resultado: **742 ids únicos, 0 duplicados**.

## Salidas (`data/osm/`)

| Archivo | Contenido |
|---|---|
| `stops.geojson` | 742 paradas normalizadas (Point + propiedades) |
| `shapes.geojson` | 13 trazados normalizados (LineString + propiedades) |
| `stops.csv` | paradas en tabla legible para revisión |
| `routes.csv` | resumen por ruta |

## Resumen por ruta

| REF | Nombre | Paradas | Trazados | Notas |
|---|---|---:|---:|---|
| R-9605 | URBANITO | 47 | 1 | falta retorno (1 solo sentido) |
| R-IO66 | LA 50 | 94 | 2 | única con `SENTIDO` explícito (IDA/VUELTA); `ref` parece typo de R-1066 |
| R-1702 | NUEVA AMERICA | 315 | 2 | OK |
| R-1802 | ETUCHISA-A | 264 | 4 | 3 trazados son fragmentos (<5 vértices) — marcados `fragment:true` |
| R-1132B | AERODIRECTO CENTRO | 0 | 2 | sin paradas |
| R-1435XS | AERODIRECTO NORTE | 22 | 2 | paradas sin nº de secuencia ni código |

## Pendientes de calidad (no resolubles sin el cliente / se resuelven en Fase 3)

- **Sentido (ida/vuelta) sin asignar** salvo LA 50. En NUEVA AMERICA y ETUCHISA hay 2 trazados
  pero las paradas no indican a cuál pertenecen → se asignará por proximidad al trazado en OSM (Fase 3).
- **22 paradas sin secuencia** (AERODIRECTO NORTE, esquema genérico).
- **`stop_code` ausente** en 124 paradas (LA 50, AERODIRECTO NORTE) → usan id generado.
- **Secuencias duplicadas dentro de un sentido** (R-9605 ×1, R-1702 ×1, R-1802 ×4) y **códigos
  repetidos en origen** (p. ej. NUEVA AMERICA usa solo el número como código) → desambiguados, pero a revisar.
- **`ref` R-IO66**: casi seguro es **R-1066** mal transcrito desde My Maps. Confirmar con cliente.

→ Estos puntos alimentan el mensaje al cliente (Fase 2) y el mapeo en OSM (Fase 3).
