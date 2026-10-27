"""Step 1. Build the record of great town fires (1000 to 1899) from Wikipedia text.

Reads (in place, never copied):
  _data10/wikipedia_towns_fires_rolls.json.gz  town articles linked from the Wikipedia lists of towns in England and
                                               Wales and of UK cities: every sentence that mentions fire, burnt,
                                               burned, conflagration or blaze (CC BY-SA 4.0)
  _data10/wikipedia_batch10.json.gz            "List of urban fires", the Fires in England / Scotland category
                                               articles and the Great Fire articles (CC BY-SA 4.0)
  osnames_gb.tsv                               OS Open Names (OGL v3), for places without a coordinate and for regions

Writes:
  data/fire_snippets_reviewed.csv  every fire sentence in a town article that carries a year from 1000 to 1899
                                   (plus a few without a year that I used), with the decision and the reason
  data/great_fires.csv             one row per town fire: town, year, class, what the source says, houses lost if
                                   stated, the articles it came from, where the map point came from, a review note

THE RULE (applied by reading each sentence, not by keyword alone):
  A sentence records a GREAT FIRE when all three hold:
   (a) it gives a year from 1000 to 1899 (or the same article gives it in a sentence I cite with it);
   (b) it describes damage to the town as a whole, not one building: words such as "much / most / a great part /
       a third / three quarters of the town", "the town was almost destroyed", a fire the article names
       "the Great Fire of <town>", or 20 or more houses, dwellings, buildings or properties lost;
   (c) it was not a deliberate burning in war, raid, rebellion or riot (those are kept as class "war" and left
       out of every count).
  POSSIBLE: a dated town fire whose scale the sentence does not make clear ("several serious fires", one street,
       fewer than 20 houses). Kept in the file, left out of the main counts, used in a sensitivity check.
  BUILDING: one building or site (church, mill, hall, manor house, inn, theatre, school). Left out.
  MODERN:   1900 onwards. Left out.
Every row was read by me (with Claude's help) and carries a manual review note.
"""
import csv
import gzip
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
OUT = os.path.join(ROOT, "data")
os.makedirs(OUT, exist_ok=True)

T = json.load(gzip.open(f"{H}/_data10/wikipedia_towns_fires_rolls.json.gz"))["towns"]
B = json.load(gzip.open(f"{H}/_data10/wikipedia_batch10.json.gz"))["articles"]


def clean(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref.*$", "", s, flags=re.S)
    s = re.sub(r"\{\{(?:snd|ndash)\}\}", " ", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"'{2,}", "", s)
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"(\d)\s*[\u2013\u2014]\s*(\d)", r"\1 to \2", s)  # house style: no en or em dashes
    s = re.sub(r"\s*[\u2013\u2014]\s*", ", ", s).replace("--", ", ")
    s = re.sub(r"\s+", " ", s).strip(" *")
    return s


def snip(title, i):
    return clean(T[title]["fire_snippets"][i])


def find(title, pattern):
    """First line or sentence of a batch10 article matching the pattern (for list and fire articles)."""
    tx = B[title]["text"]
    tx = re.sub(r"<ref[^>]*/>", "", tx)
    tx = re.sub(r"<ref.*?</ref>", "", tx, flags=re.S)
    for part in re.split(r"\n|(?<=[a-z\]\)])\. ", tx):
        if re.search(pattern, part):
            return clean(part)
    raise SystemExit(f"pattern not found in {title}: {pattern}")


UF = "List of urban fires"
EF = "Early fires of London"
# ---------------------------------------------------------------------------------------------------------
# The record. Each entry: place (the Wikipedia town article used for the town), year, class, houses lost, unit,
# sources [(article, snippet index or regex)], review note.  Classes: great_fire, possible, war.
# ---------------------------------------------------------------------------------------------------------
E = []


