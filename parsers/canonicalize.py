"""
Canonical name/film normalization using data/oscar_nominations.csv as the source of truth.

For each name or film title in a precursor CSV, if an unambiguous match is found in the
Oscar data (after accent stripping, hyphen/period/comma normalization, and case-folding),
the value is replaced with the Oscar canonical form. Non-matching values are left unchanged.

Fuzzy key function handles the known divergence patterns:
  - Accent variants:     "Chloé Zhao"      ↔  "Chloe Zhao"
  - Hyphen variants:     "Bong Joon-ho"    ↔  "Bong Joon Ho"
  - Initial spacing:     "J. K. Simmons"   ↔  "J.K. Simmons"
  - Suffix punctuation:  "Cuba Gooding, Jr." ↔ "Cuba Gooding Jr."
  - Film casing:         "One Battle After Another" ↔ "One Battle after Another"

Usage in a parser's main():

    from canonicalize import build_lookups, normalize_records

    lookups = build_lookups()
    records, n = normalize_records(records, lookups, person_col="actor", person_lookup="actors")
    if n:
        print(f"  Normalized: {n} values")
"""

import csv
import re
import unicodedata
from pathlib import Path


OSCAR_CSV = Path(__file__).parent.parent / "data" / "oscar_nominations.csv"


def _key(s):
    """Produce a fuzzy match key: lowercase, strip accents, remove punctuation and spaces."""
    s = s.lower()
    # Strip combining accent characters (NFD decomposition)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Remove punctuation that varies across sources
    s = re.sub(r"[.\-,]", " ", s)
    # Collapse all whitespace (including spaces between initials like "J K" vs "JK")
    s = re.sub(r"\s+", "", s)
    return s


def _add(lookup, key, value):
    """Add an entry to a lookup dict; mark as ambiguous (None) on conflict."""
    if key not in lookup:
        lookup[key] = value
    elif lookup[key] != value:
        lookup[key] = None  # two different canonical forms → skip during lookup


def build_lookups():
    """Read oscar_nominations.csv and return canonical lookup dicts.

    Returns a dict with keys:
        'films'      — film titles (from Film column, all categories)
        'directors'  — director names (DIRECTING category)
        'actors'     — actor names (ACTOR IN A LEADING/SUPPORTING ROLE)
        'actresses'  — actress names (ACTRESS IN A LEADING/SUPPORTING ROLE)
    """
    films = {}
    directors = {}
    actors = {}
    actresses = {}

    with open(OSCAR_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Film column may be pipe-separated for split nominations
            for film in row["Film"].split("|"):
                film = film.strip()
                if film:
                    _add(films, _key(film), film)

            cat = row["CanonicalCategory"]
            name = row["Name"].strip()
            if not name:
                continue

            if cat == "DIRECTING":
                _add(directors, _key(name), name)
            elif cat in ("ACTOR IN A LEADING ROLE", "ACTOR IN A SUPPORTING ROLE"):
                _add(actors, _key(name), name)
            elif cat in ("ACTRESS IN A LEADING ROLE", "ACTRESS IN A SUPPORTING ROLE"):
                _add(actresses, _key(name), name)

    return {"films": films, "directors": directors, "actors": actors, "actresses": actresses}


def canonicalize(value, lookup):
    """Return the Oscar canonical form if an unambiguous match exists, else the original value."""
    canonical = lookup.get(_key(value))
    if canonical is None:
        return value  # not found, or ambiguous
    return canonical


def normalize_records(records, lookups, person_col=None, person_lookup=None):
    """Apply canonicalization to film and (optionally) person fields in-place.

    Args:
        records:       list of row dicts from parse()
        lookups:       dict returned by build_lookups()
        person_col:    name of the person column ('actor', 'actress', 'director'), or None
        person_lookup: key into lookups for the person type ('actors', 'actresses', 'directors')

    Returns:
        (records, n_changes) — records modified in place; n_changes counts substitutions made
    """
    n = 0
    for r in records:
        if "film" in r:
            new = canonicalize(r["film"], lookups["films"])
            if new != r["film"]:
                r["film"] = new
                n += 1
        if person_col and person_col in r:
            new = canonicalize(r[person_col], lookups[person_lookup])
            if new != r[person_col]:
                r[person_col] = new
                n += 1
    return records, n
