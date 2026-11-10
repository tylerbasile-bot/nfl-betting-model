#!/usr/bin/env python3
"""Model 12 candidate: independent NFL win probabilities; offline Colab research.

Football-only model. Sportsbook moneylines are NOT inputs to model training or
prediction, only a comparator in held-out evaluation. Does not publish into the
Model 11 live inbox. The historical 2025 holdout has already been examined by
earlier models; results are research diagnostics, not untouched confirmation.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.optimize import minimize

from train_nflverse import (build_pregame_features, load_stats,
                            to_game_frame, evaluate)

FEATURES = [
    "margin_diff", "win_rate_diff", "points_for_diff",
    "points_against_diff", "passing_epa_diff", "rushing_epa_diff",
]
EVAL_YEARS = (2022, 2023, 2024, 2025)
TRAIN_START = 2020
# Predeclared test criteria, not tuned after viewing outcomes.
GATE_MIN_GAMES = 800
GATE_MIN_IMPROVEMENT = 0.002
GATE_MIN_GOOD_YEARS = 3

def raw_features(frame):
    x = frame[FEATURES].copy().astype(float).replace([np.inf,-np.inf],np.nan)
    return x

def fit_model(train, reg=15.0):
    xdf=raw_features(train)
    fill=xdf.median().fillna(0).to_numpy()
    x=xdf.fillna(pd.Series(fill,index=FEATURES)).to_numpy()
    mean=x.mean(axis=0)
    std=np.maximum(x.std(axis=0),1.0)
    norm=(x-mean)/std
    y=train["home_win"].to_numpy(dtype=float)
    # Include intercept but don't penalize it.
    design=np.c_[np.ones(len(norm)),norm]
    def objective(beta):
        z=design@beta
        penalty=.5*reg*np.dot(beta[1:],beta[1:])
        loss=np.logaddexp(0,z).sum()-y@z+penalty
        gradient=design.T@(expit(z)-y)
        gradient[1:]+=reg*beta[1:]
        return loss,gradient
    sol=minimize(objective,np.zeros(design.shape[1]),jac=True,method="L-BFGS-B")
    if not sol.success:
        raise RuntimeError(f"Logistic training failed: {sol.message}")
    return {"weights":sol.x.tolist(),"fill":fill.tolist(),
            "mean":mean.tolist(),"std":std.tolist(),
            "features":FEATURES,"reg":reg}

def predict(model, frame):
    xdf=raw_features(frame)
    fill=pd.Series(model["fill"],index=FEATURES)
    x=xdf.fillna(fill).to_numpy()
    norm=(x-np.asarray(model["mean"]))/np.asarray(model["std"])
    logits=np.c_[np.ones(len(norm)),norm]@np.asarray(model["weights"])
    return np.clip(expit(logits),1e-5,1-1e-5)

def eligible_history(all_games):
    return all_games[
        all_games["completed"] &
        all_games["home_win"].notna() &
        (all_games["season"]<=2025)
    ].copy()

def validate(all_games):
    historical=eligible_history(all_games)
    rows=[]
    metrics=[]
    for year in EVAL_YEARS:
        train=historical[(historical.season>=TRAIN_START)&(historical.season<year)]
        test=historical[historical.season==year].copy()
        if len(train)<100 or len(test)<100:
            continue
        fitted=fit_model(train)
        test["independent_prob"]=predict(fitted,test)
        test=test[test["market_prob"].between(.01,.99)].copy()
        if len(test)<100:
            continue
        for name,col in (("market","market_prob"),("independent_football","independent_prob")):
            metrics.append({"season":year,"method":name,**evaluate(test,test[col].to_numpy())})
        rows.append(test[[
            "game_id","season","week","home_team","away_team",
            "home_win","market_prob","independent_prob"
        ]])
    if not rows:
        raise ValueError("Missing sufficient historical scores and odds")
    predictions=pd.concat(rows,ignore_index=True)
    year_stats=pd.DataFrame(metrics)
    totals={}
    for label,col in (("market","market_prob"),("independent_football","independent_prob")):
        totals[label]=evaluate(predictions,predictions[col].to_numpy())
    diffs=year_stats.pivot(index="season",columns="method",values="brier")
    good_years=int((diffs["independent_football"]<diffs["market"]).sum())
    improves=(totals["market"]["brier"]-totals["independent_football"]["brier"])
    approved=(
        len(predictions)>=GATE_MIN_GAMES
        and good_years>=GATE_MIN_GOOD_YEARS
        and improves>=GATE_MIN_IMPROVEMENT
        and totals["independent_football"]["logloss"]<totals["market"]["logloss"]
    )
    gate={
        "historical_candidate_passes_predeclared_thresholds":bool(approved),
        "test_games":len(predictions),
        "brier_improvement_over_market":round(improves,6),
        "better_seasons":good_years,
        "required_better_seasons":GATE_MIN_GOOD_YEARS,
        "min_brier_improvement":GATE_MIN_IMPROVEMENT,
        "important_caveat":"2025 has been examined during earlier model development; no genuinely untouched confirmation yet.",
        "deployment_permission":"NO_AUTOMATIC_PROMOTION",
    }
    return predictions,year_stats,totals,gate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",default="/content/drive/MyDrive/NFL_Betting_Data")
    parser.add_argument("--output-dir",default=None)
    args=parser.parse_args()
    folder=Path(args.data_dir)
    schedule=folder/"schedules.parquet"
    if not schedule.is_file():
        raise SystemExit("Cannot find schedules.parquet. Mount Google Drive first.")
    games=to_game_frame(pd.read_parquet(schedule))
    teamstats=load_stats(folder/"team_stats.parquet")
    full=build_pregame_features(games,teamstats)
    preds,years,totals,gate=validate(full)
    out=Path(args.output_dir) if args.output_dir else folder/"model12_independent_candidate"
    out.mkdir(parents=True,exist_ok=True)
    preds.to_csv(out/"heldout_predictions.csv",index=False)
    years.to_csv(out/"heldout_metrics.csv",index=False)
    with (out/"validation_gate.json").open("w") as handle:
        json.dump(gate,handle,indent=2)
    print("\nMODEL 12 — FOOTBALL-ONLY PROBABILITY CANDIDATE")
    print("No sportsbook odds were features.")
    print(years.round(4).to_string(index=False))
    print("\nPOOLED")
    for method,metric in totals.items():
        print(method, {k:round(float(v),5) for k,v in metric.items()})
    print("\nPREDECLARED VALIDATION GATE:", "PASS (RESEARCH ONLY)" if gate["historical_candidate_passes_predeclared_thresholds"] else "FAIL")
    print("Detailed gate:",gate)
    print("\nNo live forecast exported or ingested into Model 11.")
    print("No historic season here constitutes a genuinely new untouched prospective test.")
    print("Output:",out)

if __name__=="__main__":
    main()