def ev(place, year, cls, sources, houses=None, unit="", note="", display=None):
    E.append(dict(place=place, year=year, cls=cls, sources=sources, houses=houses, unit=unit, note=note,
                  display=display or place.split(",")[0]))


G, P, W = "great_fire", "possible", "war"
# ---- medieval
ev("Doncaster", 1204, G, [("Doncaster", 0)], note="'a disastrous fire'; scale read as town-wide")
ev("Andover, Hampshire", 1141, G, [("Andover, Hampshire", 0)], note="'ravaged by two serious fires'")
ev("Andover, Hampshire", 1435, G, [("Andover, Hampshire", 0)], note="second of the two fires in the same sentence")
ev("Beverley", 1188, G, [("Beverley", 0)], note="'destroyed numerous houses'")
ev("Worcester, England", 1189, G, [("Worcester, England", 1)], note="'destroyed much of the city'; the earlier 1139 to 1151 fires were in civil war and are class war")
ev("Worcester, England", 1139, W, [("Worcester, England", 0)], note="fires during the war between Stephen and Matilda")
ev("Gloucester", 1222, G, [("Gloucester", 0)], note="'a massive fire destroyed part of Gloucester'")
ev("Lichfield", 1291, G, [("Lichfield", 0)], note="'destroyed most of the town'")
ev("Chatteris", 1310, G, [("Chatteris", 1)], note="'a large portion of the town was destroyed'")
ev("Tamworth, Staffordshire", 1345, G, [("Tamworth, Staffordshire", 1)], note="'much of the town burned'")
ev("Leatherhead", 1392, G, [("Leatherhead", 0)], note="year from 'In 1393, one year after a serious fire had destroyed much of Leatherhead'")
ev("Shrewsbury", 1394, G, [("Shrewsbury", 1)], note="named 'The Great Fire of Shrewsbury'; accidental")
ev("Crowland", 1469, G, [("Crowland", 0)], note="article gives '1469 to 1476'; first year used")
ev("Yeovil", 1499, G, [("Yeovil", 0)], note="'destroyed many wooden, thatch-roofed buildings in the town'")
ev("London", 1087, G, [(EF, r"major fire occurred in London in 1087")], note="'consumed much of the Norman city'")
ev("London", 1133, G, [(EF, r"first dates to \[\[Pentecost"), (UF, r"^\* 1135")], note="Early fires of London gives 1133; List of urban fires gives 1135; 1133 used")
ev("London", 1212, G, [(EF, r"began on 10 July 1212"), (UF, r"^\* 1212")], note="the Great Fire of Southwark; 'the great part of the city'")
ev("London", 1123, P, [("City of London", 6)], note="City of London article names 1123 as one of the worst fires; may be the same fire as 1133/1135; not counted")
for y in (1130, 1132, 1220, 1227, 1299):
    ev("London", y, P, [(EF, r"other serious fires in London in 1130")], note="listed as serious or major without scale")
ev("London", 1678, P, [(EF, r"another major fire in 1678")], note="'another major fire'; no scale")
# ---- 1500s
ev("Norwich", 1507, G, [("Norwich", 9), ("Fires of Norwich (1507)", r"718 houses")], houses=718, unit="houses",
   note="Blomefield's figure of 718 houses, about 40% of the housing stock, from the 1507 fires article")
