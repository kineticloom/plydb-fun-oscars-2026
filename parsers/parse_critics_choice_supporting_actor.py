"""
Parser for the Critics' Choice Movie Award for Best Supporting Actor.
Source: wikipedia/Critics' Choice Movie Award for Best Supporting Actor - Wikipedia.html
Output: data/critics_choice_supporting_actor.csv with columns: year, actor, film, is_winner

Notes:
- Early years (pre-2010) list winners only; later years include nominees
- Winner rows are highlighted in blue (#B0C4DE) rather than the typical yellow
- Some nominee rows share a film cell via rowspan (e.g. two actors from Belfast)
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "Critics' Choice Movie Award for Best Supporting Actor - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "critics_choice_supporting_actor.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#B0C4DE" in style or "background: #B0C4DE" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[‡†]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_name(element):
    text = clean(element)
    is_tie = "(TIE)" in text
    name = re.sub(r"\s*\(TIE\)\s*", "", text).strip()
    return name, is_tie


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Data tables have width="70%"; excludes the infobox
    tables = soup.find_all("table", class_="wikitable", attrs={"width": "70%"})
    if not tables:
        raise RuntimeError("Could not find data tables in HTML")

    records = []

    for table in tables:
        current_year = None
        # Track film cells that span multiple rows: (film_text, remaining_rows)
        pending_film = None
        pending_film_rows = 0

        for row in table.find_all("tr"):
            # Year cell is a <th> containing a 4-digit year
            th = row.find("th")
            if th:
                m = re.search(r"\d{4}", th.get_text())
                if m:
                    current_year = m.group(0)

            tds = row.find_all("td")
            if not tds:
                continue

            actor_td = tds[0]
            actor, is_tie = extract_name(actor_td)
            winner = is_winner_cell(actor_td)

            # Film is tds[2] when present; otherwise carried over from a rowspan
            if len(tds) >= 3:
                film_td = tds[2]
                film = clean(film_td)
                rowspan = int(film_td.get("rowspan", 1))
                if rowspan > 1:
                    pending_film = film
                    pending_film_rows = rowspan - 1
            elif pending_film_rows > 0:
                film = pending_film
                pending_film_rows -= 1
            else:
                film = ""

            records.append({
                "year": current_year,
                "actor": actor,
                "film": film,
                "is_winner": "true" if winner else "false",
                "is_tie": "true" if is_tie else "false",
            })

    return records


def main():
    records = parse()
    lookups = build_lookups()
    records, n = normalize_records(records, lookups, person_col="actor", person_lookup="actors")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "actor", "film", "is_winner", "is_tie"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
