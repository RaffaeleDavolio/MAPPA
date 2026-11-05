"""Converte il feed GTFS SETA Reggio Emilia nel file data/seta.js usato dalla mappa.

Uso:
    python3 scripts/build_seta.py <feed.zip oppure cartella> data/seta.js
"""
import csv, json, sys, math, io, zipfile, os
from collections import defaultdict, Counter

feed, out = sys.argv[1], sys.argv[2]
if feed.endswith(".zip"):
    _z = zipfile.ZipFile(feed)
    rd = lambda f: csv.DictReader(io.TextIOWrapper(_z.open(f), encoding="utf-8-sig"))
else:
    rd = lambda f: csv.DictReader(open(os.path.join(feed, f), encoding="utf-8-sig"))

URBANE = {f"{i:02d}" for i in range(1, 15)}
NAVETTE = {"E", "E1", "E2", "G", "M"}
SCOLASTICHE = {"22", "23", "24", "25", "26", "30"}
def gruppo(short):
    if short in URBANE: return "urbana"
    if short in NAVETTE: return "navetta"
    if short in SCOLASTICHE: return "scolastica"
    return "extraurbana"

def color(c, short):
    c = (c or "").upper()
    # colori troppo chiari per una mappa chiara (lavanda delle navette centro)
    if not c or c in {"E6E6FA", "FFFFFF"}: return "#6A5ACD"
    return "#" + c

routes = {}
for r in rd("routes.txt"):
    s = r["route_short_name"].strip()
    routes[r["route_id"]] = dict(id=r["route_id"], n=s, name=r["route_long_name"].strip(),
                                 c=color(r.get("route_color"), s), g=gruppo(s))

trip_route, shape_count = {}, Counter()
for t in rd("trips.txt"):
    trip_route[t["trip_id"]] = t["route_id"]
    if t.get("shape_id"):
        shape_count[(t["route_id"], t.get("direction_id", "0"), t["shape_id"])] += 1
trips_per_route = Counter(trip_route.values())

# shape più usata per linea e direzione
best = {}
for (rid, d, sid), n in shape_count.items():
    k = (rid, d)
    if k not in best or n > best[k][1]: best[k] = (sid, n)
wanted = {sid for sid, _ in best.values()}

pts = defaultdict(list)
for p in rd("shapes.txt"):
    if p["shape_id"] in wanted:
        pts[p["shape_id"]].append((int(p["shape_pt_sequence"]), float(p["shape_pt_lat"]), float(p["shape_pt_lon"])))

def simplify(line, tol):
    # Douglas-Peucker in metri (proiezione equirettangolare locale)
    if len(line) < 3: return line
    lat0 = math.radians(line[0][0]); kx = 111320 * math.cos(lat0); ky = 110540
    P = [(p[1] * kx, p[0] * ky) for p in line]
    keep = [False] * len(P); keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = P[a], P[b]
        dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1e-9
        dmax, idx = 0, -1
        for i in range(a + 1, b):
            x, y = P[i]
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
            d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
            if d > dmax: dmax, idx = d, i
        if dmax > tol:
            keep[idx] = True; stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(line, keep) if k]

lines = []
for (rid, d), (sid, n) in sorted(best.items()):
    seq = [(la, lo) for _, la, lo in sorted(pts[sid])]
    simp = simplify(seq, 6)
    lines.append(dict(r=rid, d=int(d or 0), p=[[round(a, 5), round(b, 5)] for a, b in simp]))

# fermate con le linee che le servono
stop_routes = defaultdict(set)
for st in rd("stop_times.txt"):
    rid = trip_route.get(st["trip_id"])
    if rid: stop_routes[st["stop_id"]].add(rid)

order = lambda rid: (len(routes[rid]["n"]) > 2 or not routes[rid]["n"].isdigit(), routes[rid]["n"].zfill(3))
stops = []
for s in rd("stops.txt"):
    rs = stop_routes.get(s["stop_id"])
    if not rs: continue
    stops.append([round(float(s["stop_lat"]), 5), round(float(s["stop_lon"]), 5),
                  s["stop_name"].strip().title(), sorted(rs, key=order)])

info = next(rd("feed_info.txt"))
data = dict(
    meta=dict(fonte="SETA S.p.A. via BusOne (GTFS)", validita=[info["feed_start_date"], info["feed_end_date"]]),
    routes={k: dict(v, t=trips_per_route[k]) for k, v in routes.items()},
    lines=lines, stops=stops)
with open(out, "w", encoding="utf-8") as fh:
    fh.write("window.SETA_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"linee {len(routes)}, percorsi {len(lines)}, punti {sum(len(l['p']) for l in lines)}, fermate {len(stops)}")
