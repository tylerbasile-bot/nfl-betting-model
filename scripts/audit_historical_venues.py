#!/usr/bin/env python3
"""Break down HISTORICAL paper outcomes by venue, with no selection changes.

Novig is an actual exchange venue, not a synthetic 'no vig' line.
Exchange fees may be incorporated in exported odds; execution and liquidity
are not verified. Missing/mismatched finals are always excluded from returns.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

EXCHANGES={"novig","kalshi","polymarket","polymarket_us","prophetx"}

def venue_category(book):
    if book.strip().lower() in EXCHANGES:
        return "Exchange / prediction market"
    return "Other bookmaker / unclassified venue"

def describe(rows):
    out=[]
    sections=defaultdict(list)
    for row in rows:
        if row.get("outcome_status")!="FINAL":
            continue
        sections[venue_category(row.get("book",""))].append(row)
        sections["All verified historical candidates"].append(row)
    for label,records in sorted(sections.items()):
        profits=[float(row["paper_profit_per_unit"]) for row in records]
        wins=sum(row["won"] in ("1",1) for row in records)
        out.append({
            "category":label,"verified_selections":len(records),
            "paper_wins":wins,
            "win_rate":wins/len(records) if records else None,
            "paper_profit_units":sum(profits),
            "paper_roi":sum(profits)/len(profits) if profits else None
        })
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outcomes",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/model13_sample/historical_model13_outcomes.csv")
    parser.add_argument("--outdir",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/model13_sample")
    args=parser.parse_args()
    with Path(args.outcomes).open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream))
    if not rows:
        raise SystemExit("Outcome file is empty.")
    report=describe(rows)
    lines=["# Historical Model 13 — venue sensitivity audit","",
           "> Descriptive paper research only. Venue group results do not constitute independent backtests or verified profitable opportunities.","",
           "| Venue category | Matched finals | Wins | Win rate | Profit (units) | Paper ROI |",
           "|---|---:|---:|---:|---:|---:|"]
    for r in report:
        lines.append(f"| {r['category']} | {r['verified_selections']} | {r['paper_wins']} | {r['win_rate']:.1%} | {r['paper_profit_units']:+.3f} | {r['paper_roi']:+.1%} |")
    lines+=["",
        "Exchange / prediction market includes Novig, Kalshi, Polymarket, and ProphetX if selected.",
        "The residual group is not necessarily made up entirely of US-accessible sportsbooks; it may include offshore or unfamiliar providers.",
        "**These are groups of the original, preselected 13 historical candidates. This is NOT a new sportsbook-only replay and does not claim how a sportsbook-only strategy would have performed.**",
        "Prices may have limited liquidity, stale quotes, fees, regional availability or restricted fills.",
        "Near-kickoff data coverage was only one of thirteen candidates, limiting line-quality validation.",
        "The 13-game sample is too small to support a reliable positive-EV claim.",""]
    out=Path(args.outdir)
    out.mkdir(parents=True,exist_ok=True)
    dest=out/"historical_model13_venue_audit.md"
    dest.write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved: {dest}")

if __name__=="__main__":main()
