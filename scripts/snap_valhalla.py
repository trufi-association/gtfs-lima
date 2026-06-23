#!/usr/bin/env python3
"""
Fase 2.5 — Snap-to-roads con Valhalla (enfoque map-match).

Para cada TRAZADO del KML (data/osm/shapes.geojson) hace **map-matching** contra las
calles reales de OSM (`/trace_route`, costing bus → auto), obteniendo geometría limpia
pegada a la calle SIN inventar rodeos. Luego `/trace_attributes` para los `way_id` de OSM.

Por qué map-match del trazado y no routing entre paradas:
  - Sigue la FORMA dibujada en el KML (no toma atajos de carro ni hace vueltas en U).
  - Cada LineString del KML ya es un SENTIDO → resuelve ida/vuelta sin depender del
    campo `direction` de las paradas (que solo traía LA 50).
Si un trazado es demasiado corto/roto (p. ej. fragmentos de ETUCHISA), cae a routing por
las paradas de esa ruta como respaldo, y se marca para revisión manual.

Salida: data/osm/shapes_snapped.geojson (un LineString por trazado + metadatos).

Uso:
  VALHALLA_URL=… python3 scripts/snap_valhalla.py            # todas
  VALHALLA_URL=… python3 scripts/snap_valhalla.py R-9605     # una ruta
"""
import json
import math
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

VALHALLA_URL = os.environ.get("VALHALLA_URL", "https://valhalla.busboy.app")
SHAPES = Path("data/osm/shapes.geojson")
STOPS = Path("data/osm/stops.geojson")
OUT = Path("data/osm/shapes_snapped.geojson")
COSTINGS = ("bus", "auto")     # preferir bus; si el server no lo soporta, auto
MIN_VERTS = 8                   # trazado más corto que esto → respaldo por paradas


def post(path, payload):
    req = urllib.request.Request(f"{VALHALLA_URL}{path}",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def decode_polyline(enc, precision=6):
    inv = 1.0 / (10 ** precision)
    out, lat, lon, i = [], 0, 0, 0
    while i < len(enc):
        for axis in (0, 1):
            shift = res = 0
            while True:
                b = ord(enc[i]) - 63
                i += 1
                res |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(res >> 1) if (res & 1) else (res >> 1)
            if axis == 0:
                lat += d
            else:
                lon += d
        out.append([round(lon * inv, 6), round(lat * inv, 6)])
    return out


def legs_to_coords(trip):
    coords = []
    for leg in trip["legs"]:
        dec = decode_polyline(leg["shape"])
        if coords:
            dec = dec[1:]
        coords += dec
    return coords, sum(l["summary"]["length"] for l in trip["legs"])


def hav(a, b):
    R = 6371
    dlat = math.radians(b[1] - a[1])
    dlon = math.radians(b[0] - a[0])
    h = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[1]))
         * math.cos(math.radians(b[1])) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def length_km(c):
    return sum(hav(c[i], c[i + 1]) for i in range(len(c) - 1))


def _bearing(a, b):
    y = math.sin(math.radians(b[0] - a[0])) * math.cos(math.radians(b[1]))
    x = (math.cos(math.radians(a[1])) * math.sin(math.radians(b[1]))
         - math.sin(math.radians(a[1])) * math.cos(math.radians(b[1]))
         * math.cos(math.radians(b[0] - a[0])))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def count_uturns(coords):
    """nº de retrocesos (>150°), muestreando cada ~80 m para ignorar ruido."""
    s = [coords[0]]
    for c in coords[1:]:
        if hav(s[-1], c) * 1000 > 80:
            s.append(c)
    n = 0
    for i in range(1, len(s) - 1):
        d = abs(_bearing(s[i - 1], s[i]) - _bearing(s[i], s[i + 1]))
        if min(d, 360 - d) > 150:
            n += 1
    return n


def match_trace(coords):
    """map-match de un trazado [[lon,lat]] → (coords, km, costing) o None."""
    shape = [{"lat": c[1], "lon": c[0]} for c in coords]
    for costing in COSTINGS:
        d = post("/trace_route", {"shape": shape, "costing": costing,
                                  "shape_match": "map_snap"})
        if "trip" in d:
            cc, km = legs_to_coords(d["trip"])
            return cc, km, costing
    return None


