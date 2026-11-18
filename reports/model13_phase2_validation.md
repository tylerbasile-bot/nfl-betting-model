# Model 13 — Phase 2 Prospective Validation

Generated UTC: `2026-11-18T07:37:47.727933+00:00`

> **NO VERIFIED POSITIVE EV. PAPER RESEARCH ONLY.** No bets are placed by this workflow.

## 1. Sample accrual (no forced picks)

- Frozen prospective selections: **10/100** (planning target, not a sufficient statistical sample guarantee).
- Independently verified results: **3**.
- Games with kickoff reached: **3**; games not yet kicked off: **7**.
- The target is an observation milestone; do not adjust selection criteria to meet it.

## 2. Market validation coverage

- Later five-book market references: **10/10**.
- Later selected-book quotes: **10/10**.
- Near-kickoff (<=3h) five-book references: **3/10**.
- Near-kickoff selected-book quotes: **3/10**.
- Matured games missing a near-kickoff market quote: **0/3**.
- Observed near-kickoff market shift mean: **-1.360 percentage points** (n=3).
- Observed same-book near-kickoff implied-price shift mean: **+0.479 percentage points** (n=3).
- These measures are market-price movement proxies, **not** certified closing-line value.

## 3. Execution/availability evidence

- ACCOUNT_RESTRICTED: **0**.
- LIMITED_LIQUIDITY: **0**.
- PRICE_CONFIRMED: **0**.
- PRICE_UNAVAILABLE: **0**.
- REGION_RESTRICTED: **0**.
- UNKNOWN: **0**.
- UNREVIEWED: **10**.

Prices from the odds feed are **not proof of fillability**. The optional manual CSV
`data/model13/execution_observations.csv` can document independently checked
availability, stake limits, fees and evidence references. Never store credentials,
personal financial data, or identifying screenshots in the repository.

## 4. Probability calibration, selected-side reference only

- Mean predicted selected-side win probability (other-book no-vig median): **20.58%**.
- Actual selected-side win rate: **0.00%**.
- Selected-side Brier score: **0.04257**.
- Selected-side log loss: **0.23059**.
- Calibration gap (actual minus reference mean): **-20.58%**.
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
- Candidates without independent execution confirmation: **10**.

The live Model 13 selection rule remains unchanged. Do not use this dashboard as a wagering signal.
