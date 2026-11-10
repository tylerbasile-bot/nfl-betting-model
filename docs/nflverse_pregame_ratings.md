# Historical offense/defense matchup database (free nflverse)

Source: [nflverse play-by-play releases](https://github.com/nflverse/nflverse-data/releases/tag/pbp)
using the season-specific `play_by_play_YYYY.parquet` assets.

## Use in Google Colab

Mount Google Drive first if it is not mounted:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Install dependencies and download our **single script** (large PBP files stay in private Drive):

```python
!pip -q install "pandas>=2.0,<3" pyarrow
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/build_nflverse_pregame_ratings.py -o /content/build_nflverse_pregame_ratings.py
!python /content/build_nflverse_pregame_ratings.py --seasons 2022:2025 --download
```

Once four seasons succeed, optionally expand to 2015–2025:

```python
!python /content/build_nflverse_pregame_ratings.py --seasons 2015:2025 --download
```

Cached parquet files are reused. Each year can be fairly large, so Colab RAM,
network time, and Google Drive space may be constraints. Re-running a range
regenerates **only the output research database**, never Model 13's
`frozen_price_candidates.csv`. No sportsbook API key required.

## Outputs

Location: `/content/drive/MyDrive/NFL_Betting_Data/historical_matchups/`

- `pregame_team_ratings.csv`: each eligible team-week's *before-the-week*
  offense and defense ranks, EPA per play, success rate, passing and rushing
  efficiency, plus previous-five-team-game EPA ratings.
- `pregame_matchup_features.csv`: one row per regular-season NFL game
  with home and away pregame ranks, efficiency and matchup differences.
- `README.md`: data-source and leakage qualifications.

Definitions:

- **Offense EPA/play:** sum of EPA on a team's run/pass plays divided by its
  count of those plays. Higher is better.
- **Defense EPA allowed/play:** sum of opponent EPA on run/pass plays faced
  divided by that count. **Lower** is better.
- **Offensive/defensive success rate:** the mean of nflverse's supplied
  `success` indicator on eligible plays, not the traditional 40/60/100
  success-rate heuristic.
- **Passing/rushing EPA:** play_type-specific EPA/play (separately for
  offense and defense).
- **Rolling five:** last 5 completed games played by that particular team,
  not the previous 5 calendar weeks or the current game.
- **Ranks:** 1 = strongest, computed among teams that **had played previously
  in the same season**. Tied values receive the same competition rank.
  Week 1 has no history, so rankings are blank.

### Avoiding outcome leakage

The builder calculates team stats for NFL Week N **before incorporating any
Week N game** into history. Same-week games cannot contribute, even for
Monday-vs-Thursday comparisons. Rankings reset at each new season and
never use final-season ranks as a proxy for prior-week strength.

**Limitation:** The weekly granularity intentionally cannot exploit stats
from earlier games in the same NFL week. It can be conservative, but is
safe for a pre-week historical evaluation. It also excludes postseason.
There is no opponent adjustment, explicit QB/injury availability, weather,
schedule strength, market baseline, probability calibration, or independent
price comparison in this dataset alone.

## Next research steps (NOT implemented in this stage)

1. Join to verified historical moneylines and results by exact teams,
   schedule dates, and game ID mapping with ambiguity safeguards.
2. Establish chronological train/validation/test splits (earlier seasons for
   training; later **untouched** seasons for evaluation).
3. Compare proper probabilistic scores against no-vig betting-market baselines
   and previous football-only models that **did not** demonstrate an advantage.
4. Only then test whether these features add anything beyond market prices
   after plausible execution costs.

This research database **does not change** live Model 13 betting/paper
selection criteria, and does not itself predict moneyline probabilities or
demonstrate positive expected value.
