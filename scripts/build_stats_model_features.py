#!/usr/bin/env python3
"""Build leak-safe pregame football features for the separate Stats Model.

Uses regular-season nflverse play-by-play. Each team's features for a target
week use only completed team games from earlier weeks in that same season.
"""
import argparse
from collections import defaultdict
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

ASSET = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.parquet"
COLS = [
    "season", "week", "season_type", "game_id", "home_team", "away_team",
    "posteam", "defteam", "play_type", "pass_attempt", "sack", "passing_yards",
    "pass_touchdown", "interception", "sack_yards", "fumble_lost",
    "rush_attempt", "yards_gained", "yardline_100", "touchdown", "drive",
    "epa", "success",
]
METRICS = (
    "any_a", "turnover_margin", "explosive_rate", "redzone_td_rate",
    "success_rate", "epa_per_play",
)
SIDES = ("off", "def_allowed")
MATCHUP_FIELDS = [
    "season", "week", "game_id", "home_team", "away_team",
    "home_prior_games", "away_prior_games",
] + [
    f"{side}_{team}_{metric}"
    for team in ("home", "away")
    for side in SIDES
    for metric in METRICS
]


def read_year(year, cache, download):
    path = cache / f"play_by_play_{year}.parquet"
    if not path.exists():
        if not download:
            raise FileNotFoundError(f"Missing {path}; rerun with --download.")
        cache.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".download")
        try:
            print(f"Downloading nflverse play-by-play for {year}...")
            urlretrieve(ASSET.format(year=year), temp)
            temp.replace(path)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    return pd.read_parquet(path, columns=COLS)


def make_game_stats(pbp):
    missing = sorted(set(COLS) - set(pbp.columns))
    if missing:
        raise ValueError(f"nflverse play-by-play is missing columns: {missing}")
    x = pbp[pbp["season_type"].eq("REG") & pbp["play_type"].isin(["run", "pass"])].copy()
    for col in ("season", "week", "pass_attempt", "sack", "passing_yards",
                "pass_touchdown", "interception", "sack_yards", "fumble_lost",
                "rush_attempt", "yards_gained", "yardline_100", "touchdown",
                "epa", "success"):
        x[col] = pd.to_numeric(x[col], errors="coerce")
    x = x.dropna(subset=["season", "week", "game_id", "posteam", "defteam"])
    x["season"] = x["season"].astype(int)
    x["week"] = x["week"].astype(int)
    for col in ("pass_attempt", "sack", "pass_touchdown", "interception",
                "fumble_lost", "rush_attempt", "touchdown"):
        x[col] = x[col].fillna(0)
    x["yards_gained"] = x["yards_gained"].fillna(0)
    x["drive"] = x["drive"].fillna(-1)

    rows = []
    group_keys = ["season", "week", "game_id", "posteam", "defteam"]
    for keys, plays in x.groupby(group_keys, sort=True):
        season, week, game_id, team, opponent = keys
        pass_attempts = plays["pass_attempt"].eq(1) & plays["sack"].ne(1)
        sacks = plays["sack"].eq(1)
        attempts = int(pass_attempts.sum())
        sack_count = int(sacks.sum())
        denominator = attempts + sack_count
        pass_yards = plays.loc[pass_attempts, "passing_yards"].fillna(0).sum()
        pass_tds = plays.loc[pass_attempts, "pass_touchdown"].sum()
        interceptions = plays.loc[pass_attempts, "interception"].sum()
        sack_loss = plays.loc[sacks, "sack_yards"].abs().fillna(0).sum()
        any_a = ((pass_yards + 20 * pass_tds - 45 * interceptions - sack_loss) / denominator
                 if denominator else np.nan)

        scrimmage_plays = plays[plays["play_type"].isin(["run", "pass"])]
        explosive = scrimmage_plays["yards_gained"].ge(20).sum()
        explosive_rate = explosive / len(scrimmage_plays) if len(scrimmage_plays) else np.nan
        success_rate = pd.to_numeric(scrimmage_plays["success"], errors="coerce").mean()
        epa_per_play = pd.to_numeric(scrimmage_plays["epa"], errors="coerce").mean()

        drive_rows = scrimmage_plays.groupby("drive", dropna=False).agg(
            reached_redzone=("yardline_100", lambda s: pd.to_numeric(s, errors="coerce").le(20).any()),
            touchdown=("touchdown", "max"),
        )
        redzone = drive_rows[drive_rows["reached_redzone"]]
        redzone_td_rate = redzone["touchdown"].mean() if len(redzone) else np.nan
        giveaways = plays["interception"].sum() + plays["fumble_lost"].sum()
        rows.append({
            "season": int(season), "week": int(week), "game_id": str(game_id),
            "team": str(team), "opponent": str(opponent),
            "any_a": float(any_a) if pd.notna(any_a) else np.nan,
            "giveaways": float(giveaways),
            "explosive_rate": float(explosive_rate) if pd.notna(explosive_rate) else np.nan,
            "redzone_td_rate": float(redzone_td_rate) if pd.notna(redzone_td_rate) else np.nan,
            "success_rate": float(success_rate) if pd.notna(success_rate) else np.nan,
            "epa_per_play": float(epa_per_play) if pd.notna(epa_per_play) else np.nan,
        })

    stats = pd.DataFrame(rows)
    if stats.empty:
        raise ValueError("No team-game rows were built from regular-season play-by-play.")
    if stats.duplicated(["season", "week", "game_id", "team"]).any():
        raise ValueError("Duplicate team-game stats; refusing ambiguous ratings.")

    # A team's takeaways are its opponent's giveaways from that same game.
    opp = stats[["season", "week", "game_id", "team", "giveaways"]].rename(
        columns={"team": "opponent", "giveaways": "takeaways"})
    stats = stats.merge(opp, on=["season", "week", "game_id", "opponent"], how="left", validate="one_to_one")
    stats["turnover_margin"] = stats["takeaways"] - stats["giveaways"]
    stats["def_allowed_any_a"] = stats.groupby(
        ["season", "week", "game_id"])["any_a"].transform(lambda s: s.iloc[::-1].to_numpy())
    stats["def_allowed_explosive_rate"] = stats.groupby(
        ["season", "week", "game_id"])["explosive_rate"].transform(lambda s: s.iloc[::-1].to_numpy())
    stats["def_allowed_redzone_td_rate"] = stats.groupby(
        ["season", "week", "game_id"])["redzone_td_rate"].transform(lambda s: s.iloc[::-1].to_numpy())
    stats["def_allowed_success_rate"] = stats.groupby(
        ["season", "week", "game_id"])["success_rate"].transform(lambda s: s.iloc[::-1].to_numpy())
    stats["def_allowed_epa_per_play"] = stats.groupby(
        ["season", "week", "game_id"])["epa_per_play"].transform(lambda s: s.iloc[::-1].to_numpy())
    return stats


