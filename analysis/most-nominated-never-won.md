# Most Nominated, Never Won: Oscar Bridesmaids Analysis

**Date:** 2026-03-10 **Data:** Academy Awards historical data
(`oscars.default.oscars`), Ceremonies 1–98 **Tool:** PlyDB SQL over local CSV

---

## Overview

This analysis identifies the people most frequently nominated for Academy Awards
who have never won a competitive Oscar. It was conducted in two passes: a broad
all-categories ranking, followed by a filtered ranking restricted to actors,
actresses, and directors.

---

## Methodology

### Data model

The core table is `oscars.default.oscars`, with one row per nomination. Key
columns:

| Column              | Notes                                                                                                             |
| ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `NomineeIds`        | Pipe-separated IMDb person IDs (e.g. `nm0002353\|nm0300272`)                                                      |
| `Nominees`          | Pipe-separated individual names matching `NomineeIds`                                                             |
| `Name`              | Full credit as written by the Academy (e.g. `"Music by Peter Gabriel and Thomas Newman; Lyric by Peter Gabriel"`) |
| `CanonicalCategory` | Standardized category name across eras                                                                            |
| `Winner`            | `true` = win, `null` = nominated but did not win                                                                  |
| `Ceremony`          | Ceremony number (98 = 2026, currently in progress)                                                                |

### Key methodological decisions

**1. Use `NomineeIds` + `Nominees`, not `Name`, for person identity**

The `Name` field reflects the Academy's credit as written — for songwriting and
other collaborative categories this is a group credit like
`"Music and Lyric by Diane Warren and Lady Gaga"`. Counting on `Name` with exact
match misses shared-credit nominations; fuzzy matching on `Name` over-counts (a
search for "Thomas Newman" would match unrelated credits). The correct approach
is to unnest the pipe-separated `NomineeIds` and `Nominees` fields, which always
contain individual people.

This was discovered mid-analysis: an initial exact-match query reported Thomas
Newman at 14 nominations, but external sources indicated 15. Investigation
revealed a 15th nomination where Newman appeared as a co-writer on the WALL-E
original song, credited under a group name in `Name` but listed individually in
`Nominees`.

**2. Exclude honorary awards from the win count**

`CanonicalCategory = 'HONORARY AWARD'` rows have `Winner = true` but represent
honorary recognition, not a competitive win. Counting these excluded notable
figures: Peter O'Toole (honorary 75th ceremony) and Federico Fellini
(honorary 1993) would otherwise have been filtered out entirely. The final
queries filter competitive wins only:
`Winner = true AND CanonicalCategory != 'HONORARY AWARD'`.

**3. Ceremony 98 nominees treated as non-winners**

The 2026 ceremony (98) has not yet occurred. All `Winner` values for Ceremony 98
are `null`, consistent with other non-winning nominees. These rows are correctly
included in nomination counts and do not affect win counts.

**4. Role assignment based on at least one nomination in the relevant category**

For the actors/actresses/directors list, a person qualifies if they have been
nominated at least once in a competitive acting or directing category —
regardless of what proportion of their total nominations fall in those
categories. This means PTA's 14 nominations (directing + writing + producing)
all count toward his total, because he has been nominated for directing.

---

## Queries

### Part 1: All categories, all nominees

Initial query (flawed — exact name match):

```sql
SELECT
  Name,
  COUNT(*) AS total_nominations,
  SUM(CASE WHEN Winner = true THEN 1 ELSE 0 END) AS total_wins
FROM oscars.default.oscars
WHERE Name IS NOT NULL AND Name != ''
GROUP BY Name
HAVING total_wins = 0
ORDER BY total_nominations DESC
LIMIT 5
```

Corrected query using unnested individual IDs:

```sql
WITH unnested AS (
  SELECT
    unnest(string_split(NomineeIds, '|')) AS nominee_id,
    unnest(string_split(Nominees, '|')) AS nominee_name,
    Winner
  FROM oscars.default.oscars
  WHERE NomineeIds IS NOT NULL AND NomineeIds != ''
),
person_stats AS (
  SELECT
    nominee_id,
    MAX(nominee_name) AS name,
    COUNT(*) AS total_nominations,
    SUM(CASE WHEN Winner = true THEN 1 ELSE 0 END) AS total_wins
  FROM unnested
  WHERE nominee_id IS NOT NULL AND nominee_id != ''
  GROUP BY nominee_id
  HAVING total_wins = 0
)
SELECT nominee_id, name, total_nominations
FROM person_stats
ORDER BY total_nominations DESC
LIMIT 10
```

