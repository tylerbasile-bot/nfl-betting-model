#!/usr/bin/env python3
"""Free nflverse offense/defense EPA pregame ratings; separate from Model 13.

Only REG season run/pass plays with nonmissing EPA and actual play_type.
No current game, future week, end-season or result-derived predictors.
Rolling last-five team GAMES (not same-week plays) and season-to-date stats
ranked among teams with at least one completed prior game.
All teams ranked before each target game. By design Week 1 has no ratings.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from urllib.request import urlretrieve
import pandas as pd

ASSET="https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.parquet"
COLS=["season","week","season_type","game_id","home_team","away_team",
      "posteam","defteam","play_type","epa","success"]
TEAM_FIELDS=["season","week","team","prior_games","off_epa_per_play","def_epa_allowed_per_play",
"off_success_rate","def_success_allowed_rate","off_pass_epa","off_rush_epa",
"def_pass_epa_allowed","def_rush_epa_allowed","off_last5_epa","def_last5_epa_allowed",
"off_rank","def_rank","off_last5_rank","def_last5_rank"]
MATCHUP_FIELDS=["season","week","game_id","home_team","away_team","home_prior_games","away_prior_games",
"home_off_rank","home_def_rank","away_off_rank","away_def_rank",
"home_off_epa","home_def_epa_allowed","away_off_epa","away_def_epa_allowed",
"home_off_last5_epa","away_off_last5_epa","home_def_last5_epa_allowed","away_def_last5_epa_allowed",
"home_off_vs_away_def_epa_diff","away_off_vs_home_def_epa_diff"]

def load_year(year,cache,download):
    file=cache/f"play_by_play_{year}.parquet"
    if not file.exists():
        if not download:raise FileNotFoundError(f"Missing {file}. Re-run with --download.")
        cache.mkdir(parents=True,exist_ok=True)
        tmp=file.with_suffix(".download")
        try:
            print(f"Downloading season {year} from nflverse releases...")
            urlretrieve(ASSET.format(year=year),tmp)
            tmp.replace(file)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    # Projection avoids loading the entire giant PBP table into RAM.
    try:return pd.read_parquet(file,columns=COLS)
    except Exception as e:raise ValueError(f"Could not read {file}: {e}") from e

def games_and_plays(raw):
    missing=[c for c in COLS if c not in raw.columns]
    if missing:raise ValueError(f"Missing required nflverse columns: {missing}")
    raw=raw[raw["season_type"].eq("REG")].copy()
    raw["season"]=pd.to_numeric(raw["season"],errors="coerce")
    raw["week"]=pd.to_numeric(raw["week"],errors="coerce")
    raw=raw.dropna(subset=["season","week","game_id","home_team","away_team"])
    raw["season"]=raw["season"].astype(int)
    raw["week"]=raw["week"].astype(int)
    games=(raw[["season","week","game_id","home_team","away_team"]]
            .drop_duplicates().sort_values(["season","week","game_id"]).reset_index(drop=True))
    # Reject ambiguous game identifiers rather than creating competing team ratings.
    if games.duplicated(["season","game_id"]).any():
        raise ValueError("Conflicting NFL game identifiers/metadata")
    plays=raw[raw["play_type"].isin(["run","pass"])].copy()
    plays["epa"]=pd.to_numeric(plays["epa"],errors="coerce")
    plays["success"]=pd.to_numeric(plays["success"],errors="coerce")
    plays=plays.dropna(subset=["posteam","defteam","epa","success"])
    plays=plays[plays["posteam"].ne(plays["defteam"])]
    plays=plays[plays["success"].isin([0,1])]
    return games,plays

def weekly_game_team_stats(plays):
    """Each row aggregates a team's own offensive plays in one game."""
    if plays.empty:return pd.DataFrame()
    grouped=plays.groupby(["season","week","game_id","posteam","defteam"],as_index=False).agg(
        count=("epa","size"),sum_epa=("epa","sum"),sum_success=("success","sum"))
    return grouped

