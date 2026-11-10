#!/usr/bin/env python3
"""Model 14: historical closing-market + PRE-WEEK NFL EPA probability experiment.

Separate from immutable prospective Model 13. Uses official nflverse game scores
and historical *closing* moneylines from cached schedules; these prices are NOT
assumed to be known at an early-week selection time. Never outputs wagers/ROI.

Fixed training 2015-2021, validation 2022-2023, later historical test 2024-2025.
Market-only calibration and market+football models trained on identical rows.
No model selection/tuning on evaluation data; all metrics on paired same games.
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

from evaluate_historical_epa_probabilities import (
    FEATURE_COLS, normalize_data, TRAIN, VALID, TEST
)

ROOT="/content/drive/MyDrive/NFL_Betting_Data/historical_matchups"
OUTPUT_COLUMNS=["season","week","game_id","home_team","away_team",
                "home_win","split","home_score","away_score",
                "home_moneyline","away_moneyline",
                "market_close_no_vig_home_prob","market_logit",
                "market_calibrated_prob","model14_combined_prob",
                "market_brier","market_calibrated_brier","model14_combined_brier",
                "market_logloss","market_calibrated_logloss","model14_combined_logloss",
                "model14_minus_market_brier","model14_minus_market_logloss",
                "model14_minus_calibrated_market_brier"]

def prepare(features,schedules):
    # Reuse strict 1:1 canonicalized game-ID + exact home/away identity checks,
    # chronology, tied-game exclusion, and 3-prior-games eligibility.
    df=normalize_data(features,schedules).copy()
    if not {"home_moneyline","away_moneyline"}.issubset(df.columns):
        raise ValueError("No paired closing moneyline columns in nflverse schedules; cannot build market model.")
    h=pd.to_numeric(df["home_moneyline"],errors="coerce")
    a=pd.to_numeric(df["away_moneyline"],errors="coerce")
    usable=(h.notna() & a.notna() & (h!=0) & (a!=0)
            & df["market_close_no_vig_home_prob"].between(0.00001,0.99999,inclusive="both"))
    df=df.loc[usable].copy()
    df["market_logit"]=np.log(df["market_close_no_vig_home_prob"]/
                              (1-df["market_close_no_vig_home_prob"]))
    if not np.isfinite(df["market_logit"]).all():
        raise ValueError("Nonfinite closing-market log odds")
    if df.duplicated(["season","week","game_id"]).any():
        raise ValueError("Duplicate game identifiers after filtering")
    return df.reset_index(drop=True)

def market_only_pipeline():
    # Fit probability calibration from past closing odds, not from future games.
    return Pipeline([("scale",StandardScaler()),
                     ("logit",LogisticRegression(C=1.0,max_iter=2000,random_state=14))])

def combined_pipeline():
    numeric=["market_logit",*FEATURE_COLS]
    prep=ColumnTransformer([("predictors",Pipeline([
        ("fill",SimpleImputer(strategy="median")),
        ("scale",StandardScaler())
    ]),numeric)],remainder="drop")
    return Pipeline([("preprocess",prep),
                     ("logit",LogisticRegression(C=1.0,max_iter=2000,random_state=14))])

def score(y,p):
    p=np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)
    y=np.asarray(y,dtype=int)
    brier=(p-y)**2
    logloss=-(y*np.log(p)+(1-y)*np.log(1-p))
    return brier,logloss

def fit_predict(df):
    train=df[df["split"]=="train"]
    if len(train)<30 or train["home_win"].nunique()!=2:
        raise ValueError("Insufficient valid historical training games for market model.")
    # Fixed features/regularization; no validation/test labels can change a fit.
    only=market_only_pipeline()
    full=combined_pipeline()
    only.fit(train[["market_logit"]],train["home_win"])
    full.fit(train[["market_logit",*FEATURE_COLS]],train["home_win"])
    out=df[["season","week","game_id","home_team","away_team","home_win",
            "split","home_score","away_score","home_moneyline",
            "away_moneyline","market_close_no_vig_home_prob","market_logit"]].copy()
    out["market_calibrated_prob"]=only.predict_proba(df[["market_logit"]])[:,1]
    out["model14_combined_prob"]=full.predict_proba(df[["market_logit",*FEATURE_COLS]])[:,1]
    for name,col in [("market","market_close_no_vig_home_prob"),
                     ("market_calibrated","market_calibrated_prob"),
                     ("model14_combined","model14_combined_prob")]:
        brier,ll=score(out["home_win"],out[col])
        out[name+"_brier"]=brier
        out[name+"_logloss"]=ll
    out["model14_minus_market_brier"]=out["model14_combined_brier"]-out["market_brier"]
    out["model14_minus_market_logloss"]=out["model14_combined_logloss"]-out["market_logloss"]
    out["model14_minus_calibrated_market_brier"]=(out["model14_combined_brier"]-
                                                  out["market_calibrated_brier"])
    return out.reset_index(drop=True),only,full

def number(value):return f"{value:.5f}"

def report(out,eligible_before_market):
    lines=["# Model 14 — Closing Market + Pregame Football Efficiency",
        "",
        "> **HISTORICAL RESEARCH ONLY. NO VALIDATED +EV, NO REAL BETS, NO LIVE MODEL 14 PICKS.**",
        "",
        "## Study protocol","",
        "- Models fitted on 2015–2021; development check 2022–2023; later historical evaluation 2024–2025.",
        "- All models evaluate *exactly the same games* within each split, with both sportsbook moneylines available.",
        "- Model 14 predictors: closing-market logit plus pre-week EPA, defense, rolling form, matchup and ranking features.",
        "- Comparators: raw de-vigged closing-market probability; a market-only, training-calibrated logistic regression.",
        "- Logistic regression C=1.0, fixed features; imputation/scaling fit on training observations only.",
        "- Season weeks with fewer than three prior games per team and tied games are excluded.",
        "- Closing odds were **not known at an early-week selection timestamp**. This is a closing-market *conditional experiment*, not a bettable pregame forecast.",
        "- nflverse closing moneylines are offered without per-bookside executable timestamps or stake limits.",
        "- 2024–2025 have appeared in prior project analyses; chronological test does not mean scientifically untouched.",
        "",
        "## Paired predictive accuracy (lower is better)","",
        "| Split | Games | Raw market Brier | Calibrated-market Brier | Model 14 Brier | Model 14 minus raw market | Raw market log loss | Model 14 log loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for split in ["train","validation","historical_test"]:
        s=out[out["split"]==split]
        if s.empty:continue
        lines.append(f"| {split} | {len(s)} | {s['market_brier'].mean():.5f} | "
                     f"{s['market_calibrated_brier'].mean():.5f} | "
                     f"{s['model14_combined_brier'].mean():.5f} | "
                     f"{s['model14_minus_market_brier'].mean():+.5f} | "
                     f"{s['market_logloss'].mean():.5f} | "
                     f"{s['model14_combined_logloss'].mean():.5f} |")
    lines+=["","## Later historical test: individual seasons","",
            "| Season | Games | Raw market Brier | Market-only calibrated Brier | Model 14 Brier | Model 14 minus raw market |",
            "|---|---:|---:|---:|---:|---:|"]
    for yr in TEST:
        s=out[out["season"]==yr]
        if s.empty:continue
        lines.append(f"| {yr} | {len(s)} | {s['market_brier'].mean():.5f} | "
                     f"{s['market_calibrated_brier'].mean():.5f} | "
                     f"{s['model14_combined_brier'].mean():.5f} | "
                     f"{s['model14_minus_market_brier'].mean():+.5f} |")
    test=out[out["split"]=="historical_test"]
    lines+=["","## Historical test reliability (descriptive)",""]
    if not test.empty:
        lines+=["| Predicted probability bucket | Games | Model 14 predicted mean | Actual home win rate |",
                "|---|---:|---:|---:|"]
        for lo,hi in [(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000001)]:
            b=test[test["model14_combined_prob"].between(lo,hi,inclusive="left")]
            if b.empty:continue
            lines.append(f"| {lo:.0%}–{min(hi,1):.0%} | {len(b)} | "
                         f"{b['model14_combined_prob'].mean():.1%} | {b['home_win'].mean():.1%} |")
        better=test["model14_minus_market_brier"].mean()<0
        lines+=["",
            f"- Model 14 versus raw closing market on 2024–25 Brier: **{'lower (better)' if better else 'not lower (no improvement)'}**.",
            f"- Model 14 versus calibrated-market-only on 2024–25 Brier: **{test['model14_minus_calibrated_market_brier'].mean():+.5f}** (negative favors football features)."]
    else:
        lines.append("- No test observations. No out-of-sample conclusion.")
    total_pre=sum(eligible_before_market.values())
    total_model=len(out)
    lines+=["","## Coverage and caveats","",
            f"- Eligible game outcomes after predeclared football eligibility and ties exclusions: **{total_pre}**.",
            f"- Complete two-sided closing-market price records evaluated: **{total_model}**.",
            f"- Games omitted for incomplete prices: **{total_pre-total_model}**.",
            "- Brier and log loss assess predictions, not wager returns; apparent improvements do not establish EV.",
            "- This design cannot evaluate whether a Model 14 price was bettable before kickoff, nor whether it beat an *early* market.",
            "- Avoid selection/tuning based on the 2024–25 scores; require fresh prospective prices and a new independent forward test.",
            "- Live prospective Model 13 and its original frozen ledger are unchanged.",
            ""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features",default=f"{ROOT}/pregame_matchup_features.csv")
    parser.add_argument("--schedules",default=f"{ROOT}/games.csv")
    parser.add_argument("--outdir",default=ROOT)
    args=parser.parse_args()
    features=pd.read_csv(args.features)
    schedules=pd.read_csv(args.schedules)
    eligible=normalize_data(features,schedules)
    before=eligible["split"].value_counts().to_dict()
    df=prepare(features,schedules)
    out,_,_=fit_predict(df)
    dest=Path(args.outdir);dest.mkdir(parents=True,exist_ok=True)
    csv_path=dest/"model14_market_plus_epa_predictions.csv"
    md_path=dest/"model14_market_plus_epa_report.md"
    out.to_csv(csv_path,index=False)
    text=report(out,before)
    md_path.write_text(text,encoding="utf-8")
    print(text)
    print("Saved:",csv_path)
    print("Saved:",md_path)

if __name__=="__main__":
    main()
