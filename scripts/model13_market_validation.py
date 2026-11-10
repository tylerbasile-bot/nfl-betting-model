#!/usr/bin/env python3
"""Prospective Model 13 market-validation tracker. Read-only toward frozen ledger.

Uses valid source odds snapshots (book update <=15 min old), never prices from
after kickoff. Reports last observed and <=3h-before-kickoff prices distinctly.
Settles only independently verified Model 13 outcomes. Not executable CLV.
"""
import csv
import statistics
from datetime import datetime,timedelta,timezone
from pathlib import Path
from model9 import load_quotes
from model13 import LEDGER,implied,profit_if_win
from collect_model13_results import RESULTS

OUTCSV=Path("reports/model13_market_validation.csv")
OUTMD=Path("reports/model13_market_validation.md")
FRESHNESS=timedelta(minutes=15)
NEAR=timedelta(hours=3)
FIELDS=["event_id","kickoff_utc","matchup","side","sportsbook","frozen_odds",
        "frozen_utc","lead_hours","frozen_reference_prob","frozen_apparent_ev",
        "latest_market_utc","latest_market_prob","latest_market_shift_pp",
        "latest_market_lead_hours","latest_same_book_utc","latest_same_book_odds",
        "latest_same_book_shift_pp","near_kickoff_utc","near_kickoff_market_prob",
        "near_kickoff_market_shift_pp","near_kickoff_same_book_utc",
        "near_kickoff_same_book_odds","near_kickoff_same_book_shift_pp",
        "verified_result","candidate_won","paper_profit_per_unit",
        "snapshot_quality_note"]