ev("Retford", 1528, G, [("Retford", 0), ("Retford", 6)], note="'destroyed more than three-quarters of the buildings in East Retford'")
ev("Attleborough", 1559, G, [("Attleborough", 0)], note="'a great part of the town'")
ev("Chard, Somerset", 1577, G, [("Chard, Somerset", 1)], note="'most of the town'")
ev("Dereham", 1581, G, [("Dereham", 0)], note="'numerous medieval buildings were destroyed'")
ev("Nantwich", 1583, G, [("Nantwich", 1)], note="'destroyed most of the town to the east of the Weaver'")
ev("Retford", 1585, G, [("Retford", 1)], note="'the poor men of the late burned town of Retford'")
ev("Wolverhampton", 1590, G, [("Wolverhampton", 0), ("Wolverhampton", 2)], note="'left nearly 700 people homeless'")
ev("Shifnal", 1591, G, [("Shifnal", 0)], note="'a fire swept through the town'")
ev("Church Stretton", 1593, G, [("Church Stretton", 0)], note="'much of the town'")
ev("Stratford-upon-Avon", 1595, P, [("Stratford-upon-Avon", 2)], note="'the fire of 1595' named but its scale is not stated in the sentence")
ev("Tiverton, Devon", 1598, G, [("Tiverton fire of 1731", r"first recorded fire was in April 1598")], houses=400, unit="houses",
   note="from the Tiverton fire of 1731 article; 33 deaths")
# ---- 1600s
ev("North Walsham", 1600, G, [("North Walsham", 0), ("North Walsham", 1)], houses=118, unit="homes", note="also 70 shops")
ev("Basingstoke", 1601, G, [("Basingstoke", 0)], note="'the great fires of 1601 and 1656'")
ev("Bury St Edmunds", 1608, G, [("Bury St Edmunds", 1)], houses=160, unit="dwellings", note="and 400 outhouses")
ev("Tiverton, Devon", 1612, G, [("Tiverton, Devon", 2), ("Tiverton fire of 1731", r"more serious fire occurred in August 1612")], houses=600, unit="houses",
   note="Tiverton fire article: 600 houses; Barnstaple register quoted in the town article: 260 dwelling houses")
ev("Dorchester, Dorset", 1613, G, [("Dorchester, Dorset", 1)], houses=300, unit="houses", note="and two churches")
ev("Dorchester, Dorset", 1622, P, [("Dorchester, Dorset", 0)], note="one of 'several serious fires'; scale not stated")
ev("Wymondham", 1615, G, [("Wymondham", 3), (UF, r"Great Fire of \[\[Wymondham")], houses=300, unit="properties", note="List of urban fires: 300 properties")
ev("London", 1633, G, [(EF, r"Another fire broke out in 1633")], houses=122, unit="buildings", note="42 premises on London Bridge and 80 buildings on Thames Street")
ev("Ramsey, Cambridgeshire", 1636, P, [("Ramsey, Cambridgeshire", 0)], houses=15, unit="tenements", note="fewer than 20 tenements")
ev("Bridgnorth", 1646, W, [("Bridgnorth", 1)], note="named the great fire of Bridgnorth; it happened during the Civil War siege of the town (not stated in the sentence), so classed war and not counted")
ev("Wrexham", 1643, W, [("Wrexham", 0)], note="houses burned during the quartering of troops in the Civil War")
ev("Retford", 1631, P, [("Retford", 2)], note="'caused £1,300 worth of damage'; scale in houses not stated")
ev("Market Drayton", 1651, G, [("Market Drayton", 0)], note="'damaged more than 50% of the town'")
ev("Marlborough, Wiltshire", 1653, G, [("Marlborough, Wiltshire", 0), (UF, r"Great Fire of Marlborough")], houses=244, unit="houses",
   note="town article: 244 houses; List of urban fires: 224 dwellings")
ev("Basingstoke", 1656, G, [("Basingstoke", 0)], note="second of the 'great fires'")
ev("Southwold", 1659, G, [("Southwold", 0)], note="'devastated most of the town'")
ev("Willenhall", 1659, G, [("Willenhall", 0)], note="'most of the town centre was devastated'")
ev("Fakenham", 1660, P, [("Fakenham", 0)], note="'destroyed or partly destroyed a number of buildings'")
ev("Newport, Shropshire", 1665, G, [("Newport, Shropshire", 1), ("Newport, Shropshire", 0)], houses=162, unit="families' homes", note="'the homes of 162 families'; 'destroyed most of the High Street'")
ev("London", 1666, G, [("London", 1), ("Great Fire of London", r"computed at 13,200")], houses=13200, unit="houses",
   note="13,200 to 13,500 houses; lower figure used")
