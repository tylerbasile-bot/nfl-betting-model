#!/usr/bin/env python3
"""Append independently verified finals for prospectively frozen Model 13 games.

Never alters candidate ledger. ESPN's public scoreboard is an unofficial
provider; exact team names, +/-6 hour kickoff, completed status required.
On any upstream failure, no partial final results are committed.
"""
import csv
from datetime import datetime,timedelta,timezone
from pathlib import Path
from collect_results import get_scoreboard,match_finals,parse_time,refresh_kickoff_times

LEDGER=Path("data/model13/frozen_price_candidates.csv")
RESULTS=Path("data/model13/verified_results.csv")
FIELDS=["event_id","status","winner","home_score","away_score","source","source_event_id","verified_utc"]

def read(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def pending_candidates(candidates,existing,now):
    done={r["event_id"] for r in existing if r.get("status") in {"final","tie"}}
    return [{"event_id":r["event_id"],"kickoff_utc":r["kickoff_utc"],
             "home_team":r["home_team"],"away_team":r["away_team"]}
            for r in candidates
            if r["event_id"] not in done and parse_time(r["kickoff_utc"])<now]

def collect(candidates,existing,now,fetch=get_scoreboard):
    pending=pending_candidates(candidates,existing,now)
    if not pending:return []
    dates=set()
    for row in pending:
        kickoff=parse_time(row["kickoff_utc"])
        for offset in (-1,0,1):
            dates.add((kickoff+timedelta(days=offset)).date())
    # Fetch complete date set before evaluating; fail closed on upstream failure.
    scoreboards={day:fetch(day) for day in sorted(dates)}
    return match_finals(pending,scoreboards,now)

def main():
    candidates=refresh_kickoff_times(read(LEDGER))
    existing=read(RESULTS)
    now=datetime.now(timezone.utc)
    try:
        new=collect(candidates,existing,now)
    except (OSError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        print(f"Model 13 results unavailable ({type(exc).__name__}); no results written.")
        return
    if not new:
        print("Model 13: no new unambiguous completed games.")
        return
    RESULTS.parent.mkdir(parents=True,exist_ok=True)
    with RESULTS.open("a",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        if f.tell()==0:writer.writeheader()
        writer.writerows(new)
    print(f"Model 13: appended {len(new)} independently verified final outcomes.")

if __name__=="__main__":
    main()
