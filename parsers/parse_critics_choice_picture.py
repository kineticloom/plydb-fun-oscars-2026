"""
Parser for the Critics' Choice Movie Award for Best Picture.
Source: wikipedia/Critics' Choice Movie Award for Best Picture - Wikipedia.html
Output: data/critics_choice_picture.csv with columns: year, film, director, is_winner, is_tie

Notes:
- Winner rows are highlighted in blue (#B0C4DE) on film cell
- Tables use class "wikitable sortable sticky-header"
- 3 columns: Year (th), Film, Director(s)
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Critics' Choice Movie Award for Best Picture - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "critics_choice_picture.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#B0C4DE" in style or "background: #B0C4DE" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[‡†]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_film(element):
    text = clean(element)
    is_tie = "(TIE)" in text
    title = re.sub(r"\s*\(TIE\)\s*", "", text).strip()
    return title, is_tie


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Target the sortable data tables, not the plain legend table
    tables = [t for t in soup.find_all("table", class_="wikitable") if "sortable" in t.get("class", [])]
    if not tables:
        raise RuntimeError("Could not find sortable wikitables in HTML")

    records = []

    for table in tables:
        current_year = None

        for row in table.find_all("tr"):
            th = row.find("th")
            if th:
                m = re.search(r"\d{4}", th.get_text())
                if m:
                    current_year = m.group(0)

            tds = row.find_all("td")
            if len(tds) < 2:
                continue

            film_td = tds[0]
            director_td = tds[1]

            film, is_tie = extract_film(film_td)
            director = clean(director_td)
            winner = is_winner_cell(film_td)

            records.append({
                "year": current_year,
                "film": film,
                "director": director,
                "is_winner": "true" if winner else "false",
                "is_tie": "true" if is_tie else "false",
            })

    return records


def main():
    records = parse()
    lookups = build_lookups()
    records, n = normalize_records(records, lookups, person_col="director", person_lookup="directors")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "film", "director", "is_winner", "is_tie"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
