#!/usr/bin/env python3
"""Historical Model 13 replay on The Odds Gap free SAMPLE, not prospective ledger.

No retroactive selection is added to Model 13. Replays the fixed >=5 bookmaker,
>=2% indicative value, >=12h lead requirements on synchronized *actual* captured
quotes (never devig values supplied by source). One earliest qualifying instant
per game. Near-kickoff pricing is a proxy; no winnings/ROI without verified finals.
"""
import argparse
from pathlib import Path
import pandas as pd

SOURCE_COLUMNS=["snapshot_ts","sport","away","home","commence_time","market","side",
                "book","american_odds","game_id"]
FIELDS=["game_id","away","home","kickoff_utc","selection_utc","selected_side",
        "book","offered_odds","reference_prob","break_even_prob","apparent_ev",
        "reference_books","near_kickoff_utc","near_kickoff_prob",
        "market_shift_pp","same_book_near_kickoff_utc","same_book_near_kickoff_odds",
        "same_book_implied_shift_pp","historical_data_status"]
MIN_OTHERS=4
MIN_EV=0.02
MIN_LEAD_HOURS=12
MAX_SNAPSHOT_AGE_MINUTES=15
NEAR_KICKOFF_HOURS=3

def implied(odds):
    return -odds/(100-odds) if odds<0 else 100/(100+odds)

def profit(odds):
    return odds/100 if odds>0 else 100/(-odds)

def load_sample(path):
    dtype={"sport":"string","market":"string","side":"string","book":"string",
           "game_id":"string","home":"string","away":"string"}
    chunks=[]
    raw=0
    for frame in pd.read_csv(path,chunksize=150_000,dtype=dtype,usecols=lambda c:c in SOURCE_COLUMNS):
        raw+=len(frame)
        frame=frame[(frame["sport"]=="americanfootball_nfl")&
                    (frame["market"].str.lower()=="ml")&
                    (frame["side"].str.lower().isin(["home","away"]))].copy()
        if len(frame):chunks.append(frame)
    if not chunks:
        return raw,pd.DataFrame(columns=SOURCE_COLUMNS)
    df=pd.concat(chunks,ignore_index=True)
    df["snapshot_ts"]=pd.to_datetime(df["snapshot_ts"],utc=True,errors="coerce")
    df["commence_time"]=pd.to_datetime(df["commence_time"],utc=True,errors="coerce")
    df["american_odds"]=pd.to_numeric(df["american_odds"],errors="coerce")
    df=df.dropna(subset=["snapshot_ts","commence_time","american_odds",
                         "game_id","book","side","home","away"])
    df=df[(df["snapshot_ts"]<df["commence_time"])&
          (df["american_odds"]!=0)].copy()
    return raw,df

def pair_quotes(df):
    """One paired, coherent two-way quote per game/snapshot/book."""
    if df.empty:return pd.DataFrame()
    # In case a provider exports duplicates, skip ambiguous pairs entirely.
    group=["game_id","snapshot_ts","book"]
    counts=df.groupby(group+["side"],dropna=False).size()
    valid=counts[counts==1].reset_index()[group+["side"]]
    df=df.merge(valid,on=group+["side"],how="inner")
    pairs=df.pivot_table(index=group,columns="side",values="american_odds",
                         aggfunc="first").dropna(subset=["home","away"]).reset_index()
    meta=df.groupby(group,as_index=False).agg(
        commence_time=("commence_time","first"),home_team=("home","first"),away_team=("away","first")
    )
    pairs=pairs.merge(meta,on=group,how="inner")
    pairs["home_prob"]=pairs.apply(
        lambda r:implied(r["home"])/(implied(r["home"])+implied(r["away"])),axis=1)
    pairs["lead_hours"]=(pairs["commence_time"]-pairs["snapshot_ts"]).dt.total_seconds()/3600
    return pairs

