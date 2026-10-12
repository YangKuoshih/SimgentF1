"""Build data/circuit-layouts.json: the layout raced at every Grand Prix, and its shape.

Sources (pinned below, checked by SHA-256):
- F1DB (https://github.com/f1db/f1db, CC BY 4.0): for each race, the circuit layout, direction,
  course length, turns, laps, distance and fastest lap.
- f1-circuits-svg (https://github.com/MisterSix2295/f1-circuits-svg, MIT, (c) 2024-2025 Jules
  Roy): one SVG outline per layout, using F1DB's layout ids.

Our geographic outlines (bacinger/f1-circuits and OpenStreetMap) are kept for the layout each
one matches; they carry the real start/finish line. Every other layout gets its SVG outline,
scaled to F1DB's length and turned to F1DB's race direction. Its start/finish line is taken
from the venue's geographic outline when the two share that stretch of track, otherwise the
middle of the longest straight, and is marked approximate either way.

    uv run --with svgpathtools --with numpy --with defusedxml python scripts/build_circuit_layouts.py
"""

import csv
import glob
import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
import urllib.request
import zipfile
import defusedxml.ElementTree as ET  # third-party SVGs: no entity expansion
import numpy as np
from svgpathtools import parse_path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "circuit-layouts.json")

F1DB_TAG = "v2026.17.0"
F1DB_URL = f"https://github.com/f1db/f1db/releases/download/{F1DB_TAG}/f1db-csv.zip"
F1DB_SHA256 = "1c5c07d064e2988cb31a44206cc679662e0523a9bde0c191eed8ffc22831eec6"
SVG_COMMIT = None  # set by --svg-commit or resolved from the repository's main branch
SVG_REPO = "MisterSix2295/f1-circuits-svg"

# F1DB gives Indianapolis's circuit direction to both layouts; the Indy 500 oval (1950-60)
# runs anticlockwise (only the 2000-07 F1 road course ran clockwise)
DIRECTION_OVERRIDES = {"indianapolis-1": "ANTI_CLOCKWISE"}
# Start/finish lines that moved while the track stayed: before the Wing pits opened in 2011,
# Silverstone's line was on the old pit straight between Woodcote (T8) and Copse (T9) of the
# current layout. Applied to every layout up to that season, and per race on the current one.
START_BEFORE = {"silverstone": {"until": 2010, "between_turns": (8, 9)}}

N_SAMPLE = 1200
N_OUT = 360
GEO_FIT_MAX = 0.15          # loose shape check (SVG drawings are approximate); length decides


def fetch(url, sha256=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "simgent-build"}), timeout=120) as r:
        data = r.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"checksum mismatch for {url}")
    return data


def load_f1db(zip_bytes):
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    read = lambda name: list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8")))
    return {k: read(f"f1db-{k}.csv") for k in ("races", "circuits", "circuits-layouts", "races-fastest-laps", "drivers")}


def load_svgs(tar_bytes):
    """layout id -> (points y-down, as drawn), and the dataset's circuits.json"""
    tf = tarfile.open(fileobj=io.BytesIO(tar_bytes))
    shapes, circuits = {}, None
    for m in tf.getmembers():
        if m.name.endswith("/circuits.json"):
            circuits = json.load(tf.extractfile(m))
        mm = re.search(r"/circuits/black/([a-z0-9-]+)\.svg$", m.name)
        if mm:
            root = ET.fromstring(tf.extractfile(m).read())
            d = [e.get("d") for e in root.iter() if e.tag.endswith("path") and e.get("d")]
            # the longest continuous piece (one file has stray sub-paths drawn in the same path)
            path = max((sub for x in d for sub in parse_path(x).continuous_subpaths()), key=lambda p: p.length())
            pts = [path.point(i / N_SAMPLE) for i in range(N_SAMPLE)]
            shapes[mm.group(1)] = np.array([(z.real, z.imag) for z in pts])
    return shapes, circuits


