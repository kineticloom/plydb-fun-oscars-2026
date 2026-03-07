"""
Parser for the SAG Award for Outstanding Performance by a Cast in a Motion Picture.
Source: wikipedia/Actor Award for Outstanding Performance by a Cast in a Motion Picture - Wikipedia.html
Output: data/sag_cast_award.csv with columns: year, film, is_winner, is_tie
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Actor Award for Outstanding Performance by a Cast in a Motion Picture - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "sag_cast_award.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def parse_rowspan(td):
    rawspan = td.get("rowspan", "1")
    digits = re.sub(r"\D", "", str(rawspan))
    return int(digits) if digits else 1


def extract_year(td):
    """Extract 4-digit year from a year cell (which may contain <br> and <small> tags)."""
    text = td.get_text(" ", strip=True)
    m = re.search(r"\d{4}", text)
    return m.group(0) if m else text


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Data is split across multiple wikitables (one per decade)
    tables = soup.find_all("table", class_="wikitable")
    if not tables:
        raise RuntimeError("Could not find any wikitable in HTML")

    records = []

    for table in tables:
        rows = table.find_all("tr")
        current_year = None
        year_rows_remaining = 0

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue  # header row

            cell_idx = 0

            if year_rows_remaining <= 0:
                year_td = cells[cell_idx]
                current_year = extract_year(year_td)
                year_rows_remaining = parse_rowspan(year_td)
                cell_idx += 1

            year_rows_remaining -= 1

            if cell_idx >= len(cells):
                continue

            film_td = cells[cell_idx]
            winner = is_winner_cell(film_td)
            film = re.sub(r"\s+", " ", film_td.get_text(" ", strip=True))

            records.append({
                "year": current_year,
                "film": film,
                "is_winner": "true" if winner else "false",
                "is_tie": "false",
            })

    return records


def main():
    records = parse()
    lookups = build_lookups()
    records, n = normalize_records(records, lookups)
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "film", "is_winner", "is_tie"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
