"""
Parser for the BAFTA Award for Best Actress in a Supporting Role.
Source: wikipedia/BAFTA Award for Best Actress in a Supporting Role - Wikipedia.html
Output: data/bafta_supporting_actress.csv with columns: year, actress, film, is_winner, is_tie

Notes:
- Year cells are <td rowspan="N">, not <th>
- Table headers label columns as "Actor | Role(s) | Film" but actual data order is
  Actress | Film | Role (the last two are swapped in the header)
- Row types by td count:
    5 tds: [year·rs] [actress] [film] [role] [ref·rs] — new year + actress
    3 tds: [actress] [film] [role]                    — same year, new actress
    2 tds: [film] [role]                              — same actress via rowspan (multiple films)
- Winner: background:#FAEB86 on actress cell
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Actress in a Supporting Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_supporting_actress.csv"


def is_winner_cell(td):
    style = td.get("style", "")
    return "background:#FAEB86" in style or "background: #FAEB86" in style


def clean(element):
    for small in element.find_all("small"):
        small.decompose()
    text = element.get_text(" ", strip=True)
    text = re.sub(r"[†‡]", "", text)
    # Strip footnote markers like [A], [B]
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

        for row in table.find_all("tr"):
            tds = row.find_all("td")
            n = len(tds)

            if n == 5:
                # [year·rs] [actress] [film] [role] [ref·rs]
                year_text = tds[0].get_text(" ", strip=True)
                m = re.search(r"\d{4}", year_text)
                current_year = m.group(0) if m else current_year

                actress_td = tds[1]
                current_actress, is_tie = extract_name(actress_td)
                current_winner = is_winner_cell(actress_td)
                film = clean(tds[2])

            elif n == 3:
                # [actress] [film] [role]
                actress_td = tds[0]
                current_actress, is_tie = extract_name(actress_td)
                current_winner = is_winner_cell(actress_td)
                film = clean(tds[1])

            elif n == 2:
                # [film] [role] — actress carried via rowspan
                is_tie = False
                film = clean(tds[0])

            else:
                continue

            records.append({
                "year": current_year,
                "actress": current_actress,
                "film": film,
                "is_winner": "true" if current_winner else "false",
                "is_tie": "true" if is_tie else "false",
            })

    # Consolidate same actress appearing multiple times in one year (multiple films via rowspan)
    seen = {}
    consolidated = []
    for r in records:
        key = (r["year"], r["actress"])
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
        writer = csv.DictWriter(f, fieldnames=["year", "actress", "film", "is_winner", "is_tie", "num_films"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