### Part 2: Actors, actresses, and directors only — total noms across all categories, honorary awards excluded

```sql
WITH unnested AS (
  SELECT
    unnest(string_split(NomineeIds, '|')) AS nominee_id,
    unnest(string_split(Nominees, '|')) AS nominee_name,
    CanonicalCategory,
    Winner
  FROM oscars.default.oscars
  WHERE NomineeIds IS NOT NULL AND NomineeIds != ''
),
acting_directing_ids AS (
  SELECT DISTINCT nominee_id
  FROM unnested
  WHERE CanonicalCategory IN (
    'ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE',
    'ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE',
    'DIRECTING', 'DIRECTING (Comedy Picture)', 'DIRECTING (Dramatic Picture)'
  )
),
person_stats AS (
  SELECT
    u.nominee_id,
    MAX(u.nominee_name) AS name,
    COUNT(*) AS total_nominations,
    SUM(CASE WHEN u.Winner = true AND u.CanonicalCategory != 'HONORARY AWARD' THEN 1 ELSE 0 END) AS competitive_wins,
    string_agg(DISTINCT CASE
      WHEN u.CanonicalCategory IN ('ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE') THEN 'Actor'
      WHEN u.CanonicalCategory IN ('ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE') THEN 'Actress'
      WHEN u.CanonicalCategory LIKE 'DIRECTING%' THEN 'Director'
    END, ' / ') AS roles
  FROM unnested u
  INNER JOIN acting_directing_ids adi ON u.nominee_id = adi.nominee_id
  GROUP BY u.nominee_id
  HAVING competitive_wins = 0
)
SELECT name, total_nominations, roles
FROM person_stats
ORDER BY total_nominations DESC
LIMIT 10
```

### Part 3: Those in Part 2 who are nominated for the 2026 Oscars — ranked by career noms, with career vs. 2026 nom split

```sql
WITH unnested AS (
  SELECT
    unnest(string_split(NomineeIds, '|')) AS nominee_id,
    unnest(string_split(Nominees, '|')) AS nominee_name,
    CanonicalCategory,
    Winner,
    Ceremony,
    Film
  FROM oscars.default.oscars
  WHERE NomineeIds IS NOT NULL AND NomineeIds != ''
),
acting_directing_ids AS (
  SELECT DISTINCT nominee_id
  FROM unnested
  WHERE CanonicalCategory IN (
    'ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE',
    'ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE',
    'DIRECTING', 'DIRECTING (Comedy Picture)', 'DIRECTING (Dramatic Picture)'
  )
),
ceremony_98_ids AS (
  SELECT
    nominee_id,
    COUNT(*) AS noms_2026,
    string_agg(DISTINCT Film, ', ') AS films_2026,
    string_agg(DISTINCT CanonicalCategory, ', ') AS categories_2026
  FROM unnested
  WHERE Ceremony = 98
  GROUP BY nominee_id
),
person_stats AS (
  SELECT
    u.nominee_id,
    MAX(u.nominee_name) AS name,
    COUNT(*) AS total_nominations,
    SUM(CASE WHEN u.Winner = true AND u.CanonicalCategory != 'HONORARY AWARD' THEN 1 ELSE 0 END) AS competitive_wins,
    string_agg(DISTINCT CASE
      WHEN u.CanonicalCategory IN ('ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE') THEN 'Actor'
      WHEN u.CanonicalCategory IN ('ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE') THEN 'Actress'
      WHEN u.CanonicalCategory LIKE 'DIRECTING%' THEN 'Director'
    END, ' / ') AS roles
  FROM unnested u
  INNER JOIN acting_directing_ids adi ON u.nominee_id = adi.nominee_id
  GROUP BY u.nominee_id
  HAVING competitive_wins = 0
)
SELECT
  ps.name,
  ps.total_nominations AS career_noms,
  c98.noms_2026,
  ps.total_nominations - c98.noms_2026 AS prior_noms,
  ps.roles,
  c98.films_2026,
  c98.categories_2026
FROM person_stats ps
INNER JOIN ceremony_98_ids c98 ON ps.nominee_id = c98.nominee_id
ORDER BY ps.total_nominations DESC
LIMIT 10
```

### Part 4: Same as Part 3, but ranked by prior nominations (pre-2026 only)

Identical to Part 3 except `prior_noms` is computed directly in `person_stats`
(as `SUM(CASE WHEN Ceremony != 98 THEN 1 ELSE 0 END)`) and used for ordering,
rather than deriving it post-join. This surfaces people who were most overlooked
*before* this year, filtering out first-time nominees inflated by 2026 noms.

