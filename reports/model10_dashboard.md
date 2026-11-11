# Model 10 — Prospective NFL Market Validation

Updated: `2026-11-11T16:15:16.526421+00:00`

> **NO VERIFIED EDGE — RESEARCH ONLY.** This is a frozen market-derived baseline, not an independently validated predictive betting model.

## Data integrity

- First-run forecasts created this execution: **0**
- Total immutable forecast records: **14**
- Historical odds files scanned: **3**
- Rejected malformed odds observations: **2**
- Forecasts with near-kickoff reference: **0**
- Forecasts with verified final game results: **0**

## Locked pregame predictions

| Game | Kickoff UTC | Frozen at UTC | Home win % | First home ML | First away ML | Latest shift (pp) | Near kickoff? | Result |
|---|---|---|---:|---|---|---:|---|---|
| Washington Commanders @ New York Giants | 2026-11-13T01:15 | 2026-11-10T14:34 | 54.27% | FanDuel (-126) | BetUS (+115) | 0.985 | NO | AWAITING_VERIFIED_RESULT |
| New England Patriots @ Detroit Lions | 2026-11-15T14:30 | 2026-11-10T14:34 | 58.72% | DraftKings (-148) | BetRivers (+140) | -0.004 | NO | AWAITING_VERIFIED_RESULT |
| Buffalo Bills @ New York Jets | 2026-11-15T18:00 | 2026-11-10T14:34 | 21.34% | DraftKings (+390) | BetOnline.ag (-440) | -0.017 | NO | AWAITING_VERIFIED_RESULT |
| Jacksonville Jaguars @ Tennessee Titans | 2026-11-15T18:00 | 2026-11-10T14:34 | 18.37% | BetRivers (+480) | BetUS (-500) | 0.000 | NO | AWAITING_VERIFIED_RESULT |
| Kansas City Chiefs @ Atlanta Falcons | 2026-11-15T18:00 | 2026-11-10T14:34 | 37.89% | BetOnline.ag (+157) | FanDuel (-178) | -0.136 | NO | AWAITING_VERIFIED_RESULT |
| Minnesota Vikings @ Green Bay Packers | 2026-11-15T18:00 | 2026-11-10T14:34 | 65.73% | DraftKings (-205) | BetOnline.ag (+186) | -3.994 | NO | AWAITING_VERIFIED_RESULT |
| Miami Dolphins @ Indianapolis Colts | 2026-11-15T18:00 | 2026-11-10T14:34 | 55.26% | DraftKings (-135) | Bovada (+122) | 8.831 | NO | AWAITING_VERIFIED_RESULT |
| Houston Texans @ Cleveland Browns | 2026-11-15T18:00 | 2026-11-10T14:34 | 33.08% | BetMGM (+195) | DraftKings (-225) | -0.125 | NO | AWAITING_VERIFIED_RESULT |
| Carolina Panthers @ New Orleans Saints | 2026-11-15T18:00 | 2026-11-10T14:34 | 51.71% | FanDuel (-112) | Bovada (+102) | 3.739 | NO | AWAITING_VERIFIED_RESULT |
| Seattle Seahawks @ Las Vegas Raiders | 2026-11-15T21:05 | 2026-11-10T14:34 | 38.13% | Bovada (+158) | FanDuel (-178) | -9.596 | NO | AWAITING_VERIFIED_RESULT |
| Los Angeles Rams @ Arizona Cardinals | 2026-11-15T21:05 | 2026-11-10T14:34 | 21.36% | MyBookie.ag (+370) | BetUS (-450) | 0.258 | NO | AWAITING_VERIFIED_RESULT |
| San Francisco 49ers @ Dallas Cowboys | 2026-11-15T21:25 | 2026-11-10T14:34 | 34.25% | BetUS (+183) | BetRivers (-210) | 0.677 | NO | AWAITING_VERIFIED_RESULT |
| Pittsburgh Steelers @ Cincinnati Bengals | 2026-11-16T01:20 | 2026-11-10T14:34 | 63.41% | DraftKings (-180) | LowVig.ag (+170) | -0.891 | NO | AWAITING_VERIFIED_RESULT |
| Los Angeles Chargers @ Baltimore Ravens | 2026-11-17T01:15 | 2026-11-10T14:34 | 67.42% | DraftKings (-218) | BetUS (+200) | -1.532 | NO | AWAITING_VERIFIED_RESULT |

## Future outcome scoring

No verified final results yet. No accuracy, return, or profitability claim is possible.

## Validation rules

- Each game is frozen once, from a snapshot collected within 15 minutes of workflow execution, at least 12 hours before kickoff.
- The saved forecast never updates, even when market lines move.
- At least four bookmakers with quotes updated within 30 minutes are required.
- Market probability = median no-vig bookmaker probability; it is not an independently fitted NFLverse model.
- Later snapshots are observation-only. A quote within 3 hours of kickoff is a near-kickoff proxy, **not necessarily the closing line**.
- Scores are accepted only when a user-verified `data/results.csv` explicitly lists `status=final` and the winning team.
- The system does not issue betting recommendations, calculate speculative ROI, or identify verified +EV selections.
- API event IDs and NFLverse game IDs must be matched carefully before importing NFLverse statistics.
