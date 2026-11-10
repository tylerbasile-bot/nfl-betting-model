# NFL Betting Model — Market Research

This repository collects **timestamped, pregame NFL moneyline quotes** from The Odds API for research into price movement, calibration and closing-line value. It does **not** establish or guarantee positive-EV wagers.

## Setup (one-time)

1. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
2. Name the secret `ODDS_API_KEY` and paste your The Odds API key. **Never put the API key in code or CSV files.**
3. Open **Actions → Capture NFL pregame moneylines → Run workflow** to test.
4. Check the run's logs and then browse `data/odds/YYYY-MM-DD.csv` for stored observations.

## Automation

The GitHub Actions workflow runs at **00:00, 02:00, ... 22:00 UTC** (12 runs/day), with manual runs also available. GitHub scheduled runs may be delayed or skipped; this is not a guaranteed minute-accurate service.

Every run:
- Retrieves US-region `h2h` NFL odds.
- Excludes games at or after kickoff.
- Stores per-bookmaker moneylines, provider update time, observed time, and no-vig home probability.
- Appends a dated CSV and commits the new observations.

A request may consume more than one API credit depending on your Odds API plan and markets. At 12 successful runs daily, **roughly 360 scheduled requests per 30 days** are expected before any extra market charges/manual tests. Monitor your quota; adjust the cron schedule if necessary.

## Research interpretation

`home_no_vig` is computed from each bookmaker's home and away moneylines after normalizing implied probabilities to sum to one. It is a **market estimate, not a verified true win probability**. A difference between prices is not proof of positive expected value. Past model backtests were unprofitable.

Historical data previously stored in Google Drive is not automatically migrated into this GitHub repository. The GitHub workflow begins its own independent history from its first successful run.

## Repository content

- `scripts/collect_odds.py`: API fetcher and append-only CSV writer
- `.github/workflows/collect-odds.yml`: scheduled and manual workflow
- `data/odds/`: auto-generated snapshots (once the collector runs)

## Security

The key is read only from the `ODDS_API_KEY` environment variable. This repository is currently public; **quote data and workflow files will be public** unless you change its visibility. Do not commit API keys, betting account details, or personal betting history.

## Model 9 — Market Intelligence and Validation

The collector now calls `python scripts/model9.py` after every successful odds fetch. The built-in standard-library analysis writes:

- [Model 9 dashboard](reports/model9_dashboard.md): first observed market forecast, latest market probability, movement, and methodology
- [Model 9 forecast ledger](reports/model9_forecasts.csv): one pregame forecast per game, with first-snapshot time and later reference movements

**Key design choices:** only pregame moneylines updated within 30 minutes of capture are eligible; at least four sportsbooks must be present. First eligible snapshot is locked as the baseline. Median bookmaker no-vig probability is a *market-derived baseline*, not an independently calibrated edge. The dashboard does not recommend bets.

### Optional actual-game scoring

To evaluate the pregame predictions, create `data/results.csv` with the following columns:

```csv
event_id,status,winner
```

Use the exact Odds API event ID and full winning team name shown in the forecast ledger, with `status=final`. Enter only independently verified outcomes; ties, postponed, and incomplete games are excluded. The next workflow run computes Brier score, log loss, and winner accuracy for matched games.

### What Model 9 does not yet do

Model 9 is **not** an independent trained NFL predictive model. It does not infer game winners from the betting odds, does not have live injury/QB feeds, and does not assert positive expected value or ROI. Outcome data is not automatically fetched. A near-kickoff price within three hours is an *observed market proxy*, not a verified closing line. The pipeline is an auditable foundation for future out-of-sample model comparisons.

**After this commit:** run **Actions → Capture NFL pregame moneylines → Run workflow** once to generate the first Model 9 report.

## Model 9B — Train on NFLverse data in your private Google Drive

This research script compares a regularized market-offset logistic model using the previous five completed games of team form and offensive EPA (when available) against the pure sportsbook baseline. Each evaluation year (2022–2025) is held out chronologically, with training exclusively on earlier years.

In a new Google Colab notebook:

```python
from google.colab import drive
drive.mount("/content/drive")
!pip -q install pandas pyarrow numpy scipy
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/train_nflverse.py -o /content/train_nflverse.py
!python /content/train_nflverse.py
```