def per_game_records(plays):
    """Offensive and allowed defensive rows; pass/rush separated."""
    if plays.empty:return []
    def extract(frame):
        p=frame["play_type"].eq("pass")
        r=frame["play_type"].eq("run")
        return dict(
            plays=len(frame), epa_sum=float(frame["epa"].sum()),
            success_sum=float(frame["success"].sum()),
            pass_plays=int(p.sum()),pass_epa_sum=float(frame.loc[p,"epa"].sum()),
            rush_plays=int(r.sum()),rush_epa_sum=float(frame.loc[r,"epa"].sum()))
    data=[]
    for (season,week,game_id),gp in plays.groupby(["season","week","game_id"],sort=True):
        # Deduplicate team side per game and ensure both offensive teams represented.
        home=gp["home_team"].iloc[0]
        away=gp["away_team"].iloc[0]
        if set(gp["posteam"].unique())-set([home,away]):continue
        if set(gp["defteam"].unique())-set([home,away]):continue
        for team in (home,away):
            off=gp[gp["posteam"]==team]
            allowed=gp[gp["defteam"]==team]
            if off.empty or allowed.empty:continue
            data.append({"season":int(season),"week":int(week),"game_id":str(game_id),
                         "team":str(team),"off":extract(off),"def":extract(allowed)})
    return data

def pool(records,part,prefix):
    total=sum(r[part]["plays"] for r in records)
    if not total:return {}
    den=lambda num,den:round(num/den,6) if den else None
    return {
        f"{prefix}_epa_per_play" if prefix=="off" else "def_epa_allowed_per_play":
            den(sum(r[part]["epa_sum"] for r in records),total),
        f"{prefix}_success_rate" if prefix=="off" else "def_success_allowed_rate":
            den(sum(r[part]["success_sum"] for r in records),total),
        f"{prefix}_pass_epa" if prefix=="off" else "def_pass_epa_allowed":
            den(sum(r[part]["pass_epa_sum"] for r in records),
                sum(r[part]["pass_plays"] for r in records)),
        f"{prefix}_rush_epa" if prefix=="off" else "def_rush_epa_allowed":
            den(sum(r[part]["rush_epa_sum"] for r in records),
                sum(r[part]["rush_plays"] for r in records)),
    }

