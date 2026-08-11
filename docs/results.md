# Results

Five questions, five answers. Two of the five hypotheses were wrong, and this file says
which. The questions and their falsification criteria were committed in
[questions.md](questions.md) **before** any of this was computed; git history is the
honesty mechanism, not this paragraph.

Every number here was measured against the archive downloaded 2026-08-11 — 295,732
deliveries, 1,243 matches, 19 seasons — by running
[`notebooks/01_explore.ipynb`](../notebooks/01_explore.ipynb). Super overs (`innings > 2`,
175 deliveries) are excluded throughout, and a delivery's total is `runs_off_bat + extras`.

## The standard each entry is held to

- **The number.** A single figure, with its units and its denominator.
- **The caveat.** What population the number is actually over, and what it does not cover.
- **The chart**, saved to `reports/` via `plots.save_fig` and referenced by filename.
- **How it could be wrong.** The aggregation rejected, or the confound not controlled for.

A finding without a caveat is not finished.

---

## Q1 — Do runs per over spike in the death overs?

> **Hypothesis:** yes, and the rise is steeper than the powerplay's.
> **Falsified if:** the curve is flat after over 6, or the powerplay is the higher peak.

**Half right.** The death overs (16–20) average **9.78 runs per over** against **7.94** in
the middle overs (7–15) — a premium of **+1.84**. The denominator is innings that actually
reached each over, not all 2,480.

But the second clause is **wrong**. The powerplay climbs at **+0.47 runs/over per over**
(6.36 → 8.73 across overs 1–6); the death climbs at **+0.40** (9.01 → 10.59 across 16–20).
The death overs are higher, and they get there more slowly.

Neither falsification condition fires: the curve is not flat after over 6, and the
powerplay peak (8.73) is below the death peak (10.59). So the hypothesis stands as
written and its stated reasoning does not.

**Caveat.** This pools both innings, and a chase behaves differently from a first innings
once the target is close. It also counts a part-bowled last over as a whole over: measured
per six *legal* balls, the last over is **11.43** rather than 10.59.

**Chart.** `reports/q1_runs_per_over.png` — a Manhattan, with the wrong denominator drawn
over it in red.

**How it could be wrong.** Where the death overs begin is an argument, not a fact. This
uses the conventional last five; moving the boundary to over 17 or 15 moves the premium,
which is why no `phase` column exists in the package ([ADR 0006](decisions/0006-analysis-in-notebooks.md)).
The per-over series is in the chart so a reader can draw the line somewhere else.

---

## Q2 — Has scoring inflated across 19 seasons?

> **Hypothesis:** risen, but less than commentary implies, and unevenly.
> **Falsified if:** flat, or non-monotonic in a way no rule change explains.

**Risen, and unevenly — but not modestly.** Scoring went from **8.24 runs per over in 2008
to 9.80 in 2026**, **+1.56 (+18.9%)**, over overs actually bowled.

"Unevenly" is an understatement. The first fourteen seasons average **8.07** and never
exceed 8.59. The last five average **9.25** and rise every single year. Essentially the
entire increase arrives after 2021.

"Less than commentary implies" is the part that looks wrong. A 19% rise concentrated into
four seasons is a large move.

**Caveat.** Seasons are not directly comparable. 2009 was played in South Africa and 2020
in the UAE; the lowest season in the series (7.43) and the biggest year-on-year fall
(−0.81) are both 2009. CSK and RR were suspended in 2016–17, and the league expanded from
eight teams to ten in 2022 — the same year the climb starts.

**Chart.** `reports/q2_runs_per_over_by_season.png`

**How it could be wrong.** The 2022 step coincides with expansion and the 2023 step with
the impact player rule, but this data cannot test either — there is no counterfactual
season. Rate per over also hides whether more runs come from more boundaries or fewer dot
balls, which is a different question this does not answer.

---

## Q3 — Does a first-over wicket reduce the innings total?

> **Hypothesis:** yes, but by under 10 runs on average.
> **Falsified if:** the difference is under 2 runs, or reverses.

