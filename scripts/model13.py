#!/usr/bin/env python3
"""Model 13: frozen cross-sportsbook price-discrepancy PAPER research.

Signals use only observed pregame quotes from the latest snapshot. Candidate
selection rules are fixed BEFORE results; no claims of true EV or betting advice.
"""
import csv
import math
import statistics
from datetime import datetime,timedelta,timezone
from pathlib import Path
from model9 import load_quotes,qualified_snapshots,load_results

LEDGER=Path("data/model13/frozen_price_candidates.csv")
DASH=Path("reports/model13_dashboard.md")
AUDIT=Path("reports/model13_audit.csv")
FIELDS=["event_id","kickoff_utc","home_team","away_team","selected_side","book","book_key",
        "offered_odds","selection_utc","reference_prob","break_even_prob",
        "apparent_ev","reference_books","research_status"]
EXTRA=["near_kickoff_utc","near_kickoff_prob","market_shift_pp","result",
       "paper_profit_per_unit","candidate_won"]
MIN_OTHER_BOOKS=4
MIN_INDICATIVE_EV=.02
MIN_LEAD=timedelta(hours=12)
MAX_AGE=timedelta(minutes=15)
NEAR_KICKOFF=timedelta(hours=3)

def read_csv(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf8") as f:return list(csv.DictReader(f))

def implied(odds):
    x=float(odds)
    if not x:raise ValueError("Zero odds")
    return -x/(100-x) if x<0 else 100/(100+x)

def profit_if_win(odds):
    x=float(odds)
    return x/100 if x>0 else 100/(-x)

def choose_candidates(quotes,existing,now):
    frozen={r["event_id"] for r in existing}
    new=[]
    for event,by_time in quotes.items():
        if event in frozen:continue
        snapshots=qualified_snapshots(by_time)
        if not snapshots:continue
        stamp,_,books,info=snapshots[-1]
        if not timedelta(0)<=now-stamp<=MAX_AGE:continue
        if info["kickoff"]-now<MIN_LEAD:continue
        possible=[]
        for book_key,quote in books.items():
            others=[q["prob"] for k,q in books.items() if k!=book_key]
            if len(others)<MIN_OTHER_BOOKS:continue
            other_home=statistics.median(others)
            for side in ("HOME","AWAY"):
                probability=other_home if side=="HOME" else 1-other_home
                odds=quote["home_odds"] if side=="HOME" else quote["away_odds"]
                ev=probability*(1+profit_if_win(odds))-1
                if ev>=MIN_INDICATIVE_EV:
                    possible.append((ev,side,book_key,quote,probability,odds,len(others)))
        if not possible:continue
        # Precommitted rule: select at most one observation per game,
        # the highest indicative discrepancy. No selection after seeing results.
        ev,side,key,quote,ref,odds,n=max(possible,key=lambda x:x[0])
        new.append({
            "event_id":event,"kickoff_utc":info["kickoff"].isoformat(),
            "home_team":info["home_team"],"away_team":info["away_team"],
            "selected_side":side,"book":quote["book_name"],"book_key":key,
            "offered_odds":odds,"selection_utc":stamp.isoformat(),
            "reference_prob":f"{ref:.8f}","break_even_prob":f"{implied(odds):.8f}",
            "apparent_ev":f"{ev:.6f}","reference_books":n,
            "research_status":"UNVERIFIED_MARKET_DISCREPANCY_ONLY"
        })
        frozen.add(event)
    if new:
        LEDGER.parent.mkdir(parents=True,exist_ok=True)
        with LEDGER.open("a",newline="",encoding="utf8") as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS)
            if f.tell()==0:writer.writeheader()
            writer.writerows(new)
    return new

