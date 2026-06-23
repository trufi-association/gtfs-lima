#!/usr/bin/env python3
"""
Fase 1 — Normalización del KML fuente a un modelo único.

Entrada : data/source/aemus mapa 2.kml  (Google My Maps, 6 capas, 5 esquemas)
Salidas : data/osm/stops.geojson    (paradas normalizadas)
          data/osm/shapes.geojson   (trazados normalizados)
          data/osm/stops.csv        (paradas, legible para revisión)
          data/osm/routes.csv       (resumen por ruta)

Qué hace:
  1. Corrige el mojibake (doble-encoding CP1252→UTF-8) de nombres.
  2. Mapea los campos heterogéneos de <ExtendedData> a un modelo común.
  3. Usa la geometría del Point como fuente de coordenadas (la más confiable).
  4. Detecta sentido (IDA/VUELTA) donde es explícito o inferible por nombre.
No modifica la fuente. Reproducible: borra y regenera data/osm/.
"""
import csv
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

NS = '{http://www.opengis.net/kml/2.2}'
SRC = Path("data/source/aemus mapa 2.kml")
OUT = Path("data/osm")

# ---------- utilidades ----------

def fix_encoding(s):
    """Corrige mojibake doble-UTF8. CP1252 cubre comillas tipográficas (Ñ→Ã‘);
    latin-1 cubre bytes 0x81/0x8d (Á, Í) que CP1252 no asigna. Fallback: original."""
    if not s or ('Ã' not in s and 'Â' not in s):
        return s
    for enc in ('cp1252', 'latin-1'):
        try:
            return s.encode(enc).decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s

def norm_key(k):
    """Normaliza nombre de campo: minúsculas, sin acentos, sin signos."""
    k = unicodedata.normalize('NFKD', k).encode('ascii', 'ignore').decode()
    return k.strip().lower().replace('°', '').replace(' ', '_')

# Mapeo de los 5 esquemas a campos canónicos
SEQ_KEYS  = {'rp_numero', 'numero', 'n'}            # nº de orden de la parada
CODE_KEYS = {'rp_codigo_alfanumerico', 'codigo_alfanumerico', 'codigo'}
DIR_KEYS  = {'sentido'}
SKIP_KEYS = {'latitud', 'longitud', 'descripcion'}  # coords vienen de geometría

def parse_extended(pm):
    """Devuelve dict canónico {seq, code, direction} desde ExtendedData."""
    out = {'seq': None, 'code': None, 'direction': None}
    ed = pm.find(NS + 'ExtendedData')
    if ed is None:
        return out
    for d in ed.findall(NS + 'Data'):
        key = norm_key(d.get('name') or '')
        val = fix_encoding((d.findtext(NS + 'value') or '').strip())
        if not val:
            continue
        if key in SEQ_KEYS:
            try:
                out['seq'] = int(float(val))
            except ValueError:
                out['seq'] = val
        elif key in CODE_KEYS:
            out['code'] = val
        elif key in DIR_KEYS:
            out['direction'] = val.upper()
    return out

