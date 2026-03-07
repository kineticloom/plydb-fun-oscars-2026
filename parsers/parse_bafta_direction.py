"""
Parser for the BAFTA Award for Best Direction.
Source: wikipedia/BAFTA Award for Best Direction - Wikipedia.html
Output: data/bafta_direction.csv with columns: year, director, film, is_winner, is_tie, num_films

Notes:
- Year cells are <td rowspan="N">, not <th>
- Row types by td count:
    4 tds: [year·rs] [director] [film] [ref·rs] — new year + director (always the winner)
    2 tds: [director] [film]                    — same year, new director (nominee)
    1 td:  [film]                               — director carried via rowspan (multiple films)
- Winner: background:#FAEB86 on director cell
- Multi-film nominees for same director+year are consolidated (film joined with " / ", num_films > 1)
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Direction - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_direction.csv"


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
        current_director = None
        current_winner = False
        director_rowspan = 0

        for row in table.find_all("tr"):
            tds = row.find_all("td")
            n = len(tds)

            if n == 4:
                # [year·rs] [director] [film] [ref·rs]
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                director_td = tds[1]
                current_director, is_tie = extract_name(director_td)
                current_winner = is_winner_cell(director_td)
                director_rowspan = int(director_td.get("rowspan", 1)) - 1
                film = clean(tds[2])

            elif n == 2:
                # [director] [film]
                director_td = tds[0]
                current_director, is_tie = extract_name(director_td)
                current_winner = is_winner_cell(director_td)
                director_rowspan = int(director_td.get("rowspan", 1)) - 1
                film = clean(tds[1])

            elif n == 1:
                # [film] — director carried via rowspan
                if director_rowspan > 0:
                    is_tie = False
                    film = clean(tds[0])
                    director_rowspan -= 1
                else:
                    continue

            else:
                continue

            records.append({
                "year": current_year,
                "director": current_director,
                "film": film,
                "is_winner": "true" if current_winner else "false",
                "is_tie": "true" if is_tie else "false",
            })

    # Consolidate same director+year with multiple films (rowspan multi-film)
    seen = {}
    consolidated = []
    for r in records:
        key = (r["year"], r["director"])
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
    records, n = normalize_records(records, lookups, person_col="director", person_lookup="directors")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "director", "film", "is_winner", "is_tie", "num_films"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")
    multi = [r for r in records if r["num_films"] > 1]
    if multi:
        print(f"  Multi-film: {len(multi)} rows")
        for r in multi:
            print(f"    {r['year']} {r['director']}: {r['film']}")


if __name__ == "__main__":
    main()