def evaluate(locked,quotes,results,now):
    rows=[]
    for row in locked:
        event=row["event_id"]
        kickoff=datetime.fromisoformat(row["kickoff_utc"])
        frozen=datetime.fromisoformat(row["selection_utc"])
        candidates=[t for t in qualified_snapshots(quotes.get(event,{}))
                    if frozen<t[0]<kickoff and kickoff-t[0]<=NEAR_KICKOFF]
        close=candidates[-1] if candidates else None
        side=row["selected_side"]
        p=(close[1] if side=="HOME" else 1-close[1]) if close else None
        original=float(row["reference_prob"])
        shift=100*(p-original) if p is not None else None
        winner=results.get(event) if now>kickoff else None
        if winner not in (row["home_team"],row["away_team"]):winner=None
        won=(winner==row["home_team"] if side=="HOME" else winner==row["away_team"]) if winner else None
        profit=(profit_if_win(row["offered_odds"]) if won else -1) if won is not None else None
        rows.append({**row,
            "near_kickoff_utc":close[0].isoformat() if close else "",
            "near_kickoff_prob":f"{p:.6f}" if p is not None else "",
            "market_shift_pp":f"{shift:+.3f}" if shift is not None else "",
            "result":"VERIFIED_FINAL" if winner else "PENDING",
            "paper_profit_per_unit":f"{profit:.4f}" if profit is not None else "",
            "candidate_won":int(won) if won is not None else ""})
    return sorted(rows,key=lambda r:(r["kickoff_utc"],r["event_id"]))

def report(rows,new,now):
    DASH.parent.mkdir(exist_ok=True)
    with AUDIT.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS+EXTRA)
        writer.writeheader()
        writer.writerows(rows)
    settled=[r for r in rows if r["result"]=="VERIFIED_FINAL"]
    with_close=[r for r in rows if r["near_kickoff_utc"]]
    lines=[
        "# Model 13 — Prospective Cross-Book Pricing Study","",
        f"Updated: `{now.isoformat()}`","",
        "> **NO VERIFIED +EV. PAPER RESEARCH ONLY.** Differences between sportsbooks are not independent probabilities.",
        "",
        f"- New frozen candidate observations: **{len(new)}**",
        f"- Total locked observations: **{len(rows)}**",
        f"- With near-kickoff reference: **{len(with_close)}**",
        f"- With verified finals: **{len(settled)}**","",
        "## Precommitted selection rule","",
        "At least five fresh bookmakers, a snapshot observed within 15 minutes, kickoff at least 12 hours ahead, and a minimum 2% *indicative* return using the median no-vig probability of OTHER books. One candidate per event; highest apparent discrepancy wins. No backfilled picks, no post-result selection.","",
        "| Matchup | Side | Observed odds | Market reference | Indicative return | Near-kickoff shift | Status |",
        "|---|---|---|---:|---:|---:|---|"
    ]
    for r in rows:
        lines.append(
            f"| {r['away_team']} @ {r['home_team']} | {r['selected_side']} | "
            f"{r['book']} ({int(r['offered_odds']):+d}) | {100*float(r['reference_prob']):.2f}% | "
            f"{100*float(r['apparent_ev']):+.2f}% | "
            f"{r['market_shift_pp']+' pp' if r['market_shift_pp'] else '—'} | {r['result']} |"
        )
    if not rows:
        lines.append("| No pregame candidates yet | — | — | — | — | — | — |")
    lines.extend(["","## Outcome evaluation",""])
    if settled:
        roi=statistics.mean(float(r["paper_profit_per_unit"]) for r in settled)
        lines.append(f"- Hypothetical one-unit-per-selection ROI: **{roi:+.2%}** over {len(settled)} finalized selections (not actual executable returns).")
    else:
        lines.append("No settled paper candidates. No performance claim possible.")
    lines.extend(["",
        "## Interpretation and limitations","",
        "- Bookmakers' probabilities are correlated and often share information. Apparent EV is not proof of true EV.",
        "- Prices may be stale, restricted, inaccessible, or not executable at the logged timestamp.",
        "- A near-kickoff quote is only a proxy, not confirmed closing-line value.",
        "- No money is wagered; all selections and wins/losses are hypothetical.",
        "- Results are matched against verified full-team identities and kickoff, not inferred from prices.",
        "- Injury information is recorded separately and is NOT an unvalidated betting signal.",""])
    DASH.write_text("\n".join(lines),encoding="utf8")
    print(f"Model 13: {len(new)} new, {len(rows)} frozen, {len(settled)} settled; NO VERIFIED +EV")

def main(now=None):
    now=now or datetime.now(timezone.utc)
    quotes,_,_=load_quotes()
    new=choose_candidates(quotes,read_csv(LEDGER),now)
    rows=evaluate(read_csv(LEDGER),quotes,load_results(),now)
    report(rows,new,now)

if __name__=="__main__":main()