**Yes — by 12.5 runs.** Across 1,243 first innings: **158.1 runs** when a wicket fell in
the first over (n=199) against **170.6** when none did (n=1,044). Difference **−12.5**,
rough 95% interval **−17.5 to −7.5**.

Not falsified — the gap is far more than 2 runs and does not reverse. But the hypothesis
predicted "under 10" and the point estimate is 12.5. Since 10 sits inside the interval,
this is a mis-estimate rather than a refutation.

**Caveat.** **First innings only.** A chase is stopped by the result — 38% of second
innings end before the last over — so a second-innings total measures the target, not what
the side could have made. Including them gives −10.0 runs, which looks closer to the
hypothesis and is contaminated.

**Chart.** `reports/q3_first_over_wicket.png`

**How it could be wrong.** This is an association, not a cost. The conditions that produce
a first-over wicket — a seaming pitch, a new ball moving — keep suppressing runs for the
rest of the innings, and nothing here separates the wicket from the conditions that caused
it. The honest reading is "innings that lose an early wicket score 12.5 fewer runs", not
"an early wicket costs 12.5 runs".

The rejected aggregation is recorded below: filtering to innings of at least 19 overs, as
this repo's own notebook originally advised, removes the collapses that *are* the effect.

---

## Q4 — Which venue shows the largest home advantage?

> **Hypothesis:** a real but small effect, concentrated in two or three pitches.
> **Falsified if:** no venue's advantage survives separating eras.

**No longer deferred.** Match winners are now read from the 1,243 `_info.csv` files by
`loaders.load_match_info()` — see [ADR 0007](decisions/0007-reading-the-info-files.md).

**The largest is Hyderabad's Rajiv Gandhi International Stadium, +19.5 percentage points.**
Sunrisers Hyderabad win **61.8%** there (n=68) against **42.3%** away (n=123). Then
Chepauk at +14.6 (CSK, n=83) and Sawai Mansingh at +11.4 (RR, n=66).

League-wide the effect is real and small: **53.3% at home against 48.2% away, +5.1
points**. Nine of the fifteen teams show no home advantage at all.

Not falsified: four of the eight teams with at least 15 home and 15 away matches in both
eras keep a positive advantage. But only just — see below.

**Caveat.** Home advantage is **collapsing**. Before 2016 it was **+8.5 points** (55.3% vs
46.8%); from 2016 it is **+2.6** (51.7% vs 49.1%). Rajasthan had the largest early-era
advantage at +26.4 and it **reverses** to −3.4 in the late era; KKR's +18.5 goes to −2.9.
The pooled ranking is largely a fossil of the first eight seasons.

Sample sizes are small. No ground has more than 100 home matches and most have under 70.
A 5-point difference on 68 matches is about one extra win every three seasons.

2009 (South Africa) and 2020 (UAE) are excluded before "home" is defined, because nobody
was at home in either.

**Chart.** `reports/q4_home_advantage.png` — sample size is in every label, because it is
the story.

**How it could be wrong.** "Home" is not in the data. It is defined here as a team's modal
ground, which is a choice, and it misfires for franchises that moved or were suspended.
The measure is also **team-at-ground, not ground**: Deccan Chargers and Sunrisers Hyderabad
share the Rajiv Gandhi International Stadium and sit at opposite ends of the table (−24.8
and +19.5), so what is being measured is not a property of the pitch. Nothing separates
crowd from pitch familiarity from travel. Playoff and final matches at a team's own ground
are counted as home matches, which they arguably are not.

---

## Q5 — Are wides and no-balls getting rarer?

> **Hypothesis:** slightly rarer, and the effect is smaller than the noise between seasons.
> **Falsified if:** the rate is rising, or the between-season variance swamps the trend
> entirely — in which case the honest answer is "cannot tell from this data".

**Falsified.** Wides are getting **more** common: **4.42 per 100 deliveries in 2008 to 5.20
in 2026**, correlation with season year **+0.43**, and 2026 is the highest of all nineteen
seasons. No-balls did fall, **0.61 to 0.36**, correlation **−0.31**.