def replay(pairs):
    """Replay selections at earliest >=5-book coherent captured instant."""
    if pairs.empty:return pd.DataFrame(columns=FIELDS),{}
    selected=[]
    stats={"eligible_instant_groups":0,"snapshot_groups_with_5_books":0,
           "games_with_5_books":0,"games_with_frozen_pick":0}
    for game,game_rows in pairs.groupby("game_id",sort=True):
        # Enforce exact matching timestamps, avoiding stale/asynchronous books.
        instants=list(game_rows.groupby("snapshot_ts",sort=True))
        made=False
        has_five=False
        for stamp,group in instants:
            if len(group)<5:continue
            has_five=True
            stats["snapshot_groups_with_5_books"]+=1
            lead=float(group["lead_hours"].min())
            if lead<MIN_LEAD_HOURS:continue
            stats["eligible_instant_groups"]+=1
            # Ignore contradictory event metadata, no inferred team matching.
            if group["commence_time"].nunique()!=1 or group["home_team"].nunique()!=1 or group["away_team"].nunique()!=1:
                continue
            choices=[]
            for _,q in group.iterrows():
                others=group[group["book"]!=q["book"]]["home_prob"]
                if len(others)<MIN_OTHERS:continue
                ref_home=float(others.median())
                for side in ("HOME","AWAY"):
                    ref=ref_home if side=="HOME" else 1-ref_home
                    price=float(q["home"] if side=="HOME" else q["away"])
                    ev=ref*(1+profit(price))-1
                    if ev>=MIN_EV:
                        choices.append((ev,side,str(q["book"]),price,ref,len(others)))
            if not choices:continue
            # Fixed tie-breaker: highest EV, then side/book for reproducibility.
            ev,side,book,price,ref,n=sorted(choices,key=lambda x:(-x[0],x[1],x[2]))[0]
            info=group.iloc[0]
            selected.append({
                "game_id":str(game),"away":str(info["away_team"]),
                "home":str(info["home_team"]),"kickoff_utc":info["commence_time"],
                "selection_utc":stamp,"selected_side":side,"book":book,
                "offered_odds":price,"reference_prob":ref,
                "break_even_prob":implied(price),"apparent_ev":ev,"reference_books":n
            })
            made=True
            break
        if has_five:stats["games_with_5_books"]+=1
        if made:stats["games_with_frozen_pick"]+=1
    results=[]
    for pick in selected:
        r=pick.copy()
        bygame=pairs[pairs["game_id"]==pick["game_id"]]
        close=bygame[(bygame["snapshot_ts"]>pick["selection_utc"])&
                     (bygame["snapshot_ts"]<pick["kickoff_utc"])&
                     ((pick["kickoff_utc"]-bygame["snapshot_ts"]).dt.total_seconds() <= 3*3600)]
        if close.empty:
            r.update(near_kickoff_utc="",near_kickoff_prob="",market_shift_pp="",
                     same_book_near_kickoff_utc="",same_book_near_kickoff_odds="",
                     same_book_implied_shift_pp="",historical_data_status="NO_NEAR_KICKOFF_QUOTE")
        else:
            # Use latest timestamp with 5+ books; median all books, independent of future outcomes.
            ordered=list(close.groupby("snapshot_ts",sort=True))
            qualified=[(time,g) for time,g in ordered if len(g)>=5]
            if qualified:
                time,g=qualified[-1]
                median=float(g["home_prob"].median())
                p=median if pick["selected_side"]=="HOME" else 1-median
                r.update(near_kickoff_utc=time,near_kickoff_prob=p,
                         market_shift_pp=100*(p-pick["reference_prob"]))
            else:
                r.update(near_kickoff_utc="",near_kickoff_prob="",market_shift_pp="")
            same=close[close["book"]==pick["book"]].sort_values("snapshot_ts")
            if len(same):
                last=same.iloc[-1]
                odds=float(last["home"] if pick["selected_side"]=="HOME" else last["away"])
                r.update(same_book_near_kickoff_utc=last["snapshot_ts"],
                         same_book_near_kickoff_odds=odds,
                         same_book_implied_shift_pp=100*(implied(odds)-implied(pick["offered_odds"])))
            else:
                r.update(same_book_near_kickoff_utc="",same_book_near_kickoff_odds="",
                         same_book_implied_shift_pp="")
            r["historical_data_status"]=("NEAR_KICKOFF_REFERENCE" if qualified else "SAME_BOOK_ONLY" if len(same) else "INSUFFICIENT_NEAR_KICKOFF_BOOKS")
        results.append(r)
    return pd.DataFrame(results,columns=FIELDS),stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--outdir",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds/model13_sample")
    args=p.parse_args()
    raw,ml=load_sample(args.input)
    paired=pair_quotes(ml)
    picks,stats=replay(paired)
    out=Path(args.outdir)
    out.mkdir(parents=True,exist_ok=True)
    picks.to_csv(out/"historical_model13_sample_candidates.csv",index=False)
    diagnostics={
        "all_raw_rows":raw,
        "nfl_pregame_moneyline_side_rows":len(ml),
        "nfl_games":int(ml["game_id"].nunique()) if len(ml) else 0,
        "unique_snapshot_times":int(ml["snapshot_ts"].nunique()) if len(ml) else 0,
        "distinct_books":int(ml["book"].nunique()) if len(ml) else 0,
        "two_sided_paired_book_quotes":len(paired),
        "qualifying_historical_picks":len(picks),
        "with_near_kickoff_market_reference":int(picks["near_kickoff_utc"].notna().sum()) if len(picks) else 0,
        **stats,
        "note":"No outcomes or backtested ROI calculated. Not a true closing line or proven edge."
    }
    # Nonempty string is not a valid near-kickoff observation; calculate exactly.
    diagnostics["with_near_kickoff_market_reference"]=int((picks["near_kickoff_utc"]!="").sum()) if len(picks) else 0
    diagnostics["with_same_book_near_kickoff"]=int((picks["same_book_near_kickoff_utc"]!="").sum()) if len(picks) else 0
    lines=["# Historical Model 13 — free sample audit","",
           "> Retrospective market-price study only; prospective Model 13 ledger never modified.","",
           "| Metric | Value |","|---|---:|"]
    for name,value in diagnostics.items():
        lines.append(f"| {name.replace('_',' ')} | {value} |")
    lines+=["","## Limitations","",
            "- Select one first qualifying observation per game at an exactly synchronized snapshot timestamp.",
            "- Source may lack five simultaneous sportsbooks or near-kickoff records; no fabricated comparisons.",
            "- A historical sample week is not a statistical validation of positive EV.",
            "- No confirmed final-score matching or paper ROI is attempted here.",
            "- Distinct historical replay logic is isolated from original Model 13 prospective selection.",""]
    (out/"historical_model13_sample_audit.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
    print(f"Saved audit and candidates to {out}")

if __name__=="__main__":
    main()
