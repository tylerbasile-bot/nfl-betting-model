#!/usr/bin/env python3
"""Model 13 Phase 2: precommitted prospective validation (NO new picks).

Reads immutable frozen candidates, market-validation CSV, verified results,
and optional MANUALLY verified execution observations. No data backfills.
Outputs aggregate diagnostics, selected-side calibration, and evidence gaps.
"""
import csv
import math
import statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

FROZEN=Path("data/model13/frozen_price_candidates.csv")
VALIDATION=Path("reports/model13_market_validation.csv")
RESULTS=Path("data/model13/verified_results.csv")
EXECUTION=Path("data/model13/execution_observations.csv")
REPORT=Path("reports/model13_phase2_validation.md")
DETAIL=Path("reports/model13_phase2_candidates.csv")
TARGET=100
DETAIL_FIELDS=[
    "event_id","matchup","selected_side","selection_utc","kickoff_utc",
    "book","frozen_price","reference_prob","break_even_prob","indicative_ev",
    "market_followup","same_book_followup","near_kickoff_reference","near_same_book",
    "market_shift_pp","same_book_implied_shift_pp",
    "verified_final","win","outcome_brier","outcome_logloss",
    "manual_execution_status","manual_execution_evidence","manual_net_price",
    "manual_effective_ev_proxy","data_quality_warning"
]
STATUSES={"UNREVIEWED","PRICE_CONFIRMED","PRICE_UNAVAILABLE","REGION_RESTRICTED",
          "LIMITED_LIQUIDITY","ACCOUNT_RESTRICTED","UNKNOWN"}
MANUAL_FIELDS=["event_id","checked_utc","book_key","selected_side","offered_odds_checked",
               "execution_status","max_stake_units","fees_per_unit","evidence_reference","notes"]

