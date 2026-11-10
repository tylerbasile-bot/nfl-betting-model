#!/usr/bin/env python3
"""Capture pregame NFL moneylines from The Odds API.

Requires ODDS_API_KEY environment variable. No credentials are written to disk.
Run on GitHub Actions or locally. Research only; no betting recommendations.
"""
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
COLUMNS = [
    "snapshot_utc", "event_id", "kickoff_utc", "home_team", "away_team",
    "sportsbook_key", "sportsbook", "book_last_update", "home_moneyline",
    "away_moneyline", "home_no_vig"
]

def implied_probability(american):
    price = float(american)
    if price < 0:
        return -price / (100 - price)
    if price > 0:
        return 100 / (100 + price)
    raise ValueError("Invalid zero-valued American odds")

def capture():
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        raise SystemExit("Missing ODDS_API_KEY secret; no request made.")
    params = urlencode({
        "apiKey": key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "dateFormat": "iso",
    })
    request = Request(
        API_URL + "?" + params,
        headers={"User-Agent": "nfl-betting-model-research/1.0"},
    )
    try:
        with urlopen(request, timeout=40) as response:
            payload = json.load(response)
            remaining = response.headers.get("x-requests-remaining", "unknown")
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Odds API request failed: {type(exc).__name__}") from None

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    records = []
    for game in payload:
        try:
            kickoff = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError):
            continue
        if kickoff <= now:
            continue  # No in-game or post-game odds.
        home, away = game.get("home_team"), game.get("away_team")
        if not home or not away:
            continue
        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = {o.get("name"): o.get("price") for o in market.get("outcomes", [])}
                if home not in outcomes or away not in outcomes:
                    continue
                try:
                    hp = implied_probability(outcomes[home])
                    ap = implied_probability(outcomes[away])
                except (ValueError, TypeError):
                    continue
                records.append({
                    "snapshot_utc": timestamp,
                    "event_id": game["id"],
                    "kickoff_utc": game["commence_time"],
                    "home_team": home,
                    "away_team": away,
                    "sportsbook_key": book.get("key", ""),
                    "sportsbook": book.get("title", ""),
                    "book_last_update": market.get("last_update") or book.get("last_update", ""),
                    "home_moneyline": outcomes[home],
                    "away_moneyline": outcomes[away],
                    "home_no_vig": round(hp / (hp + ap), 8),
                })
    # A new dated CSV per UTC day avoids one continuously growing file.
    path = Path("data/odds") / f"{now:%Y-%m-%d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.exists()
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        if not existing:
            writer.writeheader()
        writer.writerows(records)
    print(f"Pregame games: {len(set(x['event_id'] for x in records))}")
    print(f"Bookmaker quotes saved: {len(records)}")
    print(f"Path: {path}")
    print(f"API requests remaining (reported): {remaining}")

if __name__ == "__main__":
    capture()