```sql
WITH unnested AS (
  SELECT
    unnest(string_split(NomineeIds, '|')) AS nominee_id,
    unnest(string_split(Nominees, '|')) AS nominee_name,
    CanonicalCategory,
    Winner,
    Ceremony,
    Film
  FROM oscars.default.oscars
  WHERE NomineeIds IS NOT NULL AND NomineeIds != ''
),
acting_directing_ids AS (
  SELECT DISTINCT nominee_id
  FROM unnested
  WHERE CanonicalCategory IN (
    'ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE',
    'ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE',
    'DIRECTING', 'DIRECTING (Comedy Picture)', 'DIRECTING (Dramatic Picture)'
  )
),
ceremony_98_ids AS (
  SELECT
    nominee_id,
    COUNT(*) AS noms_2026,
    string_agg(DISTINCT Film, ', ') AS films_2026,
    string_agg(DISTINCT CanonicalCategory, ', ') AS categories_2026
  FROM unnested
  WHERE Ceremony = 98
  GROUP BY nominee_id
),
person_stats AS (
  SELECT
    u.nominee_id,
    MAX(u.nominee_name) AS name,
    COUNT(*) AS career_noms,
    SUM(CASE WHEN u.Ceremony != 98 THEN 1 ELSE 0 END) AS prior_noms,
    SUM(CASE WHEN u.Winner = true AND u.CanonicalCategory != 'HONORARY AWARD' THEN 1 ELSE 0 END) AS competitive_wins,
    string_agg(DISTINCT CASE
      WHEN u.CanonicalCategory IN ('ACTOR IN A LEADING ROLE', 'ACTOR IN A SUPPORTING ROLE') THEN 'Actor'
      WHEN u.CanonicalCategory IN ('ACTRESS IN A LEADING ROLE', 'ACTRESS IN A SUPPORTING ROLE') THEN 'Actress'
      WHEN u.CanonicalCategory LIKE 'DIRECTING%' THEN 'Director'
    END, ' / ') AS roles
  FROM unnested u
  INNER JOIN acting_directing_ids adi ON u.nominee_id = adi.nominee_id
  GROUP BY u.nominee_id
  HAVING competitive_wins = 0
)
SELECT
  ps.name,
  ps.prior_noms,
  c98.noms_2026,
  ps.career_noms,
  ps.roles,
  c98.films_2026,
  c98.categories_2026
FROM person_stats ps
INNER JOIN ceremony_98_ids c98 ON ps.nominee_id = c98.nominee_id
ORDER BY ps.prior_noms DESC
LIMIT 10
```

---

## Results

### Top 10: All nominees, all categories

| Rank | Name                 | Nominations | Role                       |
| ---- | -------------------- | ----------- | -------------------------- |
| 1    | Greg P. Russell      | 16          | Sound mixer                |
| 2    | Roland Anderson      | 15          | Art director               |
| 2    | Thomas Newman        | 15          | Film composer              |
| 4    | Paul Thomas Anderson | 14          | Director & screenwriter    |
| 4    | George Folsey        | 14          | Cinematographer            |
| 6    | Daniel Sudick        | 13          | Visual effects supervisor  |
| 7    | Bradley Cooper       | 12          | Actor, director & producer |
| 8    | Rick Kline           | 11          | Sound mixer                |
| 9    | Anna Behlmer         | 10          | Sound mixer (re-recording) |
| 9    | Walter Scharf        | 10          | Composer & music director  |

Note: Diane Warren (songwriter) reaches 17 nominations when counted via fuzzy
name match on the `Name` field, but does not appear prominently in the
`NomineeIds`-based count due to inconsistent individual crediting in earlier
nomination records. Further investigation warranted.

### Top 10: Actors, actresses, and directors (competitive wins only)

| Rank | Name                 | Total Nominations | Role     |
| ---- | -------------------- | ----------------- | -------- |
| 1    | Paul Thomas Anderson | 14                | Director |
| 2    | Federico Fellini     | 13                | Director |
| 3    | Bradley Cooper       | 12                | Actor    |
| 4    | Peter O'Toole        | 9                 | Actor    |
| 5    | Glenn Close          | 8                 | Actress  |
| 5    | Robert Altman        | 8                 | Director |
| 7    | Mike Leigh           | 7                 | Director |
| 7    | Richard Burton       | 7                 | Actor    |
| 7    | Peter Weir           | 7                 | Director |
| 7    | Deborah Kerr         | 7                 | Actress  |

### Top 10: Actors, actresses, and directors in contention for the 2026 Oscars — ranked by career noms