def read(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def fmt_time(ts):
    return ts.isoformat() if ts is not None else ""

def fmt_num(value,digits=3):
    return f"{value:.{digits}f}" if value is not None else ""

def good_snapshots(times,kickoff,frozen):
    """Return ordered, source-fresh group observations AFTER original freeze."""
    out=[]
    for stamp,books in times.items():
        try: captured=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        except (ValueError,TypeError):continue
        if not (frozen<captured<kickoff):continue
        fresh={}
        for key,q in books.items():
            updated=q.get("updated")
            if updated is None or not timedelta(0)<=captured-updated<=FRESHNESS:
                continue
            if q.get("captured")!=captured:continue
            fresh[key]=q
        if len(fresh)<5:continue
        p=statistics.median(v["prob"] for v in fresh.values())
        out.append((captured,p,fresh))
    return sorted(out,key=lambda item:item[0])

def choose_latest(snaps):
    return snaps[-1] if snaps else None

def choose_same(snaps,book_key):
    return next(((t,p,quotes[book_key]) for t,p,quotes in reversed(snaps)
                 if book_key in quotes),None)

def validate_result(row,existing,now):
    kickoff=datetime.fromisoformat(row["kickoff_utc"].replace("Z","+00:00"))
    if now<=kickoff:return None
    matches=[r for r in existing if r.get("event_id")==row["event_id"]
             and r.get("status")=="final"
             and r.get("winner") in (row["home_team"],row["away_team"])
             and r.get("source")=="espn_scoreboard"
             and r.get("source_event_id")]
    if len(matches)!=1:return None
    return matches[0]

def build_rows(frozen_rows,quotes,verified_rows,now):
    output=[]
    for row in frozen_rows:
        kick=datetime.fromisoformat(row["kickoff_utc"].replace("Z","+00:00"))
        freeze=datetime.fromisoformat(row["selection_utc"].replace("Z","+00:00"))
        key=row["book_key"]
        side=row["selected_side"]
        original=float(row["reference_prob"])
        odds=float(row["offered_odds"])
        snaps=good_snapshots(quotes.get(row["event_id"],{}),kick,freeze)
        latest=choose_latest(snaps)
        near=choose_latest([q for q in snaps if kick-q[0]<=NEAR])
        same=choose_same(snaps,key)
        near_same=choose_same([q for q in snaps if kick-q[0]<=NEAR],key)

        def side_probability(q):
            return (q[1] if side=="HOME" else 1-q[1]) if q else None

        def market_shift(q):
            p=side_probability(q)
            return 100*(p-original) if p is not None else None

        def same_odds(q):
            if not q:return None
            return float(q[2]["home_odds"] if side=="HOME" else q[2]["away_odds"])

        def same_shift(q):
            price=same_odds(q)
            return 100*(implied(price)-implied(odds)) if price is not None else None

        settled=validate_result(row,verified_rows,now)
        won=None
        paper=None
        if settled:
            winner=settled["winner"]
            won=int(winner==(row["home_team"] if side=="HOME" else row["away_team"]))
            paper=profit_if_win(odds) if won else -1.0
        # This is a quality descriptor, not evidence of a real closing price.
        note=("NO_POST_FREEZE_FIVE_FRESH_BOOKS" if not latest else
              "NO_NEAR_KICKOFF_FIVE_FRESH_BOOKS" if not near else
              "NEAR_KICKOFF_PROXY_NOT_VERIFIED_CLOSE")
        output.append({
            "event_id":row["event_id"],"kickoff_utc":row["kickoff_utc"],
            "matchup":f"{row['away_team']} @ {row['home_team']}",
            "side":side,"sportsbook":row["book"],"frozen_odds":row["offered_odds"],
            "frozen_utc":row["selection_utc"],
            "lead_hours":fmt_num((kick-freeze).total_seconds()/3600,2),
            "frozen_reference_prob":row["reference_prob"],
            "frozen_apparent_ev":row["apparent_ev"],
            "latest_market_utc":fmt_time(latest[0]) if latest else "",
            "latest_market_prob":fmt_num(side_probability(latest),6),
            "latest_market_shift_pp":fmt_num(market_shift(latest)),
            "latest_market_lead_hours":fmt_num((kick-latest[0]).total_seconds()/3600,2) if latest else "",
            "latest_same_book_utc":fmt_time(same[0]) if same else "",
            "latest_same_book_odds":fmt_num(same_odds(same),0),
            "latest_same_book_shift_pp":fmt_num(same_shift(same)),
            "near_kickoff_utc":fmt_time(near[0]) if near else "",
            "near_kickoff_market_prob":fmt_num(side_probability(near),6),
            "near_kickoff_market_shift_pp":fmt_num(market_shift(near)),
            "near_kickoff_same_book_utc":fmt_time(near_same[0]) if near_same else "",
            "near_kickoff_same_book_odds":fmt_num(same_odds(near_same),0),
            "near_kickoff_same_book_shift_pp":fmt_num(same_shift(near_same)),
            "verified_result":"VERIFIED_FINAL" if settled else "PENDING_OR_UNVERIFIED",
            "candidate_won":won if won is not None else "",
            "paper_profit_per_unit":fmt_num(paper,4),
            "snapshot_quality_note":note,
        })
    return sorted(output,key=lambda r:(r["kickoff_utc"],r["event_id"]))

def render(rows,now):
    finals=[r for r in rows if r["verified_result"]=="VERIFIED_FINAL"]
    latest=[r for r in rows if r["latest_market_utc"]]
    near=[r for r in rows if r["near_kickoff_utc"]]
    same=[r for r in rows if r["latest_same_book_utc"]]
    same_near=[r for r in rows if r["near_kickoff_same_book_utc"]]
    lines=["# Model 13 — Prospective Market Validation","",
        f"Updated: `{now.isoformat()}`","",
        "> **PAPER RESEARCH ONLY. NO VERIFIED +EV.** Captured prices may not have been executable.",
        "",
        "## Tracking coverage","",
        f"- Frozen prospective selections: **{len(rows)}**",
        f"- With any later five-book fresh market observation: **{len(latest)}**",
        f"- With later selected-sportsbook observation: **{len(same)}**",
        f"- With five-book observation within 3h of kickoff: **{len(near)}**",
        f"- With selected-sportsbook observation within 3h of kickoff: **{len(same_near)}**",
        f"- With independently verified final outcomes: **{len(finals)}**","",
        "## Frozen selections and follow-up","",
        "| Game | Pick | Frozen offer | Last observed market shift | Near-kickoff market shift | Near-kickoff same-book shift | Verified outcome |",
        "|---|---|---:|---:|---:|---:|---|"]
    for r in rows:
        last=f"{float(r['latest_market_shift_pp']):+.3f} pp" if r["latest_market_shift_pp"]!="" else "—"
        nearval=f"{float(r['near_kickoff_market_shift_pp']):+.3f} pp" if r["near_kickoff_market_shift_pp"]!="" else "—"
        sameval=f"{float(r['near_kickoff_same_book_shift_pp']):+.3f} pp" if r["near_kickoff_same_book_shift_pp"]!="" else "—"
        outcome=("WIN" if r["candidate_won"]==1 else "LOSS") if r["verified_result"]=="VERIFIED_FINAL" else "PENDING"
        lines.append(f"| {r['matchup']} | {r['side']} · {r['sportsbook']} | {r['frozen_odds']} | {last} | {nearval} | {sameval} | {outcome} |")
    if not rows:lines.append("| No prospective selections yet | — | — | — | — | — | — |")
    lines+=["","## Descriptive paper outcomes",""]
    if finals:
        total=sum(float(r["paper_profit_per_unit"]) for r in finals)
        wins=sum(int(r["candidate_won"]) for r in finals)
        lines+=[f"- Settled selections: **{len(finals)}**, wins: **{wins}**",
                f"- Flat-one-unit hypothetical profit: **{total:+.3f} units**",
                f"- Flat-one-unit ROI on verified finals only: **{total/len(finals):+.2%}**"]
    else:lines+=["No independently verified finalized selections yet. ROI not reported."]
    lines+=["","## Audit rules and limitations","",
        "- The frozen selection ledger is read-only. No historical rows are added.",
        "- Later observations require **at least five books** with book-specific reported last updates <=15 minutes before their scan timestamp.",
        "- Every comparison is strictly after the original selection and before kickoff.",
        "- **Last observed** is NOT called near-kickoff unless captured within three hours of kickoff.",
        "- Same-book comparisons use the exact frozen book key and selected team; a positive implied-probability shift indicates an earlier better offer, not verified CLV.",
        "- Model 13 finals are independently matched against completed ESPN games using exact home/away identities and kickoff proximity; unknowns are not treated as losses.",
        "- Final outcomes and paper returns are not sufficient to demonstrate expected value, fillability, or profitability.",
        "- Collection gaps and bookmaker timestamp granularity can prevent otherwise valid comparisons.",""]
    return "\n".join(lines)

def main():
    now=datetime.now(timezone.utc)
    quotes,_,_=load_quotes()
    rows=build_rows(read(LEDGER),quotes,read(RESULTS),now)
    OUTCSV.parent.mkdir(parents=True,exist_ok=True)
    with OUTCSV.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    OUTMD.write_text(render(rows,now),encoding="utf-8")
    print(f"Model 13 validation: {len(rows)} locked, {sum(r['verified_result']=='VERIFIED_FINAL' for r in rows)} verified, {sum(bool(r['near_kickoff_utc']) for r in rows)} near kickoff proxies")

if __name__=="__main__":main()
