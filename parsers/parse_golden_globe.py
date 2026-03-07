"""
Parser for the List of Golden Globe winners (film categories only).
Source: wikipedia/List of Golden Globe winners - Wikipedia.html
Outputs (in data/):
  Pre-1950 (table 0) — single undivided categories:
    golden_globe_picture.csv         year_from, year_to, film, is_winner, is_tie
    golden_globe_actor.csv           year_from, year_to, actor, film, is_winner, is_tie
    golden_globe_actress.csv         year_from, year_to, actress, film, is_winner, is_tie
    golden_globe_director.csv        year_from, year_to, director, film, is_winner, is_tie

  Post-1950 (table 1) — Drama / Musical/Comedy split; director appended to above:
    golden_globe_picture_drama.csv   year_from, year_to, film, is_winner, is_tie
    golden_globe_picture_comedy.csv  year_from, year_to, film, is_winner, is_tie
    golden_globe_actor_drama.csv     year_from, year_to, actor, film, is_winner, is_tie
    golden_globe_actor_comedy.csv    year_from, year_to, actor, film, is_winner, is_tie
    golden_globe_actress_drama.csv   year_from, year_to, actress, film, is_winner, is_tie
    golden_globe_actress_comedy.csv  year_from, year_to, actress, film, is_winner, is_tie
    (golden_globe_director.csv — post-1950 director rows appended to same file)

Notes:
- All rows are winners (this page lists winners only); is_winner is always "true".
- Film ties: multiple <a> tags in cell, each winner gets its own row with is_tie="true".
- Person+film ties: marked with "(TIE)" text; multiple person-film pairs each get a row.
- Person links are bare <a>; film links are <i><a> — used to separate them cleanly.
- N/a cells (comedy category not yet awarded): skipped.
- Year column contains ranges like "1943–1944"; split into year_from / year_to.
"""

import csv
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("beautifulsoup4 is required: pip install beautifulsoup4")

from canonicalize import build_lookups, normalize_records


HTML_FILE = Path(__file__).parent.parent / "wikipedia" / "List of Golden Globe winners - Wikipedia.html"
DATA_DIR = Path(__file__).parent.parent / "data"

FIELDNAMES_FILM = ["year_from", "year_to", "film", "is_winner", "is_tie"]
FIELDNAMES_ACTOR = ["year_from", "year_to", "actor", "film", "is_winner", "is_tie"]
FIELDNAMES_ACTRESS = ["year_from", "year_to", "actress", "film", "is_winner", "is_tie"]
FIELDNAMES_DIRECTOR = ["year_from", "year_to", "director", "film", "is_winner", "is_tie"]


def parse_year(th_text):
    """Extract year_from and year_to from strings like '1943–1944' or '1948–1950'."""
    years = re.findall(r"\d{4}", th_text)
    if len(years) >= 2:
        return years[0], years[1]
    if len(years) == 1:
        return years[0], years[0]
    return None, None