def rows(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def number(text):
    try:
        if text is None or str(text).strip()=="":return None
        x=float(text)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def probability_score(p,y):
    if p is None or not 0<p<1:return None,None
    return (p-y)**2,-(y*math.log(p)+(1-y)*math.log(1-p))

def execution_record(original,manual):
    valid=[]
    for item in manual:
        if item.get("event_id")!=original["event_id"]:continue
        status=item.get("execution_status","").strip().upper()
        if status not in STATUSES:continue
        if item.get("book_key","").strip().lower()!=original["book_key"].strip().lower():continue
        if item.get("selected_side","").strip().upper()!=original["selected_side"].upper():continue
        # Manual records must NOT overwrite historical offered odds.
        valid.append(item)
    # Most recent explicit check; never infer an executable bet from an API quote.
    valid.sort(key=lambda r:r.get("checked_utc",""))
    return valid[-1] if valid else None

def build(frozen,validation,finals,manual):
    by_validation={r["event_id"]:r for r in validation}
    unique_final={}
    for x in finals:
        if x.get("status")=="final" and x.get("source")=="espn_scoreboard":
            unique_final.setdefault(x.get("event_id"),[]).append(x)
    detail=[]
    for pick in frozen:
        v=by_validation.get(pick["event_id"],{})
        f=unique_final.get(pick["event_id"],[])
        selected=pick["home_team"] if pick["selected_side"]=="HOME" else pick["away_team"]
        verified=(len(f)==1 and f[0].get("winner") in (pick["home_team"],pick["away_team"])
                  and f[0].get("source_event_id"))
        won=int(f[0]["winner"]==selected) if verified else None
        p=number(pick.get("reference_prob"))
        brier,loss=probability_score(p,won) if won is not None else (None,None)
        manualrow=execution_record(pick,manual)
        status=manualrow.get("execution_status","UNREVIEWED").upper() if manualrow else "UNREVIEWED"
        evidence=manualrow.get("evidence_reference","") if manualrow else ""
        # No adjusted EV inference from a price check; original reference is unvalidated.
        issues=[]
        if p is None or not 0<p<1:issues.append("INVALID_FROZEN_REFERENCE")
        if not v:issues.append("NO_MARKET_VALIDATION_ROW")
        if status=="PRICE_CONFIRMED" and not evidence:issues.append("NO_EXECUTION_EVIDENCE_REFERENCE")
        if status=="PRICE_CONFIRMED" and manualrow:
            checked=manualrow.get("checked_utc","")
            try:
                check_time=datetime.fromisoformat(checked.replace("Z","+00:00"))
                selection=datetime.fromisoformat(pick["selection_utc"].replace("Z","+00:00"))
                # Evidence must pertain to the frozen observed price, not days later.
                if abs((check_time-selection).total_seconds())>900:
                    issues.append("PRICE_CHECK_OUTSIDE_15_MINUTES")
            except (TypeError,ValueError):
                issues.append("INVALID_PRICE_CHECK_TIMESTAMP")
        detail.append({
            "event_id":pick["event_id"],
            "matchup":f"{pick['away_team']} @ {pick['home_team']}",
            "selected_side":pick["selected_side"],"selection_utc":pick["selection_utc"],
            "kickoff_utc":pick["kickoff_utc"],"book":pick["book"],
            "frozen_price":pick["offered_odds"],"reference_prob":pick["reference_prob"],
            "break_even_prob":pick.get("break_even_prob",""),
            "indicative_ev":pick["apparent_ev"],
            "market_followup":"YES" if v.get("latest_market_utc") else "NO",
            "same_book_followup":"YES" if v.get("latest_same_book_utc") else "NO",
            "near_kickoff_reference":"YES" if v.get("near_kickoff_utc") else "NO",
            "near_same_book":"YES" if v.get("near_kickoff_same_book_utc") else "NO",
            "market_shift_pp":v.get("near_kickoff_market_shift_pp",""),
            "same_book_implied_shift_pp":v.get("near_kickoff_same_book_shift_pp",""),
            "verified_final":"YES" if verified else "NO",
            "win":won if won is not None else "",
            "outcome_brier":round(brier,6) if brier is not None else "",
            "outcome_logloss":round(loss,6) if loss is not None else "",
            "manual_execution_status":status,
            "manual_execution_evidence":evidence,
            "manual_net_price":"",
            "manual_effective_ev_proxy":"",
            "data_quality_warning":";".join(issues) if issues else "NONE"
        })
    return detail

def report(detail,manual,now):
    total=len(detail)
    settled=[r for r in detail if r["verified_final"]=="YES" and r["outcome_brier"]!=""]
    near=[r for r in detail if r["near_kickoff_reference"]=="YES"]
    same_near=[r for r in detail if r["near_same_book"]=="YES"]
    shifts=[number(r["market_shift_pp"]) for r in near]
    shifts=[x for x in shifts if x is not None]
    same_shifts=[number(r["same_book_implied_shift_pp"]) for r in same_near]
    same_shifts=[x for x in same_shifts if x is not None]
    lines=[
        "# Model 13 — Phase 2 Prospective Validation","",
        f"Generated UTC: `{now.isoformat()}`","",
        "> **NO VERIFIED POSITIVE EV. PAPER RESEARCH ONLY.** No bets are placed by this workflow.",
        "",
        "## 1. Sample accrual (no forced picks)","",
        f"- Frozen prospective selections: **{total}/{TARGET}** (planning target, not a sufficient statistical sample guarantee).",
        f"- Independently verified results: **{len(settled)}**.",
        "- The target is an observation milestone; do not adjust selection criteria to meet it.",
        "",
        "## 2. Market validation coverage","",
        f"- Later five-book market references: **{sum(r['market_followup']=='YES' for r in detail)}/{total}**.",
        f"- Later selected-book quotes: **{sum(r['same_book_followup']=='YES' for r in detail)}/{total}**.",
        f"- Near-kickoff (<=3h) five-book references: **{len(near)}/{total}**.",
        f"- Near-kickoff selected-book quotes: **{len(same_near)}/{total}**.",
        f"- Observed near-kickoff market shift mean: **{statistics.mean(shifts):+.3f} percentage points** (n={len(shifts)})." if shifts else "- Observed near-kickoff market shift: **not yet measurable**.",
        f"- Observed same-book near-kickoff implied-price shift mean: **{statistics.mean(same_shifts):+.3f} percentage points** (n={len(same_shifts)})." if same_shifts else "- Same-book near-kickoff shift: **not yet measurable**.",
        "- These measures are market-price movement proxies, **not** certified closing-line value.",
        "",
        "## 3. Execution/availability evidence","",
    ]
    counts=Counter(r["manual_execution_status"] for r in detail)
    for status in sorted(STATUSES):
        lines.append(f"- {status}: **{counts[status]}**.")
    lines+= [
        "",
        "Prices from the odds feed are **not proof of fillability**. The optional manual CSV",
        "`data/model13/execution_observations.csv` can document independently checked",
        "availability, stake limits, fees and evidence references. Never store credentials,",
        "personal financial data, or identifying screenshots in the repository.",
        "",
        "## 4. Probability calibration, selected-side reference only","",
    ]
    if settled:
        ps=[number(r["reference_prob"]) for r in settled]
        actual=[int(r["win"]) for r in settled]
        lines+= [
            f"- Mean predicted selected-side win probability (other-book no-vig median): **{statistics.mean(ps):.2%}**.",
            f"- Actual selected-side win rate: **{statistics.mean(actual):.2%}**.",
            f"- Selected-side Brier score: **{statistics.mean(float(r['outcome_brier']) for r in settled):.5f}**.",
            f"- Selected-side log loss: **{statistics.mean(float(r['outcome_logloss']) for r in settled):.5f}**.",
            f"- Calibration gap (actual minus reference mean): **{statistics.mean(actual)-statistics.mean(ps):+.2%}**.",
        ]
        if len(settled)<30:
            lines+=["- **Insufficient observations for meaningful calibration reliability bins; do not infer model validity.**"]
        else:
            lines+=["","| Probability bin | Count | Mean predicted | Observed win rate |",
                    "|---|---:|---:|---:|"]
            for lo,hi in [(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.00000001)]:
                subset=[r for r in settled if lo<=float(r["reference_prob"])<hi]
                if not subset:continue
                lines.append(f"| {lo:.0%}–{min(hi,1):.0%} | {len(subset)} | {statistics.mean(float(r['reference_prob']) for r in subset):.1%} | {statistics.mean(int(r['win']) for r in subset):.1%} |")
    else:
        lines+=["- No independently verified settled selections. **No Brier score, log loss, or calibration claims yet.**"]
    lines+=["",
        "### Interpretation requirements","",
        "- The probability used here is the other-books' median no-vig *market estimate*, NOT an independently trained probability model.",
        "- This is a *selected-only* cohort and may be biased by selecting cross-book discrepancies. Do not extrapolate calibration to all NFL games.",
        "- No candidate is added retroactively, and all evaluation timestamps follow the original freeze.",
        "- Outcomes are sourced only from independently matched Model 13 final-score observations.",
        "- Missing prices and finals remain missing, never interpreted as losses or zero movement.",
        "",
        "## 5. Data-quality / pending work","",
        f"- Candidates with audit warnings: **{sum(r['data_quality_warning']!='NONE' for r in detail)}**.",
        f"- Candidates awaiting verified finals: **{total-len(settled)}**.",
        f"- Candidates missing near-kickoff market observations: **{total-len(near)}**.",
        f"- Candidates without independent execution confirmation: **{total-counts['PRICE_CONFIRMED']}**.",
        "",
        "The live Model 13 selection rule remains unchanged. Do not use this dashboard as a wagering signal.",
        ""]
    return "\n".join(lines)

def main():
    now=datetime.now(timezone.utc)
    frozen=rows(FROZEN)
    validation=rows(VALIDATION)
    finals=rows(RESULTS)
    manual=rows(EXECUTION)
    detail=build(frozen,validation,finals,manual)
    DETAIL.parent.mkdir(parents=True,exist_ok=True)
    with DETAIL.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=DETAIL_FIELDS)
        writer.writeheader()
        writer.writerows(detail)
    REPORT.write_text(report(detail,manual,now),encoding="utf-8")
    print(f"Model 13 Phase 2: {len(detail)} selections, {sum(x['verified_final']=='YES' for x in detail)} verified finals, {sum(x['near_kickoff_reference']=='YES' for x in detail)} near-kickoff references.")

if __name__=="__main__":
    main()