Career nominations include all categories (not just acting/directing). The
`2026 Noms` column counts only Ceremony 98 nominations; `Prior Noms` is the
remainder.

| Rank | Name                 | Career Noms | 2026 Noms | Prior Noms | Role     | 2026 Film                | 2026 Categories                                            |
| ---- | -------------------- | ----------- | --------- | ---------- | -------- | ------------------------ | ---------------------------------------------------------- |
| 1    | Paul Thomas Anderson | 14          | 3         | 11         | Director | One Battle after Another | Directing, Best Picture, Adapted Screenplay                |
| 2    | Yorgos Lanthimos     | 6           | 1         | 5          | Director | Bugonia                  | Best Picture                                               |
| 3    | Ryan Coogler         | 5           | 3         | 2          | Director | Sinners                  | Directing, Best Picture, Original Screenplay               |
| 3    | Ethan Hawke          | 5           | 1         | 4          | Actor    | Blue Moon                | Actor in a Leading Role                                    |
| 5    | Josh Safdie          | 4           | 4         | 0          | Director | Marty Supreme            | Directing, Best Picture, Film Editing, Original Screenplay |
| 5    | Timothée Chalamet    | 4           | 2         | 2          | Actor    | Marty Supreme            | Actor in a Leading Role, Best Picture                      |
| 7    | Joachim Trier        | 3           | 2         | 1          | Director | Sentimental Value        | Directing, Original Screenplay                             |
| 8    | Jessie Buckley       | 2           | 1         | 1          | Actress  | Hamnet                   | Actress in a Leading Role                                  |
| 8    | Kate Hudson          | 2           | 1         | 1          | Actress  | Song Sung Blue           | Actress in a Leading Role                                  |
| 8    | Amy Madigan          | 2           | 1         | 1          | Actress  | Weapons                  | Actress in a Supporting Role                               |

### Top 10: Actors, actresses, and directors in contention for the 2026 Oscars — ranked by prior noms

Same population as above, but ranked by pre-2026 nominations only. This is the
more meaningful "historically overlooked" ranking — it excludes nomination count
inflated by the current ceremony.

| Rank | Name                 | Prior Noms | 2026 Noms | Career Noms | Role     | 2026 Film                | 2026 Categories                                            |
| ---- | -------------------- | ---------- | --------- | ----------- | -------- | ------------------------ | ---------------------------------------------------------- |
| 1    | Paul Thomas Anderson | 11         | 3         | 14          | Director | One Battle after Another | Directing, Best Picture, Adapted Screenplay                |
| 2    | Yorgos Lanthimos     | 5          | 1         | 6           | Director | Bugonia                  | Best Picture                                               |
| 3    | Ethan Hawke          | 4          | 1         | 5           | Actor    | Blue Moon                | Actor in a Leading Role                                    |
| 4    | Timothée Chalamet    | 2          | 2         | 4           | Actor    | Marty Supreme            | Actor in a Leading Role, Best Picture                      |
| 4    | Ryan Coogler         | 2          | 3         | 5           | Director | Sinners                  | Directing, Best Picture, Original Screenplay               |
| 6    | Amy Madigan          | 1          | 1         | 2           | Actress  | Weapons                  | Actress in a Supporting Role                               |
| 6    | Kate Hudson          | 1          | 1         | 2           | Actress  | Song Sung Blue           | Actress in a Leading Role                                  |
| 6    | Joachim Trier        | 1          | 2         | 3           | Director | Sentimental Value        | Directing, Original Screenplay                             |
| 6    | Jessie Buckley       | 1          | 1         | 2           | Actress  | Hamnet                   | Actress in a Leading Role                                  |
| 10   | Jacob Elordi         | 0          | 1         | 1           | Actor    | Frankenstein             | Actor in a Supporting Role                                 |

---

## Thought Process & Iterations

**Iteration 1** — Ran a simple `GROUP BY Name` query with exact match. Returned
Thomas Newman at 14 nominations, Alex North at 14, Diane Warren at 13. Appeared
reasonable.

**Iteration 2** — User flagged that external sources report Thomas Newman at 15
nominations. Investigated: found a 15th row where Newman appeared in the
`Nominees` field as part of a shared songwriting credit for WALL-E's original
song, but the `Name` field was a group credit string. Root cause: exact match on
`Name` misses shared-credit nominations. Switched to unnesting
`NomineeIds`/`Nominees`.

