"""Step 2. The comparison panel: every town and city article in the Wikipedia lists of towns in England and Wales
and of UK cities that sits in England or Wales, with its fires, its size in 1377 and 1801 (where the historical
population tables list it), its size in 2021, its household income, its Domesday households and its oldest
listed buildings.

Reads (in place):
  _data10/wikipedia_towns_fires_rolls.json.gz  town articles (titles, coordinates, article length) (CC BY-SA 4.0)
  _data9/wikipedia_wikitext.json               "List of towns and cities in England by historical population" (CC BY-SA 4.0)
  _data10/wd_osm_bundle10.json.gz              wd_listed_top: Grade I, Grade II* and Category A listed buildings (Wikidata, CC0)
  osnames_gb.tsv                               OS Open Names (OGL v3)
  _data8/ons_geo.json, lsoa21_bua22_lookup.json, census/census2021-ts001-{lsoa,msoa}.csv, ons_msoa_income_fye2023.xlsx (ONS, OGL v3)
  domesday-destiny/data/domesday_places.csv    Hull Domesday Project via realm-domesday (CC BY-NC-SA)
  data/great_fires.csv                         from step 1

Writes:
  data/towns.csv               the panel (CC BY-SA 4.0 and OGL)
  data/towns_domesday1086.csv  Domesday households within 2.5 km of each town point (CC BY-NC-SA 4.0, kept apart)
"""
import csv
import gzip
import json
import math
import os
import re
from collections import Counter, defaultdict

import numpy as np
import openpyxl
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
OUT = os.path.join(ROOT, "data")
LAT0 = 53.0
KX, KY = 111.32 * math.cos(math.radians(LAT0)), 110.57


def xy(lon, lat):
    return (lon * KX, lat * KY)


d = json.load(gzip.open(f"{H}/_data10/wikipedia_towns_fires_rolls.json.gz"))
T = d["towns"]
req2title = {}
for t, v in T.items():
    req2title[v.get("requested") or t] = t
    req2title[t] = t
listed_in = defaultdict(set)
for k in ["List of towns in England", "List of towns in Wales", "List of cities in the United Kingdom"]:
    for r in d["town_lists"][k]:
        if r in req2title:
            listed_in[req2title[r]].add(k.replace("List of ", ""))

PLACE = re.compile(r"\b(town|city|village|parish|settlement|community|suburb|area of|port|resort|conurbation|capital|county town)\b", re.I)
NOTPLACE = re.compile(r"^(Region of|County of|Local authority|Local government|District|Act|Period|Sovereign|Ethnic|Anglican|Placename|Constituent|Ceremonial|Metropolitan county|Non-metropolitan county|Unitary authority|Former)", re.I)

