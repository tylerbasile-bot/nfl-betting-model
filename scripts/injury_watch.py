#!/usr/bin/env python3
"""Descriptive injury watchboard; not a prediction, not verified starter availability."""
import csv
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

DATA=Path("data/injury_observations")
OUT=Path("reports/injury_watch.md")
UNCERTAIN={"OUT","DOUBTFUL","QUESTIONABLE","DNP","DID NOT PARTICIPATE","LIMITED"}

def main():
    files=sorted(DATA.glob("*.csv"))
    rows=[]
    if files:
        with files[-1].open(newline="",encoding="utf8") as f:
            rows=list(csv.DictReader(f))
    OUT.parent.mkdir(exist_ok=True)
    lines=[
        "# QB & Offensive-Line Injury Watch",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "> Observation-only. No starter classification, game-day availability prediction, or positive-EV signal.",
        "",
    ]
    if not rows:
        lines.append("No injury snapshots have been captured successfully yet.")
    else:
        lines+= [
            f"- Snapshot file: `{files[-1]}`",
            f"- QB/OL injury-report rows recorded: **{len(rows)}**",
            "",
            "The source may include prior weeks; below is only the largest observed week in the dataset, not automatically the current week's confirmed report.",
            "",
        ]
        def key(r):
            try:return (int(r.get("season") or 0),int(r.get("week") or 0))
            except ValueError:return (0,0)
        current=max(key(r) for r in rows)
        latest=[r for r in rows if key(r)==current]
        groups=defaultdict(list)
        for r in latest:
            groups[(r["team"],r["group"])].append(r)
        lines.extend([
            f"## Source season {current[0]}, week {current[1]}",
            "",
            "| Team | QB reports | OL reports | QB uncertain status | OL uncertain status |",
            "|---|---:|---:|---:|---:|",
        ])
        teams=sorted({t for t,_ in groups})
        for team in teams:
            q=groups.get((team,"QB"),[])
            o=groups.get((team,"OL"),[])
            def flagged(vals):
                return sum(
                    any(token in (r.get(field) or "").upper() for token in UNCERTAIN)
                    for r in vals
                    for field in ["report_status"] # practice rows are described, not scored as confirmed game-out
                )
            lines.append(f"| {team} | {len(q)} | {len(o)} | {flagged(q)} | {flagged(o)} |")
        lines+=["",
            "Counts represent **report entries**, not unique starters or confirmed absences. Missing report entries do not imply health.",
            "The observed timestamp is when our own pipeline fetched the source. Historical source modification dates do not prove past pregame availability.",
            ""]
    OUT.write_text("\n".join(lines),encoding="utf8")
    print(f"Injury watchboard saved: {OUT}; source snapshots={len(files)}")

if __name__=="__main__":main()
