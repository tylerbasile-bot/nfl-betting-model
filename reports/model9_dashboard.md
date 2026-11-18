# Model 9 — NFL Market Intelligence

Generated: `2026-11-18T07:37:47+00:00`

> **Research only — NO VERIFIED EDGE.** Prices and market consensus are not independently validated win probabilities.

## Pipeline summary

- Odds files read: **9**
- Pregame games with at least 4 fresh books: **27**
- Quotes rejected due to malformed fields or prices: **0**
- Games with an observed quote within 3 hours of kickoff after the initial snapshot: **13**
- Games with verified results supplied: **14**

## Pregame baseline and movement

| Game | Kickoff (UTC) | First market home % | Latest home % | Change (pp) | Best first home | Best first away | Near kickoff? |
|---|---|---:|---:|---:|---|---|---|
| Washington Commanders @ New York Giants | 2026-11-13T01:15 | 53.79% | 53.25% | -0.540 | FanDuel (-124) | BetOnline.ag (+115) | YES |
| New England Patriots @ Detroit Lions | 2026-11-15T14:30 | 57.98% | 57.21% | -0.777 | BetUS (-150) | DraftKings (+130) | NO |
| Buffalo Bills @ New York Jets | 2026-11-15T18:00 | 21.34% | 20.63% | -0.717 | DraftKings (+390) | BetOnline.ag (-440) | YES |
| Jacksonville Jaguars @ Tennessee Titans | 2026-11-15T18:00 | 19.35% | 17.41% | -1.941 | FanDuel (+440) | BetUS (-500) | YES |
| Kansas City Chiefs @ Atlanta Falcons | 2026-11-15T18:00 | 37.89% | 38.13% | +0.238 | Bovada (+160) | FanDuel (-178) | YES |
| Minnesota Vikings @ Green Bay Packers | 2026-11-15T18:00 | 65.73% | 57.46% | -8.266 | DraftKings (-205) | BetOnline.ag (+186) | YES |
| Miami Dolphins @ Indianapolis Colts | 2026-11-15T18:00 | 55.26% | 65.75% | +10.488 | BetOnline.ag (-133) | Bovada (+122) | YES |
| Houston Texans @ Cleveland Browns | 2026-11-15T18:00 | 32.95% | 36.14% | +3.197 | BetUS (+195) | BetRivers (-205) | YES |
| Carolina Panthers @ New Orleans Saints | 2026-11-15T18:00 | 51.71% | 49.67% | -2.039 | FanDuel (-112) | DraftKings (+100) | YES |
| Seattle Seahawks @ Las Vegas Raiders | 2026-11-15T21:05 | 38.13% | 28.25% | -9.872 | Bovada (+158) | DraftKings (-175) | YES |
| Los Angeles Rams @ Arizona Cardinals | 2026-11-15T21:05 | 20.99% | 19.62% | -1.372 | DraftKings (+360) | BetUS (-440) | YES |
| San Francisco 49ers @ Dallas Cowboys | 2026-11-15T21:25 | 34.52% | 34.93% | +0.408 | FanDuel (+180) | DraftKings (-205) | YES |
| Pittsburgh Steelers @ Cincinnati Bengals | 2026-11-16T01:20 | 63.83% | 65.07% | +1.238 | DraftKings (-180) | LowVig.ag (+171) | YES |
| Los Angeles Chargers @ Baltimore Ravens | 2026-11-17T01:15 | 67.42% | 65.89% | -1.532 | DraftKings (-225) | BetUS (+200) | YES |
| Indianapolis Colts @ Houston Texans | 2026-11-20T01:15 | 80.20% | 84.65% | +4.452 | DraftKings (-455) | FanDuel (+410) | NO |
| New Orleans Saints @ Chicago Bears | 2026-11-22T18:00 | 79.40% | 83.16% | +3.766 | DraftKings (-470) | FanDuel (+430) | NO |
| Arizona Cardinals @ Kansas City Chiefs | 2026-11-22T18:00 | 88.00% | 90.09% | +2.088 | DraftKings (-1000) | FanDuel (+750) | NO |
| Tampa Bay Buccaneers @ Detroit Lions | 2026-11-22T18:00 | 61.40% | 74.33% | +12.926 | FanDuel (-172) | DraftKings (+150) | NO |
| Baltimore Ravens @ Carolina Panthers | 2026-11-22T18:00 | 52.85% | 56.56% | +3.711 | DraftKings (-122) | FanDuel (+108) | NO |
| Miami Dolphins @ Buffalo Bills | 2026-11-22T18:00 | 91.00% | 90.40% | -0.607 | MyBookie.ag (-1695) | DraftKings (+1000) | NO |
| Tennessee Titans @ Dallas Cowboys | 2026-11-22T18:00 | 78.51% | 77.06% | -1.447 | MyBookie.ag (-420) | FanDuel (+360) | NO |
| Pittsburgh Steelers @ Philadelphia Eagles | 2026-11-22T18:00 | 35.52% | 34.19% | -1.328 | FanDuel (+172) | DraftKings (-198) | NO |
| New York Jets @ Los Angeles Chargers | 2026-11-22T21:05 | 53.42% | 61.83% | +8.412 | BetRivers (-122) | FanDuel (+108) | NO |
| Las Vegas Raiders @ Denver Broncos | 2026-11-22T21:25 | 78.42% | 81.63% | +3.210 | BetRivers (-385) | FanDuel (+350) | NO |
| Jacksonville Jaguars @ New York Giants | 2026-11-22T21:25 | 31.38% | 30.16% | -1.221 | DraftKings (+215) | BetRivers (-245) | NO |
| Minnesota Vikings @ San Francisco 49ers | 2026-11-23T01:20 | 64.69% | 60.11% | -4.579 | DraftKings (-205) | FanDuel (+190) | NO |
| Cincinnati Bengals @ Washington Commanders | 2026-11-24T01:15 | 35.43% | 28.80% | -6.635 | FanDuel (+176) | DraftKings (-205) | NO |

## Outcome validation

- Evaluated games: **14**
- Market baseline Brier score: **0.2097** (lower is better)
- Market baseline log loss: **0.6043** (lower is better)
- Market baseline winner accuracy: **64.3%**

This is a market baseline, **not** an independently trained predictive model.

## Methodology and limitations

- Snapshot rows are grouped by event ID, capture time and sportsbook; only quotes no more than 30 minutes stale are eligible.
- Each baseline forecast is the **median bookmaker no-vig home probability at the first qualifying pregame snapshot** (at least four bookmakers).
- Later probabilities are reported solely as observed movements; they never alter the initial forecast.
- A quote collected within 3 hours of kickoff is labelled **near kickoff**, not a confirmed true closing line.
- The best price is the highest American moneyline for each side, among books available at the *first* eligible snapshot.
- No positive-EV betting signals are issued. Historical performance of prior statistical models failed to show a reliable edge.
- API event IDs may differ from NFLverse game IDs. Match by teams and kickoff date only with explicit validation.
- Results are optional and must be independently verified; do not infer wins from moneyline odds.
