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
EXTRA=["near_kickoff_utc","near_kickoff_prob","market_shift_pp",
       "same_book_near_kickoff_odds","same_book_near_kickoff_utc",
       "same_book_implied_shift_pp","result","paper_profit_per_unit","candidate_won",
       "power_reference_prob","power_apparent_ev","power_reference_books"]
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

def power_novig(home_odds,away_odds):
    """Return home probability using the two-way power margin method."""
    qh,qa=implied(home_odds),implied(away_odds)
    total=qh+qa
    if abs(total-1.0)<1e-12:
        return qh
    if total>1:
        lo,hi=1.0,2.0
        while qh**hi+qa**hi>1.0 and hi<128.0:
            hi*=2
    else:
        lo,hi=0.0,1.0
    for _ in range(80):
        mid=(lo+hi)/2
        if qh**mid+qa**mid>1.0:
            lo=mid
        else:
            hi=mid
    exponent=(lo+hi)/2
    probability=qh**exponent
    if not 0<probability<1:
        raise ValueError("Power no-vig probability outside 0-1")
    return probability

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
        # Separate same-sportsbook comparison: a meaningful pricing benchmark
        # requires the same selection at the same bookmaker near kickoff.
        key=row["book_key"]
        book_snapshots=[t for t in candidates if key in t[2]]
        same_book=book_snapshots[-1] if book_snapshots else None
        side=row["selected_side"]
        final_odds=(
            same_book[2][key]["home_odds" if side=="HOME" else "away_odds"]
            if same_book else None
        )
        implied_shift=(
            100*(implied(final_odds)-implied(row["offered_odds"]))
            if final_odds is not None else None
        )
        p=(close[1] if side=="HOME" else 1-close[1]) if close else None
        original=float(row["reference_prob"])
        shift=100*(p-original) if p is not None else None
        winner=results.get(event) if now>kickoff else None
        if winner not in (row["home_team"],row["away_team"]):winner=None
        won=(winner==row["home_team"] if side=="HOME" else winner==row["away_team"]) if winner else None
        profit=(profit_if_win(row["offered_odds"]) if won else -1) if won is not None else None

        # Supplemental sensitivity only: apply POWER_V1 to the exact same
        # frozen timestamp and other-book set. This never changes/reselects picks.
        power_reference=None
        power_ev=None
        power_books=0
        frozen_snapshot=next(
            (item for item in qualified_snapshots(quotes.get(event,{})) if item[0]==frozen),
            None
        )
        if frozen_snapshot and key in frozen_snapshot[2]:
            other_power=[power_novig(q["home_odds"],q["away_odds"])
                         for book_key,q in frozen_snapshot[2].items()
                         if book_key!=key]
            power_books=len(other_power)
            if power_books>=MIN_OTHER_BOOKS:
                power_home=statistics.median(other_power)
                power_reference=power_home if side=="HOME" else 1-power_home
                power_ev=power_reference*(1+profit_if_win(row["offered_odds"]))-1

        rows.append({**row,
            "near_kickoff_utc":close[0].isoformat() if close else "",
            "near_kickoff_prob":f"{p:.6f}" if p is not None else "",
            "market_shift_pp":f"{shift:+.3f}" if shift is not None else "",
            "same_book_near_kickoff_odds":int(final_odds) if final_odds is not None else "",
            "same_book_near_kickoff_utc":same_book[0].isoformat() if same_book else "",
            "same_book_implied_shift_pp":f"{implied_shift:+.3f}" if implied_shift is not None else "",
            "result":"VERIFIED_FINAL" if winner else "PENDING",
            "paper_profit_per_unit":f"{profit:.4f}" if profit is not None else "",
            "candidate_won":int(won) if won is not None else "",
            "power_reference_prob":f"{power_reference:.8f}" if power_reference is not None else "",
            "power_apparent_ev":f"{power_ev:.6f}" if power_ev is not None else "",
            "power_reference_books":power_books})
    return sorted(rows,key=lambda r:(r["kickoff_utc"],r["event_id"]))

def report(rows,new,now):
    DASH.parent.mkdir(exist_ok=True)
    with AUDIT.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS+EXTRA)
        writer.writeheader()
        writer.writerows(rows)
    settled=[r for r in rows if r["result"]=="VERIFIED_FINAL"]
    with_close=[r for r in rows if r["near_kickoff_utc"]]
    same_book_close=[r for r in rows if r["same_book_near_kickoff_utc"]]
    lines=[
        "# Model 13 — Prospective Cross-Book Pricing Study","",
        f"Updated: `{now.isoformat()}`","",
        "> **NO VERIFIED +EV. PAPER RESEARCH ONLY.** Differences between sportsbooks are not independent probabilities.",
        "",
        f"- New frozen candidate observations: **{len(new)}**",
        f"- Total locked observations: **{len(rows)}**",
        f"- With near-kickoff reference: **{len(with_close)}**",
        f"- With same-book near-kickoff price: **{len(same_book_close)}**",
        f"- With verified finals: **{len(settled)}**","",
        "## Precommitted selection rule","",
        "At least five fresh bookmakers, a snapshot observed within 15 minutes, kickoff at least 12 hours ahead, and a minimum 2% *indicative* return using the median no-vig probability of OTHER books. One candidate per event; highest apparent discrepancy wins. No backfilled picks, no post-result selection.","",
        "| Matchup | Side | Observed odds | Proportional ref. | Proportional indic. return | Power ref. | Power indic. return | Market shift | Same-book shift | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in rows:
        power_ref=(f"{100*float(r['power_reference_prob']):.2f}%"
                   if r["power_reference_prob"] else "—")
        power_ev=(f"{100*float(r['power_apparent_ev']):+.2f}%"
                  if r["power_apparent_ev"] else "—")
        lines.append(
            f"| {r['away_team']} @ {r['home_team']} | {r['selected_side']} | "
            f"{r['book']} ({int(r['offered_odds']):+d}) | "
            f"{100*float(r['reference_prob']):.2f}% | "
            f"{100*float(r['apparent_ev']):+.2f}% | {power_ref} | {power_ev} | "
            f"{r['market_shift_pp']+' pp' if r['market_shift_pp'] else '—'} | "
            f"{r['same_book_implied_shift_pp']+' pp' if r['same_book_implied_shift_pp'] else '—'} | "
            f"{r['result']} |"
        )
    if not rows:
        lines.append("| No pregame candidates yet | — | — | — | — | — | — | — | — | — |")
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
        "- Same-book shift compares implied break-even probability for the EXACT frozen bookmaker and side; a positive shift means the earlier offered price was better (not a guaranteed edge).",
        "- No money is wagered; all selections and wins/losses are hypothetical.",
        "- Results are matched against verified full-team identities and kickoff, not inferred from prices.",
        "- Injury information is recorded separately and is NOT an unvalidated betting signal.",
        "- POWER_V1 is a supplementary same-snapshot sensitivity using the exact frozen other-book set; the proportional method and original 2% threshold alone determine selections.",
        "- Neither vig-removal method is an independent probability model or proof of executable value.",""])
    DASH.write_text("\n".join(lines),encoding="utf8")
    print(f"Model 13: {len(new)} new, {len(rows)} frozen, {len(settled)} settled; NO VERIFIED +EV")

def main(now=None):
    now=now or datetime.now(timezone.utc)
    quotes,_,_=load_quotes()
    new=choose_candidates(quotes,read_csv(LEDGER),now)
    rows=evaluate(read_csv(LEDGER),quotes,load_results(),now)
    report(rows,new,now)

if __name__=="__main__":main()
