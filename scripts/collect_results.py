#!/usr/bin/env python3
"""Import final NFL scores from ESPN's public, unofficial scoreboard endpoint.

Only matches existing Model 10 prospective games, by exact full team names,
home/away side, and kickoff within six hours. Aborts ambiguous matches.
Does not overwrite existing results. Ties are recorded as ties, never binary wins.
ESPN endpoint is unofficial and may change or be temporarily unavailable.
"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FORECASTS = Path("data/model10/prospective_forecasts.csv")
OUTPUT = Path("data/results.csv")
ODDS_DIR = Path("data/odds")
FIELDS = ["event_id", "status", "winner", "home_score", "away_score",
          "source", "source_event_id", "verified_utc"]
BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(timezone.utc)

def load_csv(path):
    if not path.exists():
        return []
    with path.open(newline="",encoding="utf-8") as fp:
        return list(csv.DictReader(fp))

def get_scoreboard(day):
    url = BASE + "?" + urlencode({"dates":day.strftime("%Y%m%d")})
    req = Request(url,headers={"User-Agent":"nfl-market-research/1.0"})
    with urlopen(req,timeout=30) as response:
        return json.load(response)

def parse_final_event(event):
    competition=(event.get("competitions") or [{}])[0]
    status=competition.get("status",event.get("status",{})).get("type",{})
    if not (status.get("completed") is True and status.get("name")=="STATUS_FINAL"):
        return None
    competitors=competition.get("competitors",[])
    by_side={c.get("homeAway"):c for c in competitors}
    if set(by_side)!={"home","away"}:
        return None
    home,away=by_side["home"],by_side["away"]
    home_name=home.get("team",{}).get("displayName")
    away_name=away.get("team",{}).get("displayName")
    if not home_name or not away_name:
        return None
    try:
        hs=int(home["score"])
        aas=int(away["score"])
        when=parse_time(event["date"])
    except (KeyError,TypeError,ValueError):
        return None
    tied=hs==aas
    return {"home_team":home_name,"away_team":away_name,"home_score":hs,
            "away_score":aas,"event_time":when,"espn_id":str(event["id"]),
            "status":"tie" if tied else "final",
            "winner":"" if tied else (home_name if hs>aas else away_name)}

def refresh_kickoff_times(forecasts, odds_dir=ODDS_DIR):
    """Use the latest date-stamped pregame quote's kickoff for rescheduled games."""
    event_ids={row.get("event_id") for row in forecasts}
    latest={}
    if not odds_dir.exists():
        return forecasts
    for path in sorted(odds_dir.glob("*.csv")):
        try:
            parsed=datetime.strptime(path.stem,"%Y-%m-%d")
        except ValueError:
            continue
        if path.name!=f"{parsed:%Y-%m-%d}.csv":
            continue
        for quote in load_csv(path):
            event=quote.get("event_id")
            if event not in event_ids:
                continue
            stamp=parse_time(quote.get("snapshot_utc",""))
            kickoff=parse_time(quote.get("kickoff_utc",""))
            if not stamp or not kickoff:
                continue
            forecast=next(row for row in forecasts if row.get("event_id")==event)
            if (quote.get("home_team")!=forecast.get("home_team")
                or quote.get("away_team")!=forecast.get("away_team")):
                continue
            if event not in latest or stamp>latest[event][0]:
                latest[event]=(stamp,kickoff)
    return [
        {**row,"kickoff_utc":latest[row["event_id"]][1].isoformat()}
        if row.get("event_id") in latest else row
        for row in forecasts
    ]

def match_finals(forecasts, scoreboard_by_date, now):
    saved=[]
    used_provider_ids=set()
    for row in forecasts:
        kickoff=parse_time(row["kickoff_utc"])
        if kickoff >= now:  # future games never receive a final result
            continue
        candidates=[]
        for offset in (-1,0,1):
            date=(kickoff+timedelta(days=offset)).date()
            for raw in scoreboard_by_date.get(date,{}).get("events",[]):
                final=parse_final_event(raw)
                if final is None:
                    continue
                if (final["home_team"]==row["home_team"]
                    and final["away_team"]==row["away_team"]
                    and abs(final["event_time"]-kickoff)<=timedelta(hours=6)):
                    candidates.append(final)
        candidates={x["espn_id"]:x for x in candidates}
        if len(candidates)!=1:
            continue
        final=next(iter(candidates.values()))
        if final["espn_id"] in used_provider_ids:
            continue
        used_provider_ids.add(final["espn_id"])
        saved.append({
            "event_id":row["event_id"], "status":final["status"], "winner":final["winner"],
            "home_score":final["home_score"],"away_score":final["away_score"],
            "source":"espn_scoreboard","source_event_id":final["espn_id"],
            "verified_utc":now.isoformat(),
        })
    return saved

def main():
    now=datetime.now(timezone.utc)
    forecasts=refresh_kickoff_times(load_csv(FORECASTS))
    existing=load_csv(OUTPUT)
    existing_ids={r.get("event_id") for r in existing}
    pending=[r for r in forecasts if r.get("event_id") not in existing_ids
             and parse_time(r["kickoff_utc"])<now]
    if not pending:
        print("No completed, unmatched forecast events to check.")
        return
    dates=set()
    for row in pending:
        kickoff=parse_time(row["kickoff_utc"])
        for offset in (-1,0,1):
            dates.add((kickoff+timedelta(days=offset)).date())
    data={}
    try:
        for day in sorted(dates):
            data[day]=get_scoreboard(day)
    except (OSError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
        # Fail closed: do not write partial or guessed result data.
        print(f"Scoreboard temporarily unavailable ({type(exc).__name__}); no scores written.")
        return
    confirmed=match_finals(pending,data,now)
    if not confirmed:
        print(f"No unambiguous final outcomes among {len(pending)} unmatched games.")
        return
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with OUTPUT.open("a",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS)
        if stream.tell()==0:
            writer.writeheader()
        writer.writerows(confirmed)
    print(f"Matched and recorded {len(confirmed)} final games from scoreboard.")

if __name__=="__main__":
    main()
