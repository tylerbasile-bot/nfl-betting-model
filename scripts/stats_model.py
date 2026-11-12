#!/usr/bin/env python3
"""Stats Model: leak-safe football features plus a market-odds probability baseline.

Research only. Fits 2015-2021, inspects 2022-2023, and reports the later
2024-2025 historical test. nflverse schedule odds are closing prices, so the
price-value columns are retrospective diagnostics, not executable bets.
"""
import argparse
import math
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SCHEDULES_URL = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
ROOT = "/content/drive/MyDrive/NFL_Betting_Data/stats_model"
TRAIN_YEARS = tuple(range(2015, 2022))
VALID_YEARS = (2022, 2023)
TEST_YEARS = (2024, 2025)
METRICS = ("any_a", "turnover_margin", "explosive_rate", "redzone_td_rate", "success_rate", "epa_per_play")
FEATURES = [
    f"{side}_{team}_{metric}"
    for team in ("home", "away")
    for side in ("off", "def_allowed")
    for metric in (METRICS if side == "off" else
                   ("any_a", "explosive_rate", "redzone_td_rate", "success_rate", "epa_per_play"))
] + ["home_prior_games", "away_prior_games"]


def american_implied(value):
    x = pd.to_numeric(value, errors="coerce")
    if pd.isna(x) or x == 0:
        return np.nan
    return -x / (100 - x) if x < 0 else 100 / (100 + x)


def american_profit_per_unit(value):
    x = float(value)
    if x == 0 or not np.isfinite(x):
        return np.nan
    return 100 / abs(x) if x < 0 else x / 100


def canonical_team(value):
    aliases = {"SD": "LAC", "LAC": "LAC", "STL": "LA", "LA": "LA", "LAR": "LA",
               "OAK": "LV", "LV": "LV", "JAC": "JAX", "JAX": "JAX",
               "WSH": "WAS", "WAS": "WAS"}
    key = str(value).strip().upper()
    return aliases.get(key, key)


def canonical_id(value):
    parts = str(value).strip().split("_")
    if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
        return "_".join((parts[0], f"{int(parts[1]):02d}",
                         canonical_team(parts[2]), canonical_team(parts[3])))
    return str(value).strip()


def load_schedules(path, download):
    source = Path(path)
    if not source.exists():
        if not download:
            raise FileNotFoundError(f"Missing {source}; rerun with --download-schedules.")
        source.parent.mkdir(parents=True, exist_ok=True)
        temp = source.with_suffix(".partial")
        try:
            urlretrieve(SCHEDULES_URL, temp)
            temp.replace(source)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    return pd.read_csv(source)


