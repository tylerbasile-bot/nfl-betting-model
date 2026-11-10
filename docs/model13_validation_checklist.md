# Model 13 validation checklist — status as of 2026-11-10

> **Paper research only. No verified positive expected value. No real-money betting is justified by the evidence currently available.**

This checklist tracks evidence for the prospective Model 13 program. A checkbox is marked complete only when the required evidence exists; scheduled workflows or generated dashboards do not substitute for observations that have not happened yet.

## Phase A — Maintain reliable data collection

- [ ] **Confirm scheduled GitHub Actions continue succeeding.** The collector's two visible scheduled runs on Nov. 10 (08:56 UTC and 17:22 UTC) succeeded. They are 8h 26m apart despite a two-hour cron, so cadence reliability is not established; the available run history does not show the expected intervening scheduled runs. Four manual dispatches failed for test, injury-observation, or commit steps; the latest scheduled collector completed successfully. The API's remaining-quota value is printed in the job log but is not retained in the dataset/report, so quota health is not auditable from committed artifacts. [Workflow](../.github/workflows/collect-odds.yml) · [Actions history](https://github.com/tylerbasile-bot/nfl-betting-model/actions)
- [ ] **Increase near-kickoff coverage.** A quota-aware workflow is installed, but its first scheduled run succeeded with the capture gate closed; no near-kickoff API call was made. The two frozen Nov. 15 selections each have later market and selected-book observations, but neither has a quote within three hours of kickoff. Confirm actual captures around kickoff before marking complete. [Workflow](../.github/workflows/near-kickoff.yml) · [Market report](../reports/model13_market_validation.md)
- [ ] **Verify sportsbook price quality.** Odds-feed rows include each bookmaker's reported update timestamp. They do not establish that a price was visible or accepted for a wager, what limits applied, whether the account/region was eligible, or what fees applied. No independent execution observations are recorded. [Execution evidence rules](./model13_execution_evidence.md)

## Phase B — Collect genuine forward evidence

- [ ] **Record outcomes for the first completed Model 13 games.** Both frozen candidates are scheduled for Nov. 15 at 18:00 UTC (1:00 p.m. ET), so outcomes cannot yet be verified. Keep the automated exact-team/kickoff matching and do not fill results early.
- [ ] **Reach 25 naturally occurring prospective selections.** Current Model 13 frozen count: **2**. Separately, Model 10 already has **14** frozen market-derived forecasts for games Nov. 13–17; those broaden the all-game evaluation cohort, but they are not extra Model 13 selections or independent model predictions. Do not loosen the Model 13 rule or backfill historical picks to reach the target.
- [ ] **Reach 50 selections.** Current frozen count: **2**. Review calibration and price movement only after the corresponding outcomes and valid follow-up observations accrue.
- [ ] **Reach 100 selections.** Current frozen count: **2**. The count is a review milestone, not a guarantee of adequate statistical power.

## Phase C — Validate statistical performance

- [ ] **Measure price movement in a predeclared near-kickoff window.** The report currently calls a quote “near-kickoff” if it is within three hours; the gate aims for a variable 10–70 minutes before kickoff. Predefine one fixed time window and compare the exact frozen sportsbook and side, using only observations inside that window. Treat the result as a price-movement proxy, not proof of executable closing-line value.
- [ ] **Test probability calibration.** There are no verified settled selections, so no outcome Brier score, log loss, or reliability analysis is available. The selected-side cross-book reference is a market estimate, not an independent model probability.
- [ ] **Calculate uncertainty around hypothetical returns.** No settled observations or return uncertainty intervals are available. Any later calculation must include every frozen selection, losses, realistic execution costs, and uncertainty intervals.
- [ ] **Conduct an untouched forward evaluation.** The selection rule is frozen, but there is not yet a sufficiently accrued sample or a clearly designated untouched evaluation period. Define the holdout period before inspecting its outcomes; do not retune thresholds on those outcomes.

## Phase D — Determine whether real-money betting is justified

- [ ] **Establish credible positive expected value.** Not established. The two current candidates are unverified market discrepancies, not evidence of an edge. The separate historical Model 14 test did not improve on the raw market benchmark in 2024–25 (Brier 0.20172 vs. 0.20085); it remains archived and is not a live-pick model.
- [ ] **Verify actual execution feasibility.** Not established. There is no independent evidence of accepted prices, accessible accounts, region eligibility, fees, or realistic stake limits.
- [ ] **Set a strict loss limit and decision rule.** No real-money loss limit or evidence threshold for a go decision has been documented. Keep the current status paper-only until both are specified and supported by the results.
- [ ] **Make a formal go/no-go decision.** **Current decision: NO-GO for real money; continue paper-only research.** Revisit only after the precommitted forward evidence, execution checks, uncertainty analysis, and loss-limit rule are complete.

## Current frozen candidates

| Game | Frozen paper pick | Offer | Current state |
|---|---|---:|---|
| Buffalo Bills @ New York Jets | Jets · DraftKings | +390 | Pending; no verified outcome or near-kickoff quote |
| Jacksonville Jaguars @ Tennessee Titans | Titans · BetRivers | +480 | Pending; no verified outcome or near-kickoff quote |

The generated [Phase 2 report](../reports/model13_phase2_validation.md) currently records **2/100 frozen selections, 0 verified results, 0 near-kickoff references, and 2 execution checks unreviewed**.