def resample(P, n):
    P = np.asarray(P, float)
    Q = np.vstack([P, P[:1]])
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, seg[-1], n, endpoint=False)
    return np.c_[np.interp(t, seg, Q[:, 0]), np.interp(t, seg, Q[:, 1])], seg[-1]


def clockwise(P):
    """In y-down coordinates a positive shoelace sum is clockwise on screen."""
    x, y = P[:, 0], P[:, 1]
    return float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) > 0


def procrustes(A, B):
    """Best rotation+scale+cyclic shift of A onto B (same direction, no mirror).
    Returns (relative error, rotation matrix, scale, shift)."""
    A0, B0 = A - A.mean(0), B - B.mean(0)
    best = None
    for s in range(0, len(A), 2):
        As = np.roll(A0, -s, axis=0)
        U, S, Vt = np.linalg.svd(As.T @ B0)
        R = U @ Vt
        if np.linalg.det(R) < 0:
            continue
        sc = S.sum() / (As ** 2).sum()
        err = np.sqrt(((sc * As @ R - B0) ** 2).sum(1).mean() / (B0 ** 2).sum(1).mean())
        if best is None or err < best[0]:
            best = (err, R, sc, s)
    return best


def geo_points(feature):
    coords = feature["geometry"]["coordinates"]
    if feature["geometry"]["type"] == "MultiLineString":
        coords = max(coords, key=len)
    lat0 = sum(c[1] for c in coords) / len(coords)
    k = 111_320.0
    pts = [(c[0] * k * math.cos(math.radians(lat0)), -c[1] * k) for c in coords]  # metres, y-down (as race_replay)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return np.array(pts)


