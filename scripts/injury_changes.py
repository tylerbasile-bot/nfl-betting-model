#!/usr/bin/env python3
"""Detect changes between *observed* QB/OL report snapshots, without hindsight.

Uses the last record for each player/week within each daily source snapshot,
and compares only identical season+week+team+player keys. Missing entries do
not imply recovery. A report row is not proof the player is a starter.
"""
import csv
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("data/injury_observations")
CSV_OUT=Path("reports/injury_changes.csv")
MD_OUT=Path("reports/injury_changes.md")
FIELDS=["previous_observed_utc","current_observed_utc","season","week",
        "team","player_id","player_name","position","group","change_type",
        "prior_report_status","current_report_status",
        "prior_practice_status","current_practice_status",
        "source_date_modified"]

def read_rows(path):
    with path.open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def latest_rows(records):
    """Deduplicate source's multiple injury dates per player for each week."""
    best={}
    for i,r in enumerate(records):
        player=(r.get("gsis_id") or r.get("full_name") or "").strip()
        if not player:
            continue
        key=(r.get("season",""),r.get("week",""),r.get("team",""),player,r.get("group",""))
        rank=(r.get("source_date_modified") or "",i)
        if key not in best or rank>best[key][0]:
            best[key]=(rank,r)
    return {key:row for key,(_,row) in best.items()}

def compare(previous,current):
    old=latest_rows(previous)
    new=latest_rows(current)
    changes=[]
    for key,now in new.items():
        before=old.get(key)
        if before is None:
            change="FIRST_OBSERVED_IN_THIS_WEEK"
        elif ((now.get("report_status") or "").strip().upper()!=(before.get("report_status") or "").strip().upper()
           or (now.get("practice_status") or "").strip().upper()!=(before.get("practice_status") or "").strip().upper()):
            change="REPORTED_STATUS_CHANGED"
        else:
            continue
        changes.append({
            "previous_observed_utc":before.get("observed_utc","") if before else "",
            "current_observed_utc":now.get("observed_utc",""),
            "season":now.get("season",""),"week":now.get("week",""),
            "team":now.get("team",""),
            "player_id":now.get("gsis_id",""),
            "player_name":now.get("full_name",""),
            "position":now.get("position",""),
            "group":now.get("group",""),"change_type":change,
            "prior_report_status":before.get("report_status","") if before else "",
            "current_report_status":now.get("report_status",""),
            "prior_practice_status":before.get("practice_status","") if before else "",
            "current_practice_status":now.get("practice_status",""),
            "source_date_modified":now.get("source_date_modified",""),
        })
    return sorted(changes,key=lambda r:(r["team"],r["group"],r["player_name"],r["week"]))

def main():
    files=sorted(ROOT.glob("????-??-??.csv"))
    changes=compare(read_rows(files[-2]),read_rows(files[-1])) if len(files)>1 else []
    CSV_OUT.parent.mkdir(parents=True,exist_ok=True)
    with CSV_OUT.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(changes)
    status_changes=[r for r in changes if r["change_type"]=="REPORTED_STATUS_CHANGED"]
    new_entries=[r for r in changes if r["change_type"]=="FIRST_OBSERVED_IN_THIS_WEEK"]
    lines=[
        "# Observed QB / Offensive-Line Injury Changes","",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`","",
        "> Observation-only. No prediction of availability or validated positive EV.",
        "",
        f"- Dated observation files: **{len(files)}**",
        f"- Newly observed player-week entries: **{len(new_entries)}**",
        f"- Changes to reported statuses/practice participation: **{len(status_changes)}**","",
        "**Comparison scope:** only the two latest dated captures; no attempt to infer that a player recovered because a report row disappeared. Status dates supplied by the source are NOT proof of when bettors could have known the update.","",
    ]
    if len(files)<2:
        lines.append("At least two dated injury snapshots are required to measure observed changes.")
    else:
        lines+= [
            f"Previous source capture: `{files[-2].name}`; latest: `{files[-1].name}`.","",
            "| Team | Player | Group | Prior report | New report | Prior practice | New practice |",
            "|---|---|---|---|---|---|---|"
        ]
        for row in status_changes[:75]:
            values=[row[k] or "—" for k in (
                "team","player_name","group","prior_report_status",
                "current_report_status","prior_practice_status","current_practice_status")]
            values=[value.replace("|","/") for value in values]
            lines.append("| "+" | ".join(values)+" |")
        if not status_changes:
            lines.append("| No comparable status changes observed | — | — | — | — | — | — |")
        if len(status_changes)>75:
            lines.append(f"Additional {len(status_changes)-75} status changes are in the CSV report.")
    lines+=["","**Missing information is not a healthy designation; a report entry does not confirm starting status.**",""]
    MD_OUT.write_text("\n".join(lines),encoding="utf-8")
    print(f"Injury changes: {len(status_changes)} reported updates, {len(new_entries)} first observed; {len(files)} dated snapshots")

if __name__=="__main__":
    main()
