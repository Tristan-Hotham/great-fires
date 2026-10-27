"""Step 3. Analysis. Writes data/results.json (every number used in the page, paper, blog and collage) and
data/_site_data.json (compact data for the page; removed by step 4 once embedded).

Samples
  Fire record: every row of data/great_fires.csv with class great_fire ("counted fires").
  Panel: data/towns.csv, towns in England and Wales. The comparisons leave out Greater London (its towns are now
  suburbs of one city; London itself is described on its own) and need a 2021 built-up area population.
  Burned town: at least one counted great fire from 1000 to 1899.
Models (OLS with robust HC1 errors)
  size:   log(2021 residents) ~ burned + log(1 + Domesday households within 2.5 km) + region
  check:  the same plus log(article length)  (bigger, older towns get longer articles and more fire sentences)
  income: log(mean household income FYE2023) ~ burned + log(2021 residents) + region
Matching
  each burned town against the unburned town in the same region with the closest log Domesday households
  (ties broken by article length), with replacement; outcome the ratio of 2021 residents and of income.
"""
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
R = {}

F = pd.read_csv(os.path.join(D, "great_fires.csv"))
P = pd.read_csv(os.path.join(D, "towns.csv"))
DOM = pd.read_csv(os.path.join(D, "towns_domesday1086.csv"))
REV = pd.read_csv(os.path.join(D, "fire_snippets_reviewed.csv"))
fm = json.load(open(os.path.join(D, "_fires_meta.json")))
tm = json.load(open(os.path.join(D, "_towns_meta.json")))
P = P.merge(DOM[["article", "dom_households_2_5km", "dom_places_2_5km"]], on="article", how="left")

# ------------------------------------------------------------------ 1. the fire record
G = F[F["class"] == "great_fire"].copy()
EW = G[G.country.isin(["England", "Wales"])]
R["source"] = {"town_articles": fm["n_town_articles"], "articles_with_fire_sentence": fm["n_with_fire_sentence"],
               "fire_sentences": fm["n_fire_sentences"], "dated_sentences_reviewed": int(len(REV)),
               "sentences_used": int(REV.decision.isin(["great_fire", "possible", "war", "context"]).sum())}
