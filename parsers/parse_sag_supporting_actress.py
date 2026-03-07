"""
Parser for the SAG Award for Outstanding Performance by a Female Actor in a Supporting Role.
Source: wikipedia/Actor Award for Outstanding Performance by a Female Actor in a Supporting Role - Wikipedia.html
Output: data/sag_supporting_actress.csv with columns: year, actress, film, is_winner, is_tie
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Actor Award for Outstanding Performance by a Female Actor in a Supporting Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "sag_supporting_actress.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def clean(element):
    # Remove <small> annotations (e.g. "won Academy Award for Best Actress") before extracting text
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    # Remove footnote markers like ‡ or †
    text = re.sub(r"[†‡]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Target only the sortable wikitables (decade tables), not the legend table
    tables = [t for t in soup.find_all("table", class_="wikitable") if "sortable" in t.get("class", [])]
    if not tables:
        raise RuntimeError("Could not find sortable wikitables in HTML")

    records = []

    for table in tables:
        current_year = None

        for row in table.find_all("tr"):
            # Year cell is a <th scope="row"> when present
            year_th = row.find("th", attrs={"scope": "row"})
            if year_th:
                year_text = year_th.get_text(" ", strip=True)
                m = re.search(r"\d{4}", year_text)
                current_year = m.group(0) if m else year_text

            tds = row.find_all("td")
            # Rows with data have at least actress + film cells
            # (ref cell is rowspanned so may or may not be present)
            if len(tds) < 2:
                continue

            actress_td = tds[0]
            film_td = tds[1]

            winner = is_winner_cell(actress_td)
            actress = clean(actress_td)
            film = clean(film_td)

            records.append({
                "year": current_year,
                "actress": actress,
                "film": film,
                "is_winner": "true" if winner else "false",
                "is_tie": "false",
            })

    return records


def main():
    records = parse()
    lookups = build_lookups()
    records, n = normalize_records(records, lookups, person_col="actress", person_lookup="actresses")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "actress", "film", "is_winner", "is_tie"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