def longest_straight_start(P):
    """Index at the middle of the longest run of nearly straight track."""
    n = len(P)
    d1 = np.roll(P, -3, axis=0) - P
    d0 = P - np.roll(P, 3, axis=0)
    ang = np.abs(np.arctan2(d0[:, 0] * d1[:, 1] - d0[:, 1] * d1[:, 0], (d0 * d1).sum(1)))
    straight = ang < math.radians(4)
    best, run = (0, 0), None
    for i in range(2 * n):
        if straight[i % n]:
            run = i if run is None else run
            if i - run > best[1] - best[0] and i - run < n:
                best = (run, i)
        else:
            run = None
    return ((best[0] + best[1]) // 2) % n


def transfer_start(P_full, G_full, min_overlap=0.35):
    """Start/finish from geographic outline G (index 0 = start line) onto layout P when they share
    that stretch: trimmed ICP over a few starting rotations, then the nearest point if it lies on P.
    Returns an index into P_full."""
    P, _ = resample(P_full, 300)
    G, _ = resample(G_full, 300)
    best = None
    for rot in range(0, 360, 15):
        th = math.radians(rot)
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        Q = (P - P.mean(0)) @ R + G.mean(0)
        for _ in range(30):
            d = np.linalg.norm(Q[:, None, :] - G[None, :, :], axis=2)
            j = d.argmin(1)
            keep = d[np.arange(len(Q)), j] < np.percentile(d.min(1), 60)
            A, B = Q[keep], G[j[keep]]
            U, S, Vt = np.linalg.svd((A - A.mean(0)).T @ (B - B.mean(0)))
            Rk = U @ Vt
            if np.linalg.det(Rk) < 0:
                break
            Q = (Q - A.mean(0)) @ Rk + B.mean(0)
        dist = np.linalg.norm(Q[:, None, :] - G[None, :, :], axis=2).min(1)
        overlap = float((dist < 25).mean())
        if best is None or overlap > best[0]:
            best = (overlap, Q)
    overlap, Q = best
    i = int(np.linalg.norm(Q - G[0], axis=1).argmin())
    # The line's position is what transfers; the cars may run the other way (Indianapolis: the
    # oval and the F1 road course shared the main straight in opposite directions)
    if overlap >= min_overlap and np.linalg.norm(Q[i] - G[0]) < 25:
        return int(round(i / len(Q) * len(P_full))) % len(P_full), overlap
    return None, overlap


def start_frac(circuit, rule):
    """Lap fraction of a moved start line on the circuit's geographic outline: halfway between
    two of its stored corner positions."""
    from app.tools import race_replay as RR
    geo = RR.circuit_geometry(circuit)
    idx = {t["number"]: t["idx"] for t in geo["turns"]}
    a, b = (idx[t] for t in rule["between_turns"])
    n = len(geo["points"])
    return ((a + ((b - a) % n) / 2) % n) / n


def main():
    global SVG_COMMIT
    if "--svg-commit" in sys.argv:
        SVG_COMMIT = sys.argv[sys.argv.index("--svg-commit") + 1]
    if not SVG_COMMIT:
        SVG_COMMIT = json.loads(fetch(f"https://api.github.com/repos/{SVG_REPO}/commits/main"))["sha"]
    f1db = load_f1db(fetch(F1DB_URL, F1DB_SHA256))
    svg_tar = fetch(f"https://codeload.github.com/{SVG_REPO}/tar.gz/{SVG_COMMIT}")
    shapes, svg_circuits = load_svgs(svg_tar)
    print(f"F1DB {F1DB_TAG}: {len(f1db['races'])} races; f1-circuits-svg {SVG_COMMIT[:7]}: {len(shapes)} layouts")

    sys.path.insert(0, ROOT)
    from app.tools import race_replay as RR
    feats = RR._geo_features()

    drivers = {d["id"]: d for d in f1db["drivers"]}
    layout_len = {l["id"]: float(l["length"]) for l in f1db["circuits-layouts"]}
    layout_turns = {l["id"]: int(l["turns"]) for l in f1db["circuits-layouts"]}
    fastest = {(r["year"], r["round"]): r for r in f1db["races-fastest-laps"] if r["positionNumber"] == "1"}

    # Jolpica circuit id for each F1DB circuit, from races both sources agree on
    jolpica_of = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "cache", "jolpica", "*_schedule.json"))):
        year = int(os.path.basename(f)[:4])
        for race in json.load(open(f, encoding="utf-8"))["MRData"]["RaceTable"]["Races"]:
            row = next((r for r in f1db["races"] if int(r["year"]) == year and r["round"] == race["round"]), None)
            if row:
                jolpica_of.setdefault(row["circuitId"], race["Circuit"]["circuitId"])

    direction, years_of = {}, {}
    for r in f1db["races"]:
        r["direction"] = DIRECTION_OVERRIDES.get(r["circuitLayoutId"], r["direction"])
        direction.setdefault(r["circuitLayoutId"], r["direction"])
        years_of.setdefault(r["circuitLayoutId"], set()).add(int(r["year"]))

    # The two datasets number layouts differently (F1DB splits some that the SVG set doesn't, and
    # names Sochi "sirius"), so pair circuits by coordinates and layouts by the seasons they cover.
    f1db_circuits = {c["id"]: c for c in f1db["circuits"]}
    def km(a, b):
        la1, lo1, la2, lo2 = map(math.radians, a + b)
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 12742 * math.asin(math.sqrt(h))
    def seasons(text):
        out = set()
        for part in text.split(","):
            lo, _, hi = part.partition("-")
            out.update(range(int(lo), int(hi or lo) + 1))
        return out
    svg_layout = {}
    for lid, yrs in years_of.items():
        c = f1db_circuits[re.sub(r"-\d+$", "", lid)]
        sc = min(svg_circuits, key=lambda x: km((float(c["latitude"]), float(c["longitude"])), (x["latitude"], x["longitude"])))
        if km((float(c["latitude"]), float(c["longitude"])), (sc["latitude"], sc["longitude"])) > 5:
            continue
        votes = {l["layoutId"]: len(yrs & seasons(l["seasons"])) for l in sc["layouts"]}
        best = max(votes, key=votes.get)
        if votes[best] == 0:
            # seasons the SVG set doesn't list yet (it ends in 2025): the layout raced closest in time
            last = max(sc["layouts"], key=lambda l: max(seasons(l["seasons"])))
            best = last["layoutId"] if min(yrs) > max(seasons(last["seasons"])) else None
        if best and best not in shapes:
            # index typo upstream: "zandvoort" for the file zandvoort-5.svg
            numbered = sorted(k for k in shapes if re.fullmatch(re.escape(best) + r"-\d+", k))
            best = numbered[-1] if numbered else None
        if best:
            svg_layout[lid] = best

    def svg_shape(lid, n):
        S, _ = resample(shapes[svg_layout[lid]], n)
        return S

    # Which F1DB layout each geographic outline is: official length within 1%, closest length first
    geo_layout, geo_pts, venue_rotation = {}, {}, {}
    for f1_cid, jcid in jolpica_of.items():
        feat = feats.get(RR.CIRCUIT_MAP.get(jcid, ""))
        if not feat:
            continue
        G, measured = resample(geo_points(feat), N_OUT)
        geo_pts[f1_cid] = G
        official = (feat["properties"].get("length") or 0) / 1000
        measured /= 1000
        # The outline data's own length label can be stale (Madring: labelled 5.474 km, the
        # outline measures 5.414 km = F1DB's 5.416); compare whichever is closer
        dist = lambda lid: min(abs(official - layout_len[lid]), abs(measured - layout_len[lid]))
        cands = []
        for lid in years_of:
            if re.sub(r"-\d+$", "", lid) != f1_cid or dist(lid) / layout_len[lid] > 0.01:
                continue
            err = 0.0
            if lid in svg_layout:
                S = svg_shape(lid, N_OUT)
                if clockwise(S) != clockwise(G):
                    S = S[::-1]
                err = procrustes(S, G)[0]
            cands.append((err, lid))
        good = [c for c in cands if c[0] <= GEO_FIT_MAX]
        if good:
            # closest length decides (Albert Park 5.278 = 2022+, not 5.303); shape fit only
            # breaks ties within 3 m (Barcelona 4.655: 2007-20 vs 4.657: 2023+)
            closest = min(dist(l) for _, l in good)
            err, lid = min(c for c in good if dist(c[1]) <= closest + 0.003)
            geo_layout[lid] = {"circuit": jcid, "fit": round(err, 4)}
            if lid in svg_layout:
                # how the SVG set draws this venue relative to the map: applied to its other
                # layouts so a venue keeps one orientation across eras
                S = svg_shape(lid, N_OUT)
                flip = clockwise(S) != clockwise(G)
                venue_rotation[f1_cid] = (procrustes(S[::-1] if flip else S, G)[1])
        print(f"  {f1_cid:18} {official:.3f} km outline = {lid if good else 'no F1DB layout'}"
              f"{'  ' + str([(l, round(e, 3)) for e, l in cands]) if cands else ''}")

    layouts, transferred = {}, {}  # venue -> [(last season, points from the start line)]
    for lid in sorted(years_of, key=lambda l: (re.sub(r"-\d+$", "", l), min(years_of[l]))):
        f1_cid = re.sub(r"-\d+$", "", lid)
        entry = {"length_km": layout_len.get(lid), "turns": layout_turns.get(lid), "direction": direction[lid],
                 "circuit": jolpica_of.get(f1_cid), "years": [min(years_of[lid]), max(years_of[lid])]}
        if lid in geo_layout:
            entry.update(shape="geographic", **geo_layout[lid])
            layouts[lid] = entry
            continue
        if lid not in svg_layout:
            entry.update(shape=None)
            layouts[lid] = entry
            print(f"  {lid}: no outline in either source")
            continue
        P, plen = resample(shapes[svg_layout[lid]], N_SAMPLE)
        P = P * (layout_len[lid] * 1000 / plen)  # SVG units -> metres
        frame = "drawing"
        if f1_cid in venue_rotation:
            P = (P - P.mean(0)) @ venue_rotation[f1_cid]
            frame = "geographic"
        if clockwise(P) != (direction[lid] == "CLOCKWISE"):
            P = P[::-1]
        start, how = None, "longest straight"
        G = geo_pts.get(f1_cid)
        if G is not None:
            Gd, _ = resample(G, N_SAMPLE)
            rule = START_BEFORE.get(jolpica_of.get(f1_cid, ""))
            ruled = bool(rule and max(years_of[lid]) <= rule["until"])
            if ruled:
                Gd = np.roll(Gd, -int(round(start_frac(jolpica_of[f1_cid], rule) * len(Gd))), axis=0)
            i, overlap = transfer_start(P, Gd, min_overlap=0.25 if ruled else 0.35)
            if i is not None:
                start, how = i, "shared with the geographic outline"
        if start is None:
            # from an earlier layout of the venue whose start line was itself transferred
            for _, sib in sorted(transferred.get(f1_cid, []), key=lambda t: -t[0]):
                i, overlap = transfer_start(P, sib)
                if i is not None:
                    start, how = i, "shared with an earlier layout"
                    break
        if start is None:
            start = longest_straight_start(P)
        P = np.roll(P, -start, axis=0)
        if how.startswith("shared"):
            transferred.setdefault(f1_cid, []).append((max(years_of[lid]), P.copy()))
        P, _ = resample(P, N_OUT)
        entry.update(shape="svg", svg_layout=svg_layout[lid], start_line=how, frame=frame,
                     points=[[round(float(x), 1), round(float(y), 1)] for x, y in P])
        layouts[lid] = entry

    races = {}
    for r in f1db["races"]:
        fl = fastest.get((r["year"], r["round"]))
        d = drivers.get(fl["driverId"]) if fl else None
        key = f"{r['year']}_{r['round']}"
        races[key] = {
            "layout": r["circuitLayoutId"], "direction": r["direction"], "length_km": float(r["courseLength"]),
            "turns": int(r["turns"]), "laps": int(r["laps"]) if r["laps"] else None,
            "distance_km": float(r["distance"]) if r["distance"] else None,
            "fastest_lap": {"time": fl["time"], "driver": f"{d['firstName']} {d['lastName']}" if d else fl["driverId"],
                            "lap": int(fl["lap"]) if fl["lap"] else None} if fl else None,
        }
        lay = layouts.get(r["circuitLayoutId"], {})
        rule = START_BEFORE.get(lay.get("circuit") or "")
        if lay.get("shape") == "geographic" and rule and int(r["year"]) <= rule["until"]:
            races[key]["start_frac"] = round(start_frac(lay["circuit"], rule), 4)

    out = {
        "sources": {
            "f1db": {"release": F1DB_TAG, "license": "CC-BY-4.0", "url": "https://github.com/f1db/f1db"},
            "f1-circuits-svg": {"commit": SVG_COMMIT, "license": "MIT", "copyright": "(c) 2024-2025 Jules Roy",
                                "url": f"https://github.com/{SVG_REPO}"},
        },
        "layouts": layouts,
        "races": races,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    shapes_used = sum(1 for l in layouts.values() if l["shape"] == "svg")
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(races)} races, {len(layouts)} layouts "
          f"({sum(1 for l in layouts.values() if l['shape'] == 'geographic')} geographic, {shapes_used} from SVG, "
          f"{sum(1 for l in layouts.values() if not l['shape'])} without an outline); "
          f"start line shared for {sum(1 for l in layouts.values() if l.get('start_line', '').startswith('shared'))}")


if __name__ == "__main__":
    main()
