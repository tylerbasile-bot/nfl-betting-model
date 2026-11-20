# Model 13 — Prospective Cross-Book Pricing Study

Updated: `2026-11-20T00:53:43.303306+00:00`

> **NO VERIFIED +EV. PAPER RESEARCH ONLY.** Differences between sportsbooks are not independent probabilities.

- New frozen candidate observations: **0**
- Total locked observations: **11**
- With near-kickoff reference: **4**
- With same-book near-kickoff price: **4**
- With verified finals: **3**

## Precommitted selection rule

At least five fresh bookmakers, a snapshot observed within 15 minutes, kickoff at least 12 hours ahead, and a minimum 2% *indicative* return using the median no-vig probability of OTHER books. One candidate per event; highest apparent discrepancy wins. No backfilled picks, no post-result selection.

| Matchup | Side | Observed odds | Proportional ref. | Proportional indic. return | Power ref. | Power indic. return | Market shift | Same-book shift | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Buffalo Bills @ New York Jets | HOME | DraftKings (+390) | 21.51% | +5.39% | 19.57% | -4.10% | -0.881 pp | +0.868 pp | VERIFIED_FINAL |
| Jacksonville Jaguars @ Tennessee Titans | HOME | BetRivers (+480) | 18.52% | +7.41% | 16.62% | -3.58% | -1.106 pp | +1.806 pp | VERIFIED_FINAL |
| Los Angeles Rams @ Arizona Cardinals | HOME | MyBookie.ag (+370) | 21.71% | +2.05% | 19.88% | -6.55% | -2.093 pp | -1.237 pp | VERIFIED_FINAL |
| Indianapolis Colts @ Houston Texans | AWAY | BetRivers (+475) | 17.79% | +2.31% | 15.83% | -8.99% | -2.485 pp | -0.998 pp | PENDING |
| New Orleans Saints @ Chicago Bears | AWAY | FanDuel (+450) | 19.87% | +9.27% | 17.56% | -3.45% | — | — | PENDING |
| Arizona Cardinals @ Kansas City Chiefs | AWAY | BetRivers (+875) | 10.84% | +5.71% | 8.27% | -19.35% | — | — | PENDING |
| Tampa Bay Buccaneers @ Detroit Lions | AWAY | FanDuel (+290) | 26.16% | +2.02% | 24.75% | -3.49% | — | — | PENDING |
| Miami Dolphins @ Buffalo Bills | AWAY | BetRivers (+1050) | 9.60% | +10.45% | 6.82% | -21.52% | — | — | PENDING |
| Tennessee Titans @ Dallas Cowboys | AWAY | FanDuel (+370) | 22.85% | +7.39% | 21.08% | -0.92% | — | — | PENDING |
| New York Jets @ Los Angeles Chargers | AWAY | BetRivers (+150) | 40.98% | +2.45% | 40.36% | +0.91% | — | — | PENDING |
| Las Vegas Raiders @ Denver Broncos | AWAY | FanDuel (+430) | 19.55% | +3.60% | 17.44% | -7.58% | — | — | PENDING |

## Outcome evaluation

- Hypothetical one-unit-per-selection ROI: **-100.00%** over 3 finalized selections (not actual executable returns).

## Interpretation and limitations

- Bookmakers' probabilities are correlated and often share information. Apparent EV is not proof of true EV.
- Prices may be stale, restricted, inaccessible, or not executable at the logged timestamp.
- A near-kickoff quote is only a proxy, not confirmed closing-line value.
- Same-book shift compares implied break-even probability for the EXACT frozen bookmaker and side; a positive shift means the earlier offered price was better (not a guaranteed edge).
- No money is wagered; all selections and wins/losses are hypothetical.
- Results are matched against verified full-team identities and kickoff, not inferred from prices.
- Injury information is recorded separately and is NOT an unvalidated betting signal.
- POWER_V1 is a supplementary same-snapshot sensitivity using the exact frozen other-book set; the proportional method and original 2% threshold alone determine selections.
- Neither vig-removal method is an independent probability model or proof of executable value.