ev("Bradninch", 1666, G, [("Bradninch", 0)], note="'largely destroyed'")
ev("Haverhill, Suffolk", 1667, G, [("Haverhill, Suffolk", 0)], note="'most of its historical buildings were lost'")
ev("Watton, Norfolk", 1674, G, [("Watton, Norfolk", 0)], houses=60, unit="houses")
ev("Northampton", 1675, G, [("Northampton", 3), ("Great Fire of Northampton", r"around 600 homes")], houses=600, unit="homes",
   note="Great Fire of Northampton article: about 600 homes (other accounts 700 of 850 buildings); 700 families homeless, 11 deaths")
ev("Wem", 1677, G, [("Wem", 5), ("Wem", 15)], houses=140, unit="dwelling houses", note="'seven score dwelling houses' = 140")
ev("Marlborough, Wiltshire", 1679, G, [("Marlborough, Wiltshire", 4)], note="'Fire swept through the town again in 1679 and 1690'")
ev("Dereham", 1679, G, [("Dereham", 0), ("Dereham", 2)], note="the article says 1679 in one sentence and 1659 in another; 1679 used")
ev("Ludgershall, Wiltshire", 1679, P, [("Ludgershall, Wiltshire", 0)], note="'damaged by fire'; then a village")
ev("Windsor, Berkshire", 1681, G, [("Windsor, Berkshire", 0)], note="named 'the Great Fire of Windsor'; scale not otherwise stated")
ev("Newmarket, Suffolk", 1683, G, [("Newmarket, Suffolk", 0)], note="'a fire swept through the town on the north side of the High Street'")
ev("Beaminster", 1684, P, [("Beaminster", 2)], note="'further accidental fires'; scale not stated")
ev("Bungay", 1688, G, [("Bungay", 0)], note="'almost destroyed'")
ev("Hingham, Norfolk", 1688, G, [("Hingham, Norfolk", 1), ("Hingham, Norfolk", 0)], note="'many of the buildings were destroyed'")
ev("St Ives, Cambridgeshire", 1689, G, [("St Ives, Cambridgeshire", 0)], note="'destroyed much of the built up infrastructure'")
ev("New Alresford", 1689, G, [("New Alresford", 1)], houses=117, unit="houses", note="article gives 1689/90")
ev("Marlborough, Wiltshire", 1690, G, [("Marlborough, Wiltshire", 4)], note="second fire in the same sentence")
ev("Builth Wells", 1690, G, [("Builth Wells", 0)], note="'a devastating fire tore through Builth'")
ev("Teignmouth", 1690, W, [("Teignmouth", 0)], houses=240, unit="dwelling houses", note="French raid")
ev("Warwick", 1694, G, [("Warwick", 3), ("Great Fire of Warwick", r"Book of Estimates")], houses=460, unit="buildings",
   note="town article: 460 buildings; Book of Estimates: 157 houses; 250 families homeless")
