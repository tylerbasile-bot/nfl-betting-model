#!/usr/bin/env python3
"""Fully scored strict-book replay and 72/48/24h historical timing sensitivity.

Reads private free Odds Gap CSV. Reselects from saved source snapshots using the
unchanged 5-book/2%-indicative/12h-lead rules; time-window analyses are labeled
post-hoc, and are NOT alterations to live Model 13.
Fetches ESPN scores independently for every candidate game/date. Fail closed if
a scoreboard request fails; never use the original 13-pick file as score source.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

from backtest_free_odds_gap import load_sample, pair_quotes, replay
from audit_historical_price_reliability import SPORTSBOOKS
from collect_results import get_scoreboard, parse_time
from evaluate_free_historical_odds import evaluate

WINDOWS=(72,48,24)
ALL_GROUP="ALL_VENUES"
STRICT_GROUP="STRICT_SPORTSBOOKS"

def in_window(pairs,hours):
    # At most H hours BEFORE kickoff, but still >=12h before kickoff.
    return pairs[(pairs["lead_hours"]>=12)&(pairs["lead_hours"]<=hours)].copy()

def create_scenarios(pairs):
    strict=pairs[pairs["book"].astype(str).str.lower().isin(SPORTSBOOKS)].copy()
    scenarios=[("STRICT_ALL_AVAILABLE",strict, "First qualifying instant at least 12h before kickoff (no upper limit)")]
    for hours in WINDOWS:
        scenarios.append((f"STRICT_WITHIN_{hours}H",in_window(strict,hours),
                          f"First qualifying instant 12–{hours}h before kickoff"))
        scenarios.append((f"ALL_VENUES_WITHIN_{hours}H",in_window(pairs,hours),
                          f"All-venue sensitivity, first qualifying instant 12–{hours}h before kickoff"))
    chosen=[]
    metrics=[]
    for name,frame,definition in scenarios:
        picks,stats=replay(frame)
        rows=picks.to_dict("records")
        for row in rows:
            row["scenario"]=name
        chosen.extend(rows)
        metrics.append({"scenario":name,"definition":definition,
                        "games_with_5_books":int(stats.get("games_with_5_books",0)),
                        "selected_games":len(rows),
                        "with_near_kickoff_reference":sum(bool(r.get("near_kickoff_utc","")) for r in rows)})
    return chosen,metrics

def dates_for(picks,now):
    days=set()
    for row in picks:
        kickoff=parse_time(row["kickoff_utc"])
        if kickoff>=now: continue
        for offset in (-1,0,1):
            days.add((kickoff+timedelta(days=offset)).date())
    return sorted(days)

def get_scoreboards(picks,now,provider=get_scoreboard):
    dates={}
    for day in dates_for(picks,now):
        dates[day]=provider(day)
    return dates

def score_scenarios(picks,scoreboards,now):
    # The validator verifies exact teams, kickoff within 6h, completed/tie
    # status. No blind joining of ESPN event IDs and bookmaker event IDs.
    evaluated=evaluate(picks,scoreboards,now)
    return [{**row, "scenario":pick["scenario"],
             "lead_hours":round((parse_time(pick["kickoff_utc"])-parse_time(pick["selection_utc"])).total_seconds()/3600,2)}
            for row,pick in zip(evaluated,picks)]

def summarize(metrics,scored):
    for m in metrics:
        group=[r for r in scored if r["scenario"]==m["scenario"]]
        finals=[r for r in group if r["outcome_status"]=="FINAL"]
        m["verified_finals"]=len(finals)
        m["unverified_or_pending"]=len(group)-len(finals)
        if group and len(finals)==len(group):
            m["wins"]=sum(int(r["won"]) for r in finals)
            m["profit_units"]=sum(float(r["paper_profit_per_unit"]) for r in finals)
            m["paper_roi"]=m["profit_units"]/len(finals)
        else:
            # Never call 7-of-8 score-matched selections an 8-pick ROI.
            m["wins"]=""
            m["profit_units"]=""
            m["paper_roi"]=""
    return metrics

def format_report(metrics):
    lines=[
        "# Historical Model 13 — Fully Checked Sportsbook Replay & Timing",
        "",
        "> **POST-HOC RESEARCH ONLY. NO VERIFIED +EV OR EXECUTABLE PROFIT CLAIM.**",
        "",
        "Each scenario freezes the earliest qualifying snapshot **inside its own explicitly defined window**, independently of the outcome. Requirements remain at least five two-sided, same-timestamp books; the median no-vig probability of the other books; indicative return >=2%; kickoff >=12h away.",
        "",
        "The strict scenarios allow only predeclared US sportsbook names in **both** the offers and reference prices. All-venue scenarios are comparators, not newly optimized models.",
        "",
        "A 72-hour window means selections from **72 to 12 hours before kickoff**; 48-hour = 48–12h; 24-hour = 24–12h. These are NOT disjoint bins and do not require a snapshot at exactly the 72/48/24-hour mark.",
        "",
        "| Scenario | Eligible games (>=5 books) | Picks | Verified finals | Missing | Wins | Paper ROI | Near-kickoff refs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in metrics:
        wins=str(r["wins"]) if r["wins"]!="" else "—"
        roi=f"{r['paper_roi']:+.2%}" if r["paper_roi"]!="" else "—"
        lines.append(f"| {r['scenario']} | {r['games_with_5_books']} | {r['selected_games']} | {r['verified_finals']} | {r['unverified_or_pending']} | {wins} | {roi} | {r['with_near_kickoff_reference']} |")
    lines+=["","## Limitations","",
        "- All results are **retrospective sensitivity checks** on one freely provided sample, not independent out-of-sample evidence.",
        "- Missing ESPN outcomes are left explicitly unmatched. ROI is suppressed unless **every pick in that scenario** has an unambiguous verified final.",
        "- Some windows have sparse/no near-kickoff data; a positive return cannot be interpreted as closing-line value.",
        "- Source scan timestamps do not prove bookmaker quote age or wager fillability.",
        "- An exchange can have a genuine quote but different fees, liquidity and accessibility.",
        "- The original 13 historical selections, their result files, and prospective Model 13 ledgers were NOT changed.",
        ""]
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser()
    root="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds"
    parser.add_argument("--odds",default=f"{root}/odds_gap_free_sample.csv")
    parser.add_argument("--outdir",default=f"{root}/model13_sample")
    args=parser.parse_args()
    if not Path(args.odds).is_file():
        raise SystemExit(f"Source sample missing: {args.odds}")
    _,ml=load_sample(args.odds)
    pairs=pair_quotes(ml)
    selections,metrics=create_scenarios(pairs)
    now=datetime.now(timezone.utc)
    try:
        scoreboards=get_scoreboards(selections,now)
    except (OSError,TimeoutError,ValueError) as exc:
        raise SystemExit(f"ESPN final-score request failed: {type(exc).__name__}; no report written.") from None
    scored=score_scenarios(selections,scoreboards,now)
    summarize(metrics,scored)
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    fields=["scenario","game_id","home","away","kickoff_utc","selection_utc","lead_hours",
            "selected_side","book","offered_odds","reference_prob","apparent_ev",
            "outcome_status","home_score","away_score","selected_team","won",
            "paper_profit_per_unit","score_source","score_event_id"]
    with (out/"historical_timing_scored_selections.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(scored)
    with (out/"historical_timing_summary.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(metrics[0]) if metrics else [])
        writer.writeheader()
        writer.writerows(metrics)
    report=format_report(metrics)
    (out/"historical_timing_report.md").write_text(report,encoding="utf-8")
    print(report)
    print(f"Saved three new files under {out}")

if __name__=="__main__":
    main()