def assemble(features, schedules):
    required_f = {"season", "week", "game_id", "home_team", "away_team", *FEATURES}
    required_s = {"season", "week", "game_id", "game_type", "home_team", "away_team",
                  "home_score", "away_score", "home_moneyline", "away_moneyline"}
    if missing := sorted(required_f - set(features.columns)):
        raise ValueError(f"Stats feature file is missing columns: {missing}")
    if missing := sorted(required_s - set(schedules.columns)):
        raise ValueError(f"Schedule file is missing columns: {missing}")
    f = features.copy()
    s = schedules[schedules["game_type"].eq("REG")].copy()
    for frame in (f, s):
        frame["season"] = pd.to_numeric(frame["season"], errors="coerce")
        frame["week"] = pd.to_numeric(frame["week"], errors="coerce")
        frame["_key"] = frame["game_id"].map(canonical_id)
    key = ["season", "week", "_key"]
    if f.duplicated(key).any() or s.duplicated(key).any():
        raise ValueError("Duplicate canonical game key; refusing an ambiguous join.")
    f["_home"] = f["home_team"].map(canonical_team)
    f["_away"] = f["away_team"].map(canonical_team)
    s["_home"] = s["home_team"].map(canonical_team)
    s["_away"] = s["away_team"].map(canonical_team)
    keep = key + ["home_score", "away_score", "home_moneyline", "away_moneyline", "_home", "_away"]
    merged = f.merge(s[keep], on=key, how="inner", validate="one_to_one", suffixes=("", "_schedule"))
    if (merged["_home"] != merged["_home_schedule"]).any() or (merged["_away"] != merged["_away_schedule"]).any():
        raise ValueError("Home/away identity mismatch after strict game-key join.")
    merged["home_score"] = pd.to_numeric(merged["home_score"], errors="coerce")
    merged["away_score"] = pd.to_numeric(merged["away_score"], errors="coerce")
    merged["home_moneyline"] = pd.to_numeric(merged["home_moneyline"], errors="coerce")
    merged["away_moneyline"] = pd.to_numeric(merged["away_moneyline"], errors="coerce")
    for col in FEATURES:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged = merged.dropna(subset=["home_score", "away_score", "home_moneyline", "away_moneyline"])
    merged = merged[(merged["home_moneyline"] != 0) & (merged["away_moneyline"] != 0)].copy()
    merged = merged[merged["home_score"] != merged["away_score"]].copy()
    merged = merged[(merged["home_prior_games"] >= 3) & (merged["away_prior_games"] >= 3)].copy()
    home_raw = merged["home_moneyline"].map(american_implied)
    away_raw = merged["away_moneyline"].map(american_implied)
    merged["market_home_probability"] = home_raw / (home_raw + away_raw)
    merged = merged[merged["season"].isin((*TRAIN_YEARS, *VALID_YEARS, *TEST_YEARS))].copy()
    merged["home_win"] = (merged["home_score"] > merged["away_score"]).astype(int)
    merged["market_logit"] = np.log(merged["market_home_probability"] / (1 - merged["market_home_probability"]))
    merged["split"] = np.select(
        [merged["season"].isin(TRAIN_YEARS), merged["season"].isin(VALID_YEARS)],
        ["train", "development"], default="historical_test")
    return merged.reset_index(drop=True)


def model_pipeline(columns, seed):
    prep = ColumnTransformer([("numeric", Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ]), columns)], remainder="drop")
    return Pipeline([("prep", prep),
                     ("logit", LogisticRegression(C=1.0, max_iter=3000, random_state=seed))])


def score(y, p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, dtype=int)
    return {
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1-y) * np.log(1-p))),
        "accuracy": float(np.mean((p >= 0.5) == y)),
    }


def fit_models(frame):
    train = frame[frame["split"].eq("train")]
    if len(train) < 100 or train["home_win"].nunique() != 2:
        raise ValueError("Not enough paired historical training games (need at least 100).")
    stats = model_pipeline(FEATURES, 15)
    market = model_pipeline(["market_logit"], 15)
    combined = model_pipeline(["market_logit", *FEATURES], 15)
    stats.fit(train[FEATURES], train["home_win"])
    market.fit(train[["market_logit"]], train["home_win"])
    combined.fit(train[["market_logit", *FEATURES]], train["home_win"])
    out = frame.copy()
    out["stats_model_home_probability"] = stats.predict_proba(frame[FEATURES])[:, 1]
    out["market_calibrated_home_probability"] = market.predict_proba(frame[["market_logit"]])[:, 1]
    out["stats_plus_market_home_probability"] = combined.predict_proba(
        frame[["market_logit", *FEATURES]])[:, 1]
    out["stats_plus_market_away_probability"] = 1 - out["stats_plus_market_home_probability"]
    out["home_model_expected_return"] = (
        out["stats_plus_market_home_probability"] * out["home_moneyline"].map(american_profit_per_unit)
        - (1 - out["stats_plus_market_home_probability"])
    )
    out["away_model_expected_return"] = (
        out["stats_plus_market_away_probability"] * out["away_moneyline"].map(american_profit_per_unit)
        - (1 - out["stats_plus_market_away_probability"])
    )
    out["higher_model_value_side"] = np.where(
        out["home_model_expected_return"] >= out["away_model_expected_return"], "HOME", "AWAY")
    out["higher_model_value_expected_return"] = np.maximum(
        out["home_model_expected_return"], out["away_model_expected_return"])
    out["illustrative_2pct_value_flag"] = out["higher_model_value_expected_return"] >= 0.02
    return out


