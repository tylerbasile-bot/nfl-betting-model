# Model 13 — Phase 2 Prospective Validation

Generated UTC: `2026-11-21T03:15:57.061580+00:00`

> **NO VERIFIED POSITIVE EV. PAPER RESEARCH ONLY.** No bets are placed by this workflow.

## 1. Sample accrual (no forced picks)

- Frozen prospective selections: **11/100** (planning target, not a sufficient statistical sample guarantee).
- Independently verified results: **4**.
- Games with kickoff reached: **4**; games not yet kicked off: **7**.
- The target is an observation milestone; do not adjust selection criteria to meet it.

## 2. Market validation coverage

- Later five-book market references: **11/11**.
- Later selected-book quotes: **11/11**.
- Near-kickoff (<=3h) five-book references: **4/11**.
- Near-kickoff selected-book quotes: **4/11**.
- Matured games missing a near-kickoff market quote: **0/4**.
- Observed near-kickoff market shift mean: **-1.641 percentage points** (n=4).
- Observed same-book near-kickoff implied-price shift mean: **+0.110 percentage points** (n=4).
- These measures are market-price movement proxies, **not** certified closing-line value.

## 3. Execution/availability evidence

- ACCOUNT_RESTRICTED: **0**.
- LIMITED_LIQUIDITY: **0**.
- PRICE_CONFIRMED: **0**.
- PRICE_UNAVAILABLE: **0**.
- REGION_RESTRICTED: **0**.
- UNKNOWN: **0**.
- UNREVIEWED: **11**.

Prices from the odds feed are **not proof of fillability**. The optional manual CSV
`data/model13/execution_observations.csv` can document independently checked
availability, stake limits, fees and evidence references. Never store credentials,
personal financial data, or identifying screenshots in the repository.

## 4. Probability calibration, selected-side reference only

- Mean predicted selected-side win probability (other-book no-vig median): **19.88%**.
- Actual selected-side win rate: **0.00%**.
- Selected-side Brier score: **0.03984**.
- Selected-side log loss: **0.22193**.
- Calibration gap (actual minus reference mean): **-19.88%**.
- **Insufficient observations for meaningful calibration reliability bins; do not infer model validity.**

### Interpretation requirements

- The probability used here is the other-books' median no-vig *market estimate*, NOT an independently trained probability model.
- This is a *selected-only* cohort and may be biased by selecting cross-book discrepancies. Do not extrapolate calibration to all NFL games.
- No candidate is added retroactively, and all evaluation timestamps follow the original freeze.
- Outcomes are sourced only from independently matched Model 13 final-score observations.
- Missing prices and finals remain missing, never interpreted as losses or zero movement.

## 5. Data-quality / pending work

- Candidates with audit warnings: **0**.
- Candidates awaiting verified finals: **7**.
- Candidates missing near-kickoff market observations: **7**.
- Candidates without independent execution confirmation: **11**.

The live Model 13 selection rule remains unchanged. Do not use this dashboard as a wagering signal.