ev("Wolverhampton", 1696, G, [("Wolverhampton", 0), ("Wolverhampton", 2)], houses=60, unit="homes")
# ---- 1700s
ev("Fordingbridge", 1702, G, [("Fordingbridge", 0)], houses=43, unit="dwelling houses")
ev("Chatteris", 1706, G, [("Chatteris", 2)], note="'destroyed most medieval and Georgian architecture' (with 1864)")
ev("Wincanton", 1707, G, [("Wincanton", 0)], note="'a great part of the town was destroyed by fires in 1707 and 1747'")
ev("Holt, Norfolk", 1708, G, [("Holt, Norfolk", 1)], note="'destroyed most of the medieval town in three hours'")
ev("New Alresford", 1710, G, [("New Alresford", 1)], note="'another in 1710'")
ev("Fakenham", 1718, P, [("Fakenham", 0)], note="scale not stated")
ev("Woburn, Bedfordshire", 1724, G, [("Woburn, Bedfordshire", 2)], note="'a third fire destroyed much of the town'")
ev("Bicester", 1724, P, [("Bicester", 0)], note="one street side")
ev("Buckingham", 1725, G, [("Buckingham", 0), ("Buckingham", 1)], houses=138, unit="dwellings", note="138 of 387 dwellings")
ev("Dorchester, Dorset", 1725, P, [("Dorchester, Dorset", 0)], note="one of 'several serious fires'")
ev("Blandford Forum", 1731, G, [("Blandford Forum", 6), (UF, r"\[\[Blandford Forum\]\]")], note="'almost all of Blandford's buildings were destroyed'")
ev("Tiverton, Devon", 1731, G, [("Tiverton, Devon", 4), ("Tiverton fire of 1731", r"298 houses were destroyed")], houses=298, unit="houses")
ev("Wellington, Somerset", 1731, G, [("Wellington, Somerset", 0)], note="'major rebuilding took place following a fire in the town'")
ev("Ramsey, Cambridgeshire", 1731, G, [("Ramsey, Cambridgeshire", 1)], note="'a great part of the High Street'")
ev("New Alresford", 1736, G, [("New Alresford", 1)], note="'a like calamity'")
ev("Stony Stratford", 1736, G, [("Stony Stratford", 0)], note="'almost completely consumed by fire'")
ev("Fakenham", 1738, G, [("Fakenham", 1)], houses=26, unit="buildings")
ev("Southam", 1741, G, [("Southam", 0)], note="'a large fire devastated the town'")
ev("Stony Stratford", 1742, G, [("Stony Stratford", 0)], note="second of the two fires")
ev("Crediton", 1743, G, [("Crediton", 0), ("Crediton", 1)], note="'completely destroying High Street and buildings in the West Town'")
ev("Honiton", 1747, G, [("Honiton", 1)], note="'the town was badly damaged by fires'")
ev("Wincanton", 1747, G, [("Wincanton", 0)], note="second year in the same sentence")
ev("Shepshed", 1753, G, [("Shepshed", 0)], houses=85, unit="bays of buildings")
ev("Hindon", 1754, G, [(UF, r"Great Fire of Hindon")], houses=144, unit="houses", note="a village; from List of urban fires; location from OS Open Names")
ev("Llanfair Caereinion", 1758, G, [("Llanfair Caereinion", 0)], note="'almost completely wiped out'")
ev("Havant", 1760, G, [("Havant", 0)], note="'much of Havant was destroyed'")
ev("Wareham, Dorset", 1762, G, [("Wareham, Dorset", 0)], note="'destroyed two thirds of the town'")
ev("Honiton", 1765, G, [("Honiton", 1)], note="second fire in the same sentence")
ev("Crediton", 1766, P, [("Crediton", 2)], note="'other large fires occurred in 1766, 1769 and 1772'; scale not stated")
ev("Crediton", 1769, P, [("Crediton", 2)], note="as above")
ev("Crediton", 1772, P, [("Crediton", 2)], note="as above")
ev("Dorchester, Dorset", 1775, P, [("Dorchester, Dorset", 0)], note="one of 'several serious fires'")
ev("Beaminster", 1781, P, [("Beaminster", 2)], note="scale not stated")
ev("Potton", 1783, G, [("Potton", 0)], note="'destroyed a large part of the town'")
ev("Biggleswade", 1785, G, [("Biggleswade", 0), ("Biggleswade", 5)], note="'destroying nearly one-third of the town'")
ev("Brandon, Suffolk", 1789, G, [("Brandon, Suffolk", 0)], note="named 'Brandon's Great Fire'")
ev("Minehead", 1791, G, [("Minehead", 0)], note="'major rebuilding took place in the Lower or Middle town area following a fire'")
# ---- 1800s
ev("Bedford", 1802, G, [("Bedford", 0)], houses=72, unit="properties", note="the Great Fire of Bedford")
ev("Stevenage", 1807, G, [("Stevenage", 2)], note="named the Great Fire of Stevenage")
ev("Chudleigh", 1807, G, [("Chudleigh", 5)], houses=180, unit="houses",
   note="the snippet has no year; the article dates the fire to 22 May 1807 (checked on en.wikipedia.org/wiki/Chudleigh, 27 Oct 2026)")
