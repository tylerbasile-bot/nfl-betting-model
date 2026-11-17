# Model 10B — Football stats + market challenger

**Status: implemented historical research script; not yet trained on the private data; not a live betting model.**

Model 10 remains the immutable, timestamped sportsbook-consensus baseline. Model 10B
is an independent challenger, not a replacement for Model 10 or Model 13. It tests
whether NFLverse **pregame** offense/defense EPA, recent five-game form, rankings
and matchup differentials add probabilistic information to a market baseline.

## What has been implemented

- `scripts/model10b_historical.py`: four-way, fixed-protocol comparison:
  1. Raw no-vig sportsbook closing-market probability.
  2. Logistic market-only calibration.
  3. Pregame football-only logistic model.
  4. Market-plus-football Model 10B logistic model.
- **Train** 2015–2021; **development** 2022–2023; **historical test** 2024–2025.
- Identical eligible games and complete market pairs for every comparator.
- Per-split Brier score, log loss, winner accuracy; held-out year breakdown.
- Training-only imputation and standardization; three prior games required
  for both teams, and ties excluded.
- Inputs and outputs stay in the user's private Google Drive by default.

## Run in the existing Google Colab with Drive mounted

```python
from google.colab import drive
drive.mount("/content/drive")
!pip -q install "pandas>=2.0,<3" numpy "scikit-learn>=1.4,<2"
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_historical_epa_probabilities.py -o /content/evaluate_historical_epa_probabilities.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_model14_market_plus_epa.py -o /content/evaluate_model14_market_plus_epa.py
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/model10b_historical.py -o /content/model10b_historical.py
!python /content/model10b_historical.py
```

Requires preexisting:
- `MyDrive/NFL_Betting_Data/historical_matchups/pregame_matchup_features.csv`
- `MyDrive/NFL_Betting_Data/historical_matchups/games.csv`

If missing, follow `docs/nflverse_pregame_ratings.md` to generate the pregame
features; get `games.csv` via the independently documented nflverse schedules
step. Downloaded raw PBP and private data are **not** committed to public GitHub.

Outputs:
- `MyDrive/NFL_Betting_Data/historical_matchups/model10b/historical_report.md`
- `MyDrive/NFL_Betting_Data/historical_matchups/model10b/historical_predictions.csv`

## Critical limitation: early-week versus closing-market prices

The input `games.csv` generally supplies historical **closing** moneylines,
not the precise early-week odds visible at Model 10's original freeze timestamps.
Accordingly this is **not** a backtest of adding football features to actual
Model 10 frozen quotes. It is a historical conditional test with later market
information. Model 14 and this study overlap methodologically.

**Do not** put these fitted historical probabilities into existing 2026
Model 10 forecast rows, call them prospectively frozen, or infer achievable ROI.

## Conditions before enabling live Model 10B

1. Create a reliably updated 2026 nflverse pregame feature feed with exact
   season/week/game and home/away joins, and an observation cutoff before
   each kickoff/freeze; handle missing player/QB/injury data honestly.
2. Combine it with **only the first Model 10 frozen consensus probability**
   available at that forecast timestamp. Never use later quotes to revise
   a previously frozen prediction.
3. Register a fixed trained artifact/version and a new append-only Model 10B
   ledger, adding predictions only for **future** games after the artifact
   and features have actually been generated.
4. Compare Model 10 and Model 10B on **the same prospective matched games**.
   Review Brier, log loss, calibration, missing-coverage rate, and forecast
   provenance before any practical deployment decision.
5. Collect independently verified offered-price availability before assessing
   executable hypothetical EV; a good winner-accuracy score is not an edge.

**No live Model 10B forecasts, performance claims, ROI, or +EV signals exist yet.**
Model 10 and Model 13 files, thresholds, and workflows are not modified.
