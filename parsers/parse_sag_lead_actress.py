"""
Parser for the SAG Award for Outstanding Performance by a Female Actor in a Leading Role.
Source: wikipedia/Actor Award for Outstanding Performance by a Female Actor in a Leading Role - Wikipedia.html
Output: data/sag_lead_actress.csv with columns: year, actress, film, is_winner, is_tie
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Actor Award for Outstanding Performance by a Female Actor in a Leading Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "sag_lead_actress.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[†‡]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    tables = [t for t in soup.find_all("table", class_="wikitable") if "sortable" in t.get("class", [])]
    if not tables:
        raise RuntimeError("Could not find sortable wikitables in HTML")

    records = []

    for table in tables:
        current_year = None

        for row in table.find_all("tr"):
            year_th = row.find("th", attrs={"scope": "row"})
            if year_th:
                m = re.search(r"\d{4}", year_th.get_text(" ", strip=True))
                current_year = m.group(0) if m else None

            tds = row.find_all("td")
            if len(tds) < 2:
                continue

            actress_td = tds[0]
            film_td = tds[1]

            records.append({
                "year": current_year,
                "actress": clean(actress_td),
                "film": clean(film_td),
                "is_winner": "true" if is_winner_cell(actress_td) else "false",
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
