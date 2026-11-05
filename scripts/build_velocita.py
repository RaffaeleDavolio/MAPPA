"""Velocità commerciale prevista dagli orari SETA, tratto per tratto (fermata -> fermata successiva).

Uso:
    python3 scripts/build_velocita.py <feed.zip oppure cartella> data/velocita.js [AAAAMMGG]

AAAAMMGG è il giorno di riferimento (di default il primo martedì coperto dal feed).
Per ogni coppia di fermate consecutive calcola, per fascia oraria, la velocità mediana
prevista dagli orari: distanza lungo il percorso / (arrivo alla fermata B - partenza dalla fermata A).
"""
import csv, io, json, math, os, sys, zipfile, datetime
from collections import defaultdict

feed, out = sys.argv[1], sys.argv[2]
if feed.endswith(".zip"):
    _z = zipfile.ZipFile(feed)
    rd = lambda f: csv.DictReader(io.TextIOWrapper(_z.open(f), encoding="utf-8-sig"))
else:
    rd = lambda f: csv.DictReader(open(os.path.join(feed, f), encoding="utf-8-sig"))

BANDS = {"m": (7, 10), "g": (10, 16), "s": (16, 20)}   # mattina, giorno, sera; "t" = tutto il giorno
URBANE = {f"{i:02d}" for i in range(1, 15)}
NAVETTE = {"E", "E1", "E2", "G", "M"}
SCOLASTICHE = {"22", "23", "24", "25", "26", "30"}
def gruppo(s):
    return "urbana" if s in URBANE else "navetta" if s in NAVETTE else "scolastica" if s in SCOLASTICHE else "extraurbana"

# ---- giorno di riferimento
active_by_date = defaultdict(set)
for r in rd("calendar_dates.txt"):
    if r["exception_type"] == "1":
        active_by_date[r["date"]].add(r["service_id"])
try:
    for r in rd("calendar.txt"):
        pass  # il feed SETA usa solo calendar_dates
except KeyError:
    pass
if len(sys.argv) > 3:
    day = sys.argv[3]
else:
    day = next(d for d in sorted(active_by_date)
               if datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])).weekday() == 1)
services = active_by_date[day]

routes = {}
for r in rd("routes.txt"):
    s = r["route_short_name"].strip()
    c = (r.get("route_color") or "").upper()
    routes[r["route_id"]] = dict(n=s, name=r["route_long_name"].strip(), g=gruppo(s),
                                 c="#6A5ACD" if c in ("", "E6E6FA", "FFFFFF") else "#" + c)

trips = {}
for t in rd("trips.txt"):
    if t["service_id"] in services and t.get("shape_id"):
        trips[t["trip_id"]] = (t["route_id"], t["shape_id"])

stops = {s["stop_id"]: (float(s["stop_lat"]), float(s["stop_lon"]), s["stop_name"].strip().title())
         for s in rd("stops.txt")}

shapes = defaultdict(list)
need = {sh for _, sh in trips.values()}
for p in rd("shapes.txt"):
    if p["shape_id"] in need:
        shapes[p["shape_id"]].append((int(p["shape_pt_sequence"]), float(p["shape_pt_lat"]), float(p["shape_pt_lon"])))

