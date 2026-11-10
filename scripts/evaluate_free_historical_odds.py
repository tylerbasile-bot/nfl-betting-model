#!/usr/bin/env python3
"""Evaluate historical free-sample candidates against confirmed ESPN finals.

Separate from prospective Model 13: no edits to frozen picks.
Exact home/away names and kickoff <= 6 hours, completed STATUS_FINAL only.
Output is a descriptive, selection-biased tiny sample; not evidence of +EV.
"""
import argparse
import csv
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError,URLError

from collect_results import get_scoreboard, parse_final_event, parse_time

FIELDS=["game_id","away","home","kickoff_utc","selection_utc","selected_side",
        "book","offered_odds","reference_prob","apparent_ev",
        "outcome_status","home_score","away_score","selected_team","won",
        "paper_profit_per_unit","score_source","score_event_id"]

def selected_team(row):
    side=(row.get("selected_side") or "").upper()
    if side=="HOME":return row["home"]
    if side=="AWAY":return row["away"]
    raise ValueError(f"Invalid selected_side: {side}")

def moneyline_profit(odds):
    odds=float(odds)
    if odds==0: raise ValueError("Zero moneyline")
    return odds/100 if odds>0 else 100/(-odds)

def match_candidate(row, dates, now):
    kickoff=parse_time(row["kickoff_utc"])
    if kickoff >= now:
        return ("FUTURE_GAME",None)
    found={}
    for offset in (-1,0,1):
        date=(kickoff+timedelta(days=offset)).date()
        for event in dates.get(date,{}).get("events",[]):
            final=parse_final_event(event)
            if final and final["home_team"]==row["home"] and final["away_team"]==row["away"] and abs(final["event_time"]-kickoff)<=timedelta(hours=6):
                found[final["espn_id"]]=final
    if len(found)>1:return ("AMBIGUOUS_MATCH",None)
    if not found:return ("NO_VERIFIED_FINAL",None)
    return ("FINAL",next(iter(found.values())))

def evaluate(rows,scoreboards,now):
    output=[]
    for row in rows:
        status,final=match_candidate(row,scoreboards,now)
        side=selected_team(row)
        base={k:row.get(k,"") for k in ("game_id","away","home","kickoff_utc","selection_utc",
                                        "selected_side","book","offered_odds","reference_prob","apparent_ev")}
        result={**base,"outcome_status":status,"home_score":"","away_score":"",
                "selected_team":side,"won":"","paper_profit_per_unit":"",
                "score_source":"","score_event_id":""}
        if status=="FINAL":
            won=(final["winner"]==side)
            result.update(home_score=final["home_score"],away_score=final["away_score"],
                          won=int(won),paper_profit_per_unit=moneyline_profit(row["offered_odds"]) if won else -1.0,
                          score_source="ESPN public scoreboard",score_event_id=final["espn_id"])
        output.append(result)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--candidates",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/model13_sample/historical_model13_sample_candidates.csv")
    parser.add_argument("--outdir",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/model13_sample")
    args=parser.parse_args()
    path=Path(args.candidates)
    if not path.exists():raise SystemExit(f"Candidate CSV not found: {path}")
    with path.open(newline="",encoding="utf-8") as handle:
        candidates=list(csv.DictReader(handle))
    if not candidates:
        print("No historical selections: no outcomes to evaluate.")
        return
    now=datetime.now(timezone.utc)
    dates=set()
    for row in candidates:
        kickoff=parse_time(row["kickoff_utc"])
        if kickoff>=now:continue
        for delta in (-1,0,1):
            dates.add((kickoff+timedelta(days=delta)).date())
    scoreboards={}
    # Avoid silent partial result when a provider request fails.
    try:
        for day in sorted(dates):
            scoreboards[day]=get_scoreboard(day)
    except (OSError,HTTPError,URLError,TimeoutError,ValueError) as exc:
        raise SystemExit(f"ESPN score lookup failed ({type(exc).__name__}); no evaluation file written.") from None
    outcomes=evaluate(candidates,scoreboards,now)
    out=Path(args.outdir)
    out.mkdir(parents=True,exist_ok=True)
    dest=out/"historical_model13_outcomes.csv"
    with dest.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(outcomes)
    settled=[r for r in outcomes if r["outcome_status"]=="FINAL"]
    wins=sum(int(r["won"]) for r in settled)
    status_counts={}
    for row in outcomes:status_counts[row["outcome_status"]]=status_counts.get(row["outcome_status"],0)+1
    lines=["# Historical Model 13 — free sample outcomes","",
           "> Descriptive historical paper replay. NOT a proven betting edge. Not an independent prospective test.","",
           f"- Historical candidates: **{len(outcomes)}**",
           f"- Confirmed, matched finals: **{len(settled)}**",
           f"- Unmatched, tied, not-yet-final, or future games: **{len(outcomes)-len(settled)}**",
           ""]
    for status,count in sorted(status_counts.items()):
        lines.append(f"- {status}: **{count}**")
    lines.append("")
    if settled:
        roi=statistics.mean(float(r["paper_profit_per_unit"]) for r in settled)
        lines+= [
            f"- Historical paper wins: **{wins}/{len(settled)}**",
            f"- Hypothetical flat-one-unit ROI on matched finals: **{roi:+.2%}**",
            f"- Total hypothetical profit in units: **{sum(float(r['paper_profit_per_unit']) for r in settled):+.3f}**",
            "",
            "**Caution:** Small convenience sample; retrospective selection, correlated sportsbook prices, unverifiable execution, and unmatched games make ROI unstable and potentially misleading.",
        ]
    else:
        lines.append("No verified games yet; ROI and win rate deliberately omitted.")
    lines+=["","Score source: ESPN public NFL scoreboard; only exact home/away, kickoff within six hours, completed status, and non-tied finals.","",
            "| Candidate | Book | Price | Final | Outcome |",
            "|---|---|---:|---|---|"]
    for row in outcomes:
        result=(f"{row['away_score']}–{row['home_score']}" if row["outcome_status"]=="FINAL" else "—")
        lines.append(f"| {row['away']} @ {row['home']} — {row['selected_side']} | {row['book']} | {row['offered_odds']} | {result} | {row['outcome_status']} |")
    (out/"historical_model13_outcomes.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved {dest}")

if __name__=="__main__":
    main()
