# Model 11 — Independent Edge Validation

Updated: `2026-11-10T15:17:47.144440+00:00`

> **NO VERIFIED POSITIVE EV. Research-only. No wagering recommendations.**

## Prospective research summary

- Independent forecasts added this run: **0**
- Total locked independent forecasts: **0**
- Settled paper observations: **0**
- Near-kickoff price proxies: **0**
- Evidence level: **INSUFFICIENT_FORWARD_EVIDENCE**

**No independent calibrated model has been promoted.** This is correct: the existing NFLverse-adjusted historical model failed to improve pooled probability scoring versus sportsbook consensus. An independently developed, timestamped model forecast must be supplied to begin this test.


## Outcome diagnostics

No independent paper forecasts with verified final results exist; profitability cannot be evaluated.

## Guardrails

- Model 11 **does not create** independent probabilities from sportsbook prices.
- New independent forecasts must be ingested within 15 minutes of their stated generation time, at least 12 hours before kickoff, and use a previously locked Model 10 event.
- Only matching recent bookmaker observations are used; forecasts, model versions and offered odds freeze upon ingestion.
- Model-projected EV is an unvalidated arithmetic hypothesis; a positive number is never promoted to a verified betting edge.
- Market movements are merely later observations. A near-kickoff market probability is not automatically a final closing line.
- Source results must match exact teams and kickoff; no speculative outcome filling.
- A meaningful claim would require enough independent prospective settlements, probability calibration, market comparison, and realistic execution checks. None has been established.

## Optional input schema

Place a CSV at `data/model11/independent_forecasts_inbox.csv` with columns:
`event_id,forecast_utc,trained_through_utc,model_id,model_version,home_probability`.
The model's production process must be external, documented and leakage-free.
Do not fabricate a forecast or set its timestamp retroactively.