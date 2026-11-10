# Model 14 — Market + Pregame EPA, historical conditional experiment

**Status: research only. No demonstrated +EV and no automated wagers.**

## Question

Does a fixed, historical, pre-week NFL offense/defense feature set
improve outcome probability predictions *conditional on historical NFLverse
closing-market moneyline prices*?

This is **not** an early-week wager backtest: closing prices are generally
not observable at the early-week selection timestamp, and the historical
nflverse schedules do not establish per-book quotes, bet availability, limits,
fees, or true closing line value.

## Run on your existing Google Drive data in Colab

The 2015–2025 `pregame_matchup_features.csv` and `games.csv` files were
previously created in:

`/content/drive/MyDrive/NFL_Betting_Data/historical_matchups/`

Run this cell (no odds API key, no nflverse PBP redownload):

```python
!pip -q install "pandas>=2.0,<3" numpy "scikit-learn>=1.4,<2"
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_historical_epa_probabilities.py -o /content/evaluate_historical_epa_probabilities.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_model14_market_plus_epa.py -o /content/evaluate_model14_market_plus_epa.py
!PYTHONPATH=/content python /content/evaluate_model14_market_plus_epa.py
```

The program uses the same strict, relocation-aware nflverse schedule join
as the completed football-only experiment. It aborts on ambiguous or
mismatched game metadata. It excludes ties, games with fewer than three
prior completed team games, and any game without both closing moneyline
prices. All models score identical games.

## Pre-specified models

- **Raw closing market:** de-vig home win probability from nflverse
  `home_moneyline` and `away_moneyline` (no training).
- **Market-only calibrated:** logistic regression on the raw market's
  *log odds*, trained exclusively on 2015–2021.
- **Model 14 combined:** logistic regression (fixed C=1.0) on closing
  market log odds plus 16 pre-week offense/defense EPA, rolling-five,
  ranking, and matchup variables. Median imputation and scaling are
  fitted on training data only.

Evaluation: 2015–2021 training, 2022–2023 development, 2024–2025
later historical test. The test seasons have already been examined
elsewhere in this project; they are not wholly untouched research data.

Outcome metrics: paired Brier score and log loss, an individual-season
breakdown, selected probability reliability bins, and change relative to
each market benchmark. Lower scores are better. A negative **Model 14
minus market** Brier delta means better than that benchmark on those
games; it does **not** demonstrate positive expected value.

## Outputs (private Drive)

- `model14_market_plus_epa_predictions.csv`
- `model14_market_plus_epa_report.md`

No live Model 13 frozen selection records, schedules, thresholds,
report files, or odds API automation is touched. No new betting
recommendation or hypothetical ROI is generated.

## Next steps *after* examining results

If results suggest incremental information beyond raw market AND
market-only calibration, test against historical **timestamp-matched**
pre-kickoff quotes at the time a pick would actually be made. Our
existing free historical odds sample is sparse and does not cover all
2015–2025 games; it cannot support an assertion of executable
profitability from this experiment. Collect additional genuinely
prospective observations rather than inventing them.
