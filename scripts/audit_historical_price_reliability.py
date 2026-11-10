#!/usr/bin/env python3
"""Independent reliability/sensitivity audit for free Odds Gap NFL moneylines.

Keeps the original historical candidates/outcomes immutable, and never edits
live prospective Model 13. Sportsbook-only replay is a new, labeled sensitivity
run, NOT a valid out-of-sample experiment. No edge/profitability claims.
"""
import argparse
import csv
import math
from pathlib import Path
import pandas as pd
from backtest_free_odds_gap import load_sample,pair_quotes,replay,implied,profit

# Strict, documented manual allowlist, not an inference based on the absence
# of a prediction-market name. Unknown/offshore venues are intentionally out.
SPORTSBOOKS={
    "draftkings","fanduel","betmgm","caesars","betrivers","espnbet",
    "fanatics","bet365","hardrock","hardrockbet","pointsbet",
    "betparx","ballybet","betway","wynnbet"
}
EXCHANGES={"novig","kalshi","polymarket","polymarket_us","prophetx"}
AUDIT_FIELDS=[
    "game_id","away","home","book","venue_type","selected_side",
    "kickoff_utc","selection_utc","lead_hours","lead_bucket",
    "offered_odds","offered_break_even_prob","other_books",
    "median_other_no_vig_prob","discrepancy_pp",
    "indicative_ev_recomputed","quoted_pair_overround_pct",
    "selected_book_quote_repeated_prior_snapshot","synchronized_quote_check",
    "reference_recomputed_matches_frozen","reliability_warning"
]

def venue(book):
    b=str(book).strip().lower()
    if b in SPORTSBOOKS:return "ALLOWLIST_SPORTSBOOK"
    if b in EXCHANGES:return "EXCHANGE_OR_PREDICTION_MARKET"
    return "UNKNOWN_OR_UNVERIFIED"

def lead_bucket(hours):
    if hours<12:return "UNDER_12H"
    if hours<24:return "12-24H"
    if hours<48:return "24-48H"
    if hours<72:return "48-72H"
    return "72H_PLUS"

def read_records(path):
    with Path(path).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def reliability(picks,pairs):
    """Evaluate each already-frozen price only against its actual snapshot."""
    rows=[]
    for pick in picks:
        event=str(pick["game_id"])
        book=str(pick["book"])
        side=str(pick["selected_side"]).upper()
        stamp=pd.to_datetime(pick["selection_utc"],utc=True,errors="coerce")
        kickoff=pd.to_datetime(pick["kickoff_utc"],utc=True,errors="coerce")
        subset=pairs[(pairs["game_id"]==event)&(pairs["snapshot_ts"]==stamp)]
        chosen=subset[subset["book"]==book]
        other=subset[subset["book"]!=book]
        warning=[]
        reference=float("nan")
        delta=float("nan")
        ev=float("nan")
        overround=float("nan")
        repeat=""
        price=float(pick["offered_odds"])
        quoted=""
        matching=""
        if len(chosen)!=1 or len(other)<4:
            warning.append("MISSING_SYNCHRONIZED_FIVE_BOOK_REFERENCE")
            quoted="NO"
        else:
            q=chosen.iloc[0]
            quoted="YES"
            actual=float(q["home"] if side=="HOME" else q["away"])
            if not math.isclose(price,actual,abs_tol=1e-6):
                warning.append("SELECTED_PRICE_DIFFERS_FROM_SOURCE")
            reference=float(other["home_prob"].median())
            if side=="AWAY":reference=1-reference
            delta=100*(reference-implied(price))
            ev=reference*(1+profit(price))-1
            overround=100*(implied(float(q["home"]))+implied(float(q["away"]))-1)
            if abs(overround)>15:
                warning.append("UNUSUAL_PAIRED_OVERROUND")
            if delta>=5:
                warning.append("LARGE_CROSS_BOOK_PRICE_DISCREPANCY_5PP")
            if delta>=10:
                warning.append("EXTREME_CROSS_BOOK_PRICE_DISCREPANCY_10PP")
            if abs(float(pick["reference_prob"])-reference)>0.0002:
                warning.append("FROZEN_REFERENCE_MISMATCH")
            # Source snapshot timestamp is not book-specific last_update.
            # Repeated odds at preceding captured instant = weak stale proxy.
            prior=pairs[(pairs["game_id"]==event)&(pairs["book"]==book)&
                        (pairs["snapshot_ts"]<stamp)].sort_values("snapshot_ts")
            if len(prior):
                previous=prior.iloc[-1]
                repeat="YES" if (previous["home"]==q["home"] and previous["away"]==q["away"]) else "NO"
            else:repeat="NO_PRIOR_SNAPSHOT"
        matching="UNKNOWN" if math.isnan(reference) else ("YES" if abs(float(pick["reference_prob"])-reference)<=0.0002 else "NO")
        lead=(kickoff-stamp).total_seconds()/3600
        rows.append(dict(
            game_id=event,away=pick["away"],home=pick["home"],book=book,
            venue_type=venue(book),selected_side=side,
            kickoff_utc=kickoff.isoformat(),selection_utc=stamp.isoformat(),
            lead_hours=round(lead,2),lead_bucket=lead_bucket(lead),
            offered_odds=price,offered_break_even_prob=round(implied(price),8),
            other_books=len(other),median_other_no_vig_prob=round(reference,8) if math.isfinite(reference) else "",
            discrepancy_pp=round(delta,3) if math.isfinite(delta) else "",
            indicative_ev_recomputed=round(ev,6) if math.isfinite(ev) else "",
            quoted_pair_overround_pct=round(overround,3) if math.isfinite(overround) else "",
            selected_book_quote_repeated_prior_snapshot=repeat,
            synchronized_quote_check=quoted,
            reference_recomputed_matches_frozen=matching,
            reliability_warning=";".join(warning) if warning else "NONE_DETECTED"
        ))
    return rows