def pregame_frames(games,records):
    """All game-week features built from prior weeks only.

    Teams on byes retain their most recent ratings and ranks are re-evaluated
    weekly against available league teams. All ratings reset by NFL season.
    """
    by_week=defaultdict(list)
    for record in records:by_week[(record["season"],record["week"])].append(record)
    out_team=[];out_matchup=[]
    for season,sg in games.groupby("season",sort=True):
        history=defaultdict(list)
        weeks=sorted(sg["week"].unique())
        league_teams=set(sg["home_team"]).union(sg["away_team"])
        for week in weeks:
            # Deliberate read-before-update, so no same-week games can leak.
            curr={}
            for team in sorted(league_teams):
                prior=history[team]
                if not prior:continue
                full_off=pool(prior,"off","off")
                full_def=pool(prior,"def","def")
                last_off=pool(prior[-5:],"off","off")
                last_def=pool(prior[-5:],"def","def")
                curr[team]={"season":int(season),"week":int(week),"team":team,
                            "prior_games":len(prior),**full_off,**full_def,
                            "off_last5_epa":last_off.get("off_epa_per_play"),
                            "def_last5_epa_allowed":last_def.get("def_epa_allowed_per_play")}
            # Tied team values get same competition rank; no fake ranking for Week 1.
            for metric,rank,descending in (
                ("off_epa_per_play","off_rank",True),
                ("def_epa_allowed_per_play","def_rank",False),
                ("off_last5_epa","off_last5_rank",True),
                ("def_last5_epa_allowed","def_last5_rank",False)):
                valid=[(k,r[metric]) for k,r in curr.items() if r.get(metric) is not None]
                ordered=sorted(valid,key=lambda pair:pair[1],reverse=descending)
                for i,(k,value) in enumerate(ordered):
                    curr[k][rank]=1+sum((x>value if descending else x<value) for _,x in ordered)
            for team in sorted(curr):out_team.append(curr[team])
            # Even if a team has no prior game (Week 1 / bye), create matchup
            # but explicitly leave all missing features as blanks, never zero.
            for game in sg[sg["week"].eq(week)].itertuples(index=False):
                home=curr.get(game.home_team,{})
                away=curr.get(game.away_team,{})
                field=lambda value:value if value is not None else ""
                h_off=home.get("off_epa_per_play")
                a_def=away.get("def_epa_allowed_per_play")
                a_off=away.get("off_epa_per_play")
                h_def=home.get("def_epa_allowed_per_play")
                out_matchup.append({
                    "season":int(season),"week":int(week),"game_id":game.game_id,
                    "home_team":game.home_team,"away_team":game.away_team,
                    "home_prior_games":home.get("prior_games",0),
                    "away_prior_games":away.get("prior_games",0),
                    "home_off_rank":field(home.get("off_rank")),"home_def_rank":field(home.get("def_rank")),
                    "away_off_rank":field(away.get("off_rank")),"away_def_rank":field(away.get("def_rank")),
                    "home_off_epa":field(h_off),"home_def_epa_allowed":field(h_def),
                    "away_off_epa":field(a_off),"away_def_epa_allowed":field(a_def),
                    "home_off_last5_epa":field(home.get("off_last5_epa")),
                    "away_off_last5_epa":field(away.get("off_last5_epa")),
                    "home_def_last5_epa_allowed":field(home.get("def_last5_epa_allowed")),
                    "away_def_last5_epa_allowed":field(away.get("def_last5_epa_allowed")),
                    "home_off_vs_away_def_epa_diff":field(h_off-a_def if h_off is not None and a_def is not None else None),
                    "away_off_vs_home_def_epa_diff":field(a_off-h_def if a_off is not None and h_def is not None else None),
                })
            # Only AFTER every feature for the week has been frozen do we ingest
            # the week's results/play statistics for next week's features.
            for record in by_week.get((int(season),int(week)),[]):
                history[record["team"]].append(record)
    return pd.DataFrame(out_team,columns=TEAM_FIELDS),pd.DataFrame(out_matchup,columns=MATCHUP_FIELDS)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",default="2022:2025",help="YYYY:YYYY inclusive, or comma-separated years. Recommend start with 2022:2025.")
    p.add_argument("--cache",default="/content/drive/MyDrive/NFL_Betting_Data/nflverse_pbp")
    p.add_argument("--outdir",default="/content/drive/MyDrive/NFL_Betting_Data/historical_matchups")
    p.add_argument("--download",action="store_true",help="Download missing free season PBP parquet files from official nflverse releases.")
    args=p.parse_args()
    if ":" in args.seasons:
        left,right=map(int,args.seasons.split(":"))
        years=list(range(left,right+1))
    else: years=[int(x.strip()) for x in args.seasons.split(",")]
    if not years or any(y<1999 or y>2026 for y in years):
        raise SystemExit("Select valid seasons, 1999–2026.")
    if len(years)>20:raise SystemExit("Limit to 20 seasons per invocation.")
    raw=[]
    for year in years:
        frame=load_year(year,Path(args.cache),args.download)
        print(f"Read {year}: {len(frame):,} plays")
        raw.append(frame)
    games,plays=games_and_plays(pd.concat(raw,ignore_index=True))
    print(f"Regular-season games: {len(games):,}; eligible run/pass plays: {len(plays):,}")
    recs=per_game_records(plays)
    teams,matchups=pregame_frames(games,recs)
    target=Path(args.outdir);target.mkdir(parents=True,exist_ok=True)
    teams.to_csv(target/"pregame_team_ratings.csv",index=False)
    matchups.to_csv(target/"pregame_matchup_features.csv",index=False)
    summary=[
        "# NFL Historical Pregame Efficiency Ratings","",
        "Source: nflverse official free play-by-play release (run/pass plays, regular season).",
        f"Seasons requested: {args.seasons}.",
        f"Regular-season games: {len(games)}; eligible run/pass plays: {len(plays)}.",
        f"Team-week pregame ratings with prior games: {len(teams)}.",
        f"Game matchup feature rows (including unranked Week 1): {len(matchups)}.","",
        "**No future leakage:** all ratings for Week N depend only on Weeks < N of the SAME season; no current-week game is included.",
        "Rank 1 offense = highest positive EPA per play; rank 1 defense = lowest EPA allowed per play.",
        "Success rate = nflverse success flag average, not the conventional binary 40/60/100 success-rate definition.",
        "EPA is pooled over eligible run/pass plays. No opponent-strength, injury, QB status, weather, market odds or score input is used.",
        "Ranks are recalculated before each week, among teams with prior games. Week 1 (and any no-history teams) have blank ratings.",
        "Rolling values use up to five most recent completed team games, never including current/future games.",
        "**Season reset:** Week 1 ratings are blank (not previous season). Add preseason priors separately only if justified.",
        "**Study only:** no impact on frozen prospective Model 13; not a verified positive-EV betting model.",""]
    (target/"README.md").write_text("\n".join(summary),encoding="utf-8")
    print("\n".join(summary))
    print("Output files:",target/"pregame_team_ratings.csv",target/"pregame_matchup_features.csv")

if __name__=="__main__":
    main()
