#!/usr/bin/env python3
"""Model 10: append-only prospective NFL market benchmark.

Requires fresh odds snapshots from scripts/collect_odds.py. A forecast is only
created from a snapshot observed in this very recent run; older historical data
is NEVER backfilled as prospective predictions.

No independent trained model and no wagering signals.
"""
import csv
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from model9 import load_quotes, qualified_snapshots, load_results

LEDGER = Path("data/model10/prospective_forecasts.csv")
DASHBOARD = Path("reports/model10_dashboard.md")
EVALUATION = Path("reports/model10_evaluation.csv")

# Snapshot is valid at execution time only if collected recently.
MAX_SNAPSHOT_AGE = timedelta(minutes=15)
MIN_TIME_BEFORE_KICKOFF = timedelta(hours=12)
CLOSING_HORIZON = timedelta(hours=3)
MIN_BOOKS = 4
FIELDS = [
    "event_id", "home_team", "away_team", "kickoff_utc",
    "forecast_utc", "home_probability", "away_probability",
    "books", "best_home_book", "best_home_odds",
    "best_away_book", "best_away_odds", "method", "research_status"
]
EVAL_FIELDS = FIELDS + [
    "latest_observed_utc", "latest_home_probability",
    "latest_market_shift_pp", "near_kickoff_utc",
    "near_kickoff_home_probability", "market_shift_near_kickoff_pp",
    "result", "home_win", "brier", "logloss"
]

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()

def safe_probability(value):
    p = float(value)
    if not math.isfinite(p) or not 0 < p < 1:
        raise ValueError("Probability must be between 0 and 1")
    return p

def read_ledger():
    if not LEDGER.exists():
        return []
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))

def capture_new_forecasts(quotes, now):
    existing = read_ledger()
    already = {row["event_id"] for row in existing}
    created = []
    for event_id, snapshots in quotes.items():
        if event_id in already:
            continue
        series = qualified_snapshots(snapshots)
        if not series:
            continue
        # Pick only the latest valid snapshot from this execution, never old history.
        stamp, probability, books, meta = series[-1]
        kickoff = meta["kickoff"]
        if not timedelta(0) <= now-stamp <= MAX_SNAPSHOT_AGE:
            continue
        if kickoff - now < MIN_TIME_BEFORE_KICKOFF:
            continue
        home_best = max(books.values(), key=lambda quote:quote["home_odds"])
        away_best = max(books.values(), key=lambda quote:quote["away_odds"])
        created.append({
            "event_id":event_id,
            "home_team":meta["home_team"],
            "away_team":meta["away_team"],
            "kickoff_utc":iso(kickoff),
            "forecast_utc":iso(stamp),
            "home_probability":f"{probability:.8f}",
            "away_probability":f"{1-probability:.8f}",
            "books":len(books),
            "best_home_book":home_best["book_name"],
            "best_home_odds":home_best["home_odds"],
            "best_away_book":away_best["book_name"],
            "best_away_odds":away_best["away_odds"],
            "method":"market_median_no_vig_v1",
            "research_status":"NO VERIFIED EDGE",
        })
        already.add(event_id)
    if created:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            if stream.tell() == 0:
                writer.writeheader()
            writer.writerows(created)
    return created

def evaluate(quotes, results, frozen, now):
    output = []
    for row in frozen:
        event = row["event_id"]
        kickoff = datetime.fromisoformat(row["kickoff_utc"])
        locked = datetime.fromisoformat(row["forecast_utc"])
        p = safe_probability(row["home_probability"])
        series = qualified_snapshots(quotes.get(event, {}))
        # Only snapshots AFTER the frozen forecast and BEFORE kickoff can update movement.
        later = [
            entry for entry in series
            if locked < entry[0] < kickoff
        ]
        latest = later[-1] if later else None
        # Explicit near-kickoff proxy; do not label it 'closing' automatically.
        near = [item for item in later if kickoff - item[0] <= CLOSING_HORIZON]
        near = near[-1] if near else None

        # Never score outcomes until the scheduled kickoff has passed.\n        winner = results.get(event) if now >= kickoff else None
        if winner == row["home_team"]:
            y=1
        elif winner == row["away_team"]:
            y=0
        else:
            y=None
        result = {
            **row,
            "latest_observed_utc":iso(latest[0]) if latest else "",
            "latest_home_probability":f"{latest[1]:.8f}" if latest else "",
            "latest_market_shift_pp":f"{100*(latest[1]-p):.3f}" if latest else "",
            "near_kickoff_utc":iso(near[0]) if near else "",
            "near_kickoff_home_probability":f"{near[1]:.8f}" if near else "",
            "market_shift_near_kickoff_pp":f"{100*(near[1]-p):.3f}" if near else "",
            "result":"VERIFIED_FINAL" if y is not None else "AWAITING_VERIFIED_RESULT",
            "home_win":"" if y is None else y,
            "brier":"" if y is None else f"{(p-y)**2:.6f}",
            "logloss":"" if y is None else f"{-(y*math.log(p)+(1-y)*math.log(1-p)):.6f}",
        }
        output.append(result)
    return sorted(output,key=lambda x:(x["kickoff_utc"],x["event_id"]))

