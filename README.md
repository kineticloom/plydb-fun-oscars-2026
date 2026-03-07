# Fun with PlyDB: Predicting the 2026 Oscars

This repo is a fun experiment in conversational analytics using
[PlyDB](https://www.plydb.com/) and Academy Awards data.

_Marketing disclaimer out of the way_: PlyDB is an open-source, universal
database gateway that lets AI agents query across live data in place - no data
movement required. It bridges the gap between your AI and your data, from SQL
databases to flat files: Postgres, MySQL, CSV, Excel, Parquet, and
[more](https://www.plydb.com/docs/data-sources/).

## What does the data say about the 2026 Oscars?

We asked Claude to predict the winners — using only SQL queries across
historical Oscar and precursor award data, no intuition allowed. Here's what it
found:

| Category                | Predicted Winner             | Win Probability |
| ----------------------- | ---------------------------- | --------------- |
| Best Picture            | **One Battle after Another** | 45%             |
| Best Director           | **Paul Thomas Anderson**     | 89%             |
| Best Actor              | **Michael B. Jordan**        | 35%             |
| Best Actress            | **Jessie Buckley**           | 90%             |
| Best Supporting Actor   | **Sean Penn**                | 59%             |
| Best Supporting Actress | **Amy Madigan**              | 76%             |

Predictions are driven entirely by precursor award wins (BAFTA, Golden Globes,
SAG, Critics Choice, TIFF), weighted by their historical accuracy as Oscar
predictors. No intuition, no box office, no buzz — only conversion rates from
historical data.

A few things that jumped out:

- **Jessie Buckley swept.** She won BAFTA, GG Drama, Critics Choice, and SAG for
  _Hamnet_ — 4 of 5 major precursors, a historically dominant sweep. The only
  other Best Actress nominees who've done that in recent history (Zellweger,
  McDormand, Larson) all won the Oscar. Model gives her 90%.

- **Paul Thomas Anderson won every directing precursor.** BAFTA, Golden Globe,
  Critics Choice — a clean 3-for-3. No other 2026 directing nominee won any of
  them. At 89%, he's the strongest data-supported call on the night.

- **Best Actor is a genuine three-way toss-up.** Jordan (SAG, 35%), Chalamet (GG
  Comedy + CC, 33%), Moura (GG Drama, 30%) are separated by signal differences
  smaller than the model's noise. Chalamet's number is partly inflated by GG
  Comedy, which converts to an Oscar only 9.2% of the time historically.

- **Sinners leads all films with 16 Oscar nominations across 16 different
  categories** — one nomination in virtually every department, an all-time
  record — yet its only Best Picture precursor win is the SAG Cast Award. The
  most-nominated film rarely wins Best Picture.

Full methodology and analysis:
[/analysis/2026-oscars-predictions.md](/analysis/2026-oscars-predictions.md)

---

## Data sources

Oscar nominations data comes from
[github.com/DLu/oscar_data](https://github.com/DLu/oscar_data). All other data
was sourced from Wikipedia and parsed into CSVs in `data/`.

| Award show      | Category                              | CSV                                     | Source                                                                                                                    |
| --------------- | ------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Academy Awards  | All categories (1st–98th ceremony)    | `oscar_nominations.csv`                 | [github.com/DLu/oscar_data](https://github.com/DLu/oscar_data)                                                            |
| Golden Globes   | Best Picture (pre-1950)               | `golden_globe_picture.csv`              | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Picture – Drama                  | `golden_globe_picture_drama.csv`        | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Picture – Musical/Comedy         | `golden_globe_picture_comedy.csv`       | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actor (pre-1950)                 | `golden_globe_actor.csv`                | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actor – Drama                    | `golden_globe_actor_drama.csv`          | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actor – Musical/Comedy           | `golden_globe_actor_comedy.csv`         | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actress (pre-1950)               | `golden_globe_actress.csv`              | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actress – Drama                  | `golden_globe_actress_drama.csv`        | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Actress – Musical/Comedy         | `golden_globe_actress_comedy.csv`       | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| Golden Globes   | Best Director                         | `golden_globe_director.csv`             | [Wikipedia](https://en.wikipedia.org/wiki/List_of_Golden_Globe_winners)                                                   |
| BAFTA           | Best Film                             | `bafta_film.csv`                        | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Film)                                                      |
| BAFTA           | Best Direction                        | `bafta_direction.csv`                   | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Direction)                                                 |
| BAFTA           | Best Actor in a Leading Role          | `bafta_leading_actor.csv`               | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Actor_in_a_Leading_Role)                                   |
| BAFTA           | Best Actress in a Leading Role        | `bafta_leading_actress.csv`             | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Actress_in_a_Leading_Role)                                 |
| BAFTA           | Best Actor in a Supporting Role       | `bafta_supporting_actor.csv`            | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Actor_in_a_Supporting_Role)                                |
| BAFTA           | Best Actress in a Supporting Role     | `bafta_supporting_actress.csv`          | [Wikipedia](https://en.wikipedia.org/wiki/BAFTA_Award_for_Best_Actress_in_a_Supporting_Role)                              |
| Critics' Choice | Best Picture                          | `critics_choice_picture.csv`            | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Picture)                                 |
| Critics' Choice | Best Actor                            | `critics_choice_actor.csv`              | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Actor)                                   |
| Critics' Choice | Best Actress                          | `critics_choice_actress.csv`            | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Actress)                                 |
| Critics' Choice | Best Director                         | `critics_choice_director.csv`           | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Director)                                |
| Critics' Choice | Best Supporting Actor                 | `critics_choice_supporting_actor.csv`   | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Supporting_Actor)                        |
| Critics' Choice | Best Supporting Actress               | `critics_choice_supporting_actress.csv` | [Wikipedia](https://en.wikipedia.org/wiki/Critics%27_Choice_Movie_Award_for_Best_Supporting_Actress)                      |
| SAG Awards      | Outstanding Cast                      | `sag_cast_award.csv`                    | [Wikipedia](https://en.wikipedia.org/wiki/Actor_Award_for_Outstanding_Performance_by_a_Cast_in_a_Motion_Picture)          |
| SAG Awards      | Outstanding Actor – Leading Role      | `sag_lead_actor.csv`                    | [Wikipedia](https://en.wikipedia.org/wiki/Actor_Award_for_Outstanding_Performance_by_a_Male_Actor_in_a_Leading_Role)      |
| SAG Awards      | Outstanding Actress – Leading Role    | `sag_lead_actress.csv`                  | [Wikipedia](https://en.wikipedia.org/wiki/Actor_Award_for_Outstanding_Performance_by_a_Female_Actor_in_a_Leading_Role)    |
| SAG Awards      | Outstanding Actor – Supporting Role   | `sag_supporting_actor.csv`              | [Wikipedia](https://en.wikipedia.org/wiki/Actor_Award_for_Outstanding_Performance_by_a_Male_Actor_in_a_Supporting_Role)   |
| SAG Awards      | Outstanding Actress – Supporting Role | `sag_supporting_actress.csv`            | [Wikipedia](https://en.wikipedia.org/wiki/Actor_Award_for_Outstanding_Performance_by_a_Female_Actor_in_a_Supporting_Role) |
| TIFF            | People's Choice Award                 | `tiff_peoples_choice.csv`               | [Wikipedia](https://en.wikipedia.org/wiki/Toronto_International_Film_Festival_People%27s_Choice_Award)                    |

## Development

### Parsers

Parser scripts live in `parsers/` and scrape source HTML files from `wikipedia/`
into CSVs in `data/`.

**Requirements:** Python 3 with `beautifulsoup4`:

```bash
pip install beautifulsoup4
```

**Run a parser:**

```bash
python3 parsers/parse_tiff_peoples_choice.py
```

Output: `data/tiff_peoples_choice.csv` — columns: `year`, `film`, `director`,
`is_winner`

Each parser automatically normalizes names and film titles against
`data/oscar_nominations.csv` as the canonical source (via
`parsers/canonicalize.py`). This resolves cross-source inconsistencies such as
accent variants (`Chloe Zhao` → `Chloé Zhao`), hyphen variants (`Bong Joon-ho` →
`Bong Joon Ho`), initial spacing (`J. K. Simmons` → `J.K. Simmons`), and suffix
punctuation (`Cuba Gooding Jr.` → `Cuba Gooding, Jr.`). Values with no Oscar
match are left unchanged.

---

## Try it yourself

To chat with this Oscars data yourself:

1. Download this repository
2. Install PlyDB and configure it with your AI agent
   ([Quickstart Guide](https://www.plydb.com/docs/quickstart/))
3. Tell your AI to query with PlyDB using the pre-configured `plydb-config.json`
   file in this repository.
4. Have fun!

## Chat with other data

Did you know? PlyDB can connect your AI to boring data too!

Whether it's business data in a dusty Excel sheet or a complex DevOps log in S3,
AI can be surprisingly good at making sense of a mess. PlyDB acts as the bridge,
letting your AI query across Postgres, MySQL, CSV, Excel, Parquet, Google
Sheets, and more - locally or in the cloud.

Open source and free.
[Give PlyDB a spin!](https://www.plydb.com/docs/quickstart/)