ev("Cullompton", 1839, G, [("Cullompton", 0), ("Cullompton", 1)], houses=145, unit="houses and other buildings", note="'about two thirds of the town burnt'")
ev("Cullompton", 1831, P, [("Cullompton", 4)], note="'It suffered from fires in 1831, 1867 and 1958'; scale not stated")
ev("Cullompton", 1867, P, [("Cullompton", 4)], note="as above")
ev("Newcastle upon Tyne", 1854, G, [("Newcastle upon Tyne", 0), (UF, r"Great fire of Newcastle and Gateshead")], note="explosion and fires; 53 killed; one event shared with Gateshead")
ev("Gateshead", 1854, G, [("Gateshead", 0)], note="same event as Newcastle; 'destroyed most of Gateshead's medieval heritage'")
ev("Chatteris", 1864, G, [("Chatteris", 2)], note="second year in the same sentence")
ev("Ottery St Mary", 1866, G, [("Ottery St Mary", 5), ("Ottery St Mary", 6)], note="'about a quarter of the town'")
ev("Whitstable", 1869, G, [(UF, r"Great Fire of Whitstable")], houses=71, unit="buildings", note="from List of urban fires")
ev("Ilfracombe", 1896, G, [("Ilfracombe", 0)], houses=35, unit="houses and business premises",
   note="the snippet has no year; the article dates it to 28 July 1896 and gives 35 houses and premises (checked on en.wikipedia.org/wiki/Ilfracombe, 27 Oct 2026)")
# ---- war burnings recorded for completeness (not counted)
for t, y, i in [("Alnwick", 1424, 0), ("Alnwick", 1448, 1), ("Hastings", 1339, 0), ("Hastings", 1377, 0), ("Newport, Isle of Wight", 1377, 0),
                ("Ryde", 1377, 0), ("Winchelsea", 1360, 1), ("Scarborough, North Yorkshire", 1318, 1), ("Morpeth, Northumberland", 1215, 0),
                ("Shrewsbury", 1234, 0), ("Bridgnorth", 1322, 0), ("Plymouth", 1403, 3), ("Wem", 1410, 2), ("Haverfordwest", 1405, 0),
                ("Warwick", 1016, 1), ("Hexham", 1297, 0), ("Lancaster, Lancashire", 1322, 0), ("Ruthin", 1400, 0), ("Flint, Flintshire", 1294, 0),
                ("Caerleon", 1171, 0), ("Chester-le-Street", 1080, 0), ("Norwich", 1004, 2), ("Bampton, Devon", 1645, 0), ("Machynlleth", 1644, 0),
                ("Yarmouth, Isle of Wight", 1544, 0), ("Winchester", 1141, 0)]:
    ev(t, y, W, [(t, i)], note="burning in war or raid")
# ---- outside England and Wales (in the record and on the map, not in the comparisons)
ev("Glasgow", 1652, G, [(UF, r"\[\[Glasgow\]\], \[\[Scotland")], note="a third of the city; over 1,000 families homeless")
ev("Dunfermline", 1624, G, [("Dunfermline", 0)], note="'engulfed around three-quarters of the medieval-renaissance burgh'")
ev("Edinburgh", 1700, G, [(UF, r"^\* 1700")], note="'over one half of the city was destroyed'")
ev("Edinburgh", 1824, G, [("Great Fire of Edinburgh", r"estimated 400 homes")], houses=400, unit="homes", note="the Great Fire of Edinburgh article (its title and opening give November 1824)")
ev("Stirling", 1405, P, [("Stirling", 0)], note="'a catastrophic fire'; scale in the town not stated")
ev("Lisburn", 1707, G, [("Lisburn", 1)], note="'the town was destroyed once again'")