R["record"] = {
    "rows": int(len(F)), "great_fires": int(len(G)), "possible": int((F["class"] == "possible").sum()),
    "war": int((F["class"] == "war").sum()), "great_fires_ew": int(len(EW)),
    "great_fires_england": int((G.country == "England").sum()), "great_fires_wales": int((G.country == "Wales").sum()),
    "great_fires_scotland": int((G.country == "Scotland").sum()), "great_fires_ni": int((G.country == "Northern Ireland").sum()),
    "towns_burned_all": int(G.town_article.nunique()), "towns_burned_ew": int(EW.town_article.nunique()),
    "first_year": int(G.year.min()), "last_year": int(G.year.max()),
    "with_houses": int(G.houses_lost.notna().sum()),
    "year_not_in_quote": int((G.year_in_quoted_text == 0).sum()),
}
cent = Counter((int(y) // 100 + 1) for y in G.year)
R["by_century"] = [{"century": c, "label": f"{c}th", "fires": cent.get(c, 0),
                    "fires_ew": int(((EW.year // 100 + 1) == c).sum())} for c in range(11, 20)]
R["record"]["fires_1600s_1700s"] = cent.get(17, 0) + cent.get(18, 0)
R["record"]["share_1600s_1700s"] = round(R["record"]["fires_1600s_1700s"] / len(G), 3)
R["record"]["fires_1500_1899"] = int(((G.year >= 1500) & (G.year <= 1899)).sum())
R["record"]["fires_before_1500"] = int((G.year < 1500).sum())
R["record"]["fires_1600s"] = cent.get(17, 0)
R["record"]["fires_1700s"] = cent.get(18, 0)
R["record"]["fires_1800s"] = cent.get(19, 0)
R["record"]["fires_1500s"] = cent.get(16, 0)
R["record"]["peak_century"] = f"{max(cent, key=cent.get)}th"
# quarter centuries 1500 to 1899
q = Counter((int(y) // 25) * 25 for y in G.year if 1500 <= y <= 1899)
R["by_quarter"] = [{"start": s, "fires": q.get(s, 0)} for s in range(1500, 1900, 25)]
qpk = max(q, key=q.get)
R["record"]["peak_quarter"] = f"{qpk} to {qpk + 24}"
R["record"]["peak_quarter_fires"] = q[qpk]
dec = Counter((int(y) // 10) * 10 for y in G.year)
R["record"]["peak_decade"] = int(max(dec, key=lambda k: (dec[k], -k)))
R["record"]["peak_decade_fires"] = dec[R["record"]["peak_decade"]]
# houses
H = G.dropna(subset=["houses_lost"]).sort_values("houses_lost", ascending=False)
R["houses"] = [{"town": r.town, "year": int(r.year), "houses": int(r.houses_lost), "unit": r.houses_unit} for r in H.itertuples()]
HE = H[H.town != "London"]
R["record"]["houses_median"] = float(np.median(H.houses_lost))
R["record"]["houses_median_ex_london"] = float(np.median(HE.houses_lost))
R["record"]["houses_sum_ex_london"] = int(HE.houses_lost.sum())
R["record"]["london_1666_houses"] = int(G[(G.town == "London") & (G.year == 1666)].houses_lost.iloc[0])
# repeat towns
rep = G.groupby("town").size().sort_values(ascending=False)
R["repeat"] = [{"town": t, "fires": int(n), "years": " ".join(str(int(y)) for y in sorted(G[G.town == t].year))} for t, n in rep.items() if n >= 2]
R["record"]["towns_burned_twice_plus"] = int((rep >= 2).sum())
R["record"]["towns_burned_three_plus"] = int((rep >= 3).sum())
# regions (England and Wales): fires and burned share of panel towns
P["burned"] = P.burned.astype(int)
reg = []
for rg, g in P.groupby("region"):
    reg.append({"region": rg, "towns": int(len(g)), "burned": int(g.burned.sum()), "share": round(g.burned.mean(), 3),
                "fires": int((EW.region == rg).sum())})
reg.sort(key=lambda r: -r["share"])
R["regions"] = reg
R["record"]["top_region"] = reg[0]["region"]
R["record"]["top_region_share"] = reg[0]["share"]
# south and east versus north (pre-industrial England was richest and most timbered in the south and east)
NORTH = {"North West", "North East", "Yorkshire and the Humber"}
pn = P[P.region.isin(NORTH)]
ps = P[P.region.isin({"South West", "South East", "Eastern", "East Midlands", "West Midlands"})]
R["record"]["share_burned_north"] = round(pn.burned.mean(), 3)
R["record"]["share_burned_south_mid"] = round(ps.burned.mean(), 3)
R["record"]["n_north"] = int(len(pn))
R["record"]["burned_north"] = int(pn.burned.sum())
ct = [[int(ps.burned.sum()), int(len(ps) - ps.burned.sum())], [int(pn.burned.sum()), int(len(pn) - pn.burned.sum())]]
R["record"]["north_south_fisher_p"] = float(stats.fisher_exact(ct)[1])
# rebuilding sentences
rb = REV[REV.decision.isin(["great_fire", "context"]) & REV.text.str.contains(r"Georgian|brick|rebuil|Rebuilding", regex=True)]
R["record"]["towns_rebuild_sentence"] = int(rb.article.nunique())
R["rebuild_towns"] = sorted(rb.article.str.split(",").str[0].unique().tolist())
R["record"]["towns_georgian_sentence"] = int(REV[REV.decision.isin(["great_fire", "context"]) & REV.text.str.contains("Georgian")].article.nunique())

# ------------------------------------------------------------------ 2. panel comparisons
R["panel"] = {"towns": int(len(P)), "burned": int(P.burned.sum()), "share_burned": round(P.burned.mean(), 3),
              "skipped": tm["panel_skipped"], "fire_towns_not_in_panel": tm["fire_towns_not_in_panel"],
              "dom_radius_km": tm["dom_radius_km"], "lb_radius_km": tm["lb_radius_km"]}
S = P[(P.region != "London") & P.pop2021.notna() & (P.pop2021 > 0)].copy()
S["lpop"] = np.log(S.pop2021)
S["ldom"] = np.log1p(S.dom_households_2_5km.fillna(0))
S["lchars"] = np.log(S.article_chars.clip(lower=1000))
S["linc"] = np.log(S.income_fye2023)
b, u = S[S.burned == 1], S[S.burned == 0]
R["cmp"] = {
    "n": int(len(S)), "n_burned": int(len(b)), "n_unburned": int(len(u)),
    "pop_median_burned": int(b.pop2021.median()), "pop_median_unburned": int(u.pop2021.median()),
    "chars_median_burned": int(b.article_chars.median()), "chars_median_unburned": int(u.article_chars.median()),
    "dom_median_burned": float(b.dom_households_2_5km.median()), "dom_median_unburned": float(u.dom_households_2_5km.median()),
    "dom_any_burned": round(float((b.dom_households_2_5km > 0).mean()), 3), "dom_any_unburned": round(float((u.dom_households_2_5km > 0).mean()), 3),
    "inc_median_burned": int(b.income_fye2023.median()), "inc_median_unburned": int(u.income_fye2023.median()),
    "pop_mw_p": float(stats.mannwhitneyu(b.pop2021, u.pop2021).pvalue),
    "chars_mw_p": float(stats.mannwhitneyu(b.article_chars, u.article_chars).pvalue),
    "inc_mw_p": float(stats.mannwhitneyu(b.income_fye2023.dropna(), u.income_fye2023.dropna()).pvalue),
}
R["cmp"]["chars_ratio"] = round(R["cmp"]["chars_median_burned"] / R["cmp"]["chars_median_unburned"], 2)


def fit(formula, df, term="burned"):
    m = smf.ols(formula, data=df).fit(cov_type="HC1")
    c, se = m.params[term], m.bse[term]
    return {"coef": float(c), "pct": round(100 * (math.exp(c) - 1), 1), "lo": round(100 * (math.exp(c - 1.96 * se) - 1), 1),
            "hi": round(100 * (math.exp(c + 1.96 * se) - 1), 1), "p": float(m.pvalues[term]), "n": int(m.nobs), "r2": round(float(m.rsquared), 3)}


R["models"] = {
    "size_raw": fit("lpop ~ burned", S),
    "size_region": fit("lpop ~ burned + C(region)", S),
    "size_dom": fit("lpop ~ burned + ldom + C(region)", S),
    "size_dom_chars": fit("lpop ~ burned + ldom + lchars + C(region)", S),
    "income_raw": fit("linc ~ burned", S.dropna(subset=["linc"])),
    "income_size": fit("linc ~ burned + lpop + C(region)", S.dropna(subset=["linc"])),
    "income_size_chars": fit("linc ~ burned + lpop + lchars + C(region)", S.dropna(subset=["linc"])),
}
# sensitivity: count possible fires as burned; only fires 1600 to 1799; only towns in the 1377 or 1801 tables excluded
S2 = S.assign(burned=((S.burned == 1) | (S.n_possible_fires > 0)).astype(int))
R["models"]["size_dom_incl_possible"] = fit("lpop ~ burned + ldom + C(region)", S2)
S3 = S[(S.burned == 0) | (S.burned_1600_1799 == 1)]
R["models"]["size_dom_1600_1799"] = fit("lpop ~ burned + ldom + C(region)", S3)
R["models"]["income_size_incl_possible"] = fit("linc ~ burned + lpop + C(region)", S2.dropna(subset=["linc"]))

# like for like: only articles described as market towns
M = S[S.shortdesc.fillna("").str.contains("arket town")]
R["market"] = {"n": int(len(M)), "n_burned": int(M.burned.sum()),
               "pop_median_burned": int(M[M.burned == 1].pop2021.median()), "pop_median_unburned": int(M[M.burned == 0].pop2021.median()),
               "inc_median_burned": int(M[M.burned == 1].income_fye2023.median()), "inc_median_unburned": int(M[M.burned == 0].income_fye2023.median()),
               "size": fit("lpop ~ burned + ldom + C(region)", M), "income": fit("linc ~ burned + lpop + C(region)", M.dropna(subset=["linc"]))}

# matched pairs
rng_pairs = []
for r in b.itertuples():
    pool = u[u.region == r.region]
    if len(pool) == 0:
        continue
    dd = (pool.ldom - r.ldom).abs() + 1e-6 * (pool.lchars - r.lchars).abs()
    m = pool.loc[dd.idxmin()]
    rng_pairs.append({"town": r.town, "region": r.region, "dom": float(r.dom_households_2_5km), "pop2021": int(r.pop2021),
                      "inc": float(r.income_fye2023) if not pd.isna(r.income_fye2023) else None,
                      "match": m.town, "match_dom": float(m.dom_households_2_5km), "match_pop2021": int(m.pop2021),
                      "match_inc": float(m.income_fye2023) if not pd.isna(m.income_fye2023) else None,
                      "first_fire": int(r.first_fire)})
MP = pd.DataFrame(rng_pairs)
lr = np.log(MP.pop2021 / MP.match_pop2021)
mi = MP.dropna(subset=["inc", "match_inc"])
li = np.log(mi.inc / mi.match_inc)
R["matched"] = {"pairs": int(len(MP)), "burned_bigger": int((lr > 0).sum()), "share_bigger": round(float((lr > 0).mean()), 3),
                "median_ratio": round(float(np.exp(np.median(lr))), 2), "mean_log_ratio": float(lr.mean()),
                "wilcoxon_p": float(stats.wilcoxon(lr).pvalue), "sign_p": float(stats.binomtest(int((lr > 0).sum()), len(lr)).pvalue),
                "distinct_matches": int(MP.match.nunique()),
                "inc_pairs": int(len(mi)), "inc_burned_higher": int((li > 0).sum()), "inc_median_pct": round(100 * (math.exp(float(np.median(li))) - 1), 1),
                "inc_wilcoxon_p": float(stats.wilcoxon(li).pvalue),
                "dom_abs_diff_median": float(np.median(np.abs(MP.dom - MP.match_dom)))}
MP.to_csv(os.path.join(D, "matched_pairs.csv"), index=False)

# ------------------------------------------------------------------ 3. the historical tables (1377 and 1801)
C77 = P[P.pop1377.notna()].copy()
C77["burned_1377_1800"] = C77.fire_years.fillna("").apply(lambda s: int(any(1377 < int(y) <= 1800 for y in str(s).split() if y)))
C77 = C77[C77.pop2021.notna()]
C77["rank2021"] = C77.pop2021.rank(ascending=False, method="min").astype(int)
C77["rank1377c"] = C77.pop1377.rank(ascending=False, method="min").astype(int)
C77["change"] = C77.rank1377c - C77.rank2021
C77["growth"] = C77.pop2021 / C77.pop1377
cb, cu = C77[C77.burned_1377_1800 == 1], C77[C77.burned_1377_1800 == 0]
R["c1377"] = {"n": int(len(C77)), "n_burned": int(len(cb)), "burned_towns": sorted(cb.town.tolist()),
              "median_growth_burned": round(float(cb.growth.median()), 1), "median_growth_unburned": round(float(cu.growth.median()), 1),
              "median_rank_change_burned": float(cb.change.median()), "median_rank_change_unburned": float(cu.change.median()),
              "mw_p_growth": float(stats.mannwhitneyu(cb.growth, cu.growth).pvalue)}
R["c1377_rows"] = [{"town": r.town, "pop1377": int(r.pop1377), "rank1377": int(r.rank1377c), "pop2021": int(r.pop2021), "rank2021": int(r.rank2021),
                    "burned": int(r.burned_1377_1800), "fires": str(r.fire_years) if not pd.isna(r.fire_years) else ""}
                   for r in C77.sort_values("rank1377c").itertuples()]
C01 = P[P.pop1801.notna() & P.pop2021.notna()].copy()
C01["growth"] = C01.pop2021 / C01.pop1801
c1b, c1u = C01[C01.burned_before_1801 == 1], C01[C01.burned_before_1801 == 0]
R["c1801"] = {"n": int(len(C01)), "n_burned": int(len(c1b)), "burned_towns": sorted(c1b.town.tolist()),
              "median_growth_burned": round(float(c1b.growth.median()), 1), "median_growth_unburned": round(float(c1u.growth.median()), 1),
              "mw_p": float(stats.mannwhitneyu(c1b.growth, c1u.growth).pvalue)}
R["c1801_rows"] = [{"town": r.town, "pop1801": int(r.pop1801), "pop2021": int(r.pop2021), "growth": round(float(r.growth), 1),
                    "burned": int(r.burned_before_1801), "region": r.region} for r in C01.sort_values("pop1801", ascending=False).itertuples()]

# ------------------------------------------------------------------ 4. the look of the rebuilt towns: dated top-listed buildings
L = S[S.lb_dated_1km >= 3].copy()
L["geo"] = L.lb_1700_1837 / L.lb_dated_1km
L["pre"] = (L.lb_pre1600 + L.lb_1600_1699) / L.lb_dated_1km
lb_, lu_ = L[L.burned_1600_1799 == 1], L[L.burned == 0]
R["listed"] = {"towns": int(len(L)), "burned": int(len(lb_)), "unburned": int(len(lu_)),
               "geo_share_burned": round(float(lb_.geo.mean()), 3), "geo_share_unburned": round(float(lu_.geo.mean()), 3),
               "pre1700_share_burned": round(float(lb_.pre.mean()), 3), "pre1700_share_unburned": round(float(lu_.pre.mean()), 3),
               "geo_mw_p": float(stats.mannwhitneyu(lb_.geo, lu_.geo).pvalue), "pre_mw_p": float(stats.mannwhitneyu(lb_.pre, lu_.pre).pvalue),
               "dated_total": int(S.lb_dated_1km.sum())}

# ------------------------------------------------------------------ 5. London on its own
lon = P[P.article == "London"].iloc[0]
R["london"] = {"pop2021": int(lon.pop2021), "pop1377": int(lon.pop1377), "pop1801": int(lon.pop1801),
               "fires": str(lon.fire_years), "n_fires": int(lon.n_great_fires)}

# ------------------------------------------------------------------ 6. highlights used in the text
def fire(town, year):
    r = G[(G.town == town) & (G.year == year)].iloc[0]
    return {"town": town, "year": year, "houses": None if pd.isna(r.houses_lost) else int(r.houses_lost), "unit": r.houses_unit}


R["highlights"] = {k: fire(*v) for k, v in {"london": ("London", 1666), "northampton": ("Northampton", 1675), "warwick": ("Warwick", 1694),
                                             "blandford": ("Blandford Forum", 1731), "tiverton": ("Tiverton", 1731), "tiverton1612": ("Tiverton", 1612),
                                             "wem": ("Wem", 1677), "marlborough": ("Marlborough", 1653), "norwich": ("Norwich", 1507),
                                             "buckingham": ("Buckingham", 1725), "chudleigh": ("Chudleigh", 1807), "dorchester": ("Dorchester", 1613),
                                             "wymondham": ("Wymondham", 1615), "edinburgh": ("Edinburgh", 1824)}.items()}
for k in ("Blandford Forum", "Warwick", "Northampton", "Wem", "Tiverton, Devon", "Marlborough, Wiltshire", "Buckingham", "Wareham, Dorset"):
    r = P[P.article == k].iloc[0]
    R["highlights"].setdefault("pop2021", {})[r.town] = None if pd.isna(r.pop2021) else int(r.pop2021)

R["record"]["dom_share_north"] = round(float((pn.dom_households_2_5km > 0).mean()), 3)
R["record"]["dom_share_south_mid"] = round(float((ps.dom_households_2_5km > 0).mean()), 3)
R["record"]["burned_wales"] = int(P[P.region == "Wales"].burned.sum())
R["record"]["towns_wales"] = int((P.region == "Wales").sum())
R["highlights"]["tiverton_years"] = " ".join(str(int(y)) for y in sorted(G[G.town == "Tiverton"].year))
R["highlights"]["marlborough_years"] = " ".join(str(int(y)) for y in sorted(G[G.town == "Marlborough"].year))
R["highlights"]["london_churches"] = "86 or 87"
R["listed"]["share_dated_near_towns"] = round(float(S.lb_dated_1km.sum() / S.lb_top_1km.sum()), 3)
json.dump(R, open(os.path.join(D, "results.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

# ------------------------------------------------------------------ site data
site = {"fires": [], "towns": []}
for r in F.itertuples():
    if pd.isna(r.lat):
        continue
    site["fires"].append({"t": r.town, "y": int(r.year), "c": {"great_fire": "g", "possible": "p", "war": "w"}[r[5]],
                          "h": None if pd.isna(r.houses_lost) else int(r.houses_lost), "u": "" if pd.isna(r.houses_unit) else r.houses_unit,
                          "la": r.lat, "lo": r.lon, "s": r.what_the_source_says[:420], "a": r.source_articles, "n": "" if pd.isna(r.manual_review) else r.manual_review})
for r in P.itertuples():
    site["towns"].append({"t": r.town, "la": r.lat, "lo": r.lon, "b": int(r.burned), "p": None if pd.isna(r.pop2021) else int(r.pop2021),
                          "i": None if pd.isna(r.income_fye2023) else int(r.income_fye2023), "r": r.region})
site["pairs"] = rng_pairs
site["scatter"] = [[r.town, float(r.dom_households_2_5km) if not pd.isna(r.dom_households_2_5km) else 0.0, int(r.pop2021), int(r.burned),
                    "" if pd.isna(r.fire_years) else str(r.fire_years)] for r in S.itertuples()]
json.dump(site, open(os.path.join(D, "_site_data.json"), "w"), separators=(",", ":"))
print(json.dumps({k: R[k] for k in ("market", "record", "cmp", "models", "matched", "c1377", "c1801", "listed", "london")}, indent=1, default=str))
print(R["regions"])
print(R["by_century"])
