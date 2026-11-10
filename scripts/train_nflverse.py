#!/usr/bin/env python3
"""Model 9B: walk-forward market-offset NFLverse research, run from Google Colab.

The model is deliberately regularized and tested on future seasons only.
It must outperform the market in proper scoring before being considered useful.
No betting decisions, ROI claims or current-season score leakage.
"""
import argparse
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit

FEATURES = [
    "margin_diff", "win_rate_diff", "points_for_diff",
    "points_against_diff", "passing_epa_diff", "rushing_epa_diff",
]
STAT_COLUMNS = ("passing_epa", "rushing_epa")
PAST_GAMES = 5
EVAL_SEASONS = (2022, 2023, 2024, 2025)

def american_prob(x):
    x = float(x)
    if x == 0 or np.isnan(x):
        return np.nan
    return -x / (100-x) if x < 0 else 100 / (100+x)

def load_stats(path):
    if not path.exists():
        return {}
    stats = pd.read_parquet(path)
    needed = {"season", "week", "team"}
    if not needed.issubset(stats.columns):
        print("Team stats missing keys; continuing without EPA.")
        return {}
    available = [c for c in STAT_COLUMNS if c in stats.columns]
    if not available:
        print("Team stats have no requested EPA columns; EPA defaults to zero.")
        return {}
    for c in available:
        stats[c] = pd.to_numeric(stats[c], errors="coerce")
    # NFLverse weekly team_stats is generally unique, but aggregate safely.
    grouped = stats.groupby(["season", "week", "team"], as_index=False)[available].sum(min_count=1)
    return {
        (int(row["season"]), int(row["week"]), str(row["team"])): {
            c: float(row[c]) if pd.notna(row[c]) else np.nan for c in available
        }
        for _, row in grouped.iterrows()
    }

def to_game_frame(schedule):
    cols = ["season","week","home_team","away_team","home_score","away_score",
            "home_moneyline","away_moneyline"]
    missing = [c for c in cols if c not in schedule.columns]
    if missing:
        raise ValueError("Missing schedule fields: " + ", ".join(missing))
    data = schedule.copy()
    if "game_type" in data.columns:
        data = data[data["game_type"].astype(str).isin(["REG","REGULAR","Regular Season"])]
    elif "season_type" in data.columns:
        data = data[data["season_type"].astype(str).isin(["REG","REGULAR","Regular Season"])]
    for c in ["season","week","home_score","away_score","home_moneyline","away_moneyline"]:
        data[c] = pd.to_numeric(data[c],errors="coerce")
    data = data.dropna(subset=["season","week","home_team","away_team"])
    if "gameday" in data.columns:
        data["sort_day"] = pd.to_datetime(data["gameday"],errors="coerce")
    else:
        data["sort_day"] = pd.NaT
    if "game_id" not in data.columns:
        data["game_id"] = (
            data["season"].astype(int).astype(str) + "_" +
            data["week"].astype(int).astype(str).str.zfill(2) + "_" +
            data["away_team"].astype(str) + "_" + data["home_team"].astype(str)
        )
    data = data.sort_values(["season","week","sort_day","game_id"]).drop_duplicates("game_id")
    return data

def build_pregame_features(schedules, teamstats):
    history = defaultdict(lambda: deque(maxlen=PAST_GAMES))
    rows = []
    for _, game in schedules.iterrows():
        season, week = int(game["season"]), int(game["week"])
        home, away = str(game["home_team"]), str(game["away_team"])
        def form(team, field, default=0.0):
            vals = [row[field] for row in history[team] if pd.notna(row.get(field))]
            return float(np.mean(vals)) if vals else default
        def feature(field):
            return form(home, field) - form(away, field)
        hml, aml = game["home_moneyline"], game["away_moneyline"]
        ph, pa = american_prob(hml) if pd.notna(hml) else np.nan, american_prob(aml) if pd.notna(aml) else np.nan
        market = ph/(ph+pa) if np.isfinite(ph) and np.isfinite(pa) else np.nan
        hs, aas = game["home_score"], game["away_score"]
        complete = pd.notna(hs) and pd.notna(aas)
        row = {
            "game_id": str(game["game_id"]), "season":season, "week":week,
            "home_team":home, "away_team":away,
            "home_score":hs, "away_score":aas, "market_prob":market,
            "completed":bool(complete),
            "home_win":int(hs>aas) if complete and hs!=aas else np.nan,
            "margin_diff":feature("margin"),
            "win_rate_diff":feature("win"),
            "points_for_diff":feature("points_for"),
            "points_against_diff":feature("points_against"),
            "passing_epa_diff":feature("passing_epa"),
            "rushing_epa_diff":feature("rushing_epa"),
        }
        rows.append(row)
        if complete:
            hp = teamstats.get((season,week,home),{})
            ap = teamstats.get((season,week,away),{})
            history[home].append({
                "margin":float(hs-aas), "win":float(hs>aas),
                "points_for":float(hs),"points_against":float(aas),
                **{c:hp.get(c,np.nan) for c in STAT_COLUMNS}
            })
            history[away].append({
                "margin":float(aas-hs), "win":float(aas>hs),
                "points_for":float(aas),"points_against":float(hs),
                **{c:ap.get(c,np.nan) for c in STAT_COLUMNS}
            })
    return pd.DataFrame(rows)

