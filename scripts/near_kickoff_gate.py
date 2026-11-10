#!/usr/bin/env python3
"""Decide whether an extra pre-kickoff quote collection merits an API call.

GitHub scheduled workflows can run frequently, but only fetch if an already-
tracked game is 10–70 minutes from kickoff. No network, no API key required.
"""
import csv
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path

LEDGER=Path("data/model10/prospective_forecasts.csv")
MIN_BEFORE=timedelta(minutes=10)
MAX_BEFORE=timedelta(minutes=70)
MIN_SINCE_PREVIOUS=timedelta(minutes=25)
HISTORY=Path("data/odds")

def dt(value):
    return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)

def read(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def eligible(now,forecast_rows,quote_rows):
    event_ids={
        r["event_id"] for r in forecast_rows
        if MIN_BEFORE <= dt(r["kickoff_utc"])-now <= MAX_BEFORE
    }
    if not event_ids:return []
    recent={}
    for r in quote_rows:
        if r.get("event_id") not in event_ids:continue
        stamp=dt(r["snapshot_utc"])
        event=r["event_id"]
        if event not in recent or stamp>recent[event]:recent[event]=stamp
    return sorted(event for event in event_ids if
                  event not in recent or now-recent[event]>=MIN_SINCE_PREVIOUS)

def main():
    now=datetime.now(timezone.utc)
    forecasts=read(LEDGER)
    # Near-kickoff games can be on either side of midnight UTC.
    quotes=[]
    for day in (now.date(),(now-timedelta(days=1)).date()):
        quotes.extend(read(HISTORY/f"{day.isoformat()}.csv"))
    games=eligible(now,forecasts,quotes)
    enabled=bool(games)
    output=os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as file:
            file.write(f"collect={'true' if enabled else 'false'}\n")
    print("NEAR-KICKOFF API GATE:", "COLLECT" if enabled else "SKIP")
    print("Tracked qualifying event IDs:",len(games))
    if games:print("IDs:",",".join(games))

if __name__=="__main__":main()
