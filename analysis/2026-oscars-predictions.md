# Predicting the 2026 Oscars with Data

**Author:** Claude Sonnet 4.6 via Claude Code + PlyDB
**Date:** March 7, 2026
**Method:** Pure data analysis — no gut feelings, no box office gossip, no Hollywood intuition. Only the numbers.

---

## Summary

| Category | Predicted Winner | Win Probability |
|---|---|---|
| Best Picture | **One Battle after Another** | 45% |
| Best Director | **Paul Thomas Anderson** | 89% |
| Best Actor | **Michael B. Jordan** | 35% |
| Best Actress | **Jessie Buckley** | 90% |
| Best Supporting Actor | **Sean Penn** | 59% |
| Best Supporting Actress | **Amy Madigan** | 76% |

Predictions are driven entirely by precursor award wins (BAFTA, Golden Globes, SAG, Critics Choice, TIFF), weighted by their historical accuracy as Oscar predictors. No intuition, no box office, no buzz — only conversion rates from historical data.

A few things that jumped out:

- **Jessie Buckley swept.** She won BAFTA, GG Drama, Critics Choice, and SAG for *Hamnet* — 4 of 5 major precursors, a historically dominant sweep. The only other Best Actress nominees who've done that in recent history (Zellweger, McDormand, Larson) all won the Oscar. Model gives her 90%.

- **Paul Thomas Anderson won every directing precursor.** BAFTA, Golden Globe, Critics Choice — a clean 3-for-3. No other 2026 directing nominee won any of them. At 89%, he's the strongest data-supported call on the night.

- **Best Actor is a genuine three-way toss-up.** Jordan (SAG, 35%), Chalamet (GG Comedy + CC, 33%), Moura (GG Drama, 30%) are separated by signal differences smaller than the model's noise. Chalamet's number is partly inflated by GG Comedy, which converts to an Oscar only 9.2% of the time historically.

- **Sinners leads all films with 16 Oscar nominations across 16 different categories** — one nomination in virtually every department, an all-time record — yet its only Best Picture precursor win is the SAG Cast Award. The most-nominated film rarely wins Best Picture.

---

## Approach

The Academy Awards don't happen in a vacuum. Every year, a gauntlet of precursor awards runs in the weeks and months before the Oscars — BAFTA, Golden Globes, SAG Awards, Critics Choice, TIFF People's Choice — and historically these have strong predictive power for Oscar outcomes.

The strategy here is simple:
1. Establish how well each precursor has predicted Oscar winners historically
2. See which 2026 nominees have won the most (and most predictive) precursors
3. Let the data make the call

