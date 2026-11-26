# Model 13 — Prospective Market Validation

Updated: `2026-11-26T23:02:27.964241+00:00`

> **PAPER RESEARCH ONLY. NO VERIFIED +EV.** Captured prices may not have been executable.

## Tracking coverage

- Frozen prospective selections: **17**
- With any later five-book fresh market observation: **16**
- With later selected-sportsbook observation: **16**
- With five-book observation within 3h of kickoff: **6**
- With selected-sportsbook observation within 3h of kickoff: **6**
- With independently verified final outcomes: **11**

## Frozen selections and follow-up

| Game | Pick | Frozen offer | Last observed market shift | Near-kickoff market shift | Near-kickoff same-book shift | Verified outcome |
|---|---|---:|---:|---:|---:|---|
| Buffalo Bills @ New York Jets | HOME · DraftKings | 390 | -0.881 pp | -0.881 pp | +0.868 pp | LOSS |
| Jacksonville Jaguars @ Tennessee Titans | HOME · BetRivers | 480 | -1.106 pp | -1.106 pp | +1.806 pp | LOSS |
| Los Angeles Rams @ Arizona Cardinals | HOME · MyBookie.ag | 370 | -2.093 pp | -2.093 pp | -1.237 pp | LOSS |
| Indianapolis Colts @ Houston Texans | AWAY · BetRivers | 475 | -2.485 pp | -2.485 pp | -0.998 pp | LOSS |
| New Orleans Saints @ Chicago Bears | AWAY · FanDuel | 450 | -3.179 pp | — | — | LOSS |
| Arizona Cardinals @ Kansas City Chiefs | AWAY · BetRivers | 875 | -1.258 pp | — | — | LOSS |
| Tampa Bay Buccaneers @ Detroit Lions | AWAY · FanDuel | 290 | +9.061 pp | — | — | LOSS |
| Miami Dolphins @ Buffalo Bills | AWAY · BetRivers | 1050 | -0.252 pp | — | — | LOSS |
| Tennessee Titans @ Dallas Cowboys | AWAY · FanDuel | 370 | +1.667 pp | — | — | LOSS |
| New York Jets @ Los Angeles Chargers | AWAY · BetRivers | 150 | -2.034 pp | -2.034 pp | +1.667 pp | WIN |
| Las Vegas Raiders @ Denver Broncos | AWAY · FanDuel | 430 | -3.417 pp | -3.417 pp | -1.627 pp | LOSS |
| Philadelphia Eagles @ Dallas Cowboys | AWAY · BetMGM | 375 | -0.919 pp | — | — | PENDING |
| Baltimore Ravens @ Houston Texans | AWAY · BetRivers | 275 | — | — | — | PENDING |
| Atlanta Falcons @ Minnesota Vikings | AWAY · DraftKings | 276 | -0.426 pp | — | — | PENDING |
| Tennessee Titans @ Jacksonville Jaguars | AWAY · FanDuel | 750 | -0.206 pp | — | — | PENDING |
| New York Giants @ Indianapolis Colts | HOME · FanDuel | 270 | +1.459 pp | — | — | PENDING |
| New Orleans Saints @ Cincinnati Bengals | AWAY · DraftKings | 472 | +0.281 pp | — | — | PENDING |

## Descriptive paper outcomes

- Settled selections: **11**, wins: **1**
- Flat-one-unit hypothetical profit: **-8.500 units**
- Flat-one-unit ROI on verified finals only: **-77.27%**

## Audit rules and limitations

- The frozen selection ledger is read-only. No historical rows are added.
- Later observations require **at least five books** with book-specific reported last updates <=15 minutes before their scan timestamp.
- Every comparison is strictly after the original selection and before kickoff.
- **Last observed** is NOT called near-kickoff unless captured within three hours of kickoff.
- Same-book comparisons use the exact frozen book key and selected team; a positive implied-probability shift indicates an earlier better offer, not verified CLV.
- Model 13 finals are independently matched against completed ESPN games using exact home/away identities and kickoff proximity; unknowns are not treated as losses.
- Final outcomes and paper returns are not sufficient to demonstrate expected value, fillability, or profitability.
- Collection gaps and bookmaker timestamp granularity can prevent otherwise valid comparisons.