def write_reports(records, created, input_files, bad, now):
    DASHBOARD.parent.mkdir(parents=True,exist_ok=True)
    with EVALUATION.open("w", newline="", encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=EVAL_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    scored=[r for r in records if r["result"]=="VERIFIED_FINAL"]
    near=sum(bool(r["near_kickoff_utc"]) for r in records)
    lines=[
        "# Model 10 — Prospective NFL Market Validation",
        "",
        f"Updated: `{iso(now)}`",
        "",
        "> **NO VERIFIED EDGE — RESEARCH ONLY.** This is a frozen market-derived baseline, not an independently validated predictive betting model.",
        "",
        "## Data integrity",
        "",
        f"- First-run forecasts created this execution: **{len(created)}**",
        f"- Total immutable forecast records: **{len(records)}**",
        f"- Historical odds files scanned: **{input_files}**",
        f"- Rejected malformed odds observations: **{bad}**",
        f"- Forecasts with near-kickoff reference: **{near}**",
        f"- Forecasts with verified final game results: **{len(scored)}**",
        "",
        "## Locked pregame predictions",
        "",
        "| Game | Kickoff UTC | Frozen at UTC | Home win % | First home ML | First away ML | Latest shift (pp) | Near kickoff? | Result |",
        "|---|---|---|---:|---|---|---:|---|---|",
    ]
    for r in records:
        lines.append(
            f"| {r['away_team']} @ {r['home_team']} | {r['kickoff_utc'][:16]} | "
            f"{r['forecast_utc'][:16]} | {100*float(r['home_probability']):.2f}% | "
            f"{r['best_home_book']} ({int(r['best_home_odds']):+d}) | "
            f"{r['best_away_book']} ({int(r['best_away_odds']):+d}) | "
            f"{r['latest_market_shift_pp'] or '—'} | "
            f"{'YES' if r['near_kickoff_utc'] else 'NO'} | {r['result']} |"
        )
    if not records:
        lines.append("| No qualifying new pregame snapshots yet | — | — | — | — | — | — | — | — |")
    lines.extend(["","## Future outcome scoring",""])
    if scored:
        lines.extend([
            f"- Evaluated count: **{len(scored)}**",
            f"- Mean Brier: **{statistics.mean(float(r['brier']) for r in scored):.4f}**",
            f"- Mean log loss: **{statistics.mean(float(r['logloss']) for r in scored):.4f}**",
            f"- Winner accuracy: **{statistics.mean((float(r['home_probability'])>=.5) == (int(r['home_win'])==1) for r in scored):.1%}**",
            "These are baseline forecast accuracy metrics, not evidence of a betting edge.",
        ])
    else:
        lines.append("No verified final results yet. No accuracy, return, or profitability claim is possible.")
    lines.extend([
        "",
        "## Validation rules",
        "",
        "- Each game is frozen once, from a snapshot collected within 15 minutes of workflow execution, at least 12 hours before kickoff.",
        "- The saved forecast never updates, even when market lines move.",
        "- At least four bookmakers with quotes updated within 30 minutes are required.",
        "- Market probability = median no-vig bookmaker probability; it is not an independently fitted NFLverse model.",
        "- Later snapshots are observation-only. A quote within 3 hours of kickoff is a near-kickoff proxy, **not necessarily the closing line**.",
        "- Scores are accepted only when a user-verified `data/results.csv` explicitly lists `status=final` and the winning team.",
        "- The system does not issue betting recommendations, calculate speculative ROI, or identify verified +EV selections.",
        "- API event IDs and NFLverse game IDs must be matched carefully before importing NFLverse statistics.",
        "",
    ])
    DASHBOARD.write_text("\n".join(lines),encoding="utf-8")
    print(f"Model 10: {len(created)} new frozen forecasts, {len(records)} total; {len(scored)} verified outcomes.")
    print("Reports: reports/model10_dashboard.md, reports/model10_evaluation.csv")

def main(now=None):
    now = now or datetime.now(timezone.utc)
    quotes,files,bad=load_quotes()
    created=capture_new_forecasts(quotes,now)
    rows=evaluate(quotes,load_results(),read_ledger(),now)
    write_reports(rows,created,files,bad,now)

if __name__=="__main__":
    main()