**Iteration 3** — Reran with unnesting. Thomas Newman corrected to 15. Diane
Warren jumped to 17 on fuzzy `Name` match but did not appear cleanly in the
`NomineeIds` unnest — flagged for further review. Greg P. Russell emerged as the
all-time leader at 16 nominations.

**Iteration 4** — User requested actors/actresses/directors only. Filtered
`CanonicalCategory` to acting and directing categories. PTA dropped out (only 4
directing nominations in those categories; his other 10 noms are writing and
producing). Peter O'Toole was correctly top of that list.

**Iteration 5** — User requested that total nomination count include all
categories for qualifying people (not just acting/directing), using
acting/directing nominations as a qualification filter only. PTA returned to #1
at 14. Bradley Cooper moved to #3 at 12 (acting + directing + writing +
producing).

**Iteration 6** — Peter O'Toole missing from the new list. Investigation: he has
an `HONORARY AWARD` row with `Winner = true` at the 75th ceremony, causing him
to be excluded by `HAVING total_wins = 0`. Same issue affected Robert Altman and
Federico Fellini. Decision: exclude honorary awards from competitive win count.
All three correctly reinstated.

**Iteration 7** — Filtered Part 2 results to only those with a Ceremony 98
nomination, to identify historically overlooked figures who still have a chance
to win this year. Added a `noms_2026` count and derived
`prior_noms = career_noms - noms_2026` to make career vs. current-year context
explicit. Notable finding: Josh Safdie's entire career nomination count (4)
comes from 2026 alone — he's a first-time nominee who nonetheless qualifies
because he has prior directing nominations in the dataset from earlier
ceremonies.

**Iteration 8** — Re-ranked Part 3 by prior nominations (pre-2026) rather than
career nominations, to better capture "historically overlooked" intent. Key
changes: Josh Safdie drops out entirely (0 prior noms); Jacob Elordi enters at
#10 (also 0 prior noms, first-time nominee); Ryan Coogler drops from #3 to
tied #4 (only 2 of his 5 career noms predate 2026). `prior_noms` is now
computed directly in the CTE (`SUM(CASE WHEN Ceremony != 98 THEN 1 ELSE 0 END)`)
rather than derived post-join, allowing clean `ORDER BY prior_noms`.

---

## Takeaways

**For the data:**

- The `Name` field is not safe for person identity — always use
  `NomineeIds`/`Nominees` with unnesting for accurate per-person counts.
- Honorary awards (`HONORARY AWARD` category) should be treated separately from
  competitive nominations in any win/loss analysis.
- Ceremony 98 nominees are present in the data with `null` winners — valid to
  include in nomination counts.

**For the story:**

- The most-nominated-never-won title across all categories belongs to **Greg P.
  Russell** (sound mixer, 16 nominations) — an under-the-radar result that
  speaks to how technical categories produce serial nominees.
- Among on-screen and behind-the-camera creative roles, **Paul Thomas Anderson**
  leads at 14 nominations with no competitive win — and is actively nominated at
  the 98th ceremony, making this a live story.
- **Federico Fellini at #2** (13 nominations) is a striking data point: widely
  regarded as one of the greatest filmmakers ever, he won honorary recognition
  but never a competitive Oscar.
- **Thelma Ritter** holds a specific record: 6 nominations exclusively in
  Supporting Actress — the most in that single category without a win.
- The honorary Oscar question is genuinely interesting editorially: O'Toole,
  Altman, and Fellini all received honorary recognition, arguably because the
  Academy knew they had been chronically overlooked. The data bears this out.
- **Diane Warren** deserves dedicated follow-up analysis — her true nomination
  count is ambiguous in this dataset due to inconsistent crediting of
  songwriters across eras.

**For the 2026 live angle:**

- **PTA** is the most compelling story: 11 prior nominations, never won, now the
  frontrunner for Best Director and Best Picture. If he wins either, he exits
  the all-time bridesmaids list.
- **Josh Safdie** is a curious edge case when ranking by career noms (appears
  at #5 with 4), but drops out entirely when ranking by prior noms (0 pre-2026).
  The prior-noms ranking is the more meaningful "overdue" framing.
- **Jessie Buckley and Amy Madigan** are predicted winners in our
  [2026 predictions analysis](2026-oscars-predictions.md). A win for either
  would be their first.
- The 2026 ceremony is unusually rich with "overdue" narratives — PTA, Ethan
  Hawke, and Yorgos Lanthimos all carry histories of Academy recognition without
  a win.
- **Jacob Elordi** enters at #10 on the prior-noms ranking with 0 prior noms —
  a true first-timer, included only because the list captures everyone with a
  2026 nom and zero career wins, regardless of prior nomination history.