# ---------------- OS Open Names
osn = defaultdict(list)
osall = []
with open(f"{H}/osnames_gb.tsv", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r["type"] == "populatedPlace" and r["local_type"] in ("City", "Town", "Village", "Suburban Area", "Hamlet", "Other Settlement") and r["country"] in ("England", "Wales"):
            osn[r["name1"]].append(r)
            if r["name2"]:
                osn[r["name2"]].append(r)
            if r["local_type"] in ("City", "Town", "Suburban Area"):
                osall.append(r)
ORDER = {"City": 0, "Town": 1, "Suburban Area": 2, "Village": 3, "Other Settlement": 4, "Hamlet": 5}
ostree = cKDTree(np.array([xy(float(r["lon"]), float(r["lat"])) for r in osall]))


def os_match(title, coord):
    name = title.split(",")[0].strip()
    hint = title.split(",")[1].strip() if "," in title else ""
    sd = T[title].get("shortdesc") or ""
    m = re.search(r" in (?:the )?([A-Z][A-Za-z' ]+?)(?:,| UK| England| Wales|$)", sd)
    hint2 = m.group(1).strip() if m else ""
    c = osn.get(name, [])
    if coord:
        c = [x for x in c if math.hypot(*(np.subtract(xy(float(x["lon"]), float(x["lat"])), xy(coord[1], coord[0])))) < 12]
    for h in (hint, hint2):
        if h and len(c) > 1:
            c2 = [x for x in c if h in (x["county"] + " " + x["district"] + " " + x["region"] + " " + x["populated_place"])]
            if c2:
                c = c2
                break
    c = sorted(c, key=lambda x: ORDER[x["local_type"]])
    return c[0] if c else None


# ---------------- fires
fires = list(csv.DictReader(open(os.path.join(OUT, "great_fires.csv"), encoding="utf-8")))
fire_by = defaultdict(list)
poss_by = defaultdict(list)
war_by = defaultdict(list)
for r in fires:
    {"great_fire": fire_by, "possible": poss_by, "war": war_by}[r["class"]][r["town_article"]].append(r)

# ---------------- historical population tables (parsing as in the canal-mania project, same source)
text = json.load(open(f"{H}/_data9/wikipedia_wikitext.json", encoding="utf-8"))[
    "List of towns and cities in England by historical population"]["text"]
hist = {}
for tb in re.findall(r"\{\|(.*?)\n\|\}", text, re.S):
    cap = re.search(r"\|\+\s*([^<\n]*)", tb)
    cap = cap.group(1).strip() if cap else ""
    key = {"1377": "1377", "1801": "1801"}.get(cap[:4])
    if not key:
        continue
    body = re.sub(r"<ref[^>]*/>", "", tb)
    body = re.sub(r"<ref.*?</ref>", "", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    rank = None
    for r in body.split("\n|-"):
        r = r.strip()
        m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", r)
        if not m or r.startswith(("!", "|+")):
            continue
        rk = re.match(r"\|\s*(?:rowspan=\d+\|)?\s*(\d+)\s*\|\|", r)
        if rk:
            rank = int(rk.group(1))
        num = re.search(r"\|\|\s*([\d,]+)", r[m.end():])
        val = int(num.group(1).replace(",", "")) if num else None
        title = m.group(1).strip()
        h = hist.setdefault(title, {})
        if val and (h.get("pop" + key) or 0) < val:
            h["pop" + key] = val
            h["rank" + key] = rank
HALIAS = {"Kingston upon Hull": "Kingston upon Hull", "Hull": "Kingston upon Hull", "Stoke-upon-Trent": "Stoke-on-Trent",
          "Preston, Lancashire": "Preston", "City of Preston, Lancashire": "Preston", "Bath, Somerset": "Bath",
          "Worcester, England": "Worcester, England", "Lincoln, England": "Lincoln, England"}
print("historical table towns", len(hist), "with 1377", sum(1 for h in hist.values() if "pop1377" in h),
      "with 1801", sum(1 for h in hist.values() if "pop1801" in h))

# ---------------- ONS: built-up areas, residents, income
geo = json.load(open(f"{H}/_data8/ons_geo.json", encoding="utf-8"))
bua = {b["BUA22CD"]: b for b in geo["bua22_gb"] if b["BUA22CD"][0] in "EW"}
lsoa_pop, msoa_pop = {}, {}
for fn, dd in (("lsoa", lsoa_pop), ("msoa", msoa_pop)):
    with open(f"{H}/_data8/census/census2021-ts001-{fn}.csv", encoding="utf-8") as f:
        for r in csv.reader(f):
            if r[0] == "2021":
                dd[r[2]] = int(r[3])
bua_pop = Counter()
for r in json.load(open(f"{H}/_data8/lsoa21_bua22_lookup.json", encoding="utf-8")):
    if r["BUA22CD"] and r["LSOA21CD"] in lsoa_pop:
        bua_pop[r["BUA22CD"]] += lsoa_pop[r["LSOA21CD"]]
inc = {}
ws = openpyxl.load_workbook(f"{H}/_data8/ons_msoa_income_fye2023.xlsx", read_only=True)["Total annual income"]
for i, r in enumerate(ws.iter_rows(values_only=True)):
    if i >= 4 and r[0] and isinstance(r[6], (int, float)):
        inc[r[0]] = r[6]
bua_w, bua_p = defaultdict(float), defaultdict(float)
for r in geo["msoa21_bua22_lookup"]:
    if r["BUA22CD"] and r["MSOA21CD"] in inc:
        p = msoa_pop.get(r["MSOA21CD"], 0)
        bua_w[r["BUA22CD"]] += inc[r["MSOA21CD"]] * p
        bua_p[r["BUA22CD"]] += p
pwc = [(m["MSOA21CD"], m["_x"], m["_y"]) for m in geo["msoa21_pwc"] if m["MSOA21CD"] in inc]
mtree = cKDTree(np.array([xy(x, y) for _, x, y in pwc]))
bua_by_name = defaultdict(list)
for b in bua.values():
    bua_by_name[b["BUA22NM"].split(" (")[0]].append(b)
btree_codes = list(bua)
btree = cKDTree(np.array([xy(bua[c]["LONG"], bua[c]["LAT"]) for c in btree_codes]))
london = [r for r in geo["msoa21_bua22_lookup"] if r["RGN22NM"] == "London"]
london_pop = sum(msoa_pop.get(r["MSOA21CD"], 0) for r in london)
london_inc = sum(inc[r["MSOA21CD"]] * msoa_pop.get(r["MSOA21CD"], 0) for r in london if r["MSOA21CD"] in inc) / london_pop
BUANAME = {"Brighton": "Brighton and Hove", "Hove": "Brighton and Hove", "Hull": "Kingston upon Hull"}

# ---------------- Domesday (households within 2.5 km of the town point)
dom = []
with open(f"{H}/domesday-destiny/data/domesday_places.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["lat"] and r["households1086"]:
            dom.append((float(r["lng"]), float(r["lat"]), float(r["households1086"]), r["name"]))
dtree = cKDTree(np.array([xy(x, y) for x, y, _, _ in dom]))
DOM_R = 2.5

# ---------------- top listed buildings with a date (Wikidata)
w = json.load(gzip.open(f"{H}/_data10/wd_osm_bundle10.json.gz"))["wd_listed_top"].split("\n")
lb = {}
for line in w[1:]:
    p = line.split("\t")
    if len(p) < 5:
        continue
    m = re.search(r"POINT\(([-\d.]+) ([-\d.]+)\)", p[3])
    if not m:
        continue
    qid = p[0].rsplit("/", 1)[-1].rstrip(">")
    yr = re.match(r"(-?\d{4})-", p[4])
    yr = int(yr.group(1)) if yr else None
    o = lb.setdefault(qid, {"lon": float(m.group(1)), "lat": float(m.group(2)), "years": set(), "des": set()})
    if yr:
        o["years"].add(yr)
    o["des"].add(p[2].rsplit("/", 1)[-1].rstrip(">"))
lbl = list(lb.values())
for o in lbl:
    o["year"] = min(o["years"]) if o["years"] else None
ltree = cKDTree(np.array([xy(o["lon"], o["lat"]) for o in lbl]))
LB_R = 1.0
print("listed buildings", len(lbl), "dated", sum(1 for o in lbl if o["year"]))

# ---------------- build the panel
rows, dom_rows, skipped = [], [], Counter()
NOLOC = []
for title, v in T.items():
    if title not in listed_in:
        continue
    sd = v.get("shortdesc") or ""
    if NOTPLACE.search(sd) or (sd and not PLACE.search(sd)):
        skipped["not a place"] += 1
        continue
    coord = (v["coord"]["lat"], v["coord"]["lon"]) if v.get("coord") else None
    o = os_match(title, coord)
    if coord is None and o is None:
        skipped["no location"] += 1
        NOLOC.append(title)
        continue
    lat, lon = coord if coord else (float(o["lat"]), float(o["lon"]))
    if o is None:
        dd, j = ostree.query(xy(lon, lat))
        if dd > 5:
            skipped["outside England and Wales"] += 1
            continue
        o = osall[j]
        osm = f"nearest OS town: {o['name1']}"
    else:
        osm = f"{o['name1']} ({o['local_type']}, {o['district'] or o['county']})"
    if title == "London":
        lat, lon = 51.50722, -0.1275
    region, country = o["region"], o["country"]
    if country not in ("England", "Wales"):
        skipped["outside England and Wales"] += 1
        continue
    r = {"town": title.split(",")[0], "article": title, "lists": "; ".join(sorted(listed_in[title])), "shortdesc": re.sub(r"\s*[\u2013\u2014]\s*", " to ", sd),
         "lat": round(lat, 5), "lon": round(lon, 5), "loc_source": "Wikipedia coordinate" if coord else "OS Open Names",
         "os_name": osm, "os_type": o["local_type"], "region": region, "country": country, "article_chars": v.get("len") or 0}
    # fires
    fg, fp, fw = fire_by.get(title, []), poss_by.get(title, []), war_by.get(title, [])
    yrs = sorted(int(x["year"]) for x in fg)
    r.update(n_great_fires=len(fg), burned=int(len(fg) > 0), fire_years=" ".join(map(str, yrs)),
             first_fire=yrs[0] if yrs else "", burned_1500_1899=int(any(1500 <= y <= 1899 for y in yrs)),
             burned_before_1801=int(any(y <= 1800 for y in yrs)), burned_1600_1799=int(any(1600 <= y <= 1799 for y in yrs)),
             n_possible_fires=len(fp), n_war_burnings=len(fw),
             max_houses_lost=max([int(x["houses_lost"]) for x in fg if x["houses_lost"]] or [0]) or "")
    # history tables
    h = hist.get(title) or hist.get(HALIAS.get(title, "")) or hist.get(title.split(",")[0]) or {}
    for k in ("pop1377", "rank1377", "pop1801", "rank1801"):
        r[k] = h.get(k, "")
    # 2021
    if title == "London":
        r.update(bua22cd="", bua22="Greater London (all London MSOAs)", bua_match="Greater London", pop2021=london_pop,
                 income_fye2023=round(london_inc), income_method="Greater London MSOAs")
    else:
        nm = BUANAME.get(title.split(",")[0], title.split(",")[0])
        c = [(math.dist(xy(b["LONG"], b["LAT"]), xy(lon, lat)), b) for b in bua_by_name.get(nm, [])]
        c = [x for x in c if x[0] < 8]
        if c:
            dist, b = min(c, key=lambda x: x[0])
            meth = "name match"
        else:
            dist, j = btree.query(xy(lon, lat))
            b = bua[btree_codes[j]]
            meth = "nearest BUA centroid" if dist < 2 else ""
        if meth:
            cd = b["BUA22CD"]
            r.update(bua22cd=cd, bua22=b["BUA22NM"], bua_match=meth, pop2021=bua_pop.get(cd, ""),
                     bua_area_km2=round(b["Shape__Area"] / 1e6, 2))
            if bua_p[cd]:
                r.update(income_fye2023=round(bua_w[cd] / bua_p[cd]), income_method="BUA: population-weighted MSOAs")
        if not r.get("income_fye2023"):
            dd, j = mtree.query(xy(lon, lat))
            if dd < 5:
                r.update(income_fye2023=round(inc[pwc[j][0]]), income_method=f"nearest MSOA {pwc[j][0]} ({dd:.1f} km)")
    # Domesday
    idx = dtree.query_ball_point(xy(lon, lat), DOM_R)
    dom_rows.append({"article": title, "dom_places_2_5km": len(idx), "dom_households_2_5km": round(sum(dom[i][2] for i in idx), 1),
                     "dom_place_names": "; ".join(sorted({dom[i][3] for i in idx}))[:300]})
    # listed buildings
    idx = ltree.query_ball_point(xy(lon, lat), LB_R)
    ys = [lbl[i]["year"] for i in idx if lbl[i]["year"] is not None]
    r.update(lb_top_1km=len(idx), lb_dated_1km=len(ys), lb_pre1600=sum(1 for y in ys if y < 1600),
             lb_1600_1699=sum(1 for y in ys if 1600 <= y < 1700), lb_1700_1837=sum(1 for y in ys if 1700 <= y <= 1837),
             lb_after1837=sum(1 for y in ys if y > 1837))
    rows.append(r)

print("panel", len(rows), dict(skipped))
print("no location sample:", NOLOC[:60])
cols = ["town", "article", "lists", "shortdesc", "lat", "lon", "loc_source", "os_name", "os_type", "region", "country", "article_chars",
        "burned", "n_great_fires", "fire_years", "first_fire", "burned_1500_1899", "burned_before_1801", "burned_1600_1799",
        "n_possible_fires", "n_war_burnings", "max_houses_lost", "pop1377", "rank1377", "pop1801", "rank1801",
        "bua22cd", "bua22", "bua_match", "bua_area_km2", "pop2021", "income_fye2023", "income_method",
        "lb_top_1km", "lb_dated_1km", "lb_pre1600", "lb_1600_1699", "lb_1700_1837", "lb_after1837"]
rows.sort(key=lambda r: r["article"])
with open(os.path.join(OUT, "towns.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    wr.writeheader()
    wr.writerows(rows)
with open(os.path.join(OUT, "towns_domesday1086.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(dom_rows[0].keys()))
    wr.writeheader()
    wr.writerows(sorted(dom_rows, key=lambda r: r["article"]))
pan = {r["article"] for r in rows}
miss = sorted({r["town_article"] for r in fires if r["class"] == "great_fire" and r["country"] in ("England", "Wales")} - pan)
print("great-fire towns not in the panel:", miss)
print("burned in panel", sum(r["burned"] for r in rows), "with pop2021", sum(1 for r in rows if r.get("pop2021")),
      "with income", sum(1 for r in rows if r.get("income_fye2023")))
print("1377:", sum(1 for r in rows if r["pop1377"]), "1801:", sum(1 for r in rows if r["pop1801"]))
json.dump({"panel_skipped": dict(skipped), "fire_towns_not_in_panel": miss, "dom_radius_km": DOM_R, "lb_radius_km": LB_R},
          open(os.path.join(OUT, "_towns_meta.json"), "w"))
