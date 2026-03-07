"""
Parser for the BAFTA Award for Best Film.
Source: wikipedia/BAFTA Award for Best Film - Wikipedia.html
Output: data/bafta_film.csv with columns: year, film, director, is_winner, is_tie, num_films

Notes:
- Tables lack "sortable" class; filtered by presence of "Film" column header th.
- Row types by td count:
    5 tds: [year·rs] [film] [director] [producer] [country] — first row for the year (winner highlighted)
    4 tds: [film] [director] [producer] [country]           — nominee (year carried via rowspan)
    3 tds: [film] [director] [producer]                     — nominee (year + country both carried)
- Winner: background:#FAEB86 on film cell
- num_films is always 1 (no multi-film-per-entry cases for Best Film)
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Film - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_film.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[†‡]", "", text)
    text = re.sub(r"\[[A-Za-z0-9 ]+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_film(element):
    text = clean(element)
    is_tie = "(TIE)" in text or "(ex-æquo)" in text or "(ex-aequo)" in text
    title = re.sub(r"\s*\((?:TIE|ex-æquo|ex-aequo)\)\s*", "", text).strip()
    return title, is_tie


def has_film_header(table):
    for th in table.find_all("th"):
        if th.get_text(strip=True) == "Film":
            return True
    return False


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    tables = [t for t in soup.find_all("table", class_="wikitable") if has_film_header(t)]
    if not tables:
        raise RuntimeError("Could not find data tables in HTML")

    records = []

    for table in tables:
        current_year = None

        for row in table.find_all("tr"):
            tds = row.find_all("td")
            n = len(tds)

            if n == 5:
                # [year·rs] [film] [director] [producer] [country]
                m = re.search(r"\d{4}", tds[0].get_text())
                if m:
                    current_year = m.group(0)
                film_td = tds[1]
                director_td = tds[2]

            elif n in (3, 4):
                # [film] [director] [producer] ([country])
                film_td = tds[0]
                director_td = tds[1]

            else:
                continue

            film, is_tie = extract_film(film_td)
            director = clean(director_td)
            winner = is_winner_cell(film_td)

            records.append({
                "year": current_year,
                "film": film,
                "director": director,
                "is_winner": "true" if winner else "false",
                "is_tie": "true" if is_tie else "false",
                "num_films": 1,
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
        writer = csv.DictWriter(f, fieldnames=["year", "film", "director", "is_winner", "is_tie", "num_films"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