def build_matchups(games, team_stats):
    stats_by_week = defaultdict(list)
    for row in team_stats.to_dict("records"):
        stats_by_week[(row["season"], row["week"])].append(row)
    out = []
    for season, season_games in games.groupby("season", sort=True):
        history = defaultdict(list)
        teams = set(season_games["home_team"]) | set(season_games["away_team"])
        for week in sorted(season_games["week"].unique()):
            ratings = {}
            for team in teams:
                prior = history[team][-5:]
                if not prior:
                    continue
                ratings[team] = {
                    "prior_games": len(history[team]),
                    **{m: float(np.nanmean([r[m] for r in prior])) for m in METRICS},
                    **{
                        f"def_allowed_{m}": float(np.nanmean([r[f"def_allowed_{m}"] for r in prior]))
                        for m in ("any_a", "explosive_rate", "redzone_td_rate", "success_rate", "epa_per_play")
                    },
                }
            for game in season_games[season_games["week"].eq(week)].itertuples(index=False):
                row = {
                    "season": int(season), "week": int(week), "game_id": str(game.game_id),
                    "home_team": str(game.home_team), "away_team": str(game.away_team),
                    "home_prior_games": len(history[game.home_team]),
                    "away_prior_games": len(history[game.away_team]),
                }
                for team_name, team in (("home", game.home_team), ("away", game.away_team)):
                    rating = ratings.get(team, {})
                    for metric in METRICS:
                        row[f"off_{team_name}_{metric}"] = rating.get(metric, np.nan)
                    for metric in ("any_a", "explosive_rate", "redzone_td_rate", "success_rate", "epa_per_play"):
                        row[f"def_allowed_{team_name}_{metric}"] = rating.get(f"def_allowed_{metric}", np.nan)
                out.append(row)
            # Freeze every matchup in the week before adding any game from that week.
            for record in stats_by_week.get((int(season), int(week)), []):
                history[record["team"]].append(record)
    features = pd.DataFrame(out)
    for col in MATCHUP_FIELDS:
        if col not in features:
            features[col] = np.nan
    return features[MATCHUP_FIELDS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2015:2025", help="Inclusive YYYY:YYYY range.")
    parser.add_argument("--cache", default="/content/drive/MyDrive/NFL_Betting_Data/stats_model/pbp")
    parser.add_argument("--outdir", default="/content/drive/MyDrive/NFL_Betting_Data/stats_model")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    first, last = map(int, args.seasons.split(":"))
    if first < 1999 or last > 2026 or first > last or last - first > 15:
        raise SystemExit("Choose a valid inclusive season range between 1999 and 2026.")
    frames = [read_year(y, Path(args.cache), args.download) for y in range(first, last + 1)]
    pbp = pd.concat(frames, ignore_index=True)
    games = (pbp[pbp["season_type"].eq("REG")][
        ["season", "week", "game_id", "home_team", "away_team"]]
        .drop_duplicates().copy())
    games["season"] = pd.to_numeric(games["season"], errors="coerce")
    games["week"] = pd.to_numeric(games["week"], errors="coerce")
    games = games.dropna(subset=["season", "week", "game_id", "home_team", "away_team"])
    games["season"] = games["season"].astype(int)
    games["week"] = games["week"].astype(int)
    if games.duplicated(["season", "week", "game_id"]).any():
        raise ValueError("Conflicting game identifiers in play-by-play.")
    features = build_matchups(games, make_game_stats(pbp))
    dest = Path(args.outdir)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "stats_model_pregame_features.csv"
    features.to_csv(path, index=False)
    print(f"Saved {len(features):,} pregame matchup rows to {path}")
    print("Ratings use prior same-season team games only; Week 1 remains unranked/missing.")


if __name__ == "__main__":
    main()
