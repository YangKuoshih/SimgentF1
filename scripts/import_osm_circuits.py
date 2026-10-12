"""Build data/osm-circuits.geojson: outlines from OpenStreetMap for F1 circuits that
bacinger/f1-circuits does not cover.

For each circuit, the race-track ways (highway=raceway, pit lanes left out) near the circuit
are joined into a graph and the closed loop whose length matches the official F1 layout is
kept. The loop starts at the start/finish line (the point nearest the pit lane) and runs in
the race direction. A loop more than 1% off the official length is rejected.

The output is derived from OpenStreetMap data, (c) OpenStreetMap contributors, and is
licensed under the Open Database License (ODbL) 1.0: see data/OSM-LICENSE.md.

Historic road circuits (ROAD_CIRCUITS) were public roads, not race tracks, so they are traced
instead: the lap is routed over today's roads through waypoints taken from the layout's
diagram, using the road data from the OpenStreetMap API.

    python scripts/import_osm_circuits.py              # query the Overpass API
    python scripts/import_osm_circuits.py --from DIR   # reuse saved Overpass responses
    python scripts/import_osm_circuits.py --only reims # rebuild some circuits, keep the rest
"""

import collections
import datetime
import heapq
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "osm-circuits.geojson")
OVERPASS = "https://overpass-api.de/api/interpreter"

# Jolpica circuitId: official length of the F1 layout (km), race direction, and the
# season whose schedule gives the circuit's coordinates. Not imported (they stay labelled
# schematics): Valencia's street circuit is not mapped as a race track, and Buddh has no pit
# lane in OpenStreetMap to place the start/finish line.
CIRCUITS = {
    "jerez": {"length_km": 4.428, "clockwise": True, "year": 1997, "firstgp": 1986},
    "fuji": {"length_km": 4.563, "clockwise": True, "year": 2008, "firstgp": 1976},
    "yeongam": {"length_km": 5.615, "clockwise": False, "year": 2013, "firstgp": 2010},
}
MAX_LENGTH_ERROR = 0.01

# Historic circuits on public roads. Waypoints (lat, lon, road ref or name the point must snap
# to) follow the layout's diagram in race direction from the start/finish line. Routing between
# them prefers the circuit's roads ("roads"); where a junction of the period was later replaced
# (Reims' Garenne corner, demolished when the RN31 became a dual carriageway), the circuit's
# roads are joined where they pass within JOIN_M of each other.
ROAD_CIRCUITS = {
    # Reims-Gueux 1926-1951 (French GP 1950-51): pits on the D27, through the centre of Gueux,
    # north past La Hovette (D26) to the Garenne corner, the RN31 to the Thillois hairpin and
    # back on the D27. https://en.wikipedia.org/wiki/Reims-Gueux (layout 1926-1951, 7.826 km)
    "reims": {
        "length_km": 7.826, "firstgp": 1950, "layout": "1926-1951",
        "name": "Reims-Gueux", "locality": "Gueux",
        "bbox": (3.89, 49.24, 3.975, 49.285),  # min lon, min lat, max lon, max lat
        "roads": ("D 27", "D 26", "N 31"),
        "waypoints": [
            (49.25434, 3.93165, "D 27"),   # start/finish, at the grandstand (OSM way 870242942)
            (49.2506, 3.9100, "D 27"),     # into Gueux
            (49.2556, 3.9095, None),       # Gueux corner, north out of the village
            (49.2620, 3.9125, "D 26"),     # La Hovette
            (49.2668, 3.9185, "D 26"),     # up to the Garenne corner
            (49.2660, 3.9260, "N 31"),     # RN31
            (49.2600, 3.9480, "N 31"),     # into the Thillois hairpin
            (49.2585, 3.9460, "D 27"),     # out of Thillois on the D27
        ],
        # The diagram's 7.826 km is the published figure; today's roads (and the rebuilt
        # Garenne corner) trace about 3% shorter. Larger gaps mean a waypoint snapped wrongly.
        "max_length_error": 0.05,
    },
}
OSM_API = "https://api.openstreetmap.org/api/0.6"
NOT_ROADS = {"motorway", "motorway_link", "footway", "path", "cycleway", "steps", "pedestrian",
             "bridleway", "construction", "proposed", "platform", "corridor"}
