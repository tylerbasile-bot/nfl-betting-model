"""Offline checks for historical pregame feature/outcome join and strict chronology."""
import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import evaluate_historical_epa_probabilities as model

class ProbabilitiesTests(unittest.TestCase):
    def sample(self):
        feature=[]
        schedule=[]
        for yr in range(2015,2026):
            for i in range(4):
                gid=f"{yr}_05_{i}"
                home="A" if i%2 else "C"
                away="B" if i%2 else "D"
                row={"season":yr,"week":5,"game_id":gid,"home_team":home,
                     "away_team":away,"home_prior_games":4,"away_prior_games":4}
                for name in model.FEATURE_COLS:
                    if name not in row:row[name]=.1+i*.2+yr*.0001
                feature.append(row)
                schedule.append({"season":yr,"week":5,"game_id":gid,
                                 "home_team":home,"away_team":away,
                                 "game_type":"REG","home_score":21 if i%2 else 10,
                                 "away_score":14,"home_moneyline":-150,
                                 "away_moneyline":130})
        return pd.DataFrame(feature),pd.DataFrame(schedule)

    def test_join_and_scores(self):
        f,s=self.sample()
        df=model.normalize_data(f,s)
        self.assertEqual(len(df),44)
        self.assertEqual(len(df[df.split=="train"]),28)
        self.assertEqual(len(df[df.split=="validation"]),8)
        self.assertEqual(len(df[df.split=="historical_test"]),8)
        self.assertTrue(df["market_close_no_vig_home_prob"].notna().all())

    def test_mismatch_teams_raises(self):
        f,s=self.sample()
        s.loc[0,"home_team"]="OTHER"
        with self.assertRaises(ValueError):model.normalize_data(f,s)

    def test_relocated_team_aliases_match_without_changing_home_side(self):
        f,s=self.sample()
        f.loc[0,"home_team"]="OAK"
        s.loc[0,"home_team"]="LV"
        f.loc[1,"away_team"]="SD"
        s.loc[1,"away_team"]="LAC"
        f.loc[2,"home_team"]="STL"
        s.loc[2,"home_team"]="LA"
        df=model.normalize_data(f,s)
        self.assertEqual(len(df),44)

    def test_aliases_inside_standard_game_ids_are_joined(self):
        f,s=self.sample()
        f.loc[0,"game_id"]="2015_05_SD_OAK"
        f.loc[0,"away_team"]="SD"
        f.loc[0,"home_team"]="OAK"
        s.loc[0,"game_id"]="2015_05_LAC_LV"
        s.loc[0,"away_team"]="LAC"
        s.loc[0,"home_team"]="LV"
        df=model.normalize_data(f,s)
        self.assertEqual(len(df),44)
        self.assertIn("2015_05_SD_OAK",set(df.game_id))

    def test_canonical_game_key_collision_is_rejected(self):
        f,s=self.sample()
        f.loc[0,"game_id"]="2015_05_SD_OAK"
        f.loc[1,"game_id"]="2015_05_LAC_LV"
        with self.assertRaisesRegex(ValueError,"Canonical game keys collide"):
            model.normalize_data(f,s)

    def test_swapped_home_away_rejected_even_with_aliases(self):
        f,s=self.sample()
        f.loc[0,"home_team"]="OAK"
        f.loc[0,"away_team"]="SD"
        s.loc[0,"home_team"]="LAC"
        s.loc[0,"away_team"]="LV"
        with self.assertRaises(ValueError):
            model.normalize_data(f,s)

    def test_unknown_franchise_mismatch_rejected(self):
        f,s=self.sample()
        f.loc[0,"home_team"]="FAKE"
        with self.assertRaises(ValueError):
            model.normalize_data(f,s)

    def test_no_future_tuning_in_training_split(self):
        f,s=self.sample()
        df=model.normalize_data(f,s)
        result,_=model.train_and_score(df)
        self.assertTrue((result.football_home_prob.between(0,1)).all())
        self.assertTrue(result.football_brier.between(0,1).all())
        altered=df.copy()
        altered.loc[altered.season>=2024,"home_win"]=1-altered.loc[altered.season>=2024,"home_win"]
        again,_=model.train_and_score(altered)
        a=result[result.split=="train"].football_home_prob.reset_index(drop=True)
        b=again[again.split=="train"].football_home_prob.reset_index(drop=True)
        pd.testing.assert_series_equal(a,b)

    def test_no_moneyline_used_as_predictor(self):
        self.assertNotIn("home_moneyline",model.FEATURE_COLS)
        self.assertNotIn("away_moneyline",model.FEATURE_COLS)
        self.assertNotIn("home_score",model.FEATURE_COLS)
        self.assertNotIn("away_score",model.FEATURE_COLS)

    def test_ties_and_first_weeks_filtered(self):
        f,s=self.sample()
        s.loc[0,"home_score"]=14
        f.loc[1,"home_prior_games"]=0
        df=model.normalize_data(f,s)
        self.assertEqual(len(df),42)

if __name__=="__main__": unittest.main()