Both falsification conditions fire. The rate is rising for wides, *and* the noise nearly
swamps the trend: the wide rate's season-to-season standard deviation is **0.62** against
a total drift of **0.78** across nineteen years. Individual seasons say nothing.

The hypothesis also assumed "extras" moves as one thing. It does not — wides and no-balls
move in opposite directions.

**Caveat.** The denominator is every delivery, which is only correct because
`clean.fill_extras` turned 96.7% and 99.6% null columns into zeros
([ADR 0003](decisions/0003-informative-nulls.md)). Left null, both rates would be computed
over only the deliveries that conceded that extra — inflating the wide rate by roughly 30×
and the no-ball rate by roughly 250×, since the two columns are null to different degrees.

**Chart.** `reports/q5_wides_and_noballs.png`

**How it could be wrong.** A wide is an umpire's decision, so this cannot separate bowlers
losing accuracy from umpires calling a tighter line — and the wide line for T20 has been
interpreted more strictly over the period. Those are different findings with the same
number.

---

## What didn't work

The section that makes the rest credible.

**1. Q1's denominator was wrong first, and it inverted the answer.** Dividing runs in an
over by *every* innings makes the last over read **8.12 runs and falling** from over 18. It
is **10.59 and rising**. 578 innings — **23.3%** — never reach the last over, because a
chase stops at the target and an innings stops at the tenth wicket. The glossary already
defined *right-censored*; it got written wrong anyway. The wrong series is kept on the Q1
chart rather than quietly deleted.

**2. Q4 was computed on venue names, and Chennai appeared to abandon their own ground in
2016.** Cricsheet does not normalise venue strings. `MA Chidambaram Stadium, Chepauk` holds
48 matches and `MA Chidambaram Stadium, Chepauk, Chennai` holds 41, split almost exactly at
that year — **60 strings for 36 grounds**. Every home sample was a fragment, and CSK fell
out of the era comparison entirely for want of matches. The data dictionary says "names not
normalised upstream" in plain sight. Fixed in `clean.canonical_venues`; the first Q4 table
produced before the fix was wrong in its ordering, not just its precision.

**3. This repo's own advice on Q3 was wrong.** The notebook said to filter to innings of at
least 19 overs. For a *first* innings that is backwards: a first innings only ends early by
being bowled out or rained off, and being bowled out is part of the effect. Short first
innings are **23.3%** first-over-wicket against a **16.0%** base rate, so the filter removes
exactly the collapses the question is about. The estimate survives it (−12.26 against
−12.52), so nothing changed here — but it would have on a smaller effect, and the guard was
recommended in this repository, in writing, before anyone checked.

**4. And the first version of that filter counted rows, not overs.** `balls < 114` reads as
"under 19 overs" and is not — a row is a delivery *recorded*, so an innings with six wides
carries six more rows than its overs imply, and the threshold quietly selects for innings
with few extras. On this archive both definitions pick the same 43 innings and the
sensitivity figure moved by 0.03 runs, so nothing here was affected. That was luck. Caught
in review, and now counted with `over.nunique()`.

**5. Two of the five hypotheses were wrong.** Q5 is falsified outright. Q1's "steeper than
the powerplay" is false, though its headline claim holds. Q2's "less than commentary
implies" is doubtful at +18.9%. Three of five landing cleanly would have been a sign the
questions were too safe.

**6. Nothing here is causal, and two questions were phrased as though they were.** Q3 asks
whether a wicket "reduces" a total and can only show association. Q4 asks which venue
"shows" an advantage and measures teams at grounds, not grounds.

**7. `actual_delivery` is still unresolved rather than understood.** It disagrees with
`ball` on 12.05% of rows. Nothing above depends on it, which is not the same as it being
harmless — [ADR 0002](decisions/0002-ball-not-actual-delivery.md) documents the exposure
rather than claiming the choice is proven right.
