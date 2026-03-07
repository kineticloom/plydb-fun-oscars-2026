"""
Parser for the BAFTA Award for Best Actor in a Leading Role.
Source: wikipedia/BAFTA Award for Best Actor in a Leading Role - Wikipedia.html
Output: data/bafta_leading_actor.csv with columns: year, actor, film, is_winner, is_tie, category

Notes:
- Early years (tables 0-1, 1952-1969) split into "Best British Actor" / "Best Foreign Actor"
  categories, detected from <th> text in section-header rows.
- Later years (tables 2-7, 1970+) use unified "Best Actor" category.
- Row types:
    th row + 1 td [year·rs]           — category section header with year; update category + year
    th row + 0 tds                    — category section header only (same year); update category
    5 tds: [year·rs][actor][film][role][ref·rs]  — modern unified format
    4 tds: [actor][film][role][ref·rs]            — early format under category header
    3 tds: [actor][film][role]
    2 tds: [film][role] if actor cell had rowspan (same actor, new film)
           [actor][role] if film cell had rowspan (new actor, same film)
- Winner: background:#FAEB86 on actor cell
- Multi-film nominees for same actor+year+category are consolidated (film joined with " / ")
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Actor in a Leading Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_leading_actor.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[†‡]", "", text)
    text = re.sub(r"\[[A-Za-z]\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_name(element):
    text = clean(element)
    is_tie = "(TIE)" in text
    name = re.sub(r"\s*\(TIE\)\s*", "", text).strip()
    return name, is_tie


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    tables = [t for t in soup.find_all("table", class_="wikitable") if "sortable" in t.get("class", [])]
    if not tables:
        raise RuntimeError("Could not find sortable wikitables in HTML")

    records = []

    for table in tables:
        current_year = None
        current_actor = None
        current_winner = False
        current_film = None
        current_category = "Best Actor"
        actor_rowspan = 0

        for row in table.find_all("tr"):
            # Detect category from th text
            for th in row.find_all("th"):
                th_text = th.get_text(" ", strip=True)
                if "Best British Actor" in th_text:
                    current_category = "Best British Actor"
                elif "Best Foreign Actor" in th_text:
                    current_category = "Best Foreign Actor"
                elif th_text == "Best Actor":
                    current_category = "Best Actor"

            tds = row.find_all("td")
            n = len(tds)

            if n == 0:
                continue

            if n == 1:
                # Year cell alongside a category th
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                actor_rowspan = 0
                continue

            if n == 5:
                # [year·rs] [actor] [film] [role] [ref·rs]
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                actor_td = tds[1]
                current_actor, is_tie = extract_name(actor_td)
                current_winner = is_winner_cell(actor_td)
                actor_rowspan = int(actor_td.get("rowspan", 1)) - 1
                current_film = clean(tds[2])
                film = current_film

            elif n == 4:
                # [actor] [film] [role] [ref·rs] — early year under category header
                actor_td = tds[0]
                current_actor, is_tie = extract_name(actor_td)
                current_winner = is_winner_cell(actor_td)
                actor_rowspan = int(actor_td.get("rowspan", 1)) - 1
                current_film = clean(tds[1])
                film = current_film

            elif n == 3:
                # [actor] [film] [role]
                actor_td = tds[0]
                current_actor, is_tie = extract_name(actor_td)
                current_winner = is_winner_cell(actor_td)
                actor_rowspan = int(actor_td.get("rowspan", 1)) - 1
                current_film = clean(tds[1])
                film = current_film

            elif n == 2:
                if actor_rowspan > 0:
                    # [film] [role] — actor carried via rowspan
                    is_tie = False
                    current_film = clean(tds[0])
                    film = current_film
                    actor_rowspan -= 1
                else:
                    # [actor] [role] — film carried via rowspan
                    actor_td = tds[0]
                    current_actor, is_tie = extract_name(actor_td)
                    current_winner = is_winner_cell(actor_td)
                    film = current_film

            else:
                continue

            records.append({
                "year": current_year,
                "actor": current_actor,
                "film": film,
                "is_winner": "true" if current_winner else "false",
                "is_tie": "true" if is_tie else "false",
                "category": current_category,
            })

    # Consolidate same actor+year+category with multiple films (rowspan multi-film)
    seen = {}
    consolidated = []
    for r in records:
        key = (r["year"], r["actor"], r["category"])
        if key in seen:
            consolidated[seen[key]]["film"] += " / " + r["film"]
            consolidated[seen[key]]["num_films"] += 1
        else:
            r["num_films"] = 1
            seen[key] = len(consolidated)
            consolidated.append(r)
    return consolidated


def main():
    records = parse()
    lookups = build_lookups()
    records, n = normalize_records(records, lookups, person_col="actor", person_lookup="actors")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "actor", "film", "is_winner", "is_tie", "category", "num_films"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")
    cats = {}
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count} rows")


if __name__ == "__main__":
    main()
