# The five questions

Written **before** any analysis, and committed so they cannot be edited afterwards to
match whatever the charts turned out to show. Git history is the honesty mechanism here.

A question belongs on this list only if a plausible answer would have surprised me. "How
many runs were scored in total?" is a lookup, not a question.

Each one records the hypothesis **and** what would falsify it. A hypothesis that cannot
be wrong is not a hypothesis.

---

## Q1 — Do runs per over spike in the death overs?

Commentary treats overs 16–20 as a different game. Quantify it: mean runs per over across
all innings, by over number.

- **Hypothesis:** yes, and the rise is steeper than the powerplay's, because field
  restrictions have lifted but batters are swinging anyway.
- **Falsified if:** the curve is roughly flat after over 6, or the powerplay is the higher
  peak.
- **Watch for:** the second innings of a chase distorts this — a team needing 4 runs off
  30 balls stops attacking. Consider splitting by innings.
- **Chart:** a *Manhattan* (see glossary).

## Q2 — Has scoring inflated across 19 seasons, or is it flat?

Everyone asserts T20 scoring keeps climbing. Test it: runs per over by season.

- **Hypothesis:** it has risen, but far less than commentary implies, and unevenly.
- **Falsified if:** the trend is flat, or non-monotonic in a way no rule change explains.
- **Watch for:** this question is the reason `season_year` must come from `start_date` —
  see [ADR 0004](decisions/0004-season-year.md). Get that wrong and 2009 and 2009/10 merge,
  which bends the early trend. Also: 2009 was played in South Africa and 2020 in the UAE.
- **Chart:** line, one point per season.

## Q3 — Does losing a wicket in the first over reduce the innings total?

The most interesting of the five, because "first-over wicket" is not a column. It has to
be derived: group to innings level, check whether any non-null `wicket_type` occurs where
`over == 0`, then join that flag back.

- **Hypothesis:** yes, but by less than 10 runs on average — T20 batting orders are deep
  enough to absorb it.
- **Falsified if:** the difference is negligible (< 2 runs), or the direction reverses.
- **Watch for:** survivorship. Innings that ended early (rain, a completed chase) have
  lower totals for reasons unrelated to the wicket. Filter to innings of at least 19 overs
  before comparing, and say so.
- **Chart:** two distributions, not two bar heights — the spread is the finding.

## Q4 — Which venue shows the largest home advantage?

- **Hypothesis:** a real effect exists but is small, and mostly concentrated in two or
  three genuinely distinctive pitches.
- **Falsified if:** no venue's advantage survives once eras are separated.
- **Watch for:** this needs the `_info.csv` files for match winners, which are key-value
  long format and currently unused — so this question **may be deferred**, and that is a
  legitimate outcome to report rather than hide. Beyond that: CSK and RR were suspended in
  2016–17, and 2009 and 2020 were played abroad, so "home" is not even defined for those
  seasons.
- **Chart:** venue on the y-axis, sorted by effect, error bars.

## Q5 — Are wides and no-balls getting rarer?

- **Hypothesis:** slightly rarer, and the effect is smaller than the noise between seasons.
- **Falsified if:** the rate is rising, or the between-season variance swamps the trend
  entirely — in which case the honest answer is "cannot tell from this data".
- **Watch for:** `wides` and `noballs` are 96.7% and 99.6% null, and null means zero.
  Forget `fill_extras` and every rate here is computed over the wrong denominator.
- **Chart:** two lines, per-season rate per 100 balls.

---

## The rule for answering these

Every answer gets **one number and one caveat**. "Death overs average 9.8 runs against
7.1 in the middle overs — but this pools both innings, and a chase behaves differently
from a first innings."

And at least one of these five gets written up as **not working**. A question that dies
honestly is worth more than five that all conveniently confirmed themselves.
