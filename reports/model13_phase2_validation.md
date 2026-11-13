# Model 13 — Phase 2 Prospective Validation

Generated UTC: `2026-11-13T23:38:16.336362+00:00`

> **NO VERIFIED POSITIVE EV. PAPER RESEARCH ONLY.** No bets are placed by this workflow.

## 1. Sample accrual (no forced picks)

- Frozen prospective selections: **3/100** (planning target, not a sufficient statistical sample guarantee).
- Independently verified results: **0**.
- Games with kickoff reached: **0**; games not yet kicked off: **3**.
- The target is an observation milestone; do not adjust selection criteria to meet it.

## 2. Market validation coverage

- Later five-book market references: **3/3**.
- Later selected-book quotes: **3/3**.
- Near-kickoff (<=3h) five-book references: **0/3**.
- Near-kickoff selected-book quotes: **0/3**.
- Matured games missing a near-kickoff market quote: **0/0**.
- Observed near-kickoff market shift: **not yet measurable**.
- Same-book near-kickoff shift: **not yet measurable**.
- These measures are market-price movement proxies, **not** certified closing-line value.

## 3. Execution/availability evidence

- ACCOUNT_RESTRICTED: **0**.
- LIMITED_LIQUIDITY: **0**.
- PRICE_CONFIRMED: **0**.
- PRICE_UNAVAILABLE: **0**.
- REGION_RESTRICTED: **0**.
- UNKNOWN: **0**.
- UNREVIEWED: **3**.

Prices from the odds feed are **not proof of fillability**. The optional manual CSV
`data/model13/execution_observations.csv` can document independently checked
availability, stake limits, fees and evidence references. Never store credentials,
personal financial data, or identifying screenshots in the repository.

## 4. Probability calibration, selected-side reference only

- No independently verified settled selections. **No Brier score, log loss, or calibration claims yet.**

### Interpretation requirements

- The probability used here is the other-books' median no-vig *market estimate*, NOT an independently trained probability model.
- This is a *selected-only* cohort and may be biased by selecting cross-book discrepancies. Do not extrapolate calibration to all NFL games.
- No candidate is added retroactively, and all evaluation timestamps follow the original freeze.
- Outcomes are sourced only from independently matched Model 13 final-score observations.
- Missing prices and finals remain missing, never interpreted as losses or zero movement.

## 5. Data-quality / pending work

- Candidates with audit warnings: **0**.
- Candidates awaiting verified finals: **3**.
- Candidates missing near-kickoff market observations: **3**.
- Candidates without independent execution confirmation: **3**.

The live Model 13 selection rule remains unchanged. Do not use this dashboard as a wagering signal.
