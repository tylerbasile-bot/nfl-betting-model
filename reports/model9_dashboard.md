# Model 9 — NFL Market Intelligence

Generated: `2026-11-10T08:56:48+00:00`

> **Research only — NO VERIFIED EDGE.** Prices and market consensus are not independently validated win probabilities.

## Pipeline summary

- Odds files read: **1**
- Pregame games with at least 4 fresh books: **12**
- Quotes rejected due to malformed fields or prices: **0**
- Games with an observed quote within 3 hours of kickoff after the initial snapshot: **0**
- Games with verified results supplied: **0**

## Pregame baseline and movement

| Game | Kickoff (UTC) | First market home % | Latest home % | Change (pp) | Best first home | Best first away | Near kickoff? |
|---|---|---:|---:|---:|---|---|---|
| Washington Commanders @ New York Giants | 2026-11-13T01:15 | 53.79% | 55.07% | +1.279 | FanDuel (-124) | BetOnline.ag (+115) | NO |
| New England Patriots @ Detroit Lions | 2026-11-15T14:30 | 57.98% | 58.14% | +0.156 | BetUS (-150) | DraftKings (+130) | NO |
| Jacksonville Jaguars @ Tennessee Titans | 2026-11-15T18:00 | 19.35% | 18.77% | -0.587 | FanDuel (+440) | BetUS (-500) | NO |
| Kansas City Chiefs @ Atlanta Falcons | 2026-11-15T18:00 | 37.89% | 37.80% | -0.092 | Bovada (+160) | FanDuel (-178) | NO |
| Miami Dolphins @ Indianapolis Colts | 2026-11-15T18:00 | 55.26% | 55.36% | +0.096 | BetOnline.ag (-133) | Bovada (+122) | NO |
| Houston Texans @ Cleveland Browns | 2026-11-15T18:00 | 32.95% | 32.95% | +0.000 | BetUS (+195) | BetRivers (-205) | NO |
| Carolina Panthers @ New Orleans Saints | 2026-11-15T18:00 | 51.71% | 51.74% | +0.024 | FanDuel (-112) | DraftKings (+100) | NO |
| Seattle Seahawks @ Las Vegas Raiders | 2026-11-15T21:05 | 38.13% | 37.99% | -0.141 | Bovada (+158) | DraftKings (-175) | NO |
| Los Angeles Rams @ Arizona Cardinals | 2026-11-15T21:05 | 20.99% | 21.34% | +0.350 | DraftKings (+360) | BetUS (-440) | NO |
| San Francisco 49ers @ Dallas Cowboys | 2026-11-15T21:25 | 34.52% | 34.52% | +0.000 | FanDuel (+180) | DraftKings (-205) | NO |
| Pittsburgh Steelers @ Cincinnati Bengals | 2026-11-16T01:20 | 63.83% | 63.83% | +0.000 | DraftKings (-180) | LowVig.ag (+171) | NO |
| Los Angeles Chargers @ Baltimore Ravens | 2026-11-17T01:15 | 67.42% | 67.42% | +0.000 | DraftKings (-225) | BetUS (+200) | NO |

## Outcome validation

No final outcomes supplied. Do **not** report accuracy, ROI, or model profitability yet.

To add results, create `data/results.csv` with columns
`event_id,status,winner`. Use `final` and the exact full team name; ties are excluded.

## Methodology and limitations

- Snapshot rows are grouped by event ID, capture time and sportsbook; only quotes no more than 30 minutes stale are eligible.
- Each baseline forecast is the **median bookmaker no-vig home probability at the first qualifying pregame snapshot** (at least four bookmakers).
- Later probabilities are reported solely as observed movements; they never alter the initial forecast.
- A quote collected within 3 hours of kickoff is labelled **near kickoff**, not a confirmed true closing line.
- The best price is the highest American moneyline for each side, among books available at the *first* eligible snapshot.
- No positive-EV betting signals are issued. Historical performance of prior statistical models failed to show a reliable edge.
- API event IDs may differ from NFLverse game IDs. Match by teams and kickoff date only with explicit validation.
- Results are optional and must be independently verified; do not infer wins from moneyline odds.
