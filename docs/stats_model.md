# Stats Model — Football Efficiency + Market Odds

This is a separate historical research track. It does not read, rewrite, or add
selections to Model 13. It does not place bets.

## What it estimates

The primary model estimates the home team's win probability from pregame
football statistics **and** the market's paired moneyline probability. The
same study also reports a football-statistics-only model, a calibrated
market-only model, and the raw no-vig market baseline. This answers both
"which team is more likely to win?" and "does the offered price compensate for
that probability?" A favorite may be the most likely winner and still be poor
value at a short price.

A historical price comparison is included as a diagnostic: probability-based
expected return is computed against each recorded schedule moneyline. The
current output uses nflverse historical schedule odds, which are generally
closing lines and are not proven executable at an earlier decision time. The
2% flag is illustrative only. It is not a live selection rule or betting
recommendation.

## Football features

scripts/build_stats_model_features.py builds same-season, prior-game team
ratings from nflverse regular-season play-by-play. For each matchup, it uses
the average of up to the team's five most recent completed games before the
target week:

- **ANY/A:** (passing yards + 20 × passing TDs − 45 × interceptions − sack
  yards lost) / (pass attempts + sacks).
- **Turnover margin:** interceptions and lost fumbles forced minus giveaways.
- **Explosive-play rate:** run/pass plays gaining at least 20 yards divided by
  run/pass plays.
- **Red-zone TD rate:** drives that reached the opponent's 20 and ended in a
  touchdown divided by drives that reached the 20.
- **Success rate:** nflverse's play-level success flag average.
- **EPA/play:** mean expected points added on run/pass plays.
- Defensive allowed versions of ANY/A, explosive-play rate, red-zone TD rate,
  success rate and EPA/play.

Every target week's ratings are frozen before any game from that week is added.
The ratings reset at each season; Week 1 features are missing rather than
filled with zero or prior-season data.

## Model and evaluation protocol

scripts/stats_model.py uses regularized logistic regression (C=1.0), with
median imputation and scaling fit on training years only. The fixed split is:

- Train: 2015–2021.
- Development: 2022–2023.
- Later historical test: 2024–2025.

All methods are scored on the same games with at least three prior games for
both teams, completed non-tied outcomes, and both moneyline sides present.
The development and later-test scores include Brier score, log loss and
accuracy. No parameters are selected using the later test.

The model output includes home and away probabilities, raw market probability,
and expected-return diagnostics for the listed historical prices. The central
comparison is whether Stats + Market improves proper probability scores over
both the raw market and calibrated-market baselines. Lower Brier and log loss
are better. Accuracy alone is not a sufficient betting metric.

## Run in Google Colab

Mount Google Drive, then run:

\`\`\`python
!pip -q install "pandas>=2.0,<3" numpy "scikit-learn>=1.4,<2" pyarrow
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/build_stats_model_features.py -o /content/build_stats_model_features.py
!python /content/build_stats_model_features.py --seasons 2015:2025 --download
!curl -fsSL https://raw.githubusercontent.com/tylerbasile-bot/nfl-betting-model/main/scripts/stats_model.py -o /content/stats_model.py
!python /content/stats_model.py --download-schedules
\`\`\`

The builder caches nflverse play-by-play in
MyDrive/NFL_Betting_Data/stats_model/pbp/. It writes
stats_model_pregame_features.csv; the evaluator downloads the official
nflverse schedules/games.csv if it is not already present and writes:

- stats_model_predictions.csv
- stats_model_report.md

## Limits and next step

Historical schedule moneylines are not time-matched early-week offers. This
version is an offline evaluation and does not yet produce a prospective 2026
prediction from the timestamped live odds collector. A later prospective
version needs to score upcoming matchups using only completed 2026 statistics,
join the actual timestamped two-sided sportsbook prices, freeze predictions
before kickoff, and evaluate verified final outcomes. That addition must stay
separate from Model 13.

No football statistic or market price establishes a true probability by
itself. Keep any future Stats Model selections paper-only until forward
calibration, price availability, and market comparisons support them.
