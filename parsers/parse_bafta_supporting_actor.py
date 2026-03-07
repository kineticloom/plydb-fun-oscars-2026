"""
Parser for the BAFTA Award for Best Actor in a Supporting Role.
Source: wikipedia/BAFTA Award for Best Actor in a Supporting Role - Wikipedia.html
Output: data/bafta_supporting_actor.csv with columns: year, actor, film, is_winner, is_tie

Notes:
- Year cells are <td rowspan="N">, not <th>
- Row types by td count:
    5 tds: [year·rs] [actor] [film] [role] [ref·rs] — new year + actor
    3 tds: [actor] [film] [role]                    — same year, new actor
    2 tds: [film] [role]                            — same actor via rowspan (multiple films)
    2 tds (year + "Not awarded")                    — skipped
- Winner: background:#FAEB86 on actor cell
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "BAFTA Award for Best Actor in a Supporting Role - Wikipedia.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "bafta_supporting_actor.csv"


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
        current_actor = None
        current_winner = False

        for row in table.find_all("tr"):
            tds = row.find_all("td")
            n = len(tds)

            if n == 5:
                # [year·rs] [actor] [film] [role] [ref·rs]
                year_text = tds[0].get_text(" ", strip=True)
                m = re.search(r"\d{4}", year_text)
                current_year = m.group(0) if m else current_year

                actor_td = tds[1]
                current_actor, is_tie = extract_name(actor_td)
                current_winner = is_winner_cell(actor_td)
                film = clean(tds[2])

            elif n == 3:
                # [actor] [film] [role]
                actor_td = tds[0]
                current_actor, is_tie = extract_name(actor_td)
                current_winner = is_winner_cell(actor_td)
                film = clean(tds[1])

            elif n == 2:
                # Either [film] [role] (actor carried via rowspan)
                # or [year] [Not awarded] — skip the latter
                first_text = tds[0].get_text(" ", strip=True)
                if re.search(r"\d{4}", first_text):
                    m = re.search(r"\d{4}", first_text)
                    current_year = m.group(0) if m else current_year
                    continue
                is_tie = False
                film = clean(tds[0])

            else:
                continue

            records.append({
                "year": current_year,
                "actor": current_actor,
                "film": film,
                "is_winner": "true" if current_winner else "false",
                "is_tie": "true" if is_tie else "false",
            })

    # Consolidate same actor appearing multiple times in one year (multiple films via rowspan)
    seen = {}
    consolidated = []
    for r in records:
        key = (r["year"], r["actor"])
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
    records, n = normalize_records(records, lookups, person_col="actor", person_lookup="actors")
    if n:
        print(f"  Normalized: {n} values")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "actor", "film", "is_winner", "is_tie", "num_films"])
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} rows to {OUTPUT_FILE}")
    winners = sum(1 for r in records if r["is_winner"] == "true")
    print(f"  Winners: {winners}, Nominees: {len(records) - winners}")


if __name__ == "__main__":
    main()
