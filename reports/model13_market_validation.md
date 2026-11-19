# Model 13 — Prospective Market Validation

Updated: `2026-11-19T00:28:28.909567+00:00`

> **PAPER RESEARCH ONLY. NO VERIFIED +EV.** Captured prices may not have been executable.

## Tracking coverage

- Frozen prospective selections: **10**
- With any later five-book fresh market observation: **10**
- With later selected-sportsbook observation: **10**
- With five-book observation within 3h of kickoff: **3**
- With selected-sportsbook observation within 3h of kickoff: **3**
- With independently verified final outcomes: **3**

## Frozen selections and follow-up

| Game | Pick | Frozen offer | Last observed market shift | Near-kickoff market shift | Near-kickoff same-book shift | Verified outcome |
|---|---|---:|---:|---:|---:|---|
| Buffalo Bills @ New York Jets | HOME · DraftKings | 390 | -0.881 pp | -0.881 pp | +0.868 pp | LOSS |
| Jacksonville Jaguars @ Tennessee Titans | HOME · BetRivers | 480 | -1.106 pp | -1.106 pp | +1.806 pp | LOSS |
| Los Angeles Rams @ Arizona Cardinals | HOME · MyBookie.ag | 370 | -2.093 pp | -2.093 pp | -1.237 pp | LOSS |
| Indianapolis Colts @ Houston Texans | AWAY · BetRivers | 475 | -2.444 pp | — | — | PENDING |
| New Orleans Saints @ Chicago Bears | AWAY · FanDuel | 450 | -2.850 pp | — | — | PENDING |
| Arizona Cardinals @ Kansas City Chiefs | AWAY · BetRivers | 875 | -0.935 pp | — | — | PENDING |
| Miami Dolphins @ Buffalo Bills | AWAY · BetRivers | 1050 | -0.086 pp | — | — | PENDING |
| Tennessee Titans @ Dallas Cowboys | AWAY · FanDuel | 370 | +0.258 pp | — | — | PENDING |
| New York Jets @ Los Angeles Chargers | AWAY · BetRivers | 150 | -0.315 pp | — | — | PENDING |
| Las Vegas Raiders @ Denver Broncos | AWAY · FanDuel | 430 | -0.816 pp | — | — | PENDING |

## Descriptive paper outcomes

- Settled selections: **3**, wins: **0**
- Flat-one-unit hypothetical profit: **-3.000 units**
- Flat-one-unit ROI on verified finals only: **-100.00%**

## Audit rules and limitations

- The frozen selection ledger is read-only. No historical rows are added.
- Later observations require **at least five books** with book-specific reported last updates <=15 minutes before their scan timestamp.
- Every comparison is strictly after the original selection and before kickoff.
- **Last observed** is NOT called near-kickoff unless captured within three hours of kickoff.
- Same-book comparisons use the exact frozen book key and selected team; a positive implied-probability shift indicates an earlier better offer, not verified CLV.
- Model 13 finals are independently matched against completed ESPN games using exact home/away identities and kickoff proximity; unknowns are not treated as losses.
- Final outcomes and paper returns are not sufficient to demonstrate expected value, fillability, or profitability.
- Collection gaps and bookmaker timestamp granularity can prevent otherwise valid comparisons.