JOIN_M = 35


def haversine(a, b):
    r = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def circuit_info(cid, year):
    with open(os.path.join(ROOT, "data", "cache", "jolpica", f"{year}_schedule.json"), encoding="utf-8") as f:
        races = json.load(f)["MRData"]["RaceTable"]["Races"]
    return next(r["Circuit"] for r in races if r["Circuit"]["circuitId"] == cid)


def fetch(lat, lon):
    query = f'[out:json][timeout:90];way["highway"="raceway"](around:3500,{lat},{lon});out body geom;'
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode(),
                                 headers={"User-Agent": "simgent-circuit-import (github.com/YangKuoshih/SimgentF1)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except OSError:
            time.sleep(30 * (attempt + 1))
    raise RuntimeError("Overpass API unavailable")


def fetch_roads(bbox):
    """Ways and nodes in a bounding box from the OpenStreetMap API (Overpass isn't needed)."""
    url = f"{OSM_API}/map.json?bbox={','.join(str(v) for v in bbox)}"
    req = urllib.request.Request(url, headers={"User-Agent": "simgent-circuit-import (github.com/YangKuoshih/SimgentF1)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.load(resp)
        except OSError:
            time.sleep(30 * (attempt + 1))
    raise RuntimeError("OpenStreetMap API unavailable")


def trace_road_loop(data, spec):
    """The lap routed over the road graph through the circuit's waypoints: (length m, points, way ids)."""
    nodes = {e["id"]: (e["lat"], e["lon"]) for e in data["elements"] if e["type"] == "node"}
    ways = [e for e in data["elements"] if e["type"] == "way"
            and e.get("tags", {}).get("highway") and e["tags"]["highway"] not in NOT_ROADS]
    label = lambda w: w["tags"].get("ref") or w["tags"].get("name")
    adj = collections.defaultdict(list)  # node -> [(next, cost, way id)]
    for w in ways:
        # Prefer the circuit's own roads; other public roads only where the lap left them
        cost = 1.0 if w["tags"].get("ref") in spec["roads"] else 1.3
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            if a in nodes and b in nodes:
                d = haversine(nodes[a], nodes[b])
                adj[a].append((b, d * cost, w["id"]))
                adj[b].append((a, d * cost, w["id"]))
    main = sorted({n for w in ways if w["tags"].get("ref") in spec["roads"] for n in w["nodes"] if n in nodes})
    for i, a in enumerate(main):
        for b in main[i + 1:]:
            d = haversine(nodes[a], nodes[b])
            if 0 < d < JOIN_M:
                adj[a].append((b, d, None))
                adj[b].append((a, d, None))

    def snap(lat, lon, road):
        cands = [n for w in ways if road is None or label(w) == road for n in w["nodes"] if n in nodes]
        return min(cands, key=lambda n: haversine(nodes[n], (lat, lon)))

    def route(a, b):
        dist, prev, queue = {a: 0.0}, {}, [(0.0, a)]
        while queue:
            c, u = heapq.heappop(queue)
            if u == b:
                break
            if c > dist[u]:
                continue
            for v, w, way in adj[u]:
                if c + w < dist.get(v, float("inf")):
                    dist[v], prev[v] = c + w, (u, way)
                    heapq.heappush(queue, (c + w, v))
        path, used = [b], set()
        while path[-1] != a:
            u, way = prev[path[-1]]
            path.append(u)
            used.add(way)
        return path[::-1], used

    stops = [snap(*wp) for wp in spec["waypoints"]]
    loop, used = [], set()
    for a, b in zip(stops, stops[1:] + stops[:1]):
        path, ways_used = route(a, b)
        loop += path[:-1]
        used |= ways_used
    points = [nodes[n] for n in loop]
    length = sum(haversine(p, q) for p, q in zip(points, points[1:] + points[:1]))
    return length, points, sorted(w for w in used if w is not None)


def is_pit(way):
    tags = way.get("tags", {})
    return "pit" in (tags.get("name") or "").lower() or tags.get("service") or tags.get("raceway") in ("pit_lane", "karting")


def best_loop(ways, target_m):
    coords, adj = {}, collections.defaultdict(list)
    track = [w for w in ways if not is_pit(w)]
    for w in track:
        for n, g in zip(w["nodes"], w["geometry"]):
            coords[n] = (g["lat"], g["lon"])
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            adj[a].append(b)
            if w.get("tags", {}).get("oneway") != "yes":
                adj[b].append(a)
    # Compress to junctions: the search then runs over a few dozen edges, not thousands of nodes
    neighbours = collections.defaultdict(set)
    for a, outs in adj.items():
        for b in outs:
            neighbours[a].add(b)
            neighbours[b].add(a)
    # Way start nodes count as junctions too, so a closed way with no branches (a karting
    # loop, or the whole circuit as one way) still has a point to start and stop at
    junctions = {n for n in neighbours if len(neighbours[n]) != 2} | {w["nodes"][0] for w in track}
    edges = collections.defaultdict(list)  # junction -> [(next junction, nodes in between + end, length)]
    for j in junctions:
        for nxt in adj[j]:
            chain, prev, cur, length = [], j, nxt, haversine(coords[j], coords[nxt])
            while cur not in junctions and len(chain) < len(coords):
                chain.append(cur)
                step = [n for n in adj[cur] if n != prev]
                if not step:
                    break
                prev, cur = cur, step[0]
                length += haversine(coords[prev], coords[cur])
            if cur in junctions:
                edges[j].append((cur, chain + [cur], length))
    best, budget = None, 2_000_000  # two-way service roads make the loop count explode
    for start in junctions:
        stack = [(start, [start], 0.0, {start})]
        while stack and budget > 0:
            budget -= 1
            node, path, length, seen = stack.pop()
            for nxt, chain, step in edges[node]:
                total = length + step
                if total > target_m * 1.08:
                    continue
                if nxt == start:
                    if best is None or abs(total - target_m) < abs(best[0] - target_m):
                        best = (total, path + chain[:-1])
                elif nxt not in seen:
                    stack.append((nxt, path + chain, total, seen | {nxt}))
    if best is None:
        return None, None
    return best[0], [coords[n] for n in best[1]]


PIT_NEAR_M = 70


def densify(points, step_m=10.0, closed=True):
    """Points every step_m metres or less: OSM draws a straight with only a few nodes."""
    out = []
    pairs = zip(points, points[1:] + points[:1]) if closed else zip(points, points[1:])
    for a, b in pairs:
        k = max(1, int(haversine(a, b) // step_m))
        out.extend((a[0] + (b[0] - a[0]) * t / k, a[1] + (b[1] - a[1]) * t / k) for t in range(k))
    if not closed:
        out.append(points[-1])
    return out


def orient(points, ways, clockwise):
    """Run in race direction from the start/finish line: the middle of the longest stretch
    of track that the pit lane runs alongside. None when OSM has no pit lane to place it."""
    # Shoelace on lon/lat: negative area means clockwise
    area = sum(a[1] * b[0] - b[1] * a[0] for a, b in zip(points, points[1:] + points[:1]))
    if (area < 0) != clockwise:
        points = points[::-1]
    pit_ways = [w for w in ways if is_pit(w)]
    # Korea has a permanent pit lane and a separate "GP Pit Lane"; the F1 start line is on the GP one
    gp = [w for w in pit_ways if re.search(r"\b(gp|f1|grand prix)\b", (w.get("tags", {}).get("name") or "").lower())]
    pit = [p for w in (gp or pit_ways)
           for p in densify([(g["lat"], g["lon"]) for g in w["geometry"]], closed=False)]
    if not pit:
        return None
    points = densify(points)
    near = [min(haversine(p, q) for q in pit) < PIT_NEAR_M for p in points]
    n, best, run = len(points), (0, 0), None
    for i in range(2 * n):  # twice round, so a stretch across the loop's end is one run
        if near[i % n]:
            run = run if run is not None else i
            length = i - run
            if length > best[1] - best[0] and length < n:
                best = (run, i)
        else:
            run = None
    mid = ((best[0] + best[1]) // 2) % n
    return points[mid:] + points[:mid]


def road_circuit_feature(cid, spec):
    data = fetch_roads(spec["bbox"])
    target = spec["length_km"] * 1000
    length, points, way_ids = trace_road_loop(data, spec)
    if abs(length - target) / target > spec["max_length_error"]:
        print(f"{cid}: traced {length / 1000:.3f} km, more than {spec['max_length_error']:.0%} off "
              f"{spec['length_km']} km; skipped")
        return None
    points = densify(points)
    coords = [[round(p[1], 6), round(p[0], 6)] for p in points + points[:1]]
    lons, lats = [c[0] for c in coords], [c[1] for c in coords]
    print(f"{cid}: traced {length / 1000:.3f} km along roads (official {spec['length_km']}), {len(points)} points")
    return {
        "type": "Feature",
        "properties": {
            "id": f"osm-{cid}", "Name": spec["name"], "Location": spec["locality"],
            "length": int(round(target)), "measured_length": int(round(length)), "firstgp": spec["firstgp"],
            "layout": spec["layout"], "traced_along_roads": True,
            "source": "OpenStreetMap", "osm_timestamp": data.get("timestamp"),
            "osm_ways": way_ids,
        },
        "bbox": [min(lons), min(lats), max(lons), max(lats)],
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def main():
    saved = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else None
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    features, kept = [], {}
    if only and os.path.exists(OUT):  # keep the circuits not being rebuilt, in their place
        with open(OUT, encoding="utf-8") as f:
            kept = {x["properties"]["id"].removeprefix("osm-"): x for x in json.load(f)["features"]}
    for cid, spec in CIRCUITS.items():
        if only and cid not in only:
            if cid in kept:
                features.append(kept[cid])
            continue
        circ = circuit_info(cid, spec["year"])
        lat, lon = float(circ["Location"]["lat"]), float(circ["Location"]["long"])
        if saved:
            with open(os.path.join(saved, f"{cid}.json"), encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = fetch(lat, lon)
            time.sleep(10)
        ways = data["elements"]
        target = spec["length_km"] * 1000
        length, points = best_loop(ways, target)
        if not points or abs(length - target) / target > MAX_LENGTH_ERROR:
            print(f"{cid}: no loop within {MAX_LENGTH_ERROR:.0%} of {spec['length_km']} km (best {length}); skipped")
            continue
        points = orient(points, ways, spec["clockwise"])
        if points is None:
            print(f"{cid}: no pit lane in OpenStreetMap to place the start/finish line; skipped")
            continue
        coords = [[round(p[1], 6), round(p[0], 6)] for p in points + points[:1]]
        lons, lats = [c[0] for c in coords], [c[1] for c in coords]
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"osm-{cid}", "Name": circ["circuitName"], "Location": circ["Location"]["locality"],
                "length": int(round(target)), "measured_length": int(round(length)), "firstgp": spec["firstgp"],
                "source": "OpenStreetMap", "osm_timestamp": data.get("osm3s", {}).get("timestamp_osm_base"),
                "osm_ways": sorted(w["id"] for w in ways if not is_pit(w)),
            },
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
            "geometry": {"type": "LineString", "coordinates": coords},
        })
        print(f"{cid}: {length / 1000:.3f} km (official {spec['length_km']}), {len(points)} points")
    for cid, spec in ROAD_CIRCUITS.items():
        if only and cid not in only:
            if cid in kept:
                features.append(kept[cid])
            continue
        feature = road_circuit_feature(cid, spec)
        if feature:
            features.append(feature)
    collection = {
        "type": "FeatureCollection", "name": "osm-circuits",
        "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
        "source": "https://www.openstreetmap.org/copyright",
        "generated": datetime.date.today().isoformat(),
        "features": features,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(features)} circuits)")


if __name__ == "__main__":
    main()
