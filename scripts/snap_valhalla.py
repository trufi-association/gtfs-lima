#!/usr/bin/env python3
"""
Fase 2.5 — Snap-to-roads con Valhalla.

Toma las paradas normalizadas (data/osm/stops.geojson), y por cada ruta+sentido:
  1. /route          → trazado siguiendo las calles reales entre las paradas (en orden).
  2. /trace_attributes (map_snap) → way_id + nombres de calle de OpenStreetMap.
Escribe data/osm/shapes_snapped.geojson (LineStrings limpios + metadatos).

Usa el mismo motor que tp-routes/BusBoy (VALHALLA_URL). No depende de Mapbox.
Receta portada de tp-routes/js/valhalla.js.

Uso:
  python3 scripts/snap_valhalla.py            # todas las rutas
  python3 scripts/snap_valhalla.py R-9605     # solo una ruta (ref)
"""
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

VALHALLA_URL = os.environ.get("VALHALLA_URL", "https://valhalla.busboy.app")
STOPS = Path("data/osm/stops.geojson")
OUT = Path("data/osm/shapes_snapped.geojson")
MAX_LOC = 20            # trocear /route en chunks (límite conservador, como tp-routes)
COSTING = "auto"        # respeta sentidos de calle; Valhalla también tiene 'bus'


# ---------- polilínea Valhalla (precisión 6) ----------
def decode_polyline(encoded, precision=6):
    inv = 1.0 / (10 ** precision)
    coords, lat, lon, i = [], 0, 0, 0
    while i < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                b = ord(encoded[i]) - 63
                i += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if axis == 0:
                lat += d
            else:
                lon += d
        coords.append([round(lon * inv, 6), round(lat * inv, 6)])  # [lon,lat]
    return coords


def post(path, payload, retries=3):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{VALHALLA_URL}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                return json.load(e)         # Valhalla devuelve JSON de error con 400
            except Exception:
                if attempt == retries - 1:
                    return {"error": f"HTTP {e.code}"}
        except Exception as e:
            if attempt == retries - 1:
                return {"error": str(e)}
            time.sleep(1.5)


# ---------- paso 1: /route (troceado) ----------
def route_through(points):
    """points: [{'lat','lon'}]. Devuelve (coords[[lon,lat]], km) o {'error'}."""
    locs = [{"lat": p["lat"], "lon": p["lon"]} for p in points]
    coords, km = [], 0.0
    chunks = ([locs] if len(locs) <= MAX_LOC
              else [locs[i:i + MAX_LOC] for i in range(0, len(locs), MAX_LOC - 1)])
    for chunk in chunks:
        if len(chunk) < 2:
            continue
        d = post("/route", {"locations": chunk, "costing": COSTING,
                            "directions_options": {"units": "kilometers"}})
        if "error" in d:
            return {"error": d["error"]}
        for leg in d["trip"]["legs"]:
            dec = decode_polyline(leg["shape"])
            if coords:
                dec = dec[1:]               # quitar solape
            coords += dec
        km += d["trip"]["summary"]["length"]
    return {"coords": coords, "km": km}


# ---------- paso 2: /trace_attributes (way_ids) ----------
def trace_wayids(coords):
    """coords [[lon,lat]] -> (way_ids únicos, nombres de calle únicos)."""
    step = max(1, len(coords) // 100)
    sampled = [{"lat": c[1], "lon": c[0]} for c in coords[::step]]
    if sampled and (sampled[-1]["lat"], sampled[-1]["lon"]) != (coords[-1][1], coords[-1][0]):
        sampled.append({"lat": coords[-1][1], "lon": coords[-1][0]})
    d = post("/trace_attributes", {
        "shape": sampled, "costing": COSTING, "shape_match": "map_snap",
        "filters": {"attributes": ["edge.way_id", "edge.names", "edge.length"],
                    "action": "include"}})
    if "error" in d:
        return [], [], d["error"]
    way_ids, names, prev = [], [], None
    for e in d.get("edges", []):
        wid = e.get("way_id")
        if wid and wid != prev:
            way_ids.append(wid)
            prev = wid
        for nm in e.get("names", []):
            if nm not in names:
                names.append(nm)
    return way_ids, names, None


# ---------- agrupar paradas por ruta+sentido ----------
def load_groups(filter_ref=None):
    fc = json.loads(STOPS.read_text())
    groups = defaultdict(list)
    for f in fc["features"]:
        p = f["properties"]
        if filter_ref and p["route_ref"] != filter_ref:
            continue
        key = (p["route_ref"], p["route_name"], p.get("direction") or "")
        lon, lat = f["geometry"]["coordinates"]
        groups[key].append({"seq": p.get("stop_seq"), "lat": lat, "lon": lon,
                            "name": p.get("stop_name")})
    # ordenar cada grupo por secuencia (los None al final, preservando orden)
    for k in groups:
        groups[k].sort(key=lambda s: (s["seq"] is None, s["seq"] if s["seq"] is not None else 0))
    return groups


def main():
    filter_ref = sys.argv[1] if len(sys.argv) > 1 else None
    groups = load_groups(filter_ref)
    if not groups:
        print(f"Sin paradas para {filter_ref!r}.")
        return

    features = []
    print(f"VALHALLA_URL = {VALHALLA_URL}\n")
    for (ref, name, direction), stops in sorted(groups.items()):
        label = f"{ref} {name}" + (f" [{direction}]" if direction else "")
        if len(stops) < 2:
            print(f"⚠️  {label}: {len(stops)} parada(s), se omite (sin trazado posible)")
            continue
        r = route_through(stops)
        if "error" in r:
            print(f"❌ {label}: {r['error']}")
            continue
        way_ids, names, terr = trace_wayids(r["coords"])
        print(f"✅ {label}: {len(stops)} paradas → {r['km']:.2f} km · "
              f"{len(r['coords'])} pts · {len(way_ids)} ways OSM"
              + (f" · trace: {terr}" if terr else ""))
        if names:
            print(f"     calles: {', '.join(names[:6])}{' …' if len(names) > 6 else ''}")
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": r["coords"]},
            "properties": {
                "route_ref": ref, "route_name": name, "direction": direction,
                "n_stops": len(stops), "distance_km": round(r["km"], 3),
                "n_points": len(r["coords"]), "osm_way_ids": way_ids,
                "osm_streets": names,
            },
        })

    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                              ensure_ascii=False, indent=1))
    print(f"\n→ {OUT}  ({len(features)} trazado(s))")


if __name__ == "__main__":
    main()