def verify_final(row):
    if row.get("outcome_status")!="FINAL":return None
    try:
        hs=int(row["home_score"]);awas=int(row["away_score"])
    except (ValueError,TypeError,KeyError):
        return None
    if hs==awas:return None
    return "HOME" if hs>awas else "AWAY"

def leave_one_out(outcomes):
    """Leave-one-candidate-out flat stake ROI, verified finals only."""
    valid=[r for r in outcomes if verify_final(r) is not None and
           r.get("paper_profit_per_unit","")!=""]
    if len(valid)<2:return None
    profits=[float(r["paper_profit_per_unit"]) for r in valid]
    scenarios=[]
    for i,r in enumerate(valid):
        roi=(sum(profits)-profits[i])/(len(profits)-1)
        scenarios.append((str(r["game_id"]),roi))
    return {
        "n":len(valid),"original_roi":sum(profits)/len(profits),
        "minimum_roi":min(v for _,v in scenarios),
        "maximum_roi":max(v for _,v in scenarios),
        "minimum_game":min(scenarios,key=lambda p:p[1])[0],
        "maximum_game":max(scenarios,key=lambda p:p[1])[0]
    }

def sportsbook_replay(pairs,outcomes):
    """Re-select candidate/reference ONLY among explicitly allowlisted books."""
    filtered=pairs[pairs["book"].astype(str).str.lower().isin(SPORTSBOOKS)].copy()
    historical,stats=replay(filtered)
    # Independently verify same game identity / kickoff using saved ESPN outcomes.
    verified={}
    for result in outcomes:
        if verify_final(result) is not None:
            verified.setdefault(str(result["game_id"]),[]).append(result)
    converted=[]
    for _,item in historical.iterrows():
        row=item.to_dict()
        matches=[r for r in verified.get(str(row["game_id"]),[])
                 if r["home"]==row["home"] and r["away"]==row["away"] and
                 abs((pd.to_datetime(r["kickoff_utc"],utc=True)-
                      pd.to_datetime(row["kickoff_utc"],utc=True)).total_seconds())<=6*3600]
        if len(matches)!=1:
            row.update(outcome_status="UNMATCHED_OR_UNVERIFIED",won="",paper_profit_per_unit="")
        else:
            winner=verify_final(matches[0])
            won=int(winner==row["selected_side"])
            row.update(outcome_status="FINAL",won=won,
                       paper_profit_per_unit=profit(float(row["offered_odds"])) if won else -1.0)
        converted.append(row)
    return converted,stats

