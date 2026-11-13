# Model 13 — Prospective Market Validation

Updated: `2026-11-13T23:38:16.261901+00:00`

> **PAPER RESEARCH ONLY. NO VERIFIED +EV.** Captured prices may not have been executable.

## Tracking coverage

- Frozen prospective selections: **3**
- With any later five-book fresh market observation: **3**
- With later selected-sportsbook observation: **3**
- With five-book observation within 3h of kickoff: **0**
- With selected-sportsbook observation within 3h of kickoff: **0**
- With independently verified final outcomes: **0**

## Frozen selections and follow-up

| Game | Pick | Frozen offer | Last observed market shift | Near-kickoff market shift | Near-kickoff same-book shift | Verified outcome |
|---|---|---:|---:|---:|---:|---|
| Buffalo Bills @ New York Jets | HOME · DraftKings | 390 | +0.148 pp | — | — | PENDING |
| Jacksonville Jaguars @ Tennessee Titans | HOME · BetRivers | 480 | -0.663 pp | — | — | PENDING |
| Los Angeles Rams @ Arizona Cardinals | HOME · MyBookie.ag | 370 | -0.545 pp | — | — | PENDING |

## Descriptive paper outcomes

No independently verified finalized selections yet. ROI not reported.

## Audit rules and limitations

- The frozen selection ledger is read-only. No historical rows are added.
- Later observations require **at least five books** with book-specific reported last updates <=15 minutes before their scan timestamp.
- Every comparison is strictly after the original selection and before kickoff.
- **Last observed** is NOT called near-kickoff unless captured within three hours of kickoff.
- Same-book comparisons use the exact frozen book key and selected team; a positive implied-probability shift indicates an earlier better offer, not verified CLV.
- Model 13 finals are independently matched against completed ESPN games using exact home/away identities and kickoff proximity; unknowns are not treated as losses.
- Final outcomes and paper returns are not sufficient to demonstrate expected value, fillability, or profitability.
- Collection gaps and bookmaker timestamp granularity can prevent otherwise valid comparisons.