# ---------------------------------------------------------------------------------------------------------
# place points and regions
osn = defaultdict(list)
with open(f"{H}/osnames_gb.tsv", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r["type"] == "populatedPlace" and r["local_type"] in ("City", "Town", "Village", "Suburban Area", "Hamlet"):
            osn[r["name1"]].append(r)
            if r["name2"]:
                osn[r["name2"]].append(r)
ORDER = {"City": 0, "Town": 1, "Suburban Area": 2, "Village": 3, "Hamlet": 4}


def os_point(title, coord=None):
    name = title.split(",")[0].strip()
    hint = title.split(",")[1].strip() if "," in title else ""
    if title == "London":
        name, hint = "London", ""
    sd = (T.get(title) or {}).get("shortdesc") or ""
    m = re.search(r"in (?:the )?([A-Z][A-Za-z ]+?)(?:,| UK| England| Wales|$)", sd)
    hint2 = m.group(1).strip() if m else ""
    c = osn.get(name, [])
    if coord:
        c = [x for x in c if abs(float(x["lat"]) - coord[0]) < 0.12 and abs(float(x["lon"]) - coord[1]) < 0.2] or c
    for h in (hint, hint2):
        if h:
            c2 = [x for x in c if h in (x["county"] + " " + x["district"] + " " + x["region"])]
            if c2:
                c = c2
                break
    c = sorted(c, key=lambda x: ORDER[x["local_type"]])
    return c[0] if c else None


def place_info(title):
    t = T.get(title)
    coord = (t["coord"]["lat"], t["coord"]["lon"]) if t and t.get("coord") else None
    o = os_point(title, coord)
    if title in ("Edinburgh", "Glasgow", "Stirling", "Dunfermline") and coord:
        return dict(lat=coord[0], lon=coord[1], country="Scotland", region="Scotland", loc_src=f"Wikipedia coordinate of '{title}'")
    if title == "Lisburn":
        return dict(lat=None, lon=None, country="Northern Ireland", region="Northern Ireland",
                    loc_src="not mapped: the Lisburn article in the data has no coordinate and OS Open Names covers Great Britain only")
    if coord:
        return dict(lat=coord[0], lon=coord[1], country=o["country"] if o else "", region=o["region"] if o else "",
                    loc_src=f"Wikipedia coordinate of '{title}'" + ("" if o else " (no OS match for region)"))
    if o:
        return dict(lat=float(o["lat"]), lon=float(o["lon"]), country=o["country"], region=o["region"],
                    loc_src=f"OS Open Names: {o['name1']} ({o['local_type']}, {o['district'] or o['county']})")
    raise SystemExit("no location for " + title)


# ---------------------------------------------------------------------------------------------------------
rows = []
used = defaultdict(list)
for e in E:
    texts, arts = [], []
    for art, loc in e["sources"]:
        if isinstance(loc, int):
            texts.append(snip(art, loc))
            used[(art, loc)].append(e)
        else:
            texts.append(find(art, loc))
        if art not in arts:
            arts.append(art)
    pi = place_info(e["place"])
    yrs = [int(y) for y in re.findall(r"\b(1[0-8]\d\d)\b", " ".join(texts))]
    rows.append({"town": e["display"], "town_article": e["place"], "year": e["year"], "century": f"{(e['year'] // 100) + 1}th",
                 "class": e["cls"], "counted": int(e["cls"] == G), "houses_lost": e["houses"] or "", "houses_unit": e["unit"],
                 "what_the_source_says": " | ".join(texts), "source_articles": "; ".join(arts),
                 "year_in_quoted_text": int(e["year"] in yrs), "country": pi["country"], "region": pi["region"],
                 "lat": round(pi["lat"], 5) if pi["lat"] is not None else "", "lon": round(pi["lon"], 5) if pi["lon"] is not None else "", "location_source": pi["loc_src"],
                 "manual_review": e["note"]})
rows.sort(key=lambda r: (r["year"], r["town"]))
cols = list(rows[0].keys())
with open(os.path.join(OUT, "great_fires.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print("rows", len(rows), Counter(r["class"] for r in rows))
print("great fires, year not in quoted text:", [(r["town"], r["year"]) for r in rows if r["counted"] and not r["year_in_quoted_text"]])

# ---------------------------------------------------------------------------------------------------------
# every dated fire sentence in the town articles, with a decision
WAR = r"raid|French|Scots|Scottish|rebel|army|siege|Civil War|invad|sacked|attack|Danes|Viking|troops|Royalist|Cavalier|Glyndwr|Glyndŵr|Despenser|Barons|Douglas|mob|riot|Wallace|Llywelyn|Myddleton|Sweyn|Edred|Edward III|Hundred Years"
BLD = r"church|chapel|mill|hall\b|Hall\b|manor|house\b|House\b|inn\b|Inn\b|hotel|Hotel|theatre|Theatre|school|School|castle|Castle|palace|Palace|rectory|Rectory|pier|Pier|cathedral|abbey|monastic|nunnery|library|Library|museum|station|tower|bridge|Shambles|wing|shop|warehouse|minster|Minster|barracks|market house"
rev = []
for title, v in T.items():
    for i, s in enumerate(v.get("fire_snippets") or []):
        c = clean(s)
        yrs = sorted({int(y) for y in re.findall(r"\b(1[0-8]\d\d)\b", c)})
        if not yrs and (title, i) not in used:
            continue
        if (title, i) in used:
            evs = used[(title, i)]
            cl = sorted({x["cls"] for x in evs})
            dec = "great_fire" if G in cl else cl[0]
            reason = "used for: " + ", ".join(f"{x['display']} {x['year']} ({x['cls']})" for x in evs)
        elif any(x["place"] == title and x["cls"] == G and str(x["year"]) in c for x in E):
            dec, reason = "context", "another sentence about a fire already recorded (often on the rebuilding)"
        elif re.search(WAR, c):
            dec, reason = "not used", "burning in war, raid, riot or by a mob, or martyrdom, or a mention in passing"
        elif re.search(r"burn(?:t|ed) at the stake", c):
            dec, reason = "not used", "execution by burning"
        elif re.search(BLD, c):
            dec, reason = "not used", "one building or site, or a fire elsewhere mentioned in passing"
        elif re.search(r"Great Fire of London|fire of London", c, re.I):
            dec, reason = "not used", "mentions the Great Fire of London in passing (London's fire is recorded once, under London)"
        else:
            dec, reason = "not used", "not a town-wide fire on reading (fire station, fire engine, figure of speech, other place, or no scale)"
        rev.append({"article": title, "snippet_index": i, "shortdesc": clean(v.get("shortdesc") or ""), "years_in_text": " ".join(map(str, yrs)),
                    "decision": dec, "reason": reason, "text": c[:700]})
with open(os.path.join(OUT, "fire_snippets_reviewed.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rev[0].keys()))
    w.writeheader()
    w.writerows(rev)
print("reviewed sentences", len(rev), Counter(r["decision"] for r in rev))
json.dump({"n_town_articles": len(T), "n_with_fire_sentence": sum(1 for v in T.values() if v.get("fire_snippets")),
           "n_fire_sentences": sum(len(v.get("fire_snippets") or []) for v in T.values()),
           "n_sentences_reviewed": len(rev)}, open(os.path.join(OUT, "_fires_meta.json"), "w"))