def clean_text(text):
    text = re.sub(r"[†‡]", "", text)
    text = re.sub(r"\s*\(TIE\)\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def is_na(cell):
    """True if the cell represents a non-awarded year (N/a placeholder)."""
    style = cell.get("style", "")
    text = cell.get_text(strip=True)
    return "ececec" in style or "background-color-interactive" in style or text in ("—", "— N/a")


def parse_film_cell(cell):
    """Film-only cell (Picture categories). Returns list of (film, is_tie)."""
    if is_na(cell):
        return []
    links = cell.find_all("a")
    if not links:
        return []
    films = [clean_text(a.get_text()) for a in links]
    is_tie = len(films) > 1
    return [(f, is_tie) for f in films]


def parse_person_film_cell(cell):
    """Person+film cell (Actor/Actress/Director). Returns list of (person, film, is_tie)."""
    if is_na(cell):
        return []
    full_text = cell.get_text()
    is_tie = "(TIE)" in full_text

    # Film links are wrapped in <i>; person links are bare <a>
    film_link_ids = {id(a) for i_tag in cell.find_all("i") for a in i_tag.find_all("a")}
    person_links = [a for a in cell.find_all("a") if id(a) not in film_link_ids]
    film_links = [a for a in cell.find_all("a") if id(a) in film_link_ids]

    entries = []
    for p_a, f_a in zip(person_links, film_links):
        person = clean_text(p_a.get_text())
        film = clean_text(f_a.get_text())
        entries.append((person, film, is_tie))
    return entries


def make_base(year_from, year_to):
    return {"year_from": year_from, "year_to": year_to, "is_winner": "true"}


def parse():
    html = HTML_FILE.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", class_="wikitable")

    # --- buckets ---
    picture_early = []
    actor_early = []
    actress_early = []
    director_all = []  # pre + post 1950

    picture_drama = []
    picture_comedy = []
    actor_drama = []
    actor_comedy = []
    actress_drama = []
    actress_comedy = []

    # ---------------------------------------------------------------
    # Table 0: pre-1950  (Best Picture | Best Actor | Best Actress | Director)
    # ---------------------------------------------------------------
    for row in tables[0].find_all("tr")[1:]:  # skip header
        year_th = row.find("th")
        if not year_th:
            continue
        year_from, year_to = parse_year(year_th.get_text())
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        base = make_base(year_from, year_to)

        # Best Picture
        for film, is_tie in parse_film_cell(cells[0]):
            picture_early.append({**base, "film": film, "is_tie": "true" if is_tie else "false"})

        # Best Actor
        for actor, film, is_tie in parse_person_film_cell(cells[1]):
            actor_early.append({**base, "actor": actor, "film": film, "is_tie": "true" if is_tie else "false"})

        # Best Actress
        for actress, film, is_tie in parse_person_film_cell(cells[2]):
            actress_early.append({**base, "actress": actress, "film": film, "is_tie": "true" if is_tie else "false"})

        # Director
        for director, film, is_tie in parse_person_film_cell(cells[3]):
            director_all.append({**base, "director": director, "film": film, "is_tie": "true" if is_tie else "false"})

    # ---------------------------------------------------------------
    # Table 1: post-1950  (Drama | Comedy | Drama Actor | Comedy Actor |
    #                       Drama Actress | Comedy Actress | Director)
    # ---------------------------------------------------------------
    for row in tables[1].find_all("tr")[1:]:  # skip header
        year_th = row.find("th")
        if not year_th:
            continue
        year_from, year_to = parse_year(year_th.get_text())
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        base = make_base(year_from, year_to)

        # Drama Picture
        for film, is_tie in parse_film_cell(cells[0]):
            picture_drama.append({**base, "film": film, "is_tie": "true" if is_tie else "false"})

        # Musical/Comedy Picture
        for film, is_tie in parse_film_cell(cells[1]):
            picture_comedy.append({**base, "film": film, "is_tie": "true" if is_tie else "false"})

        # Drama Actor
        for actor, film, is_tie in parse_person_film_cell(cells[2]):
            actor_drama.append({**base, "actor": actor, "film": film, "is_tie": "true" if is_tie else "false"})

        # Musical/Comedy Actor
        for actor, film, is_tie in parse_person_film_cell(cells[3]):
            actor_comedy.append({**base, "actor": actor, "film": film, "is_tie": "true" if is_tie else "false"})

        # Drama Actress
        for actress, film, is_tie in parse_person_film_cell(cells[4]):
            actress_drama.append({**base, "actress": actress, "film": film, "is_tie": "true" if is_tie else "false"})

        # Musical/Comedy Actress
        for actress, film, is_tie in parse_person_film_cell(cells[5]):
            actress_comedy.append({**base, "actress": actress, "film": film, "is_tie": "true" if is_tie else "false"})

        # Director (column 6, only in table 1)
        if len(cells) >= 7:
            for director, film, is_tie in parse_person_film_cell(cells[6]):
                director_all.append({**base, "director": director, "film": film, "is_tie": "true" if is_tie else "false"})

    return {
        "picture": picture_early,
        "actor": actor_early,
        "actress": actress_early,
        "director": director_all,
        "picture_drama": picture_drama,
        "picture_comedy": picture_comedy,
        "actor_drama": actor_drama,
        "actor_comedy": actor_comedy,
        "actress_drama": actress_drama,
        "actress_comedy": actress_comedy,
    }


def write_csv(path, fieldnames, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    ties = sum(1 for r in records if r["is_tie"] == "true")
    print(f"  {path.name}: {len(records)} rows, {ties} ties")


def main():
    data = parse()

    lookups = build_lookups()
    total = 0
    for key, person_col, person_lookup in [
        ("picture",       None,       None),
        ("actor",         "actor",    "actors"),
        ("actress",       "actress",  "actresses"),
        ("director",      "director", "directors"),
        ("picture_drama", None,       None),
        ("picture_comedy",None,       None),
        ("actor_drama",   "actor",    "actors"),
        ("actor_comedy",  "actor",    "actors"),
        ("actress_drama", "actress",  "actresses"),
        ("actress_comedy","actress",  "actresses"),
    ]:
        _, n = normalize_records(data[key], lookups, person_col=person_col, person_lookup=person_lookup)
        total += n
    if total:
        print(f"  Normalized: {total} values")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Pre-1950 (undivided categories):")
    write_csv(DATA_DIR / "golden_globe_picture.csv", FIELDNAMES_FILM, data["picture"])
    write_csv(DATA_DIR / "golden_globe_actor.csv", FIELDNAMES_ACTOR, data["actor"])
    write_csv(DATA_DIR / "golden_globe_actress.csv", FIELDNAMES_ACTRESS, data["actress"])

    print("Director (pre + post 1950 combined):")
    write_csv(DATA_DIR / "golden_globe_director.csv", FIELDNAMES_DIRECTOR, data["director"])

    print("Post-1950 Drama:")
    write_csv(DATA_DIR / "golden_globe_picture_drama.csv", FIELDNAMES_FILM, data["picture_drama"])
    write_csv(DATA_DIR / "golden_globe_actor_drama.csv", FIELDNAMES_ACTOR, data["actor_drama"])
    write_csv(DATA_DIR / "golden_globe_actress_drama.csv", FIELDNAMES_ACTRESS, data["actress_drama"])

    print("Post-1950 Musical/Comedy:")
    write_csv(DATA_DIR / "golden_globe_picture_comedy.csv", FIELDNAMES_FILM, data["picture_comedy"])
    write_csv(DATA_DIR / "golden_globe_actor_comedy.csv", FIELDNAMES_ACTOR, data["actor_comedy"])
    write_csv(DATA_DIR / "golden_globe_actress_comedy.csv", FIELDNAMES_ACTRESS, data["actress_comedy"])


if __name__ == "__main__":
    main()
