# Great Fires

Before 1900 many English and Welsh towns burned, and several were rebuilt in brick and stone as handsome Georgian towns. Did the towns that burned rebuild bigger? An open record of great town fires read from Wikipedia, compared with Domesday Book, the historical town tables, Census 2021 and ONS household income.

**Interactive version:** https://tristan-hotham.github.io/great-fires/

**Paper:** https://doi.org/10.5281/zenodo.23691902

This repository holds the interactive page, the datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher).

## Headline results

- From 2,213 fire sentences in 1,681 Wikipedia town articles (plus the List of urban fires and the articles on individual great fires) I recorded 102 great town fires in 81 towns, 1087 to 1896, 97 of them in England and Wales. Another 25 fires are "possible" (scale unclear) and 30 are burnings in war; neither is counted.
- 63% of the great fires fall in the 1600s (33) and 1700s (31); the busiest quarter century is 1675 to 1699 (14 fires). Only 11 date from the 1800s.
- The fires belong to the South, the Midlands and East Anglia: 16.3% of towns in the Eastern region have one, against 1.8% of towns in the three northern regions (5 of 275).
- Burned towns are bigger today in raw terms, but they were older places to begin with. Allowing for region and Domesday households, they are about 24.8% larger in 2021, with a 95% interval from -6.4% to +66.4%.
- Matched one to one with an unburned town in the same region with similar Domesday households, 40 of 71 burned towns are bigger (sign test p = 0.34).
- Burned towns have Wikipedia articles 1.5 times as long; allowing for article length the size difference is -6.1%, and among market towns -2.9%.
- Household income (FYE2023), allowing for region and size: -2.0% (95% interval -5.2% to +1.3%).

This is a record of fires remembered in Wikipedia articles, not a complete gazetteer, and the comparisons are associations, not causes.

## Files

- `index.html`: the interactive page (map of fires with a time slider, charts, tables). Data embedded; works as a single file.
- `header.png`: social card (1200 by 630), drawn by `release/figures.py`.
- `data/great_fires.csv`: one row per town fire: town, year, class (`great_fire`, `possible`, `war`), houses lost if stated and its unit, the text that records it, the Wikipedia articles it came from, where the map point came from, and a manual review note.
- `data/fire_snippets_reviewed.csv`: every fire sentence in the town articles with a year from 1000 to 1899 (and the few undated ones used), with the decision and the reason.
- `data/towns.csv`: the comparison panel of 1,162 towns in England and Wales: location, region, fires, 1377 and 1801 table figures, 2021 built-up area and residents, household income, article length, and counts of dated Grade I and II* listed buildings within 1 km.
- `data/towns_domesday1086.csv`: Domesday households within 2.5 km of each town point (CC BY-NC-SA 4.0, kept separate).
- `data/matched_pairs.csv`: each burned town and its matched unburned town.
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `code/01_fires.py`: extracts and classifies the fires (the rule is documented at the top of the script).
- `code/02_towns.py`: builds the town panel.
- `code/03_analyse.py`: comparisons, regressions and matching; writes `results.json` and a temporary page data file.
- `code/04_build_page.py`: fills `code/page_template.html` from `results.json` to make `index.html`.
- `release/`: the paper (PDF, LaTeX source and figures), the blog post and figures, and the Zenodo files. Rebuild with `python3 release/figures.py [font_dir]`, `python3 release/paper/build_paper.py` and `python3 release/build_release.py`.
- `reddit/`: the collage and its script.

## How to rerun

The scripts read the source files in place (paths at the top of each script): the Wikipedia bundles retrieved on 27 October 2026, Wikidata, OS Open Names, ONS geography lookups, Census 2021 TS001, the ONS small area income estimates for FYE2023, the Hull Domesday Project data, and the Natural Earth land polygons.

```
python3 code/01_fires.py
python3 code/02_towns.py
python3 code/03_analyse.py
python3 code/04_build_page.py
```

It needs Python 3 with pandas, numpy, scipy, statsmodels, openpyxl and matplotlib.

## Method in brief

- Great fire: the text gives a year from 1000 to 1899 and describes damage to the town as a whole (much or most of the town, a third or more, the "Great Fire of" the town, or 20 or more houses), and it was not a burning in war, raid or riot. Applied by reading every sentence, with a review note on each fire. Four great fires take their year from outside the quoted sentence (Leatherhead, Edinburgh, Chudleigh, Ilfracombe; see the notes).
- Panel: towns in the Wikipedia town lists located in England or Wales; 2021 residents summed from LSOAs to the matched built-up area (BUA22); income the population-weighted mean of the MSOA estimates over the MSOAs that best fit the area (nearest MSOA for small towns).
- Comparisons leave out Greater London. Least squares on log population and log income with region fixed effects and robust errors; matching on Domesday households within region.

## Known limits

- A record of memory: fires not mentioned in Wikipedia are missing, and better documented towns are more likely to have a fire recorded.
- Classification of scale needs judgement; the possible fires and war burnings are kept so others can apply a different rule.
- Domesday households within 2.5 km are a crude early baseline and miss the far north; the 1377 and 1801 tables list only the largest towns.
- Boundaries differ between the town that burned and its 2021 built-up area.

## Sources and licences

- Wikipedia town articles, List of urban fires, Early fires of London, articles on individual fires, and List of towns and cities in England by historical population: CC BY-SA 4.0, retrieved 27 October 2026.
- Wikidata (listed buildings): CC0.
- Census 2021 (TS001) and Income estimates for small areas, England and Wales, financial year ending 2023: Office for National Statistics, Open Government Licence v3.0.
- OS Open Names and ONS geography (BUA22, MSOA and LSOA lookups): contains OS data © Crown copyright and database right 2026; Open Government Licence v3.0.
- Domesday: Hull Domesday Project, Professor J.J.N. Palmer, George Slater and the University of Hull (CC BY-NC-SA), via https://github.com/embabel-worlds/realm-domesday
- Land polygons: Natural Earth, public domain. Base map tiles: Esri.

The data in `data/` and the text of the page are released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because they derive from Wikipedia; `data/towns_domesday1086.csv` is released under CC BY-NC-SA 4.0. The code is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026). Great Fires: Did the Towns That Burned Rebuild Bigger? Zenodo. https://doi.org/10.5281/zenodo.23691902

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
