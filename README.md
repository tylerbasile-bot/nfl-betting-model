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
