#!/usr/bin/env python3
"""Model 10B research challenger: historical football features + market.

IMPORTANT: Historical nflverse moneylines can be CLOSING prices. This experiment
CANNOT reconstruct the early-week, timestamped Model 10 market. It neither
changes the immutable Model 10 ledger nor creates retrospective 'live' picks.
All scores are on the same held-out games; no bets or ROI are generated.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from evaluate_historical_epa_probabilities import FEATURE_COLS, TRAIN, VALID, TEST
from evaluate_model14_market_plus_epa import prepare, score

DEFAULT_ROOT = "/content/drive/MyDrive/NFL_Betting_Data/historical_matchups"
PROBABILITIES = {
    "raw_market": "market_close_no_vig_home_prob",
    "market_calibrated": "market_calibrated_home_prob",
    "stats_only": "stats_only_home_prob",
    "model10b_combined": "model10b_combined_home_prob",
}

def pipeline(columns):
    return Pipeline([
        ("transform", ColumnTransformer([
            ("numeric", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler())
            ]), columns)
        ], remainder="drop")),
        ("logistic", LogisticRegression(C=1.0, max_iter=2000, random_state=10))
    ])

def fit_and_evaluate(features, schedules):
    data = prepare(features, schedules)
    train = data.loc[data["season"].isin(TRAIN)].copy()
    if len(train) < 100 or train["home_win"].nunique() != 2:
        raise ValueError("Insufficient historical training observations and outcomes")
    if data.duplicated(["season", "week", "game_id"]).any():
        raise ValueError("Duplicate game IDs")
    # This same game cohort is used by every comparator; no post-hoc filtering.
    columns = {
        "market_calibrated_home_prob": ["market_logit"],
        "stats_only_home_prob": FEATURE_COLS,
        "model10b_combined_home_prob": ["market_logit", *FEATURE_COLS],
    }
    out = data[["season", "week", "game_id", "home_team", "away_team",
                "home_win", "split", "market_close_no_vig_home_prob"]].copy()
    trained = {}
    for target, predictors in columns.items():
        model = pipeline(predictors)
        model.fit(train[predictors], train["home_win"])
        out[target] = model.predict_proba(data[predictors])[:, 1]
        trained[target] = model
    for name, col in PROBABILITIES.items():
        brier, logloss = score(out["home_win"], out[col])
        out[name + "_brier"] = brier
        out[name + "_logloss"] = logloss
        out[name + "_correct"] = (out[col].ge(0.5) == out["home_win"].eq(1)).astype(int)
    return out.sort_values(["season", "week", "game_id"]).reset_index(drop=True)

def summarize(out):
    lines = [
        "# Model 10B — Historical stats + market research challenger", "",
        "> HISTORICAL RESEARCH ONLY. NO LIVE MODEL 10B PICKS, NO VERIFIED +EV, NO WAGERS.", "",
        "## Protocol", "",
        "- Training seasons: 2015–2021; development: 2022–2023; later historical evaluation: 2024–2025.",
        "- Same games for raw market, calibrated market, football-only, and combined models.",
        "- Logistic regression C=1; median imputation and scaling fitted exclusively on training rows.",
        "- Football statistics are pre-week and lagged. Both teams require at least three prior games.",
        "- Historical market inputs are nflverse *closing* moneylines, not Model 10's frozen early-week quotes.",
        "- 2024–2025 have been examined by this project before; these are not fully untouched tests.",
        "- Model 10 immutable forecasts and Model 13 rules/ledgers remain unchanged.", "",
        "## Scores (lower Brier and log loss are better)", "",
        "| Split | Games | Model | Brier | Log loss | Winner accuracy |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for split in ("train", "validation", "historical_test"):
        cohort = out.loc[out["split"].eq(split)]
        if cohort.empty:
            continue
        for name in PROBABILITIES:
            lines.append(
                f"| {split} | {len(cohort)} | {name} | "
                f"{cohort[name + '_brier'].mean():.5f} | "
                f"{cohort[name + '_logloss'].mean():.5f} | "
                f"{cohort[name + '_correct'].mean():.1%} |"
            )
    lines.extend(["", "## Year-by-year held-out Brier", "",
                  "| Season | Games | Raw market | Market calibrated | Stats only | Model 10B combined |",
                  "|---|---:|---:|---:|---:|---:|"])
    for year in (*VALID, *TEST):
        s = out.loc[out["season"].eq(year)]
        if s.empty:
            continue
        lines.append(f"| {year} | {len(s)} | " +
                     " | ".join(f"{s[k + '_brier'].mean():.5f}" for k in PROBABILITIES) + " |")
    held = out.loc[out["season"].isin(TEST)]
    lines.extend(["", "## Promotion gate", ""])
    if held.empty:
        lines.append("- No historical test games were available. Do not claim an improvement.")
    else:
        b = held["model10b_combined_brier"].mean()
        raw = held["raw_market_brier"].mean()
        calibrated = held["market_calibrated_brier"].mean()
        l = held["model10b_combined_logloss"].mean()
        lr = held["raw_market_logloss"].mean()
        lc = held["market_calibrated_logloss"].mean()
        pass_both = b < min(raw, calibrated) and l < min(lr, lc)
        lines += [
            f"- 2024–2025 combined minus raw-market Brier: **{b-raw:+.5f}**.",
            f"- 2024–2025 combined minus calibrated-market Brier: **{b-calibrated:+.5f}**.",
            f"- Combined improves both Brier and log loss against both market benchmarks: **{'YES' if pass_both else 'NO'}**.",
            "- Even a YES is not a deployment approval: closing-odds timing mismatch prevents comparison with live Model 10.",
        ]
    lines.extend(["", "## Next requirement for a prospective Model 10B", "",
                  "Build a separate, timestamped, feature-complete 2026 pregame input and "
                  "use the exact Model 10 freeze-time consensus probability. "
                  "Train/recalibrate without using 2026 final results or future odds; "
                  "freeze new predictions prospectively once, and measure them on the same games.",
                  "There is no automatic import from private Google Drive to the public GitHub workflow.",
                  "No ROI or positive-EV claim follows from these scores.", ""])
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features", default=f"{DEFAULT_ROOT}/pregame_matchup_features.csv")
    ap.add_argument("--schedules", default=f"{DEFAULT_ROOT}/games.csv")
    ap.add_argument("--outdir", default=f"{DEFAULT_ROOT}/model10b")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    features = pd.read_csv(args.features)
    schedules = pd.read_csv(args.schedules)
    results = fit_and_evaluate(features, schedules)
    report = summarize(results)
    outdir.mkdir(parents=True, exist_ok=True)
    results.to_csv(outdir / "historical_predictions.csv", index=False)
    (outdir / "historical_report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved historical-only Model 10B report and predictions to {outdir}")

if __name__ == "__main__":
    main()