def summarize(quality,base_outcomes,strict,stats,loo):
    verified=[r for r in strict if r["outcome_status"]=="FINAL"]
    strict_roi=sum(float(r["paper_profit_per_unit"]) for r in verified)/len(verified) if verified else None
    counts=pd.Series([r["lead_bucket"] for r in quality]).value_counts()
    venue_counts=pd.Series([r["venue_type"] for r in quality]).value_counts()
    flags=[r for r in quality if r["reliability_warning"]!="NONE_DETECTED"]
    report=[
        "# Model 13 — Historical Price Reliability Audit","",
        "> **RESEARCH ONLY: no verified positive EV.** Historical data and captured timestamps cannot establish live fillability.","",
        "## Original frozen historical candidate quality","",
        f"- Original selections inspected: **{len(quality)}**",
        f"- Source-quote / same-instant check failures: **{sum(r['synchronized_quote_check']!='YES' for r in quality)}**",
        f"- Large 5+ percentage-point cross-book price gaps: **{sum(r['discrepancy_pp']!='' and float(r['discrepancy_pp'])>=5 for r in quality)}**",
        f"- Unusual source two-sided overround (absolute >15 pp): **{sum(r['quoted_pair_overround_pct']!='' and abs(float(r['quoted_pair_overround_pct']))>15 for r in quality)}**",
        f"- Any data quality warning: **{len(flags)}**","",
        "### Venue types among original historical selections","",
    ]
    for name,n in sorted(venue_counts.items()):report.append(f"- {name}: **{n}**")
    report+=["","### Time before kickoff",""]
    for bucket in ["UNDER_12H","12-24H","24-48H","48-72H","72H_PLUS"]:
        report.append(f"- {bucket}: **{int(counts.get(bucket,0))}**")
    report+=["","## Strict sportsbook-only re-selection (sensitivity analysis)","",
             "The re-selection **excludes exchanges AND all unverified venue names from both candidate and reference pools**. Only manually allowlisted sportsbooks count toward the minimum five. The original 13 selections are not modified.",
             "",
             f"- Games with at least 5 allowlisted books: **{stats.get('games_with_5_books',0)}**",
             f"- Sportsbook-only historical candidate picks: **{len(strict)}**",
             f"- Matched verified final results: **{len(verified)}**"]
    unmatched=len(strict)-len(verified)
    report.append(f"- Unmatched sportsbook-only selections: **{unmatched}**")
    if strict_roi is not None and unmatched==0:
        wins=sum(int(r["won"]) for r in verified)
        report.append(f"- Retrospective paper win rate (all outcomes verified): **{wins}/{len(verified)}**")
        report.append(f"- Retrospective paper ROI (all outcomes verified): **{strict_roi:+.2%}**")
    elif unmatched:
        report.append("- Retrospective paper ROI: **NOT REPORTED**; original outcome file verifies only original picks, and a strict re-selection can include different games. Partial-match ROI would be misleading.")
    else:report.append("- Retrospective paper ROI: **unavailable** (no independently verified outcomes)")
    report+=["","## Original sample leave-one-out sensitivity",""]
    if loo:
        report+= [
            f"- Confirmed scored original selections: **{loo['n']}**",
            f"- Original paper ROI: **{loo['original_roi']:+.2%}**",
            f"- Lowest ROI removing one game: **{loo['minimum_roi']:+.2%}** (removed {loo['minimum_game']})",
            f"- Highest ROI removing one game: **{loo['maximum_roi']:+.2%}** (removed {loo['maximum_game']})"
        ]
    else:report.append("Not enough verified original candidate outcomes.")
    report+=["","## Interpretation limits","",
        "- A 5-percentage-point price gap is a **diagnostic marker only**, not a tested filter or evidence of stale quotes.",
        "- Quote timestamps were synchronized in the export, but the data does NOT prove each bookmaker refreshed prices then.",
        "- Repeated quotes across source snapshots are weak circumstantial evidence, not a definitive stale classification.",
        "- Sportsbook allowlist is deliberately conservative and does not guarantee regional access, availability, or actual fill.",
        "- The strict sportsbook-only backtest is post-hoc exploratory research; it must not be compared as if independent or prospective.",
        "- Near-kickoff comparisons exist for only one original selection, so closing-line validation remains severely incomplete.",
        "- The full 240MB source file stays in private Drive; do not commit it or any API keys to GitHub.",
        "- The prospective Model 13 rules and frozen observations remain untouched.",""]
    return "\n".join(report)

def main():
    parser=argparse.ArgumentParser()
    root="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds"
    parser.add_argument("--odds",default=f"{root}/odds_gap_free_sample.csv")
    parser.add_argument("--candidates",default=f"{root}/model13_sample/historical_model13_sample_candidates.csv")
    parser.add_argument("--outcomes",default=f"{root}/model13_sample/historical_model13_outcomes.csv")
    parser.add_argument("--outdir",default=f"{root}/model13_sample")
    args=parser.parse_args()
    for p in (args.odds,args.candidates,args.outcomes):
        if not Path(p).is_file():raise SystemExit(f"Input not found: {p}")
    base_picks=read_records(args.candidates)
    original_results=read_records(args.outcomes)
    _,ml=load_sample(args.odds)
    pairs=pair_quotes(ml)
    quality=reliability(base_picks,pairs)
    strict,stats=sportsbook_replay(pairs,original_results)
    loo=leave_one_out(original_results)
    dest=Path(args.outdir);dest.mkdir(parents=True,exist_ok=True)
    with (dest/"historical_price_reliability.csv").open("w",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=AUDIT_FIELDS);w.writeheader();w.writerows(quality)
    pd.DataFrame(strict).to_csv(dest/"historical_sportsbook_only_replay.csv",index=False)
    report=summarize(quality,original_results,strict,stats,loo)
    (dest/"historical_price_reliability.md").write_text(report,encoding="utf-8")
    print(report)
    print(f"Saved reliability CSV, sportsbook-only replay CSV, and Markdown report to {dest}")

if __name__=="__main__":main()
