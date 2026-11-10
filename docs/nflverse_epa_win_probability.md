# Historical EPA win-probability experiment (2015–2025)

**Purpose:** test whether pregame team offense/defense efficiency can estimate NFL
home-team victory probabilities, using the free 2,895-game nflverse matchup
database the user generated in private Google Drive.

**Do not alter Model 13:** this offline experiment does not read or modify
`data/model13/frozen_price_candidates.csv`, prospectively chosen
sportsbooks, selection thresholds, or near-kickoff workflows.

## Google Colab steps

Your Google Drive should already contain:

```
/content/drive/MyDrive/NFL_Betting_Data/historical_matchups/pregame_matchup_features.csv
```

Run:

```python
!pip -q install "pandas>=2.0,<3" numpy "scikit-learn>=1.4,<2"
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/evaluate_historical_epa_probabilities.py -o /content/evaluate_historical_epa_probabilities.py
!python /content/evaluate_historical_epa_probabilities.py --download-schedules
```

The first run downloads and caches the **free** official
`nflverse/nflverse-data` `schedules/games.csv` file to the same private
`historical_matchups` folder. Subsequent runs reuse it. Only use this
downloaded dataset as an independent **outcome** source and for a late
market **evaluation benchmark**, never as pregame model features.

The model trains on **2015–2021**, evaluates on **2022–2023**, and reports
**2024–2025** as a later historical test. It uses fixed logistic
regression (C=1.0), train-fold-only median imputation and standard scaling.
Only game features computed *before each NFL week* are predictors, and games
with under three prior games on either side are omitted.

The comparison table reports Brier score and log loss for:
- historical football-only probabilities,
- no-vig **closing-market** probabilities, when both closing
  moneyline sides are available,
- constant training-era home-win base rate.

Source games are joined using exact `season,week,game_id,home_team,away_team`;
ambiguous or mismatched game data raises an error. Ties are excluded from
binary win/loss evaluation. Missing closing moneylines remain missing.

### Important limitations

- **Closing odds are NOT early-week executable lines.** Comparing football-only
  pregame predictions to closing market values is a useful but inherently
  timing-mismatched benchmark, not a like-for-like wagering test.
- The user's past research already inspected 2024–2025 NFL games. The
  'historical_test' bucket has no training leakage in this script, but it
  is NOT an entirely untouched research dataset.
- Other football-only models previously performed worse than market odds.
  A new feature set does not establish a genuine edge.
- Only one predetermined algorithm is tested here to reduce ad-hoc model
  shopping. No hyperparameter selection based on the test outcomes.
- This script does NOT backtest wagers, select live picks, claim
  validated probability calibration, or calculate ROI.

Output (private Drive):

```
historical_matchups/football_win_probability_historical.csv
historical_matchups/football_win_probability_report.md
```

After running, assess calibration by season and compare against the closing
market and a chronological market baseline. Keep all 2026 prospective
Model 13 frozen selections untouched.