Input is read directly from `/content/drive/MyDrive/NFL_Betting_Data/schedules.parquet` and `team_stats.parquet` (no public file upload). Output stays in `/content/drive/MyDrive/NFL_Betting_Data/model9_validation/`:

- `walk_forward_metrics.csv`: held-out season Brier, log loss, accuracy.
- `walk_forward_predictions.csv`: matchup, market baseline, model prediction and result.

**Interpretation:** schedules moneylines may be closing prices (unknown at earlier prediction time), so this is NOT a tradable profit backtest. The objective is to see whether NFLverse form adds out-of-sample information beyond the market. Score leakage is prevented by computing lagged features before incorporating each game result; statistics from the game being predicted are not inputs. The 2026 season is excluded from training and validation to avoid contamination with games still in progress. If the augmented model's pooled Brier and log loss do not improve, the correct decision is to keep the sportsbook market baseline.

## Model 10 — Prospective, locked-ahead market testing

Model 10 is integrated into the existing scheduled GitHub Actions collector. The workflow now runs integrity tests before API calls, records moneylines, refreshes Model 9, and generates the Model 10 reports.

Files:
- [Prospective forecast ledger](data/model10/prospective_forecasts.csv) — created on the first successful Model 10 run. One immutable prediction per Odds API event ID.
- [Model 10 dashboard](reports/model10_dashboard.md) — generated after each collector run.
- [Model 10 evaluation](reports/model10_evaluation.csv) — individual frozen predictions, subsequent movement, near-kickoff price proxies, and verified outcome scores.

**Prospective constraint:** new forecasts are only created if the most recent qualifying odds snapshot was collected in the previous 15 minutes, contains at least four fresh books, and kickoff is at least 12 hours away. Old CSV history is **not backfilled** as prospective. A game's frozen initial probability and prices never change even after future odds updates. New snapshots only update the separate evaluation report.

**Market baseline:** the median of each bookmaker's de-vigged home-win probability. This is a benchmark, not a trained proprietary probability model or evidence of positive EV. No bets are recommended.

**After kickoff:** when a quote is captured within three hours of kickoff, the evaluation labels it *near kickoff*, never as the true closing line without verification. To score completed games, supply independently checked `data/results.csv` containing `event_id,status,winner`, using `final` and the exact winning team name. No scores are fabricated or inferred from moneylines. Results cannot be scored before kickoff.

**Important:** The sportsbook-only baseline does not include independent injury information, NFLverse features or quarterback projections yet. The previous NFLverse-augmented Model 9B did not improve pooled Brier/log loss; it is deliberately not promoted to a real-money betting signal. We need forward outcomes before evaluating any proposed non-market model.

**Start it:** open **Actions → Capture NFL pregame moneylines → Run workflow**, and verify the Model 10 test and generation steps succeed. GitHub Actions scheduled runs are not guaranteed at exact clock times. Data in this repository is currently public unless repository visibility is changed. Monitor API usage.

## Model 11 — Forward positive-EV research and verified outcomes

After each scheduled moneyline capture, the GitHub workflow now:
1. Runs offline integrity tests (no API credits).
2. Retrieves odds.
3. Attempts to verify **completed games** using ESPN's publicly accessible, **unofficial** NFL scoreboard JSON endpoint. Final results must match locked Model 10 game identities, home/away sides, and kickoff within six hours; ties and ambiguous results are excluded. Unavailable feeds do not create guessed results.
4. Regenerates Model 9 and Model 10 benchmarks and outcome scoring.
5. Regenerates **[Model 11 research dashboard](reports/model11_dashboard.md)** and **[Model 11 forward audit](reports/model11_audit.csv)**.
6. Commits time-stamped snapshots, results, and research reports.

### Model 11 and positive EV

Model 11 does **not** claim that a sportsbook discrepancy is positive EV. Historical NFLverse Models 6/9B did not improve pooled proper probability scoring beyond the sportsbook baseline; no independent probability engine is currently promoted.

For a properly validated model you independently develop, the optional input is `data/model11/independent_forecasts_inbox.csv` containing exactly these headers:

```csv
event_id,forecast_utc,trained_through_utc,model_id,model_version,home_probability
```