def parse_ref(folder_name):
    """'R-9605 URBANITO' -> ('R-9605', 'URBANITO')"""
    m = re.match(r'^(R-\S+)\s+(.*)$', folder_name.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return folder_name.strip(), folder_name.strip()

def detect_dir_from_name(name):
    """Detecta sentido a partir del nombre del trazado."""
    u = (name or '').upper()
    if 'RETORNO' in u or 'VUELTA' in u or 'REGRESO' in u:
        return 'VUELTA'
    if 'IDA' in u:
        return 'IDA'
    return None

def coords_of(geom_text):
    """'lon,lat,0 lon,lat,0 ...' -> [[lon,lat], ...]"""
    pts = []
    for tup in (geom_text or '').split():
        p = tup.split(',')
        if len(p) >= 2:
            pts.append([round(float(p[0]), 7), round(float(p[1]), 7)])
    return pts

# ---------- proceso ----------

def main():
    doc = ET.parse(SRC).getroot().find(NS + 'Document')
    OUT.mkdir(parents=True, exist_ok=True)

    stop_features, shape_features = [], []
    stops_rows, routes_rows = [], []
    used_ids = {}  # stop_id provisional -> contador, para garantizar unicidad

    def unique_id(base):
        """Garantiza stop_id único añadiendo sufijo -2, -3… si colisiona."""
        n = used_ids.get(base, 0) + 1
        used_ids[base] = n
        return base if n == 1 else f"{base}-{n}"

    for fo in doc.findall(NS + 'Folder'):
        fname = fix_encoding((fo.findtext(NS + 'name') or '').strip())
        ref, rname = parse_ref(fname)

        n_stops = n_shapes = 0
        shape_dirs = []

        for pm in fo.findall(NS + 'Placemark'):
            pm_name = fix_encoding((pm.findtext(NS + 'name') or '').strip())

            pt = pm.find(NS + 'Point')
            ls = pm.find(NS + 'LineString')

            if pt is not None:
                cc = coords_of(pt.findtext(NS + 'coordinates'))
                if not cc:
                    continue
                lon, lat = cc[0]
                ext = parse_extended(pm)
                # stop_id provisional: código si existe; si no, REF[_DIR]_S<seq>.
                # Se garantiza unicidad global (ida/vuelta reusan secuencias).
                if ext['code']:
                    base = ext['code']
                else:
                    dpart = f"_{ext['direction']}" if ext['direction'] else ''
                    base = f"{ref}{dpart}_S{ext['seq']}"
                stop_id = unique_id(base)
                props = {
                    'route_ref': ref, 'route_name': rname,
                    'stop_id': stop_id, 'stop_code': ext['code'] or '',
                    'stop_name': pm_name, 'stop_seq': ext['seq'],
                    'direction': ext['direction'] or '',
                }
                stop_features.append({
                    'type': 'Feature',
                    'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                    'properties': props,
                })
                stops_rows.append({**props, 'lon': lon, 'lat': lat})
                n_stops += 1

            elif ls is not None:
                cc = coords_of(ls.findtext(NS + 'coordinates'))
                direction = detect_dir_from_name(pm_name)
                shape_dirs.append(direction)
                shape_features.append({
                    'type': 'Feature',
                    'geometry': {'type': 'LineString', 'coordinates': cc},
                    'properties': {
                        'route_ref': ref, 'route_name': rname,
                        'shape_name': pm_name, 'direction': direction or '',
                        'n_points': len(cc),
                        'fragment': len(cc) < 5,  # marca trazados sospechosos
                    },
                })
                n_shapes += 1

        routes_rows.append({
            'route_ref': ref, 'route_name': rname,
            'n_stops': n_stops, 'n_shapes': n_shapes,
            'shape_dirs': '|'.join(d or '?' for d in shape_dirs),
        })

    # ---------- escritura ----------
    (OUT / 'stops.geojson').write_text(json.dumps(
        {'type': 'FeatureCollection', 'features': stop_features},
        ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'shapes.geojson').write_text(json.dumps(
        {'type': 'FeatureCollection', 'features': shape_features},
        ensure_ascii=False, indent=1), encoding='utf-8')

    with (OUT / 'stops.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=[
            'route_ref', 'route_name', 'stop_id', 'stop_code',
            'stop_name', 'stop_seq', 'direction', 'lon', 'lat'])
        w.writeheader()
        w.writerows(stops_rows)

    with (OUT / 'routes.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=[
            'route_ref', 'route_name', 'n_stops', 'n_shapes', 'shape_dirs'])
        w.writeheader()
        w.writerows(routes_rows)

    # ---------- reporte a stdout ----------
    print(f"Paradas normalizadas : {len(stop_features)}")
    print(f"Trazados normalizados: {len(shape_features)}")
    print(f"Rutas                : {len(routes_rows)}\n")
    print(f"{'REF':<10}{'NOMBRE':<22}{'PARADAS':>8}{'TRAZ':>6}  SENTIDOS")
    for r in routes_rows:
        print(f"{r['route_ref']:<10}{r['route_name']:<22}{r['n_stops']:>8}"
              f"{r['n_shapes']:>6}  {r['shape_dirs']}")

if __name__ == '__main__':
    main()
