# 0006 — The analysis stays out of the package

**Status:** accepted

## Context

The obvious way to build this repo is to put everything in the package: a
`analyse.runs_per_over()`, a `phase` column, a `report` CLI verb that renders all five
charts. It would be tidier, more testable, and it would make `scorebook report` produce the
whole project in one command.

## Decision

The package handles acquisition, validation, cleaning, summary, and chart styling. It does
not aggregate, does not classify overs into phases, and offers no `analyse` verb.
`docs/results.md` ships as a stub. The notebook's five question sections are empty.

The dividing test: **does this have one correct answer, or does it need an argument?**

## Why

**Choices that need defending should be visible.** `phase = "death" if over >= 15` looks
like plumbing and is actually a claim. Overs 16–20 is the common convention; 15 is
defensible; some analysts use the last five *balls-remaining* rather than overs. The
threshold changes Q1's answer. Buried in `clean.py` behind a tested function it reads as
settled fact. Written in a notebook cell next to the chart it produces, it reads as what it
is — a decision a reader can disagree with.

**A tested function looks authoritative whether or not it deserves to.** `clean.add_over` is
correct in a way `analyse.death_over_premium()` could never be: one is arithmetic on a
documented field, the other is an opinion with test coverage. Putting them in the same
module implies they have the same standing.

**This project's purpose is the analysis.** It exists so its author learns to interrogate a
dataset — form a hypothesis, choose an aggregation, discover the aggregation is wrong,
choose again. A `report` verb that emits five finished charts would deliver the artefact and
skip the entire point. The plumbing is genuinely worth having pre-built, because debugging a
zip reader teaches nothing about cricket or pandas; the groupby is where the learning is.

**Notebooks are the honest place for exploratory work.** The messy path — the aggregation
that turned out to double-count wides — belongs somewhere visible, not hidden behind a clean
function signature that implies it was obvious all along.

## Cost

**The analysis is untested.** No `pytest` run catches a wrong groupby in a notebook cell.
That is a real and unmitigated gap: a bug in the analysis surfaces only if someone checks
the number against reality. Partly why `docs/questions.md` records what would *falsify* each
hypothesis — a prediction is a weak test, but it beats none.

**Coverage numbers flatter this repo.** 99% covers plumbing that is a fraction of the
intellectual work. A reader could mistake that for the analysis being verified. Stated here
so the number is not oversold.

**Notebooks diff badly and hold stale output.** Mitigated by keeping cleaning in the package
— cell order cannot corrupt the data, because every `clean` function returns a new frame —
but a notebook committed with stale output remains a real hazard.

**`scorebook report` would be genuinely convenient**, and its absence is a deliberate cost,
not an oversight. Once the five questions are answered and `docs/results.md` is written, the
argument for keeping it out gets weaker. Revisit then.