The input must be created in advance, not backfilled; its forecast timestamp must be no more than 15 minutes old at workflow execution, and the matchup must be locked in Model 10 with at least 12 hours before kickoff. An appropriate recent odds snapshot must also be present. The first accepted model forecast and best quoted offered price are frozen in `data/model11/locked_independent_forecasts.csv`. **Never invent those probabilities or times.** The script does not train a model.

The audit compares theoretical EV (based on the independent probability), later market probabilities, a near-kickoff CLV proxy, and hypothetical 1-unit paper results after final scores are confirmed. It does **not** place bets. The dashboard shows `NO VERIFIED POSITIVE EV` until a truly independent model has accumulated sufficient unseen prospective evidence, including calibration and realistic execution conditions. A theoretical 2% or 5% EV estimate alone is not proof of profitability.

Note: The final-score endpoint is unofficial and subject to change. Inspect failed or unmatched results before trusting the outcome ledger. The new results file will be visible publicly while this GitHub repository is public; do not store private betting-account information here.

**Activate:** GitHub → Actions → Capture NFL pregame moneylines → Run workflow. New reports appear only after a successful updated workflow run.

## Model 12 — Independent football-only model (offline candidate)

The [candidate training script](scripts/train_independent_candidate.py) is deliberately independent of bookmaker prices as training inputs. It uses only rolling prior-five-game form and team passing/rushing EPA where available, with chronological training/test seasons 2022–2025. Market odds are used only as a **held-out comparator**. Previous models failed to beat the market reliably, so this model is not automatically promoted to Model 11.

Run in Google Colab with existing private Drive files:

```python
from google.colab import drive
drive.mount("/content/drive")
!pip -q install numpy scipy pandas pyarrow
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/train_nflverse.py -o /content/train_nflverse.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/train_independent_candidate.py -o /content/train_independent_candidate.py
!python /content/train_independent_candidate.py
```

Results are saved privately to `NFL_Betting_Data/model12_independent_candidate/`:
- `heldout_metrics.csv` — year-by-year proper scoring, winner accuracy
- `heldout_predictions.csv` — each held-out game, independent probability, market comparator
- `validation_gate.json` — predeclared research gate and explanations

The gate requires at least 800 held-out games, lower Brier in at least 3 of 4 years, pooled Brier improvement of at least 0.002, and lower pooled log loss. Passing **would not** independently verify a betting edge because 2025 has already been examined during previous development. An untouched prospective evaluation is still necessary. The script never sends probabilities to Model 11, creates no paper bets, and never reads a personal sportsbook account.

### QB and offensive-line availability — timestamping comes first

Do not use retrospective injury status fields as pregame features: many injury tables are revised after kickoff. Future expansion requires (a) source, (b) exact status-as-of timestamp, (c) team/player identity, (d) known-at-forecast confirmation, and (e) validation that missing statuses are handled without leakage. No credible historical injury dataset is connected yet, so it is intentionally excluded from this candidate.

## Model 13 — Cross-sportsbook paper pricing study

The scheduled odds workflow now also executes [scripts/model13.py](scripts/model13.py) after the results check. It produces:
- `reports/model13_dashboard.md` — prospective cross-book discrepancy study
- `reports/model13_audit.csv` — frozen paper candidates, market shift, hypothetical settled result
- `data/model13/frozen_price_candidates.csv` — append-only list of qualifying observations (file appears after the first qualifying market discrepancy)

**Locked prospective selection rule:** at least five recent bookmaker quotes, at least 12 hours until kickoff, snapshot within 15 minutes of processing, reference probability from the median no-vig price of the *other* books, and an indicative discrepancy equivalent to at least 2% return. Choose only the single largest discrepancy per game, then freeze timestamp, book, odds and reference. Later quotes can affect only evaluation fields.

This is **NOT positive EV confirmation**. Different bookmakers' no-vig prices are correlated estimates, not independent validated win probabilities. Paper ROI and near-kickoff market shifts measure this predeclared rule prospectively, not an executable betting strategy; sportsbook limitations, stale lines, market access and uncertainty matter. No bets are placed.

## Quarterback / Offensive-line injury observations

