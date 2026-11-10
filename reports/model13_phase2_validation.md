# Model 13 — Phase 2 Prospective Validation

> **INITIALIZATION ONLY — NOT A LIVE GENERATED REPORT.** This file was created to establish the dashboard link before its first successful report-generation workflow. Do not treat any unobserved comparison as zero or as negative evidence.

## Verified starting state (November 10, 2026)

- Frozen prospective selections already recorded in `data/model13/frozen_price_candidates.csv`: **2**.
- Planning observation target: **100 prospective selections**; not a guarantee of statistical significance.
- Games currently recorded: **Buffalo Bills @ New York Jets** and **Jacksonville Jaguars @ Tennessee Titans**, both scheduled for November 15, 2026.
- Results and post-freeze market comparisons: **not re-evaluated in this initialization file**.
- Evidence of positive expected value: **not established**.

## Publish the actual current metrics

Open **GitHub Actions → Refresh Model 13 research dashboards (no odds API) → Run workflow**.

The workflow executes the read-only `scripts/model13_market_validation.py`
and `scripts/model13_phase2_validation.py` against committed data and replaces
this bootstrap page with the calculated report. No paid odds API call is made.

The scheduled collector also regenerates the report when a successful odds
run completes.

**No historical records, original frozen picks, or selection thresholds were modified by this initialization.**