def make_report(out):
    lines = [
        "# Stats Model — Football Efficiency + Market Odds", "",
        "> **HISTORICAL RESEARCH ONLY. NO LIVE PICKS OR VERIFIED +EV.**",
        "> Historical schedule odds are closing prices, not guaranteed pregame offers.", "",
        "## Fixed study design", "",
        "- Train: 2015–2021; development: 2022–2023; later historical test: 2024–2025.",
        "- Logistic regression C=1.0; train-only imputation/scaling; no tuning on development or test labels.",
        "- Same eligible games for all model comparisons; require at least three prior games per team.",
        "- Features are generated from previous games only. Games in the same week are not used to rate each other.",
        "- Included football inputs: ANY/A, turnover margin, 20+ yard explosive-play rate, red-zone touchdown rate,",
        "  nflverse success rate, and EPA/play, each with recent team offense/defense history.",
        "- Market input: paired schedule moneylines converted to a no-vig home probability.",
        "",
        "## Paired probability scores", "",
        "| Split | Method | Games | Brier (lower is better) | Log loss (lower is better) | Accuracy |",
        "|---|---|---:|---:|---:|---:|",
    ]
    methods = [
        ("market_raw", "Raw no-vig market", "market_home_probability"),
        ("market_calibrated", "Train-calibrated market", "market_calibrated_home_probability"),
        ("stats_only", "Stats only", "stats_model_home_probability"),
        ("stats_plus_market", "Stats + market", "stats_plus_market_home_probability"),
    ]
    for split in ("development", "historical_test"):
        subset = out[out["split"].eq(split)]
        for label, name, col in methods:
            sc = score(subset["home_win"], subset[col])
            lines.append(f"| {split} | {name} | {len(subset)} | {sc['brier']:.5f} | {sc['log_loss']:.5f} | {sc['accuracy']:.3%} |")
    lines += [
        "", "## Price comparison diagnostic", "",
        "The prediction CSV includes the Stats Model's estimated expected return at each historical listed moneyline.",
        "The 2% flag is an illustrative screen only. It is not a betting recommendation or a validated strategy.",
        "Because these are historical closing lines, the price may not have been available at a decision time.",
        "No ROI claim is made.", "",
        "## Feature definitions", "",
        "- ANY/A = (pass yards + 20 × pass TD − 45 × interceptions − sack yards lost) / (pass attempts + sacks).",
        "- Turnover margin = interceptions and lost fumbles forced minus giveaways.",
        "- Explosive plays = run/pass plays gaining at least 20 yards, divided by run/pass plays.",
        "- Red-zone TD rate = drives reaching the opponent 20-yard line that ended in a touchdown, divided by red-zone drives.",
        "- Success rate uses nflverse's published play success flag; its convention may differ from a custom 40/60/100 rule.",
        "- EPA/play is mean expected points added on run/pass plays.",
        "- Team ratings are the average of the most recent five completed games in the same season.",
        "",
        "Missing first-weeks features stay missing and are imputed using training data only.",
        "Ties and games without both market sides are excluded. Keep the untouched Model 13 ledger separate.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default=f"{ROOT}/stats_model_pregame_features.csv")
    parser.add_argument("--schedules", default=f"{ROOT}/games.csv")
    parser.add_argument("--outdir", default=ROOT)
    parser.add_argument("--download-schedules", action="store_true")
    args = parser.parse_args()
    frame = assemble(pd.read_csv(args.features), load_schedules(args.schedules, args.download_schedules))
    out = fit_models(frame)
    dest = Path(args.outdir)
    dest.mkdir(parents=True, exist_ok=True)
    columns = [
        "season", "week", "game_id", "home_team", "away_team", "home_score", "away_score",
        "split", "home_win", "home_moneyline", "away_moneyline", "market_home_probability",
        "stats_model_home_probability", "market_calibrated_home_probability",
        "stats_plus_market_home_probability", "stats_plus_market_away_probability",
        "home_model_expected_return", "away_model_expected_return", "higher_model_value_side",
        "higher_model_value_expected_return", "illustrative_2pct_value_flag",
    ]
    csv_path = dest / "stats_model_predictions.csv"
    report_path = dest / "stats_model_report.md"
    out[columns].to_csv(csv_path, index=False)
    report_path.write_text(make_report(out), encoding="utf-8")
    print(make_report(out))
    print(f"Saved: {csv_path}")
    print(f"Saved: {report_path}")


if __name__ == "__main__":
    main()
