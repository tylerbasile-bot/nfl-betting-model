#!/usr/bin/env python3
"""Model 9: reproducible pregame market baseline and validation report.

Standard-library only. No live odds API requests, wagers, or hidden model fitting.
Data sources:
  data/odds/YYYY-MM-DD.csv: immutable-time provider observations
  data/results.csv: optional manually verified finished-game results
Output:
  reports/model9_forecasts.csv
  reports/model9_dashboard.md

Only the FIRST valid pregame market snapshot is used for an event's forecast.
"""
import csv
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

INPUT = Path("data/odds")
RESULTS = Path("data/results.csv")
OUTPUT = Path("reports")
MIN_BOOKS = 4
FRESHNESS = timedelta(minutes=30)
CLOSE_WINDOW = timedelta(hours=3)
FORECAST_FIELDS = [
    "event_id", "kickoff_utc", "away_team", "home_team", "forecast_utc",
    "books_at_forecast", "home_probability", "away_probability",
    "initial_best_home_book", "initial_best_home_odds",
    "initial_best_away_book", "initial_best_away_odds",
    "latest_snapshot_utc", "latest_home_probability",
    "home_probability_change_pp", "near_kickoff_reference",
    "home_won", "brier", "log_loss", "research_status"
]

def parse_time(raw):
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def implied(odds):
    price = float(odds)
    if price < 0:
        return -price / (100 - price)
    if price > 0:
        return 100 / (100 + price)
    raise ValueError("Invalid odds")

def no_vig(home, away):
    h, a = implied(home), implied(away)
    return h / (h + a)

def load_quotes():
    quotes = defaultdict(lambda: defaultdict(dict))
    input_files = []
    for path in sorted(INPUT.glob("*.csv")):
        try:
            parsed = datetime.strptime(path.stem, "%Y-%m-%d")
        except ValueError:
            continue
        if path.name == f"{parsed:%Y-%m-%d}.csv":
            input_files.append(path)
    bad = 0
    for path in input_files:
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                try:
                    game_id = row["event_id"].strip()
                    captured = parse_time(row["snapshot_utc"])
                    kickoff = parse_time(row["kickoff_utc"])
                    updated = parse_time(row.get("book_last_update"))
                    book = (row.get("sportsbook_key") or row.get("sportsbook") or "").strip()
                    home_price = int(row["home_moneyline"])
                    away_price = int(row["away_moneyline"])
                    if not all((game_id, captured, kickoff, book)):
                        raise ValueError("Missing essential field")
                    if captured >= kickoff:
                        continue
                    if updated is None or updated > captured or captured - updated > FRESHNESS:
                        continue
                    prob = no_vig(home_price, away_price)
                    if not 0 < prob < 1:
                        raise ValueError("Probability outside 0-1")
                    # Collapse duplicate quotes for same snapshot and bookmaker.
                    stamp = captured.isoformat()
                    quotes[game_id][stamp][book] = {
                        "prob": prob, "home_odds": home_price,
                        "away_odds": away_price,
                        "book_name": row.get("sportsbook") or book,
                        "captured": captured, "kickoff": kickoff,
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "updated": updated,
                    }
                except (ValueError, KeyError, TypeError, OverflowError):
                    bad += 1
    return quotes, len(input_files), bad

def load_results():
    if not RESULTS.exists():
        return {}
    results = {}
    with RESULTS.open(newline="", encoding="utf-8") as file:
        for item in csv.DictReader(file):
            game_id = (item.get("event_id") or "").strip()
            winner = (item.get("winner") or "").strip()
            status = (item.get("status") or "").strip().lower()
            if game_id and winner and status == "final":
                results[game_id] = winner
    return results

def qualified_snapshots(snapshots):
    points = []
    for stamp, books in snapshots.items():
        if len(books) < MIN_BOOKS:
            continue
        sample = next(iter(books.values()))
        # Stable ordering: group by captured instant, not bookmaker provider update.
        probability = statistics.median(q["prob"] for q in books.values())
        points.append((sample["captured"], probability, books, sample))
    return sorted(points, key=lambda x: x[0])

def forecast_rows(quotes, results):
    records = []
    for event_id, snapshots in quotes.items():
        series = qualified_snapshots(snapshots)
        if not series:
            continue
        first_time, first_prob, first_books, info = series[0]
        last_time, last_prob, last_books, _ = series[-1]
        best_home = max(first_books.values(), key=lambda q: q["home_odds"])
        best_away = max(first_books.values(), key=lambda q: q["away_odds"])
        kickoff = info["kickoff"]
        # Last observed is NOT a closing line unless collected near kickoff.
        close_candidate = (
            last_time > first_time and
            timedelta(0) <= kickoff - last_time <= CLOSE_WINDOW
        )
        winner = results.get(event_id)
        home_won = None
        if winner == info["home_team"]:
            home_won = 1
        elif winner == info["away_team"]:
            home_won = 0
        # Tie/no-contest/unmatched names excluded from binary accuracy metrics.
        p = first_prob
        brier = (p - home_won) ** 2 if home_won is not None else None
        log_loss = -(home_won * math.log(p) + (1 - home_won) * math.log(1 - p)) if home_won is not None else None
        records.append({
            "event_id": event_id,
            "kickoff_utc": kickoff.isoformat(),
            "away_team": info["away_team"],
            "home_team": info["home_team"],
            "forecast_utc": first_time.isoformat(),
            "books_at_forecast": len(first_books),
            "home_probability": round(p, 8),
            "away_probability": round(1 - p, 8),
            "initial_best_home_book": best_home["book_name"],
            "initial_best_home_odds": best_home["home_odds"],
            "initial_best_away_book": best_away["book_name"],
            "initial_best_away_odds": best_away["away_odds"],
            "latest_snapshot_utc": last_time.isoformat(),
            "latest_home_probability": round(last_prob, 8),
            "home_probability_change_pp": round(100 * (last_prob - first_prob), 3),
            "near_kickoff_reference": "YES" if close_candidate else "NO",
            "home_won": "" if home_won is None else home_won,
            "brier": "" if brier is None else round(brier, 6),
            "log_loss": "" if log_loss is None else round(log_loss, 6),
            "research_status": "NO VERIFIED EDGE",
        })
    return sorted(records, key=lambda r: (r["kickoff_utc"], r["event_id"]))

