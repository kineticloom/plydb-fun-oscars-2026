"""
Parser for the TIFF People's Choice Award Wikipedia page.
Outputs: data/tiff_peoples_choice.csv with columns: year, film, director, is_winner, is_tie
"""

import csv
import re
from pathlib import Path
from html.parser import HTMLParser


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Toronto International Film Festival People's Choice Award - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "tiff_peoples_choice.csv"


try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


def clean_text(element):
    """Extract clean text from a BeautifulSoup element, stripping tags."""
    return element.get_text(separator=" ", strip=True)


def clean_film_title(text):
    """Clean up film title - remove extra whitespace."""
    # Collapse internal whitespace
    return re.sub(r"\s+", " ", text).strip()


def is_winner_cell(td):
    """Check if a film <td> cell indicates a winner (yellow background)."""
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def parse_rowspan(td):
    """Parse rowspan value from a <td>, handling malformed HTML like rowspan='3&quot;'."""
    rawspan = td.get("rowspan", "1")
    # Strip any non-digit characters (handles rowspan='3"' from malformed HTML)
    digits = re.sub(r"\D", "", str(rawspan))
    return int(digits) if digits else 1


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Find the main wikitable
    table = soup.find("table", class_="wikitable")
    if not table:
        raise RuntimeError("Could not find wikitable in HTML")

    rows = table.find_all("tr")

    records = []
    current_year = None
    year_rows_remaining = 0  # how many more rows the current year spans

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue  # header row

        cell_idx = 0

        # Determine year: if the year cell is in this row
        if year_rows_remaining <= 0:
            # First cell should be the year
            year_td = cells[cell_idx]
            current_year = clean_text(year_td)
            # Parse out just the 4-digit year in case there's extra text
            m = re.search(r"\d{4}", current_year)
            current_year = m.group(0) if m else current_year
            year_rows_remaining = parse_rowspan(year_td)
            cell_idx += 1

        year_rows_remaining -= 1

        # Film cell
        if cell_idx >= len(cells):
            continue
        film_td = cells[cell_idx]
        winner = is_winner_cell(film_td)
        film = clean_film_title(clean_text(film_td))
        cell_idx += 1

        # Director cell
        if cell_idx >= len(cells):
            continue
        director_td = cells[cell_idx]
        director = clean_text(director_td)

        records.append({
            "year": current_year,
            "film": film,
            "director": director,
            "is_winner": "true" if winner else "false",
            "is_tie": "false",
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
