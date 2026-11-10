#!/usr/bin/env python3
"""Model 11: prospectively lock independent forecasts and audit pricing claims.

No prediction generator is included: prior NFLverse candidate did not beat the
market. We accept independently generated, explicitly time-stamped forecasts
only, without backfilling or retroactive model selection. NO AUTOMATED BETS.
"""
import csv
import math
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path

from model9 import load_quotes, qualified_snapshots, load_results

INBOX=Path("data/model11/independent_forecasts_inbox.csv")
LEDGER=Path("data/model11/locked_independent_forecasts.csv")
REPORT=Path("reports/model11_dashboard.md")
AUDIT=Path("reports/model11_audit.csv")
FIELDS=["event_id","home_team","away_team","kickoff_utc","model_id",
        "model_version","trained_through_utc","forecast_utc","ingested_utc",
        "model_home_probability","market_home_probability","book_count",
        "target_side","offered_sportsbook","offered_american_odds",
        "model_ev_per_dollar","break_even_probability","research_status"]
AUDIT_FIELDS=FIELDS+["latest_snapshot_utc","later_home_probability",
                   "near_kickoff_utc","near_kickoff_home_probability",
                   "independent_clv_probability_pp","result","side_won",
                   "realized_paper_profit_per_dollar",
                   "model_brier","market_brier","model_logloss","market_logloss"]
MAX_AGE=timedelta(minutes=15)
MIN_LEAD=timedelta(hours=12)

