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
