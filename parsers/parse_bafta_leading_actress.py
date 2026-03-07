"""
Parser for the BAFTA Award for Best Actress in a Leading Role.
Source: wikipedia/BAFTA Award for Best Actress in a Leading Role - Wikipedia.html
Output: data/bafta_leading_actress.csv with columns: year, actress, film, is_winner, is_tie, category

Notes:
- Early years (tables 0-1, 1952-1969) split into "Best British Actress" / "Best Foreign Actress"
  categories, detected from <th> text in section-header rows.
- Later years (tables 2-7, 1970+) use unified "Best Actress" category.
- Row types:
    th row + 1 td [year·rs]           — category section header with year; update category + year
    th row + 0 tds                    — category section header only (same year); update category
    5 tds: [year·rs][actress][film][role][ref·rs]  — modern unified format
    4 tds: [actress][film][role][ref·rs]            — early format under category header
    3 tds: [actress][film][role]
    2 tds: [film][role] if actress cell had rowspan (same actress, new film)
           [actress][role] if film cell had rowspan (new actress, same film)
- Winner: background:#FAEB86 on actress cell
- Multi-film nominees for same actress+year+category are consolidated (film joined with " / ")
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Actress in a Leading Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_leading_actress.csv"


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
        current_actress = None
        current_winner = False
        current_film = None
        current_category = "Best Actress"
        actress_rowspan = 0

        for row in table.find_all("tr"):
            # Detect category from th text
            for th in row.find_all("th"):
                th_text = th.get_text(" ", strip=True)
                if "Best British Actress" in th_text:
                    current_category = "Best British Actress"
                elif "Best Foreign Actress" in th_text:
                    current_category = "Best Foreign Actress"
                elif th_text == "Best Actress":
                    current_category = "Best Actress"

            tds = row.find_all("td")
            n = len(tds)

            if n == 0:
                continue

            if n == 1:
                # Year cell alongside a category th
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                actress_rowspan = 0
                continue

            if n == 5:
                # [year·rs] [actress] [film] [role] [ref·rs]
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                actress_td = tds[1]
                current_actress, is_tie = extract_name(actress_td)
                current_winner = is_winner_cell(actress_td)
                actress_rowspan = int(actress_td.get("rowspan", 1)) - 1
                current_film = clean(tds[2])
                film = current_film

            elif n == 4:
                # [actress] [film] [role] [ref·rs] — early year under category header
                actress_td = tds[0]
                current_actress, is_tie = extract_name(actress_td)
                current_winner = is_winner_cell(actress_td)
                actress_rowspan = int(actress_td.get("rowspan", 1)) - 1
                current_film = clean(tds[1])
                film = current_film

            elif n == 3:
                # [actress] [film] [role]
                actress_td = tds[0]
                current_actress, is_tie = extract_name(actress_td)
                current_winner = is_winner_cell(actress_td)
                actress_rowspan = int(actress_td.get("rowspan", 1)) - 1
                current_film = clean(tds[1])
                film = current_film

            elif n == 2:
                if actress_rowspan > 0:
                    # [film] [role] — actress carried via rowspan
                    is_tie = False
                    current_film = clean(tds[0])
                    film = current_film
                    actress_rowspan -= 1
                else:
                    # [actress] [role] — film carried via rowspan
                    actress_td = tds[0]
                    current_actress, is_tie = extract_name(actress_td)
                    current_winner = is_winner_cell(actress_td)
                    film = current_film

            else:
                continue

            records.append({
                "year": current_year,
                "actress": current_actress,
                "film": film,
                "is_winner": "true" if current_winner else "false",
                "is_tie": "true" if is_tie else "false",
                "category": current_category,
            })

    # Consolidate same actress+year+category with multiple films (rowspan multi-film)
    seen = {}
    consolidated = []
    for r in records:
        key = (r["year"], r["actress"], r["category"])
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
    records, n = normalize_records(records, lookups, person_col="actress", person_lookup="actresses")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "actress", "film", "is_winner", "is_tie", "category", "num_films"])
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