The workflow also calls [scripts/collect_injuries.py](scripts/collect_injuries.py), collecting one **daily snapshot** from the [nflverse injury release](https://github.com/nflverse/nflverse-data/releases/tag/injuries), filtering QB, C, G, T, OT and other offensive-line positions. Data is stored in `data/injury_observations/YYYY-MM-DD.csv`, with *our observed UTC timestamp* plus each report's original `date_modified`. The [injury watchboard](reports/injury_watch.md) gives descriptive latest-source-week summaries. A missing entry does not imply a healthy player and a player on the report is not necessarily a starter.

nflverse documents the `date_modified`, `position`, `report_status`, and `practice_status` fields, but **historical source timestamps alone do not verify when each item was available to bettors**. We therefore do not backfill or train on retrospectively revised injury status, infer starting QBs, treat questionable as out, or use injury observations as positive-EV betting signals.

**Future QB/OL research plan:** Build per-player as-of histories using the observation timestamps accumulated from now onward, verify depth chart/starting role as of that same time, compare injury availability changes to market movement, then freeze and test separate pregame predictions on unseen games. Data quality and temporal correctness must be established before the feature is added to any active probability model.

New scripts are committed but require a fresh successful **Actions → Capture NFL pregame moneylines → Run workflow** execution for the first Model 13 and injury dashboard outputs.

## Upgrade — Injury status changes and near-kickoff price collection (November 2026)

### Injury change audit
Each existing two-hour odds workflow run also regenerates:
- [Injury status change report](reports/injury_changes.md)
- `reports/injury_changes.csv` — previous/current **observed UTC** times, player ID, team, season/week, original/new practice and report statuses, source modification date, and change type.

`scripts/injury_changes.py` compares **the last two daily injury snapshots** of identical season/week/player/team identifiers. It marks first-seen entries separately and records changed report/practice statuses. If a player disappears from the feed, that **does not** count as recovery. This report becomes informative only after the second dated observation is available. It does not verify starting roles or independently predict injury impact.

### Quota-aware near-kickoff collection
[Near-kickoff workflow](.github/workflows/near-kickoff.yml) checks tracked game start times on a UTC hourly schedule at minute 35 on NFL game days (Sun/Mon/Tue/Thu/Fri UTC). It first runs a **local API-free gate**, `scripts/near_kickoff_gate.py`, and **skips API collection** unless an already-tracked game will start in 10–70 minutes, with no sportsbook snapshot in the preceding 25 minutes. The intent is to collect a later, more useful *pregame* quote without exhausting The Odds API quota. Schedule timing is best-effort; GitHub may delay or miss scheduled runs and some games will lack a near-kickoff snapshot.

Model 13's original frozen paper observations and selection thresholds remain **unchanged**. Its [audit CSV](reports/model13_audit.csv) now contains *additional* columns:
- `same_book_near_kickoff_odds` / `same_book_near_kickoff_utc`
- `same_book_implied_shift_pp` — closing *proxy* implied break-even probability minus initially offered break-even probability, for the **exact same sportsbook and side**. A positive number indicates that the original quote was better relative to the later quote. This is not proof of positive expected value or a genuine official closing line.

No account-specific odds availability or actual bet execution is recorded. Both the ordinary and near-kickoff workflows share one GitHub Actions concurrency group to avoid overlapping collectors, and a separate [research integrity workflow](.github/workflows/ci.yml) tests code changes without spending API credits.

**To verify after deploying:** check the GitHub Actions **Research code integrity tests** workflow, then run **Capture NFL pregame moneylines** once to generate the new injury and Model 13 report columns. The near-kickoff workflow only makes an additional call when a tracked game is genuinely near kickoff, regardless of how often you manually dispatch it.

## Free historical odds backtesting (no paid plan)

**Sources verified from public documentation (November 2026):**

1. **NFLverse** schedules, already in private Google Drive: one closing moneyline per team and final game results, generally not a per-book timestamped archive.
2. **EndzoneAPI** [historical bookmaker prices](https://endzoneapi.com/docs/get-odds): a free account advertises 500 credits/month with no payment card. `get_odds` costs **10 credits per call** and can retrieve seasonal bookmaker **opening** or **closing** observations for 2020–2025, with bookmaker and `captured_at` timestamps. Opening means first captured price, not necessarily the true first listed sportsbook price. Provider records may be sparse or captured at different instants.
3. **The Odds Gap** [sample free week](https://theoddsgap.com/data/answers/free-historical-odds-data): no-key CSV containing timestamped scans for one archived sample week. This is useful for testing import formats but NOT enough to establish a profitable historical NFL strategy. Their full archive is paid and is not enabled in this project.
4. **The Odds API** live feed (already integrated) does NOT provide free historical queries; its historical endpoint requires a paid usage plan.

### Download historical per-book opening and closing observations with the free EndzoneAPI allowance

First sign up for a **free** account at https://endzoneapi.com/ and obtain an API key. No card should be needed according to its published terms. Keep the key off GitHub.

In Colab:
```python
from google.colab import drive
drive.mount("/content/drive")
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/download_free_historical_odds.py -o /content/download_free_historical_odds.py
!python /content/download_free_historical_odds.py --dry-run
!python /content/download_free_historical_odds.py --years 2022 2023 2024 2025
```

**Budget:** 2 requests × 4 seasons × 10 credits = **80 estimated credits**, out of the published 500-credit monthly free allowance. The script skips previously downloaded season/snapshot combinations and stores raw JSON plus the retrieval time in your **private Google Drive** at `NFL_Betting_Data/free_historical_odds/`.

### Interpret historical data carefully

The historical bookmaker opening and closing observations are **not** dense synchronized five-minute snapshots. Do not simply apply Model 13's existing 2%-EV screen to prices captured at widely different times: it could manufacture fake discrepancies. A valid historical study must check capture timestamps, sportsbook matchups, missing books, and only evaluate common observation windows. If insufficient simultaneous books exist, record **INSUFFICIENT DATA**, not a simulated win. Do not backfill these historical observations into Model 13's separate, already-frozen prospective data.

Data provider schemas and historical access terms can change; inspect the first saved raw JSON before writing a normalized backtester. The free archive may only support opening/closing analysis, not the full intraday selection rule.

## Historical Model 13 free Odds Gap sample audit

The free sample downloaded from `https://theoddsgap.com/api/odds-export.csv?sport=all`
was reported as 1,248,139 rows (240 MB) with columns:
`snapshot_ts,sport,away,home,commence_time,market,side,line,book,american_odds,devig_fair_prob,best_price_flag,game_id`.
Most rows are NOT NFL moneylines. Audit before extrapolating.

The independent historical replay lives in `scripts/backtest_free_odds_gap.py`.
It **does not read or modify** Model 13's prospective ledger. It:
- Streams the CSV and filters for `americanfootball_nfl` and `ml` prices only.
- Requires matching home and away moneyline quotes at the *same captured timestamp* from each bookmaker.
- Evaluates only instants with >=5 books and >=12 hours remaining to kickoff.
- Recomputes each bookmaker's no-vig probability from BOTH moneylines (does not trust the provided fair probability).
- Freezes at most one **earliest qualifying** candidate per game if indicative EV >=2%, using the other bookmakers' median and selecting the highest discrepancy.
- Reports historical near-kickoff (within 3 hours) market and exact-sportsbook price movement where available, not an official close.
- Does not infer outcome, ROI, or make positive-EV claims without verified results and a suitable evaluation sample.

In the existing Google Colab notebook with Drive mounted:
```python
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/backtest_free_odds_gap.py -o /content/backtest_free_odds_gap.py
!python /content/backtest_free_odds_gap.py --input "/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/odds_gap_free_sample.csv"
```
The script writes `historical_model13_sample_audit.md` and
`historical_model13_sample_candidates.csv` under
`NFL_Betting_Data/free_historical_odds/model13_sample/`.
If there are **no NFL games or no synchronized five-book captures**, the correct
finding is *insufficient data*, not zero profitability or a made-up backtest.

### Evaluate historical sample paper outcomes (after the separate market replay)

Historical replay audit observed **29 NFL games, 13 retrospective candidates, and just 1 near-kickoff comparison** in the October 19–25, 2026 free sample. These figures do **not** establish an edge. A high number of price discrepancies with sparse close data could represent stale/asynchronous quotes.

`scripts/evaluate_free_historical_odds.py` independently validates the **already selected** candidates against the public ESPN scoreboard, accepting only completed non-tie games, exact team matches, and kickoff within six hours; future and unmatched games are excluded. It produces a *descriptive* paper win rate and hypothetical flat-unit ROI on only matched finals, plus a per-candidate audit. The evaluation does not read or alter Model 13's prospective frozen ledger.

From Colab:
```python
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_free_historical_odds.py -o /content/evaluate_free_historical_odds.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/collect_results.py -o /content/collect_results.py
!python /content/evaluate_free_historical_odds.py
```

Outputs under `NFL_Betting_Data/free_historical_odds/model13_sample/`:
`historical_model13_outcomes.md` and `historical_model13_outcomes.csv`.
If the 13 candidate games include future games, do not report their return as 0; leave them pending.

**Caveat:** historical replay selects the first eligible discrepancy by snapshot time, whereas the *real prospective* system only captures whatever two-hour run first sees. Those are distinct sampling processes; historical selection can reveal a market-price hypothesis but is not a faithful executable ROI estimate.

## Historical Price Reliability Audit — free Odds Gap sample

After running the historical replay and ESPN result evaluation, use the
**independent** source-quality/sensitivity audit:

```python
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/audit_historical_price_reliability.py -o /content/audit_historical_price_reliability.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/backtest_free_odds_gap.py -o /content/backtest_free_odds_gap.py
!python /content/audit_historical_price_reliability.py
```

The script reads the existing private Drive files and writes **new** artifacts to
`NFL_Betting_Data/free_historical_odds/model13_sample/`:

- `historical_price_reliability.md`: summary, candidate lead-time bins,
  source quote checks, 5-percentage-point and 10-percentage-point outlier flags,
  a post-hoc strict sportsbook-only replay, and original-outcome
  leave-one-game-out sensitivity.
- `historical_price_reliability.csv`: original frozen selection-by-selection
  same-instant paired quote audit, independently recomputed leave-one-book-out
  no-vig reference, book overround, prior-snapshot quote persistence.
- `historical_sportsbook_only_replay.csv`: a **new exploratory re-selection**
  restricted to a manually curated sportsbook allowlist for both offered prices
  and reference books, with verified outcomes matched from the already obtained
  ESPN final-score audit by event, exact teams and kickoff proximity.

Novig and other prediction markets are real venues but are excluded from the
strict sportsbook-only replay. Unrecognized venues (including some offshore
books) are also excluded rather than silently treated as US sportsbooks.

**Interpretation:** an unusually large discrepancy is not proof that a quote
was stale or fillable. Captured scan timestamps do not prove book-specific
quote update times. Post-hoc filtering is not independent validation. Historical
results and the untouched prospective Model 13 should remain separate.

## Fully verified strict sportsbook replay and kickoff-window sensitivity

The earlier strict sportsbook-only replay found **8 picks**, but the evaluation
in `audit_historical_price_reliability.py` reused only the **original
13-pick outcome file** and could verify just 7/8. The independent
`scripts/evaluate_historical_timing.py` now queries the free public ESPN NFL
scoreboard for the **actual re-selected games**, checks exact team names,
kickoff within six hours, and non-tie completed finals. It refuses to report
scenario ROI unless **all picks in that scenario** can be verified.

It also performs post-hoc **72/48/24-hour timing sensitivities**. For a
72-hour window, it finds the first qualifying contemporaneous snapshot when
kickoff is **12 to 72 hours away**; 48h uses 12–48h; 24h uses 12–24h.
Each scenario independently applies 5-book minimum, leave-one-book-out median
reference, and >=2% indicative value rule. These are overlapping windows,
not predictions at precisely 72/48/24 hours.

From Google Colab with Drive already mounted:
```python
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/backtest_free_odds_gap.py -o /content/backtest_free_odds_gap.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/audit_historical_price_reliability.py -o /content/audit_historical_price_reliability.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/collect_results.py -o /content/collect_results.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_free_historical_odds.py -o /content/evaluate_free_historical_odds.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_historical_timing.py -o /content/evaluate_historical_timing.py
!python /content/evaluate_historical_timing.py
```

Outputs in Drive `NFL_Betting_Data/free_historical_odds/model13_sample/`:
- `historical_timing_report.md`
- `historical_timing_summary.csv`
- `historical_timing_scored_selections.csv`

No change to original historical outcomes, Model 13's frozen prospective
candidate file, its selection thresholds or the automatic live workflows.
This is a small, retrospective convenience sample and not a validated edge.