def read(path):
    if not path.is_file():
        return []
    with path.open(newline="",encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(timezone.utc)

def implied(odds):
    odds=float(odds)
    if odds == 0:
        raise ValueError("Zero American moneyline")
    return -odds/(100-odds) if odds<0 else 100/(100+odds)

def profit_if_win(odds):
    odds=float(odds)
    return odds/100 if odds>0 else 100/(-odds)

def probability(x):
    p=float(x)
    if not math.isfinite(p) or not .001<p<.999:
        raise ValueError("Probability out of range")
    return p

def current_matching_snapshot(snapshots, when, game):
    series=qualified_snapshots(snapshots)
    valid=[item for item in series if
           timedelta(0)<=when-item[0]<=MAX_AGE and
           item[3]["home_team"]==game["home_team"] and
           item[3]["away_team"]==game["away_team"] and
           abs(item[3]["kickoff"]-parse_time(game["kickoff_utc"]))<timedelta(minutes=30)]
    return valid[-1] if valid else None

def lock_new(inbox, prior, frozen_market, quotes, now):
    existing={x["event_id"] for x in prior}
    locked_market={x["event_id"]:x for x in frozen_market}
    additions=[]
    for item in inbox:
        event=(item.get("event_id") or "").strip()
        market=locked_market.get(event)
        if not event or not market or event in existing:
            continue
        try:
            timestamp=parse_time(item["forecast_utc"])
            cutoff=parse_time(item["trained_through_utc"])
            kickoff=parse_time(market["kickoff_utc"])
            model_p=probability(item["home_probability"])
            model_id=(item["model_id"] or "").strip()
            version=(item["model_version"] or "").strip()
            if (not model_id or not version or
                not timedelta(0)<=now-timestamp<=MAX_AGE or
                kickoff-now<MIN_LEAD or cutoff>=timestamp):
                continue
            snap=current_matching_snapshot(quotes.get(event,{}),timestamp,market)
            if snap is None:
                continue
            _, market_p, books, _=snap
            home_best=max(books.values(),key=lambda b:b["home_odds"])
            away_best=max(books.values(),key=lambda b:b["away_odds"])
            choices=[
                ("HOME",home_best,model_p),
                ("AWAY",away_best,1-model_p)
            ]
            options=[]
            for side, book, p in choices:
                odds=book["home_odds" if side=="HOME" else "away_odds"]
                ev=p*(1+profit_if_win(odds))-1
                options.append((ev,side,book,p,odds))
            ev,side,book,p,odds=max(options,key=lambda c:c[0])
            # Even a favorable computed EV is not a validated edge.
            additions.append({
                "event_id":event,"home_team":market["home_team"],
                "away_team":market["away_team"],"kickoff_utc":market["kickoff_utc"],
                "model_id":model_id,"model_version":version,
                "trained_through_utc":cutoff.isoformat(),
                "forecast_utc":timestamp.isoformat(),"ingested_utc":now.isoformat(),
                "model_home_probability":f"{model_p:.8f}",
                "market_home_probability":f"{market_p:.8f}",
                "book_count":len(books),
                "target_side":side,"offered_sportsbook":book["book_name"],
                "offered_american_odds":odds,
                "model_ev_per_dollar":f"{ev:.6f}",
                "break_even_probability":f"{implied(odds):.8f}",
                "research_status":"UNVALIDATED_RESEARCH_ONLY"
            })
            existing.add(event)
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
    if additions:
        LEDGER.parent.mkdir(parents=True,exist_ok=True)
        with LEDGER.open("a",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS)
            if stream.tell()==0:
                writer.writeheader()
            writer.writerows(additions)
    return additions

def calculate_audit(locked, quotes, final_results, now):
    output=[]
    for item in locked:
        event=item["event_id"]
        kickoff=parse_time(item["kickoff_utc"])
        first=parse_time(item["forecast_utc"])
        model=probability(item["model_home_probability"])
        baseline=probability(item["market_home_probability"])
        later=[p for p in qualified_snapshots(quotes.get(event,{}))
               if first < p[0] < kickoff]
        last=later[-1] if later else None
        near=[p for p in later if kickoff-p[0]<=timedelta(hours=3)]
        close=near[-1] if near else None
        side=item["target_side"]
        # Positive indicates market moved toward the model's selected side.
        direction=1 if side=="HOME" else -1
        clv=(100*direction*(close[1]-baseline)) if close else None
        winner=final_results.get(event) if now>=kickoff else None
        if winner not in (item["home_team"],item["away_team"]):
            winner=None
        y=int(winner==item["home_team"]) if winner else None
        selected_win=(y==1 if side=="HOME" else y==0) if y is not None else None
        odds=float(item["offered_american_odds"])
        paper=(profit_if_win(odds) if selected_win else -1.0) if y is not None else None
        def brier(p):return (p-y)**2 if y is not None else None
        def log_loss(p):return -(y*math.log(p)+(1-y)*math.log(1-p)) if y is not None else None
        output.append({
            **item,
            "latest_snapshot_utc":last[0].isoformat() if last else "",
            "later_home_probability":f"{last[1]:.8f}" if last else "",
            "near_kickoff_utc":close[0].isoformat() if close else "",
            "near_kickoff_home_probability":f"{close[1]:.8f}" if close else "",
            "independent_clv_probability_pp":f"{clv:.4f}" if clv is not None else "",
            "result":"FINAL" if winner else "NOT_FINAL",
            "side_won":int(selected_win) if selected_win is not None else "",
            "realized_paper_profit_per_dollar":f"{paper:.4f}" if paper is not None else "",
            "model_brier":f"{brier(model):.6f}" if y is not None else "",
            "market_brier":f"{brier(baseline):.6f}" if y is not None else "",
            "model_logloss":f"{log_loss(model):.6f}" if y is not None else "",
            "market_logloss":f"{log_loss(baseline):.6f}" if y is not None else "",
        })
    return output

def write_report(audit,added,now):
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    with AUDIT.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(audit)
    settled=[x for x in audit if x["result"]=="FINAL"]
    near=[x for x in audit if x["near_kickoff_utc"]]
    # 200 is a reporting minimum, not a magic proof of profitable EV.
    evidence="INSUFFICIENT_FORWARD_EVIDENCE"
    lines=[
        "# Model 11 — Independent Edge Validation",
        "",
        f"Updated: `{now.isoformat()}`",
        "",
        "> **NO VERIFIED POSITIVE EV. Research-only. No wagering recommendations.**",
        "",
        "## Prospective research summary",
        "",
        f"- Independent forecasts added this run: **{len(added)}**",
        f"- Total locked independent forecasts: **{len(audit)}**",
        f"- Settled paper observations: **{len(settled)}**",
        f"- Near-kickoff price proxies: **{len(near)}**",
        f"- Evidence level: **{evidence}**",
        "",
    ]
    if not audit:
        lines+=["**No independent calibrated model has been promoted.** This is correct: the existing NFLverse-adjusted historical model failed to improve pooled probability scoring versus sportsbook consensus. An independently developed, timestamped model forecast must be supplied to begin this test.",""]
    else:
        lines+=["| Game | Method | Side | Locked odds | Model home % | Market home % | Theoretical EV | Near-kickoff proxy | Outcome |",
               "|---|---|---|---:|---:|---:|---:|---|---|"]
        for r in sorted(audit,key=lambda x:x["kickoff_utc"]):
            lines.append(
                f"| {r['away_team']} @ {r['home_team']} | {r['model_id']} {r['model_version']} | "
                f"{r['target_side']} | {int(r['offered_american_odds']):+d} ({r['offered_sportsbook']}) | "
                f"{100*float(r['model_home_probability']):.2f}% | {100*float(r['market_home_probability']):.2f}% | "
                f"{100*float(r['model_ev_per_dollar']):+.2f}% | "
                f"{r['independent_clv_probability_pp']+' pp' if r['near_kickoff_utc'] else '—'} | {r['result']} |"
            )
    lines+=["","## Outcome diagnostics",""]
    if settled:
        brier_model=statistics.mean(float(r["model_brier"]) for r in settled)
        brier_market=statistics.mean(float(r["market_brier"]) for r in settled)
        log_model=statistics.mean(float(r["model_logloss"]) for r in settled)
        log_market=statistics.mean(float(r["market_logloss"]) for r in settled)
        roi=statistics.mean(float(r["realized_paper_profit_per_dollar"]) for r in settled)
        lines.extend([
            f"- Model Brier: **{brier_model:.4f}** vs market: **{brier_market:.4f}**",
            f"- Model log loss: **{log_model:.4f}** vs market: **{log_market:.4f}**",
            f"- Hypothetical 1-unit per candidate return: **{roi:+.2%}** across **{len(settled)}** selections",
            "This paper ROI ignores fees, restrictions, and whether quoted odds were actually available to the individual. Small samples do not establish an edge.",
        ])
    else:
        lines.append("No independent paper forecasts with verified final results exist; profitability cannot be evaluated.")
    lines+=["",
        "## Guardrails",
        "",
        "- Model 11 **does not create** independent probabilities from sportsbook prices.",
        "- New independent forecasts must be ingested within 15 minutes of their stated generation time, at least 12 hours before kickoff, and use a previously locked Model 10 event.",
        "- Only matching recent bookmaker observations are used; forecasts, model versions and offered odds freeze upon ingestion.",
        "- Model-projected EV is an unvalidated arithmetic hypothesis; a positive number is never promoted to a verified betting edge.",
        "- Market movements are merely later observations. A near-kickoff market probability is not automatically a final closing line.",
        "- Source results must match exact teams and kickoff; no speculative outcome filling.",
        "- A meaningful claim would require enough independent prospective settlements, probability calibration, market comparison, and realistic execution checks. None has been established.",
        "",
        "## Optional input schema",
        "",
        "Place a CSV at `data/model11/independent_forecasts_inbox.csv` with columns:",
        "`event_id,forecast_utc,trained_through_utc,model_id,model_version,home_probability`.",
        "The model's production process must be external, documented and leakage-free.",
        "Do not fabricate a forecast or set its timestamp retroactively.",
    ]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    print(f"Model 11: {len(added)} new independent forecasts, {len(audit)} frozen total, {len(settled)} settled.")
    print("Research-only dashboard:",REPORT)

def main(now=None):
    now=now or datetime.now(timezone.utc)
    quotes,_,_=load_quotes()
    market=read(Path("data/model10/prospective_forecasts.csv"))
    created=lock_new(read(INBOX),read(LEDGER),market,quotes,now)
    audit=calculate_audit(read(LEDGER),quotes,load_results(),now)
    write_report(audit,created,now)

if __name__=="__main__":
    main()
