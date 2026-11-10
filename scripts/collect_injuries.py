#!/usr/bin/env python3
"""Daily observed NFLverse QB/offensive line injury report snapshots.

Historical nflverse date_modified is preserved but NOT treated as proof the
record was actually available to our pipeline at that time. No medical
inferences, starter assumptions or betting predictions are generated.
"""
import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError

SOURCE="https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv"
OUTDIR=Path("data/injury_observations")
QB={"QB"}
OL={"C","G","T","OT","OG","LT","RT","LG","RG"}
FIELDS=[
    "observed_utc","season","week","team","gsis_id","full_name","position",
    "group","report_primary_injury","report_status","practice_status",
    "source_date_modified","source_url"
]

def decode_injury_csv(content):
    """Decode UTF-8 CSVs, including files prefixed with a BOM."""
    return content.decode("utf-8-sig")

def select_rows(data,observed,source):
    chosen=[]
    for row in csv.DictReader(io.StringIO(data)):
        pos=(row.get("position") or "").strip().upper()
        if pos not in QB|OL:continue
        chosen.append({
            "observed_utc":observed,"season":row.get("season",""),
            "week":row.get("week",""),"team":row.get("team",""),
            "gsis_id":row.get("gsis_id",""),"full_name":row.get("full_name",""),
            "position":pos,"group":"QB" if pos in QB else "OL",
            "report_primary_injury":row.get("report_primary_injury",""),
            "report_status":row.get("report_status",""),
            "practice_status":row.get("practice_status",""),
            "source_date_modified":row.get("date_modified",""),
            "source_url":source,
        })
    return chosen

def main(now=None):
    now=now or datetime.now(timezone.utc)
    outfile=OUTDIR/f"{now:%Y-%m-%d}.csv"
    if outfile.exists():
        print(f"Already captured QB/OL injury snapshot for {now:%Y-%m-%d}; no overwrite.")
        return
    url=SOURCE.format(season=now.year)
    try:
        req=Request(url,headers={"User-Agent":"nfl-research-injury-snapshot/1.0"})
        with urlopen(req,timeout=35) as response:
            content=response.read(4_000_001)
            if len(content)>4_000_000:
                print("Injury file exceeds safety limit; skipping.")
                return
            text=decode_injury_csv(content)
        records=select_rows(text,now.isoformat(),url)
    except (HTTPError,URLError,TimeoutError,UnicodeDecodeError) as exc:
        print(f"Injury feed unavailable: {type(exc).__name__}; skipping without guesses.")
        return
    if not records:
        print("No QB or offensive-line injury observations found; skipping.")
        return
    OUTDIR.mkdir(parents=True,exist_ok=True)
    with outfile.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Saved {len(records)} observed QB/OL injury records to {outfile}")
    print("Historical source_date_modified is NOT a verified observation time.")

if __name__=="__main__":main()
