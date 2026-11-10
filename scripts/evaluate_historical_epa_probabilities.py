#!/usr/bin/env python3
"""Chronological NFL pregame EPA-model experiment, never changes Model 13.

Free inputs: pregame NFLverse feature CSV built separately and NFLverse
schedules/games.csv containing independently observed final scores.
Train 2015-21, inspect 2022-23, report 2024-25 as a *historical* test.
Closing market moneylines are evaluation-only benchmarks and are NOT used as
training features or assumed executable early-week selection prices.
No wager picks or win-rate / ROI claims from re-optimized parameters.
"""
import argparse
import math
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss,log_loss,accuracy_score

SCHEDULES_URL="https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
FEATURE_COLS=[
    "home_off_epa","home_def_epa_allowed","away_off_epa","away_def_epa_allowed",
    "home_off_last5_epa","away_off_last5_epa",
    "home_def_last5_epa_allowed","away_def_last5_epa_allowed",
    "home_off_vs_away_def_epa_diff","away_off_vs_home_def_epa_diff",
    "home_off_rank","home_def_rank","away_off_rank","away_def_rank",
    "home_prior_games","away_prior_games"
]
TRAIN=tuple(range(2015,2022))
VALID=(2022,2023)
TEST=(2024,2025)
RESULT_COLS=["season","week","game_id","home_team","away_team","home_score","away_score",
             "split","home_win","football_home_prob","market_close_no_vig_home_prob",
             "football_brier","market_brier","football_logloss","market_logloss"]

def moneyline_implied(x):
    if pd.isna(x):return float("nan")
    x=float(x)
    if x==0:return float("nan")
    return (-x/(100-x)) if x<0 else (100/(100+x))

def normalize_data(features,schedules):
    needed=["season","week","game_id","home_team","away_team",*FEATURE_COLS]
    absent=[k for k in needed if k not in features.columns]
    if absent:raise ValueError(f"Missing pregame features: {absent}")
    expected=["season","week","game_id","game_type","home_team","away_team",
              "home_score","away_score"]
    absent=[k for k in expected if k not in schedules.columns]
    if absent:raise ValueError(f"Missing schedule columns: {absent}")
    features=features.copy()
    for c in FEATURE_COLS:features[c]=pd.to_numeric(features[c],errors="coerce")
    schedule=schedules[schedules["game_type"].eq("REG")].copy()
    for c in ["season","week","home_score","away_score"]:
        schedule[c]=pd.to_numeric(schedule[c],errors="coerce")
    features["season"]=pd.to_numeric(features["season"],errors="coerce")
    features["week"]=pd.to_numeric(features["week"],errors="coerce")
    if features.duplicated(["season","week","game_id"]).any():
        raise ValueError("Duplicate feature game keys; refusing ambiguous join")
    if schedule.duplicated(["season","week","game_id"]).any():
        raise ValueError("Duplicate schedule game keys; refusing ambiguous join")
    cols=expected+[c for c in ("home_moneyline","away_moneyline") if c in schedule.columns]
    # Validate both teams AND chronological labels, not just provider game_id.
    merged=features[needed].merge(schedule[cols],on=["season","week","game_id","home_team","away_team"],
                                  how="left",validate="one_to_one",indicator=True)
    if (merged["_merge"]!="both").any():
        failures=merged.loc[merged["_merge"]!="both",["game_id","season","week"]]
        raise ValueError(f"Unmatched team/game metadata for {len(failures)} rows (e.g. {failures.head(4).to_dict('records')})")
    merged=merged.drop(columns="_merge")
    merged=merged[merged["season"].between(2015,2025)].copy()
    merged=merged.dropna(subset=["home_score","away_score"])
    # Ties excluded from binary binary outcome label, never silently losses.
    merged=merged[merged["home_score"]!=merged["away_score"]].copy()
    merged["home_win"]=(merged["home_score"]>merged["away_score"]).astype(int)
    merged["split"]=merged["season"].apply(
        lambda y:"train" if y in TRAIN else "validation" if y in VALID else "historical_test" if y in TEST else "ignored")
    merged=merged[merged["split"]!="ignored"]
    # To avoid new-season Week 1 unranked teams and early unstable histories,
    # require 3 prior games for both teams, predeclared across all splits.
    merged=merged[(merged["home_prior_games"]>=3)&(merged["away_prior_games"]>=3)].copy()
    if {"home_moneyline","away_moneyline"}.issubset(merged.columns):
        h=merged["home_moneyline"].map(moneyline_implied)
        a=merged["away_moneyline"].map(moneyline_implied)
        merged["market_close_no_vig_home_prob"]=h/(h+a)
        merged.loc[~np.isfinite(merged["market_close_no_vig_home_prob"]),"market_close_no_vig_home_prob"]=np.nan
    else:
        merged["market_close_no_vig_home_prob"]=np.nan
    return merged.sort_values(["season","week","game_id"]).reset_index(drop=True)