def write_report(records, input_files, rejected):
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "model9_forecasts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FORECAST_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    evaluated = [r for r in records if r["home_won"] != ""]
    near_close = [r for r in records if r["near_kickoff_reference"] == "YES"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Model 9 — NFL Market Intelligence",
        "",
        f"Generated: `{now}`",
        "",
        "> **Research only — NO VERIFIED EDGE.** Prices and market consensus are not independently validated win probabilities.",
        "",
        "## Pipeline summary",
        "",
        f"- Odds files read: **{input_files}**",
        f"- Pregame games with at least {MIN_BOOKS} fresh books: **{len(records)}**",
        f"- Quotes rejected due to malformed fields or prices: **{rejected}**",
        f"- Games with an observed quote within 3 hours of kickoff after the initial snapshot: **{len(near_close)}**",
        f"- Games with verified results supplied: **{len(evaluated)}**",
        "",
        "## Pregame baseline and movement",
        "",
        "| Game | Kickoff (UTC) | First market home % | Latest home % | Change (pp) | Best first home | Best first away | Near kickoff? |",
        "|---|---|---:|---:|---:|---|---|---|",
    ]
    for r in records:
        matchup = f"{r['away_team']} @ {r['home_team']}"
        lines.append(
            f"| {matchup} | {r['kickoff_utc'][:16]} | "
            f"{r['home_probability']*100:.2f}% | {r['latest_home_probability']*100:.2f}% | "
            f"{r['home_probability_change_pp']:+.3f} | "
            f"{r['initial_best_home_book']} ({r['initial_best_home_odds']:+d}) | "
            f"{r['initial_best_away_book']} ({r['initial_best_away_odds']:+d}) | "
            f"{r['near_kickoff_reference']} |"
        )
    if not records:
        lines.append("| No eligible snapshots yet | — | — | — | — | — | — | — |")
    lines += ["", "## Outcome validation", ""]
    if evaluated:
        brier = statistics.mean(float(r["brier"]) for r in evaluated)
        logloss = statistics.mean(float(r["log_loss"]) for r in evaluated)
        accuracy = statistics.mean(
            (float(r["home_probability"]) >= .5) == bool(int(r["home_won"]))
            for r in evaluated
        )
        lines += [
            f"- Evaluated games: **{len(evaluated)}**",
            f"- Market baseline Brier score: **{brier:.4f}** (lower is better)",
            f"- Market baseline log loss: **{logloss:.4f}** (lower is better)",
            f"- Market baseline winner accuracy: **{accuracy:.1%}**",
            "",
            "This is a market baseline, **not** an independently trained predictive model.",
        ]
    else:
        lines += [
            "No final outcomes supplied. Do **not** report accuracy, ROI, or model profitability yet.",
            "",
            "To add results, create `data/results.csv` with columns",
            "`event_id,status,winner`. Use `final` and the exact full team name; ties are excluded.",
        ]
    lines += [
        "",
        "## Methodology and limitations",
        "",
        "- Snapshot rows are grouped by event ID, capture time and sportsbook; only quotes no more than 30 minutes stale are eligible.",
        "- Each baseline forecast is the **median bookmaker no-vig home probability at the first qualifying pregame snapshot** (at least four bookmakers).",
        "- Later probabilities are reported solely as observed movements; they never alter the initial forecast.",
        "- A quote collected within 3 hours of kickoff is labelled **near kickoff**, not a confirmed true closing line.",
        "- The best price is the highest American moneyline for each side, among books available at the *first* eligible snapshot.",
        "- No positive-EV betting signals are issued. Historical performance of prior statistical models failed to show a reliable edge.",
        "- API event IDs may differ from NFLverse game IDs. Match by teams and kickoff date only with explicit validation.",
        "- Results are optional and must be independently verified; do not infer wins from moneyline odds.",
        "",
    ]
    (OUTPUT / "model9_dashboard.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Model 9: {len(records)} qualifying games, {len(evaluated)} evaluated results.")
    print("Reports: reports/model9_forecasts.csv, reports/model9_dashboard.md")

if __name__ == "__main__":
    quotes, files, rejected = load_quotes()
    data = forecast_rows(quotes, load_results())
    write_report(data, files, rejected)