def route_stops(stops):
    """respaldo: routing por paradas en orden (chunked) → (coords, km)."""
    locs = [{"lat": s["lat"], "lon": s["lon"]} for s in stops]
    chunks = ([locs] if len(locs) <= 20
              else [locs[i:i + 20] for i in range(0, len(locs), 19)])
    coords, km = [], 0.0
    for ch in chunks:
        if len(ch) < 2:
            continue
        d = post("/route", {"locations": ch, "costing": "auto",
                            "directions_options": {"units": "kilometers"}})
        if "trip" not in d:
            return None
        cc, k = legs_to_coords(d["trip"])
        coords += cc[1:] if coords else cc
        km += k
    return (coords, km) if coords else None


def trace_wayids(coords):
    step = max(1, len(coords) // 100)
    sampled = [{"lat": c[1], "lon": c[0]} for c in coords[::step]]
    if sampled and (sampled[-1]["lat"], sampled[-1]["lon"]) != (coords[-1][1], coords[-1][0]):
        sampled.append({"lat": coords[-1][1], "lon": coords[-1][0]})
    d = post("/trace_attributes", {"shape": sampled, "costing": "bus",
             "shape_match": "map_snap",
             "filters": {"attributes": ["edge.way_id", "edge.names"], "action": "include"}})
    if "error" in d:
        d = post("/trace_attributes", {"shape": sampled, "costing": "auto",
                 "shape_match": "map_snap",
                 "filters": {"attributes": ["edge.way_id", "edge.names"], "action": "include"}})
    way_ids, names, prev = [], [], None
    for e in d.get("edges", []):
        wid = e.get("way_id")
        if wid and wid != prev:
            way_ids.append(wid)
            prev = wid
        for nm in e.get("names", []):
            if nm not in names:
                names.append(nm)
    return way_ids, names


def stops_by_route(filter_ref):
    fc = json.loads(STOPS.read_text())
    g = defaultdict(list)
    for f in fc["features"]:
        p = f["properties"]
        if filter_ref and p["route_ref"] != filter_ref:
            continue
        lon, lat = f["geometry"]["coordinates"]
        g[p["route_ref"]].append({"seq": p.get("stop_seq"), "lat": lat, "lon": lon})
    for k in g:
        g[k].sort(key=lambda s: (s["seq"] is None, s["seq"] or 0))
    return g


def main():
    filter_ref = sys.argv[1] if len(sys.argv) > 1 else None
    shapes = json.loads(SHAPES.read_text())
    route_stops_map = stops_by_route(filter_ref)
    print(f"VALHALLA_URL = {VALHALLA_URL}\n")
    print(f"{'TRAZADO':<42}{'MÉTODO':<12}{'KM':>7}{'U-turn':>8}  REVISAR")

    features = []
    for f in shapes["features"]:
        p = f["properties"]
        ref = p["route_ref"]
        if filter_ref and ref != filter_ref:
            continue
        kc = f["geometry"]["coordinates"]
        label = f"{ref} {p['route_name']} / {p['shape_name']}"[:40]

        method, result = None, None
        if len(kc) >= MIN_VERTS:
            m = match_trace(kc)
            if m:
                result = (m[0], m[1])
                method = f"match:{m[2]}"
        if result is None:                       # respaldo por paradas
            rs = route_stops_map.get(ref, [])
            if len(rs) >= 2:
                r = route_stops(rs)
                if r:
                    result = r
                    method = "stops:auto"
        if result is None:
            print(f"{label:<42}{'—':<12}{'—':>7}{'—':>8}  ❌ sin geometría")
            continue

        coords, km = result
        ut = count_uturns(coords)
        kml_km = length_km(kc) if len(kc) >= 2 else 0
        # marcar revisión: muchas U-turns, o gran diferencia con el KML
        revisar = []
        if ut > 0:
            revisar.append(f"{ut} U-turn")
        if kml_km and abs(km - kml_km) / kml_km > 0.20:
            revisar.append(f"Δlong {abs(km-kml_km)/kml_km*100:.0f}%")
        if len(kc) < MIN_VERTS:
            revisar.append("trazado roto")
        flag = "⚠️ " + ", ".join(revisar) if revisar else "✓"
        print(f"{label:<42}{method:<12}{km:>7.2f}{ut:>8}  {flag}")

        way_ids, names = trace_wayids(coords)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "route_ref": ref, "route_name": p["route_name"],
                "shape_name": p["shape_name"], "method": method,
                "distance_km": round(km, 3), "n_points": len(coords),
                "uturns": ut, "review": revisar,
                "osm_way_ids": way_ids, "osm_streets": names,
            },
        })

    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                              ensure_ascii=False, indent=1))
    print(f"\n→ {OUT}  ({len(features)} trazado(s))")
    n_rev = sum(1 for f in features if f["properties"]["review"])
    print(f"   {n_rev} trazado(s) marcados para revisión manual.")


if __name__ == "__main__":
    main()