def train_and_score(df):
    training=df[df["split"]=="train"].copy()
    if training.empty or training["home_win"].nunique()!=2:
        raise ValueError("Insufficient historical training outcomes")
    pipeline=Pipeline([
        ("preprocess",ColumnTransformer(
            [("numeric",Pipeline([
                ("fill",SimpleImputer(strategy="median")),
                ("scale",StandardScaler())]),FEATURE_COLS)])),
        ("lr",LogisticRegression(C=1.0,max_iter=2000,random_state=17))
    ])
    pipeline.fit(training[FEATURE_COLS],training["home_win"])
    result=df[["season","week","game_id","home_team","away_team","home_score",
               "away_score","split","home_win","market_close_no_vig_home_prob"]].copy()
    result["football_home_prob"]=pipeline.predict_proba(df[FEATURE_COLS])[:,1]
    # Non-predictive explanatory baseline (all home teams have their observed
    # training-era win frequency). Useful to detect weak features.
    result["train_home_rate_baseline"]=float(training["home_win"].mean())
    for prefix,col in (("football","football_home_prob"),
                       ("market","market_close_no_vig_home_prob"),
                       ("constant","train_home_rate_baseline")):
        p=result[col].clip(1e-6,1-1e-6)
        result[f"{prefix}_brier"]=(p-result["home_win"])**2
        result[f"{prefix}_logloss"]=-(result["home_win"]*np.log(p)+(1-result["home_win"])*np.log(1-p))
    return result,pipeline

def summarize(results):
    lines=[
        "# NFL Historical EPA/Defense Probability Experiment","",
        "> **RESEARCH ONLY — NOT AN EXECUTABLE BETTING STRATEGY OR VERIFIED POSITIVE EV.**","",
        "## Predeclared evaluation","",
        "- Model: standard-scaled logistic regression, fixed C=1.0; median imputation computed on training rows only.",
        "- Train: 2015–2021; development check: 2022–2023; historical holdout: 2024–2025.",
        "- Features: prior-week EPA offense/defense, rolling five-game EPA, cross-matchup differences, and pregame ranks.",
        "- Exclude games where either team has fewer than three prior same-season games; exclude ties.",
        "- Scores are outcome labels only, never model input.",
        "- NFLverse **closing** no-vig market moneyline is an *after-the-fact benchmark*, not a quote known at the first early-week pick timestamp. It is **not** used as model input.",
        "- The 2024–25 seasons have already appeared in this research project's earlier analyses; this is a historical holdout by training time, not a pristine untouched evaluation.","",
        "| Split | Games | Football Brier ↓ | Closing-market Brier ↓ | Constant Brier ↓ | Football log loss ↓ | Closing-market log loss ↓ |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("train","validation","historical_test"):
        g=results[results["split"]==name]
        if len(g)==0:continue
        market=g["market_brier"].notna()
        lines.append(f"| {name} | {len(g)} | {g['football_brier'].mean():.5f} | "
                     f"{g.loc[market,'market_brier'].mean():.5f} (n={market.sum()})" if False else "")
        # Keep formatting separate to prevent report creation edge cases.
        lines[-1]=(f"| {name} | {len(g)} | {g['football_brier'].mean():.5f} | "
                  f"{g.loc[market,'market_brier'].mean():.5f} (n={int(market.sum())}) | "
                  f"{g['constant_brier'].mean():.5f} | {g['football_logloss'].mean():.5f} | "
                  f"{g.loc[market,'market_logloss'].mean():.5f} |")
    lines+=["",
        "## Interpretation","",
        "- Lower Brier/log loss is better. Compare held-out rows only; the training score is not performance evidence.",
        "- Missing historical closing odds are excluded **only** from market metrics (not silently assigned neutral odds).",
        "- This does not test profitable sportsbook execution, identify live opportunities, or calculate an ROI.",
        "- Separate Model 13 prospective frozen selections and thresholds remain unchanged.",
        "- The objective is to see whether football-only features provide predictive information beyond simple baselines, before any market-augmented experiments.",
        ""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser()
    root="/content/drive/MyDrive/NFL_Betting_Data/historical_matchups"
    parser.add_argument("--features",default=f"{root}/pregame_matchup_features.csv")
    parser.add_argument("--schedules",default=f"{root}/games.csv")
    parser.add_argument("--download-schedules",action="store_true")
    parser.add_argument("--outdir",default=root)
    args=parser.parse_args()
    schedules=Path(args.schedules)
    if not schedules.exists():
        if not args.download_schedules:
            raise SystemExit("No NFLverse schedules CSV cached; run with --download-schedules.")
        import urllib.request
        schedules.parent.mkdir(parents=True,exist_ok=True)
        tmp=schedules.with_suffix(".partial")
        try:
            urllib.request.urlretrieve(SCHEDULES_URL,tmp)
            tmp.replace(schedules)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    df=normalize_data(pd.read_csv(args.features),pd.read_csv(schedules))
    results,_=train_and_score(df)
    destination=Path(args.outdir);destination.mkdir(parents=True,exist_ok=True)
    output=destination/"football_win_probability_historical.csv"
    results.to_csv(output,index=False)
    report=summarize(results)
    (destination/"football_win_probability_report.md").write_text(report,encoding="utf-8")
    print(report)
    print("Saved:",output)
    print("Saved:",destination/"football_win_probability_report.md")

if __name__=="__main__":main()