def make_arrays(frame, center=None, scale=None):
    raw = frame[FEATURES].fillna(0).astype(float).to_numpy()
    if center is None:
        center = raw.mean(axis=0)
        scale = np.maximum(raw.std(axis=0),1.0)
    return (raw-center)/scale, center, scale

def fit_market_offset(train, reg=25.0):
    x, center, scale = make_arrays(train)
    market_logit = logit(np.clip(train["market_prob"].to_numpy(), 1e-5, 1-1e-5))
    y = train["home_win"].to_numpy()
    def objective(beta):
        z = market_logit + x @ beta
        loss = np.logaddexp(0,z).sum() - y @ z + (reg/2)*np.dot(beta,beta)
        gradient = x.T@(expit(z)-y)+reg*beta
        return loss, gradient
    sol = minimize(objective, np.zeros(x.shape[1]),jac=True,method="L-BFGS-B")
    if not sol.success:
        raise RuntimeError("Optimization failed: "+sol.message)
    return sol.x, center, scale

def evaluate(frame, predicted):
    y = frame["home_win"].to_numpy(dtype=float)
    predicted = np.clip(np.asarray(predicted),1e-6,1-1e-6)
    return {
        "games":len(y),
        "accuracy":float(np.mean((predicted>=.5)==y)),
        "brier":float(np.mean((predicted-y)**2)),
        "logloss":float(np.mean(-y*np.log(predicted)-(1-y)*np.log(1-predicted))),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",default="/content/drive/MyDrive/NFL_Betting_Data")
    parser.add_argument("--output-dir",default=None)
    args = parser.parse_args()
    folder = Path(args.data_dir)
    if not (folder/"schedules.parquet").is_file():
        raise SystemExit("Missing schedules.parquet: mount Google Drive in Colab and check --data-dir.")
    schedules = to_game_frame(pd.read_parquet(folder/"schedules.parquet"))
    stats = load_stats(folder/"team_stats.parquet")
    all_games = build_pregame_features(schedules, stats)
    # Only completed REG games with both prices and non-tied final scores.
    historical = all_games[
        (all_games["completed"]) &
        (all_games["home_win"].notna()) &
        (all_games["market_prob"].between(.01,.99)) &
        (all_games["season"]<=2025)
    ].copy()
    records = []
    metrics = []
    for year in EVAL_SEASONS:
        train = historical[(historical.season >= 2020) & (historical.season < year)]
        test = historical[historical.season == year].copy()
        if len(train)<100 or len(test)<100:
            print(f"Skipping {year} — insufficient train/test games ({len(train)}/{len(test)}).")
            continue
        beta, center, scale = fit_market_offset(train)
        x, _, _ = make_arrays(test,center,scale)
        m = test["market_prob"].to_numpy()
        test["model_prob"] = expit(logit(np.clip(m,1e-5,1-1e-5)) + x@beta)
        for name, probs in [("market",m),("market_plus_nflverse",test["model_prob"])]:
            metrics.append({"test_season":year, "method":name, **evaluate(test,probs)})
        records.append(test[["game_id","season","week","home_team","away_team",
                             "home_win","market_prob","model_prob"]])
    if not records:
        raise SystemExit("No evaluable historical seasons; check the schedule file and historical moneylines.")
    predictions = pd.concat(records,ignore_index=True)
    summary = pd.DataFrame(metrics)
    out = Path(args.output_dir) if args.output_dir else folder/"model9_validation"
    out.mkdir(parents=True,exist_ok=True)
    predictions.to_csv(out/"walk_forward_predictions.csv",index=False)
    summary.to_csv(out/"walk_forward_metrics.csv",index=False)
    print("\nMODEL 9B — HELD-OUT YEAR-BY-YEAR TEST")
    print(summary.round(4).to_string(index=False))
    pooled=[]
    for name, col in [("market","market_prob"),("market_plus_nflverse","model_prob")]:
        pooled.append({"method":name,**evaluate(predictions,predictions[col].to_numpy())})
    print("\nPOOLED HELD-OUT METRICS")
    print(pd.DataFrame(pooled).round(4).to_string(index=False))
    print("\nNOTE: Odds in nflverse schedules may be closing prices; historical score comparisons")
    print("are a RESEARCH DIAGNOSTIC, not a tradable pregame backtest.")
    print("No betting recommendations. Results remain local to your Google Drive.")
    print("Saved:",out)

if __name__=="__main__":
    main()
