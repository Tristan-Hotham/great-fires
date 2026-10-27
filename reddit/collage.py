"""r/dataisbeautiful collage for Great Fires. Every number comes from ../data/results.json and the data files.
Usage: cd reddit && python3 collage.py [font_dir]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
F = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(F + f)
DISP = fm.FontProperties(fname=F + "FrauncesVar.ttf", weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, LAND, EDGE = "#EEEAE4", "#1A1614", "#6A625B", "#DCD5CB", "#C2B8AC"
EMBER, CHAR, SLATE = "#D9480F", "#2A1A12", "#7B838C"
CEN = [(1500, "#A8998B"), (1600, "#EDB458"), (1700, "#E2702A"), (1800, "#B8360E"), (9999, "#5E1C08")]


def ccol(y):
    return next(c for lim, c in CEN if y < lim)


R = json.load(open(os.path.join(D, "results.json")))
Fi = pd.read_csv(os.path.join(D, "great_fires.csv"))
G = Fi[(Fi["class"] == "great_fire") & Fi.lat.notna()]
P = pd.read_csv(os.path.join(D, "towns.csv"))
MP = pd.read_csv(os.path.join(D, "matched_pairs.csv"))
rc, mt, md = R["record"], R["matched"], R["models"]

K = np.cos(np.radians(53.5))
land = []
for ft in json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_land.geojson"))["features"]:
    g = ft["geometry"]
    for pl in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
        r = np.array(pl[0])
        if r[:, 0].max() > -11 and r[:, 0].min() < 3 and r[:, 1].max() > 49 and r[:, 1].min() < 61:
            land.append(r)

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.968, "When England's towns burned", fontproperties=DISP, fontsize=46, color=FG, va="top")
fig.text(0.04, 0.917, f"Did the towns that burned rebuild bigger? I read every fire in Wikipedia's English and Welsh\n"
         f"town articles: {rc['great_fires']} great town fires, {rc['first_year']} to {rc['last_year']}. "
         f"Circles sized by houses lost, coloured by century.", family=SER, fontsize=15.5, color=FG, va="top", linespacing=1.35)

# ---------------- hero map
ax = fig.add_axes([0.0, 0.30, 0.58, 0.565])
for r in land:
    ax.add_patch(Polygon(np.c_[r[:, 0] * K, r[:, 1]], closed=True, fc=LAND, ec=EDGE, lw=0.6, zorder=0))
u = P[P.burned == 0]
ax.scatter(u.lon * K, u.lat, s=2.2, c=SLATE, alpha=0.35, lw=0, zorder=1)
g = G.sort_values("houses_lost", ascending=False, na_position="last")
sz = np.where(g.houses_lost.notna(), np.clip(np.sqrt(g.houses_lost.fillna(0)) * 11, 40, 1500), 30)
cols = [ccol(y) for y in g.year]
for k, a in [(3.2, 0.07), (2.0, 0.12)]:  # ember glow
    ax.scatter(g.lon * K, g.lat, s=sz * k, c=cols, alpha=a, lw=0, zorder=2)
ax.scatter(g.lon * K, g.lat, s=sz, c=cols, alpha=0.95, edgecolors=BG, linewidths=0.7, zorder=3)
for t, y, dx, dy, ha in [("London", 1666, 0.3, -0.4, "left"), ("Northampton", 1675, 0.1, 0.78, "center"), ("Warwick", 1694, -0.35, -0.1, "right"),
                         ("Blandford", 1731, -0.1, -0.42, "right"), ("Tiverton", 1731, -0.45, 0.5, "right"), ("Norwich", 1507, 0.0, 0.45, "center"),
                         ("Wem", 1677, -0.35, 0.2, "right")]:
    r = G[(G.town.str.startswith(t)) & (G.year == y)].iloc[0]
    hl = f"\n{int(r.houses_lost):,} {r.houses_unit}" if not pd.isna(r.houses_lost) else ""
    ax.annotate(f"{t} {y}{hl}", (r.lon * K, r.lat), xytext=(r.lon * K + dx, r.lat + dy), fontsize=10.5, family=MONO, color=FG, ha=ha,
                arrowprops=dict(arrowstyle="-", color=FG, lw=0.7), zorder=5, linespacing=1.1)
ax.set_xlim(-5.85 * K, 1.95 * K)
ax.set_ylim(49.9, 55.35)
ax.set_aspect("equal")
ax.axis("off")
h = [plt.Line2D([], [], marker="o", ls="", mfc=c, mec=BG, ms=11, label=l) for l, (_, c) in zip(["before 1500", "1500s", "1600s", "1700s", "1800s"], CEN)]
h.append(plt.Line2D([], [], marker="o", ls="", mfc=SLATE, mec="none", ms=4, alpha=0.6, label="town, no fire recorded"))
ax.legend(handles=h, loc="upper right", bbox_to_anchor=(1.0, 1.0), frameon=False, prop={"family": MONO, "size": 11}, labelcolor=FG, handletextpad=0.3)

# ---------------- right column numbers
tx = fig.add_axes([0.61, 0.315, 0.37, 0.56])
tx.axis("off")
notes = [(f"{round(rc['share_1600s_1700s'] * 100)}%", f"of the great fires came in the 1600s\nand 1700s ({rc['fires_1600s']} and {rc['fires_1700s']}). Only {rc['fires_1800s']} after 1800."),
         (f"{R['regions'][0]['share'] * 100:.0f}% vs {rc['share_burned_north'] * 100:.0f}%", f"of towns with a great fire: the Eastern\nregion against the three northern regions\n({rc['burned_north']} of {rc['n_north']} towns)."),
         (f"{mt['burned_bigger']} of {mt['pairs']}", f"burned towns are bigger today than a\nsimilar unburned town (same region,\nsimilar Domesday size). A coin toss."),
         (f"{md['size_dom_chars']['pct']:+.0f}%", f"size gap once Wikipedia article length\nis allowed for. Household income gap:\n{md['income_size']['pct']:+.1f}%. Neither bigger nor richer.")]
for (big, small), y in zip(notes, [1.0, 0.75, 0.49, 0.23]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=34, color=EMBER, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=13, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

# ---------------- bottom row
fig.text(0.04, 0.268, "FIRES PER 25 YEARS", family=MONO, fontsize=11, color=MUT)
a = fig.add_axes([0.05, 0.105, 0.25, 0.15], facecolor=BG)
q = R["by_quarter"]
a.bar([r["start"] + 12.5 for r in q], [r["fires"] for r in q], width=22, color=[ccol(r["start"]) for r in q])
a.set_xticks([1500, 1600, 1700, 1800, 1900])
a.set_yticks([0, 5, 10, 15])
for s in ("top", "right"):
    a.spines[s].set_visible(False)
for s in ("left", "bottom"):
    a.spines[s].set_color(EDGE)
a.tick_params(colors=MUT, labelsize=10)
for t in a.get_xticklabels() + a.get_yticklabels():
    t.set_family(MONO)
pk = max(q, key=lambda r: r["fires"])
a.text(pk["start"] + 12.5, pk["fires"] + 0.4, f"{pk['start']} to {pk['start'] + 24}: {pk['fires']}", family=MONO, fontsize=10, color=FG, ha="center")

fig.text(0.36, 0.268, "WORST LOSSES (HOUSES, HOMES)", family=MONO, fontsize=11, color=MUT)
b = fig.add_axes([0.47, 0.105, 0.22, 0.15], facecolor=BG)
hs = [r for r in R["houses"] if r["town"] != "Edinburgh"][:7][::-1]
cap = 800
b.barh(range(len(hs)), [min(r["houses"], cap) for r in hs], color=[ccol(r["year"]) for r in hs], height=0.7)
for i, r in enumerate(hs):
    b.text(-15, i, f"{r['town']} {r['year']}", family=MONO, fontsize=10, color=FG, ha="right", va="center")
    b.text(min(r["houses"], cap) + 15, i, f"{r['houses']:,}", family=MONO, fontsize=10, color=FG, va="center")
b.set_xlim(0, 1050)
b.axis("off")

fig.text(0.73, 0.268, "BURNED TOWN ÷ ITS MATCH, 2021", family=MONO, fontsize=11, color=MUT)
c = fig.add_axes([0.74, 0.105, 0.24, 0.15], facecolor=BG)
lr = np.log10(MP.pop2021 / MP.match_pop2021).clip(-2, 2).sort_values().values
bins = np.round(lr / 0.12)
stack = {}
ys = []
for v in bins:
    stack[v] = stack.get(v, 0) + 1
    ys.append(stack[v])
c.scatter(bins * 0.12, ys, s=46, c=[EMBER if v > 0 else SLATE for v in lr], edgecolors=BG, linewidths=0.6)
c.axvline(0, color=FG, lw=1.2)
c.set_xlim(-2.1, 2.1)
c.set_ylim(0, max(ys) + 2.5)
c.set_xticks([-2, -1, 0, 1, 2], ["1/100", "1/10", "1x", "10x", "100x"])
c.set_yticks([])
for s in ("top", "right", "left"):
    c.spines[s].set_visible(False)
c.spines["bottom"].set_color(EDGE)
c.tick_params(colors=MUT, labelsize=10)
for t in c.get_xticklabels():
    t.set_family(MONO)
c.text(-0.1, max(ys) + 1.2, f"match bigger: {mt['pairs'] - mt['burned_bigger']}", family=MONO, fontsize=10, color=SLATE, ha="right")
c.text(0.1, max(ys) + 1.2, f"burned bigger: {mt['burned_bigger']}", family=MONO, fontsize=10, color=EMBER, ha="left")

fig.text(0.04, 0.012,
         "Data: Wikipedia town articles, List of urban fires and Great Fire articles (CC BY-SA 4.0), retrieved 27 Oct 2026; ONS Census 2021 and small area income\n"
         "estimates FYE2023, ONS geography, OS Open Names (OGL v3, contains OS data © Crown copyright 2026); Hull Domesday Project (CC BY-NC-SA); Natural Earth.\n"
         f"A record of fires remembered in Wikipedia, not a complete gazetteer; associations, not causes. London 1666: {rc['london_1666_houses']:,} houses (bar capped).\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib. tristan-hotham.github.io/great-fires",
         family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "when_englands_towns_burned.png"), facecolor=BG, dpi=200)
print("ok")
