# Glossary

Written for two readers: someone who knows pandas but not cricket, and someone who knows
cricket but not what these charts are conventionally called.

## Cricket, minimum viable

| Term | Meaning |
|---|---|
| **Delivery / ball** | One throw. The unit of a row in this dataset. |
| **Over** | Six *legal* deliveries by one bowler. A T20 innings is 20 overs. |
| **Innings** | One team's turn batting. A T20 match has 2. Values above 2 in this data mean a **super over** (a tie-breaker), not a third innings. |
| **Wicket** | A batter is out. 10 wickets ends an innings early. |
| **Extras** | Runs conceded that the batter did not score: wides, no-balls, byes, leg-byes, penalties. |
| **Wide / no-ball** | Illegal deliveries. They concede a run **and get re-bowled**, so an over can contain more than six rows. |
| **Powerplay** | Overs 1–6, when fielding restrictions apply. Scoring is usually high. |
| **Middle overs** | Roughly 7–15. Restrictions lifted, scoring usually dips. |
| **Death overs** | Roughly 16–20, the end of an innings. Where the exact boundary sits is an argument, which is why this repo does not hard-code it. |
| **Strike rate** | Runs per 100 balls faced. The batting efficiency measure in T20. |
| **Economy** | Runs conceded per over. The bowling equivalent. |
| **Chase** | The second innings, batting with a known target. Behaves differently from a first innings — a team needing 4 off 30 stops attacking. |
| **Duck** | Dismissed for 0. |
| **Maiden over** | An over conceding no runs. |

## Chart names cricket already has

Cricket invented these visualisations and named them decades before anyone called it data
viz. Using the real names costs nothing and immediately reads as insider.

| Name | What it is | Matplotlib equivalent |
|---|---|---|
| **Manhattan** | Runs per over as vertical bars. The skyline shape is the name. | `ax.bar(over, runs)` |
| **Worm** | Cumulative runs against balls faced, one line per innings. | `ax.plot(balls, runs.cumsum())` |
| **Wagon wheel** | Runs radiating from the batter by the direction they were hit. | polar scatter — **needs shot-direction data this archive does not have** |
| **Pitch map** | Where deliveries landed, as a 2-D scatter over the pitch. | scatter — **needs ball-tracking data this archive does not have** |
| **Beehive** | Where deliveries passed the batter, viewed from behind the stumps. | scatter — also unavailable here |

Only **Manhattan** and **worm** are buildable from this dataset. The others need
ball-tracking, which Cricsheet does not publish. Listed anyway so it is clear they were
considered and ruled out on data availability, not forgotten.

## Analysis terms used in this repo

| Term | Meaning here |
|---|---|
| **Informative null** | A blank that carries meaning. `wicket_type` is 95% null because 95% of deliveries take no wicket — the blank is data, not absence. |
| **Grain** | What one row represents. Here: one delivery, one innings, one match. |
| **Right-censored** | A record whose outcome has not finished yet. Relevant if this ever tracks in-progress seasons. |
| **Survivorship bias** | Drawing a conclusion from records that survived a filter. Q3's trap: short innings have low totals for reasons unrelated to a first-over wicket. |
| **Category dtype** | Pandas' interned-string type. 19 team names stored as codes instead of 295k separate strings. |
| **`usecols`** | Reading only the columns you need. Worth 1.4× here — less than the `category` dtype's 2.5×, which is the opposite of the usual advice. |