All data lives in `data/` — historical Oscar nominations going back to the 1st ceremony, plus precursor award data. SQL queries run via [PlyDB](https://www.plydb.com/). See [Data Caveats](#data-caveats) for notes on cross-source normalization and schema quirks.

---

## Step 1: How Predictive Are the Precursors?

Before scoring the 2026 nominees, we need to know which precursors to trust. Here are the historical conversion rates — how often does winning a precursor mean winning the Oscar?

### Best Picture

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| Critics Choice Best Picture | 30 | **60.0%** |
| Golden Globe Best Picture – Drama | 75 | 46.7% |
| SAG Outstanding Cast | 30 | 43.3% |
| BAFTA Best Film | 79 | 31.6% |

**Query:**
```sql
-- Example for SAG Cast → Oscar Best Picture
SELECT
    COUNT(*) AS total_years,
    SUM(CASE WHEN LOWER(s.film) = LOWER(o.Film) THEN 1 ELSE 0 END) AS matches,
    ROUND(100.0 * SUM(...) / COUNT(*), 1) AS match_pct
FROM sag_cast.default.sag_cast_award s
JOIN oscars.default.oscar_nominations o
    ON CAST(s.year AS VARCHAR) = o.Year
    AND o.CanonicalCategory = 'BEST PICTURE'
    AND o.Winner = 'True'
WHERE s.is_winner = true
```

**Takeaway:** Critics Choice is the single strongest Best Picture predictor (60%), followed by GG Drama (46.7%) and SAG Cast (43.3%). BAFTA lags at 31.6% — it's an international body with different tastes. However, when multiple precursors converge on the same film, the cumulative signal grows.

Also notable: the Best Picture winner and Best Director winner have been from the **same film** 73.3% of the time since 1980. This alignment matters for our analysis.

### Best Director

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| Critics Choice Best Director | 32 | **71.9%** |
| Golden Globe Best Director | 82 | 53.7% |
| BAFTA Best Direction | 56 | 33.9% |

### Best Actor (Leading Role)

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| SAG Outstanding Male Actor | 31 | **77.4%** |
| Golden Globe Best Actor – Drama | 76 | 65.8% |
| Critics Choice Best Actor | 31 | 64.5% |
| BAFTA Best Actor | 58 | 39.7% |
| Golden Globe Best Actor – Comedy | 76 | **9.2%** ← barely predictive |

The GG Comedy category is a red herring for Oscar prediction — historically only a 9.2% conversion rate. This is a crucial distinction.

### Best Actress (Leading Role)

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| SAG Outstanding Female Actor | 31 | **67.7%** |
| GG Best Actress – Drama | 78 | 47.4% |
| Critics Choice Best Actress | 33 | 48.5% |
| BAFTA Best Actress | 58 | 44.8% |

### Best Supporting Actor

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| SAG Outstanding Male Actor – Supporting | 31 | **71.0%** |
| Critics Choice Best Supporting Actor | 31 | 61.3% |
| BAFTA Best Supporting Actor | 56 | 30.4% |

### Best Supporting Actress

| Precursor | Years of data | Oscar win rate |
|---|---|---|
| SAG Outstanding Female Actor – Supporting | 32 | **71.9%** |
| Critics Choice Best Supporting Actress | 32 | 62.5% |
| BAFTA Best Supporting Actress | 56 | 37.5% |

**Key insight across all categories:** SAG Awards are the single best predictor for all acting categories. Critics Choice is the best predictor for Best Picture and Best Director. BAFTA, while prestigious, is the weakest predictor in every category — its voter base skews toward British and international cinema in ways that diverge from Academy tastes.

---

## Step 2: The 2025 Season Precursor Results

### Best Picture Nominees

The 2026 Oscar Best Picture field: Bugonia, F1, Frankenstein, Hamnet, Marty Supreme, One Battle after Another, Sentimental Value, Sinners, The Secret Agent, Train Dreams.

**Query:**
```sql
WITH nominees AS (
    SELECT DISTINCT Film
    FROM oscars.default.oscar_nominations
    WHERE Ceremony = 98 AND CanonicalCategory = 'BEST PICTURE'
),
-- [joined against each precursor award for year = 2025]
SELECT
    n.Film,
    COALESCE(b.bafta_win, false)  AS bafta,
    COALESCE(g.gg_drama_win, false) AS gg_drama,
    COALESCE(gc.gg_comedy_win, false) AS gg_comedy,
    COALESCE(c.cc_win, false) AS critics_choice,
    COALESCE(s.sag_win, false) AS sag_cast,
    COALESCE(t.tiff_win, false) AS tiff,
    (sum of wins) AS total_precursor_wins
FROM nominees n
LEFT JOIN bafta ... LEFT JOIN gg_drama ... ...
ORDER BY total_precursor_wins DESC
```

**Results:**

| Film | BAFTA | GG Drama | GG Comedy | Critics Choice | SAG Cast | TIFF | Total Wins |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **One Battle after Another** | ✓ | | ✓ | ✓ | | | **3** |
| **Hamnet** | | ✓ | | | | ✓ | **2** |
| **Sinners** | | | | | ✓ | | **1** |
| Bugonia | | | | | | | 0 |
| F1 | | | | | | | 0 |
| Frankenstein | | | | | | | 0 |
| Marty Supreme | | | | | | | 0 |
| Sentimental Value | | | | | | | 0 |
| The Secret Agent | | | | | | | 0 |
| Train Dreams | | | | | | | 0 |

**Observation:** Three films are in the conversation; seven are not. One interesting quirk: the Golden Globes classified "One Battle After Another" as Comedy/Musical (not Drama) — which is why Hamnet won GG Drama while One Battle won GG Comedy. The DGA equivalent split is less meaningful for Oscar prediction since GG Comedy has such a low conversion rate (16.7% for Best Picture vs ~46.7% for Drama). However, the BAFTA and Critics Choice wins for One Battle after Another are the higher-value signals.

**Sinners' 16 nominations** across 16 different categories is extraordinary breadth — one nomination in virtually every eligible department. Historical note: the most-nominated film at the Oscars rarely wins Best Picture. Recent examples of most-nominated non-winners: The Power of the Dog (12 noms, 2022), Mank (10 noms, 2021). But Sinners' SAG Cast win is the one signal that matters most.

### Best Director Nominees

Chloé Zhao (Hamnet), Josh Safdie (Marty Supreme), Paul Thomas Anderson (One Battle after Another), Joachim Trier (Sentimental Value), Ryan Coogler (Sinners).

| Director | Film | BAFTA | Golden Globe | Critics Choice | Total |
|---|---|:---:|:---:|:---:|:---:|
| **Paul Thomas Anderson** | One Battle after Another | ✓ | ✓ | ✓ | **3** |
| Chloé Zhao | Hamnet | | | | 0 |
| Josh Safdie | Marty Supreme | | | | 0 |
| Joachim Trier | Sentimental Value | | | | 0 |
| Ryan Coogler | Sinners | | | | 0 |

PTA swept all three directing precursors. That's a clean 3-for-3.

### Best Actor Nominees

Timothée Chalamet (Marty Supreme), Leonardo DiCaprio (One Battle after Another), Ethan Hawke (Blue Moon), Michael B. Jordan (Sinners), Wagner Moura (The Secret Agent).

| Actor | Film | BAFTA | GG Drama | GG Comedy | Critics Choice | SAG | Total |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Timothée Chalamet** | Marty Supreme | | | ✓ (9.2% pred) | ✓ (64.5% pred) | | **2** |
| **Michael B. Jordan** | Sinners | | | | | ✓ (77.4% pred) | **1** |
| **Wagner Moura** | The Secret Agent | | ✓ (65.8% pred) | | | | **1** |
| Ethan Hawke | Blue Moon | | | | | | 0 |
| Leonardo DiCaprio | One Battle after Another | | | | | | 0 |

**Important note:** BAFTA Lead Actor winner Robert Aramayo (*I Swear*) is not even Oscar-nominated. A BAFTA winner missing the Oscar field is a notable divergence — it means BAFTA's 2025 acting taste is especially disconnected from Academy voters this year.

### Best Actress Nominees

Jessie Buckley (Hamnet), Rose Byrne (If I Had Legs I'd Kick You), Kate Hudson (Song Sung Blue), Renate Reinsve (Sentimental Value), Emma Stone (Bugonia).

| Actress | Film | BAFTA | GG Drama | GG Comedy | Critics Choice | SAG | Total |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Jessie Buckley** | Hamnet | ✓ (44.8%) | ✓ (47.4%) | | ✓ (48.5%) | ✓ (67.7%) | **4** |
| **Rose Byrne** | If I Had Legs I'd Kick You | | | ✓ | | | **1** |
| Renate Reinsve | Sentimental Value | | | | | | 0 |
| Emma Stone | Bugonia | | | | | | 0 |
| Kate Hudson | Song Sung Blue | | | | | | 0 |

### Best Supporting Actor Nominees

Benicio Del Toro (One Battle after Another), Jacob Elordi (Frankenstein), Delroy Lindo (Sinners), Sean Penn (One Battle after Another), Stellan Skarsgård (Sentimental Value).

| Actor | Film | BAFTA | Critics Choice | SAG | Total |
|---|---|:---:|:---:|:---:|:---:|
| **Sean Penn** | One Battle after Another | ✓ (30.4%) | | ✓ (71.0%) | **2** |
| **Jacob Elordi** | Frankenstein | | ✓ (61.3%) | | **1** |
| Benicio Del Toro | One Battle after Another | | | | 0 |
| Delroy Lindo | Sinners | | | | 0 |
| Stellan Skarsgård | Sentimental Value | | | | 0 |

### Best Supporting Actress Nominees

Elle Fanning (Sentimental Value), Inga Ibsdotter Lilleaas (Sentimental Value), Amy Madigan (Weapons), Wunmi Mosaku (Sinners), Teyana Taylor (One Battle after Another).

| Actress | Film | BAFTA | Critics Choice | SAG | Total |
|---|---|:---:|:---:|:---:|:---:|
| **Amy Madigan** | Weapons | | ✓ (62.5%) | ✓ (71.9%) | **2** |
| **Wunmi Mosaku** | Sinners | ✓ (37.5%) | | | **1** |
| Elle Fanning | Sentimental Value | | | | 0 |
| Inga Ibsdotter Lilleaas | Sentimental Value | | | | 0 |
| Teyana Taylor | One Battle after Another | | | | 0 |

---

## Predictions

| Category | Predicted Winner | Win Probability |
|---|---|---|
| Best Picture | **One Battle after Another** | 45% |
| Best Director | **Paul Thomas Anderson** | 89% |
| Best Actor | **Michael B. Jordan** | 35% |
| Best Actress | **Jessie Buckley** | 90% |
| Best Supporting Actor | **Sean Penn** | 59% |
| Best Supporting Actress | **Amy Madigan** | 76% |

### Methodology

**Signal score:** Each nominee accumulates points equal to the historical Oscar conversion
rate of each precursor they won (e.g. winning the SAG Lead Actor = +77.4 points; winning
BAFTA Direction = +33.9 points). Nominees who won no tracked precursors score 0.

**Upset adjustment:** Historically, the Oscar sometimes goes to a nominee who won *none* of
the major precursors. The rate varies by category (queried from historical data):

| Category | Historical upset rate |
|---|---|
| Best Actress | 0.0% |
| Best Actor | 6.7% |
| Best Supporting Actress | 3.3% |
| Best Picture | 13.3% |
| Best Director | 13.3% |
| Best Supporting Actor | 6.7% |

**Query (example for Best Actor):**
```sql
-- Years where the Oscar Best Actor winner had no precursor wins
WITH oscar_winners AS (
    SELECT Year, Name
    FROM oscars.default.oscar_nominations
    WHERE CanonicalCategory = 'ACTOR IN A LEADING ROLE'
      AND Winner = 'True' AND Ceremony BETWEEN 68 AND 97
),
precursor_winners AS (
    SELECT CAST(year AS VARCHAR) AS year, actor AS name FROM sag_lead_actor.default.sag_lead_actor WHERE is_winner = 'true'
    UNION ALL
    SELECT CAST(year_from AS VARCHAR), actor FROM gg_actor_drama.default.gg_actor_drama WHERE is_winner = 'true'
    UNION ALL
    SELECT CAST(year_from AS VARCHAR), actor FROM gg_actor_comedy.default.gg_actor_comedy WHERE is_winner = 'true'
    UNION ALL
    SELECT CAST(year AS VARCHAR), actor FROM critics_choice_actor.default.critics_choice_actor WHERE is_winner = 'true'
    UNION ALL
    SELECT CAST(year AS VARCHAR), actor FROM bafta_leading_actor.default.bafta_leading_actor WHERE is_winner = 'true' AND category = 'Best Actor'
)
SELECT
    COUNT(DISTINCT o.Year) AS total_years,
    SUM(CASE WHEN p.name IS NULL THEN 1 ELSE 0 END) AS upset_years,
    ROUND(100.0 * SUM(CASE WHEN p.name IS NULL THEN 1 ELSE 0 END) / COUNT(DISTINCT o.Year), 1) AS upset_rate
FROM oscar_winners o
LEFT JOIN precursor_winners p ON o.Year = p.year AND o.Name = p.name
```

*Note: These rates rely on exact-string name matching enabled by source normalization. Without normalization, hyphen variants (Bong Joon-ho vs Bong Joon Ho), initial spacing (J. K. Simmons vs J.K. Simmons), and suffix punctuation (Cuba Gooding Jr. vs Cuba Gooding, Jr.) would all produce false upsets and inflate these rates.*

**Formula:** For each nominee *i* among *N* nominees:

> P(i) = signal(i) / Σ signals × (1 − upset_rate) + upset_rate / N

This allocates (1 − upset_rate) of the probability mass in proportion to precursor signal
strength, and distributes upset_rate uniformly across all nominees.

### Results

#### 🏆 Best Picture

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **One Battle after Another** | BAFTA (31.6%) + GG Comedy (16.7%) + CC (60.0%) | 108.3 | **45%** |
| Hamnet | GG Drama (46.7%) + TIFF (14.9%) | 61.6 | **26%** |
| Sinners | SAG Cast (43.3%) | 43.3 | **19%** |
| Bugonia / F1 / Frankenstein / Marty Supreme / Sentimental Value / The Secret Agent / Train Dreams | — | 0 | **1% each** |

*Upset rate 13.3% spread across 10 nominees = 1.3% floor per film.*

One Battle after Another holds the three highest-value signals: Critics Choice (60%), BAFTA (31.6%), and GG Comedy. It also benefits from a structural correlation: 73.3% of the time since 1980, the Best Picture winner's film also wins Best Director — and PTA swept all three directing precursors (see below). Sinners' 19% rests entirely on its SAG Cast win, but the underlying case is stronger than the number suggests: 16 Oscar nominations across 16 distinct departments is an extraordinary breadth of Academy support that the model can't capture. Hamnet's 26% is partly an artifact of TIFF — the People's Choice Award converts to an Oscar only 14.9% of the time (7/47 years), making it the weakest signal in the model. The stronger Hamnet signal is GG Drama (46.7%), but it arrived without any other precursor wins.

#### 🎬 Best Director

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **Paul Thomas Anderson** | BAFTA (33.9%) + GG (53.7%) + CC (71.9%) | 159.5 | **89%** |
| Chloé Zhao / Josh Safdie / Joachim Trier / Ryan Coogler | — | 0 | **3% each** |

*Upset rate 13.3% spread across 5 nominees = 2.7% floor per non-PTA nominee.*

The clearest call of the night. PTA swept every available directing precursor — no other nominee won any — making this the most concentrated signal in any category. The remaining 11% is almost entirely structural: the 13.3% upset rate distributed across 5 nominees forces a 2.7% floor for each competitor regardless of their zero signal. The most credible upset candidate is Ryan Coogler (Sinners), whose film leads all nominees with 16 Oscar nominations; but without a single directing precursor win, the data gives him nothing to work with.

#### 🎭 Best Actor

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **Michael B. Jordan** | SAG (77.4%) | 77.4 | **35%** |
| Timothée Chalamet | GG Comedy (9.2%) + CC (64.5%) | 73.7 | **33%** |
| Wagner Moura | GG Drama (65.8%) | 65.8 | **30%** |
| Ethan Hawke / Leonardo DiCaprio | — | 0 | **1% each** |

The tightest race of the night. Jordan's SAG win (77.4% predictor — the strongest of any individual acting award) gives him a narrow lead, but Chalamet's signal is inflated by GG Comedy, which carries only 9.2% historical weight. Strip that out and Chalamet's effective signal is just Critics Choice (64.5%) — essentially equal to Moura's GG Drama (65.8%), making the race a genuine three-way contest between three different precursors of similar weight. The BAFTA Lead Actor winner (Robert Aramayo, *I Swear*) was not Oscar-nominated, making BAFTA an outlier this year with no signal to contribute.

#### 💃 Best Actress

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **Jessie Buckley** | BAFTA (44.8%) + GG Drama (47.4%) + CC (48.5%) + SAG (67.7%) | 208.4 | **90%** |
| Rose Byrne | GG Comedy (22.8%) | 22.8 | **10%** |
| Renate Reinsve / Emma Stone / Kate Hudson | — | 0 | **<1% each** |

The most lopsided race of the night. Buckley's four-precursor sweep is historically rare — comparable in scope to Renée Zellweger (2019, *Judy*), Frances McDormand (2017, *Three Billboards*), and Brie Larson (2015, *Room*), all of whom converted identical sweeps to Oscar wins. The only comparable sweep that failed: Cate Blanchett for *Tár* (2022) — but Blanchett didn't win the SAG, which Buckley did. The 0.0% historical upset rate means the model assigns zero probability mass to zero-signal nominees, concentrating everything on Buckley and Byrne. Buckley's four-precursor signal accumulates 9× more than Byrne's single GG Comedy win.

#### 🎭 Best Supporting Actor

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **Sean Penn** | BAFTA (30.4%) + SAG (71.0%) | 101.4 | **59%** |
| Jacob Elordi | CC (61.3%) | 61.3 | **37%** |
| Benicio Del Toro / Delroy Lindo / Stellan Skarsgård | — | 0 | **1% each** |

*Historical upset rate is 6.7% (2/30 years: James Coburn 1998, George Clooney 2005).*

A genuine two-horse race. Penn's dual wins (BAFTA + SAG) give him a clear signal lead over Elordi's single Critics Choice win, and the 6.7% upset rate keeps the floor low. One structural wrinkle: both Penn and Benicio Del Toro are nominated from the same film (One Battle after Another). Vote-splitting between two nominees from the same film could benefit Elordi at the margins, though this dynamic is difficult to quantify from historical data alone.

#### 🌟 Best Supporting Actress

| Nominee | Precursor wins | Signal | Probability |
|---|---|---|---|
| **Amy Madigan** | CC (62.5%) + SAG (71.9%) | 134.4 | **76%** |
| Wunmi Mosaku | BAFTA (37.5%) | 37.5 | **22%** |
| Elle Fanning / Inga Ibsdotter Lilleaas / Teyana Taylor | — | 0 | **1% each** |

*Historical upset rate is 3.3% (1/30 years: Marcia Gay Harden for Pollock in 2000).*

Madigan won both the SAG and Critics Choice — the two most predictive sources in this category — making her the strongest data pick among the supporting races. The model's one unresolvable tension: *Weapons* received no other Oscar nominations in 2026. The sole historical upset in this category (Marcia Gay Harden, *Pollock*, 2000) fits precisely this pattern — a winner from a film with minimal broader Academy support. Mosaku's 22% isn't noise; Sinners' 16-nomination breadth adds qualitative weight that the signal model can't capture.

---

## Fun Stats

**Most Oscar nominations in the 2026 field:** Sinners with 16, covering 16 different categories — one nomination in essentially every department. One Battle after Another follows with 13.

**Films competing across the most key categories:** Three films appear across Best Picture, Best Director, Best Actor/Actress, and Best Supporting Actor/Actress: One Battle after Another, Sentimental Value, and Sinners each appear in 5 of the 6 main categories. Hamnet appears in 3.

**Best Picture/Best Director alignment (since 1980):** 73.3% of the time, the director of the Best Picture winner also wins Best Director. Notable exceptions in recent history: CODA (Jane Campion won for The Power of the Dog, 2022), Green Book (Alfonso Cuarón won for Roma, 2019), Spotlight/The Revenant (Iñárritu won, 2016).

**The GG Comedy trap:** The Golden Globe Best Actor in a Musical or Comedy winner has only converted to an Oscar win 9.2% of the time (7 times in 76 years). It's a beautiful award, but historically it means very little for Oscar prediction. Timothée Chalamet's GG Comedy win is the most misleadingly prestigious precursor in this year's field.

**Jessie Buckley's dominance:** Winning 4 of 5 major precursor awards in Best Actress is one of the most dominant performances by any performer in the 2025 awards season. Comparable in sweep to Renée Zellweger (2019, *Judy*), Frances McDormand (2017, *Three Billboards*), and Brie Larson (2015, *Room*) — all of whom swept BAFTA + SAG + GG Drama + Critics Choice and went on to win the Oscar. Note: The closest recent parallel that didn't convert is Cate Blanchett for *Tár* (2022) — she swept BAFTA, GG Drama, and Critics Choice but lost the SAG to Michelle Yeoh, who then went on to win the Oscar. Buckley won all four.

**The BAFTA acting outliers:** Two BAFTA acting nominees are absent from the Oscar race entirely. Robert Aramayo won BAFTA Lead Actor for *I Swear* — a film not nominated for any Oscar. Additionally, Chase Infiniti was BAFTA-nominated for Lead Actress (for *One Battle After Another*) but also received no Oscar nomination. BAFTA's 2025 acting taste is unusually disconnected from Academy voters, which reduces the value of BAFTA acting wins as a signal this year.

**SAG Cast vs. Academy across 30 years:** 13 out of 30 SAG Cast Award winners also won Oscar Best Picture (43.3%). Recent SAG Cast winners that also took Best Picture: Spotlight (2015), Green Book (2018), CODA (2021), Everything Everywhere All at Once (2022), Oppenheimer (2023) — 5 out of 10 in the last decade, suggesting SAG has become a stronger predictor in the modern era.

**TIFF reality check:** The TIFF People's Choice Award has only matched the Oscar Best Picture winner 7 times in 47 years (14.9%). The memorable hits — Slumdog Millionaire, The King's Speech, 12 Years a Slave, Green Book, Nomadland — stick in memory, but the overall rate is low. It was included in the scoring framework but should be treated as a weak signal. Hamnet's TIFF win adds marginal, not decisive, support.

---

## Data Caveats

All analysis is based on historical patterns and 2025-season precursor results available at time of writing (March 7, 2026). The 98th Academy Awards ceremony has not yet occurred.

**A note on the data:** The datasets use slightly different naming conventions across sources — film title casing, name accents, hyphen vs space variants, comma punctuation in suffixes (e.g. "Chloé Zhao" vs "Chloe Zhao", "Bong Joon-ho" vs "Bong Joon Ho"). These were resolved at the source: parser scripts normalize all precursor CSVs against `oscar_nominations.csv` as the canonical form, so joins on names and film titles are exact string matches. The Golden Globe tables use a `year_from`/`year_to` schema rather than a single `year` column — `year_from` corresponds to the film's release year.

Other data limitations:
- **BAFTA historical categories** include "Best British Actor" (early years) — filtered to modern "Best Actor/Actress" era.
- **TIFF People's Choice** data exists back to 1978 but wasn't used for individual acting predictions (no person-level data). Overall TIFF → Oscar Best Picture match rate is only **14.9%** (7/47 years) — it produces memorable matches (Nomadland, 12 Years a Slave, Green Book) but is a weak predictor overall. It was scored as a precursor for Best Picture but carries little predictive weight.
- The **GG Comedy/Musical** category for picture and actor requires careful interpretation — its historical Oscar prediction rate is significantly lower than the Drama equivalent.
- **All Golden Globe tables contain winners only** — nominee rows are absent from the data. This doesn't affect the historical win-rate calculations (which compare winners to winners) but means we cannot determine which Oscar nominees were GG-nominated without winning.

Config: `plydb-config.json` | Semantic overlay: `oscars-overlay.yaml`

---

## Methodology Critique

The model does the most important thing right: it grounds predictions in historical data rather than intuition. But it makes several simplifications worth being honest about, both to understand the confidence levels correctly and to guide future work.

### 1. Signal aggregation is not probabilistically principled

Adding conversion rates (BAFTA 30.4% + SAG 71.0% = 101.4) has no derivation from probability theory. If precursor wins were independent, correct combination would be multiplicative in probability space — P(wins Oscar | won A and B) ∝ P(won A | wins Oscar) × P(won B | wins Oscar) — not additive. The additive approach systematically inflates multi-precursor nominees relative to single-precursor nominees. In practice this means Penn's 59% and Buckley's 90% are probably directionally right but the exact values shouldn't be taken literally.

### 2. Negative evidence is ignored entirely

A nominee who didn't win the SAG gets no downward adjustment — the model only accumulates positive signal. This is a significant gap. Jordan winning the SAG is informative; Chalamet *losing* the SAG (the single strongest acting predictor) is also informative and should pull his probability down. The current model treats "didn't win" and "wasn't tracked" identically, which overcounts zero-signal nominees' baseline credibility. For SAG, BAFTA, and Critics Choice we have full nominee data and could implement this; for GG we cannot (winners only).

### 3. Precursors are correlated, but treated as independent

BAFTA, SAG, Critics Choice, and the Golden Globes all respond to the same underlying signal — the quality of a performance in a given season. When all four pick Buckley, that isn't four independent observations; it's four correlated measurements of one thing. The model counts them as if independent, which inflates the apparent certainty in sweep scenarios. Buckley's 90% is likely the right order of magnitude, but the convergence of four precursors provides less additional information than four truly independent data points would.

### 4. The upset floor is too coarse

The upset adjustment distributes probability uniformly across all zero-signal nominees. But Coogler (whose film leads all nominees with 16 Oscar nominations) is a more credible zero-signal upset candidate than a nominee with no nominations elsewhere. A more principled floor would weight zero-signal nominees by some prior — total Oscar nominations, historical analog, or film-level precursor performance — rather than treating all of them identically.

### 5. Historical window is arbitrary and treats all eras equally

Using Ceremony 68–97 (roughly 30 years) for precursor overlap was data-driven — that's when most of these precursors began — but a 1996 SAG win counts the same as a 2024 SAG win despite substantial changes in Academy composition and voting rules over that period. The preferential ballot (introduced for Best Picture in 2009), the expansion of Academy membership, and the shift toward streaming all changed the dynamics. A recency-weighted model — or simply restricting to the last 10–15 years — would likely be more predictive, though it would reduce the sample sizes materially.

### 6. Missing precursors

The Directors Guild of America (DGA) Award is historically the single strongest Best Director predictor and isn't in this model. The Producers Guild Award (PGA) similarly leads Best Picture prediction. Their absence is a data gap, not a methodological choice — we don't have that data. Including them would tighten the directing and picture probabilities considerably, and might shift Best Picture away from the current three-way signal split.

### 7. No cross-category correlation

Best Picture and Best Director share a 73.3% historical co-alignment, but the model treats each category independently. PTA's 89% in Best Director is positive evidence for One Battle after Another in Best Picture, but that structural relationship isn't formally encoded — it's mentioned in the narrative but not in the numbers. A joint model across categories would propagate these correlations into the probability estimates.

### 8. Vote-splitting has no representation

Both Penn and Del Toro are nominated from One Battle after Another for Best Supporting Actor. If Academy voters divide between them, Elordi benefits — but the model has no mechanism for this. Historically, co-nominees from the same film in the same category do sometimes split votes (Shakespeare in Love / Saving Private Ryan era is a classic case), but quantifying the effect requires data on within-category vote distributions that aren't public.

### What would improve the model most

In rough priority order:

1. **Add DGA and PGA data** — closes the biggest signal gap for the two most contested categories
2. **Restrict to a recent window (10–15 years) with recency weighting** — better reflects current Academy composition
3. **Use full nominee data to penalize precursor losses** — possible today for SAG, BAFTA, CC; requires new data collection for GG
4. **Smarter upset prior** — weight zero-signal nominees by total Oscar nomination count rather than uniform distribution
5. **Multiplicative rather than additive signal combination** — more principled, though with small samples the practical difference may be modest