def hav(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

shape_geo = {}
for sid, pts in shapes.items():
    pts.sort()
    P = [(la, lo) for _, la, lo in pts]
    cum = [0.0]
    for a, b in zip(P, P[1:]):
        cum.append(cum[-1] + hav(a, b))
    shape_geo[sid] = (P, cum)

def project(P, cum, pt, start):
    """Posizione lungo il percorso (metri) del punto più vicino a pt, cercando da start in avanti."""
    lat0 = math.radians(pt[0]); kx = 111320 * math.cos(lat0); ky = 110540
    px, py = pt[1] * kx, pt[0] * ky
    best = (1e18, start, 0.0)
    for i in range(start, len(P) - 1):
        ax, ay = P[i][1] * kx, P[i][0] * ky
        bx, by = P[i + 1][1] * kx, P[i + 1][0] * ky
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
        if d < best[0]:
            best = (d, i, t)
        elif d > best[0] + 4e6 and i > best[1] + 50:   # ormai lontani (>2 km): stop
            break
    d, i, t = best
    return i, cum[i] + t * (cum[i + 1] - cum[i]), math.sqrt(d)

def secs(t):
    h, m, s = map(int, t.split(":")); return h * 3600 + m * 60 + s

st = defaultdict(list)
for r in rd("stop_times.txt"):
    if r["trip_id"] in trips:
        st[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"], secs(r["arrival_time"]), secs(r["departure_time"])))

def simplify(line, tol=4):
    if len(line) < 3: return line
    lat0 = math.radians(line[0][0]); kx = 111320 * math.cos(lat0); ky = 110540
    Q = [(p[1] * kx, p[0] * ky) for p in line]
    keep = [False] * len(Q); keep[0] = keep[-1] = True
    stack = [(0, len(Q) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = Q[a], Q[b]
        dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1e-9
        dm, idx = 0, -1
        for i in range(a + 1, b):
            x, y = Q[i]; t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
            d = math.hypot(x - x1 - t * dx, y - y1 - t * dy)
            if d > dm: dm, idx = d, i
        if dm > tol: keep[idx] = True; stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(line, keep) if k]

seg_geom, seg_len = {}, {}
seg_speeds = defaultdict(lambda: defaultdict(list))   # key -> band -> [km/h]
seg_routes = defaultdict(set)
skipped = 0
for tid, rows in st.items():
    rid, sid = trips[tid]
    if sid not in shape_geo: continue
    P, cum = shape_geo[sid]
    rows.sort()
    pos, idx = [], 0
    for _, stop, arr, dep in rows:
        s = stops[stop]
        idx, d, off = project(P, cum, (s[0], s[1]), idx)
        pos.append((stop, d, off, idx, arr, dep))
    for (a, da, oa, ia, _, depa), (b, db, ob, ib, arrb, _) in zip(pos, pos[1:]):
        dist, dt = db - da, arrb - depa
        if dist < 30 or dt <= 0 or oa > 150 or ob > 150:
            skipped += 1; continue
        v = dist / dt * 3.6
        if not (1.5 <= v <= 110):
            skipped += 1; continue
        key = (a, b)
        if key not in seg_geom:
            line = [(stops[a][0], stops[a][1])] + P[ia + 1: ib + 1] + [(stops[b][0], stops[b][1])]
            seg_geom[key] = simplify(line)
            seg_len[key] = dist
        seg_routes[key].add(rid)
        h = depa / 3600
        seg_speeds[key]["t"].append(v)
        for band, (h0, h1) in BANDS.items():
            if h0 <= h < h1: seg_speeds[key][band].append(v)

def median(xs):
    xs = sorted(xs); n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

used_stops, segs = set(), []
for key, bands in seg_speeds.items():
    a, b = key
    used_stops.update(key)
    v = {band: [round(median(xs), 1), len(xs)] for band, xs in bands.items()}
    segs.append(dict(a=a, b=b, l=round(seg_len[key]), r=sorted(seg_routes[key]), v=v,
                     p=[[round(lo, 5), round(la, 5)] for la, lo in seg_geom[key]]))

data = dict(
    meta=dict(giorno=day, fonte="SETA S.p.A. via BusOne (GTFS)",
              fasce={"m": "7–10", "g": "10–16", "s": "16–20", "t": "Giornata"}),
    routes=routes,
    stops={s: [round(stops[s][0], 5), round(stops[s][1], 5), stops[s][2]] for s in used_stops},
    segs=segs)
with open(out, "w", encoding="utf-8") as fh:
    fh.write("window.VELOCITA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"giorno {day}: corse {len(st)}, tratti {len(segs)}, fermate {len(used_stops)}, scartati {skipped}")
