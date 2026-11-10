"""Offline tests: Model 14 paired baseline, chronology, price filtering."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import evaluate_model14_market_plus_epa as model14
from evaluate_historical_epa_probabilities import FEATURE_COLS

def synthetic(n_games=10):
    features=[]; schedules=[]
    for yr in range(2015,2026):
        for i in range(n_games):
            key=f"{yr}_05_{i}"
            home=f"H{i%5}";away=f"A{i%5}"
            feature={"season":yr,"week":5,"game_id":key,"home_team":home,
                     "away_team":away,"home_prior_games":4,"away_prior_games":4}
            for j,c in enumerate(FEATURE_COLS):
                if c not in feature:
                    feature[c]=float((i%7-3)*0.03+(j%5)*0.02)
            features.append(feature)
            schedules.append({
                "season":yr,"week":5,"game_id":key,"game_type":"REG",
                "home_team":home,"away_team":away,
                "home_score":24 if (i+yr)%3 else 10,
                "away_score":14,"home_moneyline":-140+(i%3)*5,
                "away_moneyline":125-(i%3)*5})
    return pd.DataFrame(features),pd.DataFrame(schedules)

class Model14Tests(unittest.TestCase):
    def test_paired_splits_and_probabilities(self):
        f,s=synthetic()
        df=model14.prepare(f,s)
        self.assertEqual(len(df),110)
        out,market,combined=model14.fit_predict(df)
        self.assertEqual(len(out),110)
        self.assertEqual(len(out[out.split=="train"]),70)
        self.assertEqual(len(out[out.split=="validation"]),20)
        self.assertEqual(len(out[out.split=="historical_test"]),20)
        self.assertTrue(out.model14_combined_prob.between(0,1).all())
        self.assertTrue(out.market_calibrated_prob.between(0,1).all())
        self.assertTrue(np.isfinite(out.model14_combined_brier).all())
        self.assertTrue(np.allclose(out.model14_minus_market_brier,
                                    out.model14_combined_brier-out.market_brier))

    def test_missing_or_zero_moneyline_excluded_paired(self):
        f,s=synthetic()
        s.loc[0,"home_moneyline"]=np.nan
        s.loc[1,"away_moneyline"]=0
        df=model14.prepare(f,s)
        self.assertEqual(len(df),108)
        out,_,_=model14.fit_predict(df)
        self.assertEqual(len(out),108)
        self.assertEqual(out["market_brier"].notna().sum(),108)

    def test_future_test_outcomes_do_not_change_training_fit(self):
        f,s=synthetic()
        df=model14.prepare(f,s)
        orig,_,_=model14.fit_predict(df)
        changed=df.copy()
        changed.loc[changed.season>=2024,"home_win"]=1-changed.loc[changed.season>=2024,"home_win"]
        new,_,_=model14.fit_predict(changed)
        self.assertTrue(np.allclose(orig["model14_combined_prob"],new["model14_combined_prob"]))
        self.assertTrue(np.allclose(orig["market_calibrated_prob"],new["market_calibrated_prob"]))

    def test_relocation_aliases_still_checked(self):
        f,s=synthetic()
        f.loc[0,"home_team"]="OAK"
        s.loc[0,"home_team"]="LV"
        df=model14.prepare(f,s)
        self.assertEqual(len(df),110)
        s.loc[1,"home_team"]="FAKE"
        with self.assertRaises(ValueError):model14.prepare(f,s)

    def test_no_scores_as_model_features(self):
        for field in ("home_score","away_score","home_win","home_moneyline","away_moneyline"):
            self.assertNotIn(field,FEATURE_COLS)
        self.assertEqual(list(model14.TRAIN),list(range(2015,2022)))
        self.assertEqual(model14.TEST,(2024,2025))

    def test_report_discloses_historical_market_timing(self):
        f,s=synthetic()
        df=model14.prepare(f,s)
        out,_,_=model14.fit_predict(df)
        text=model14.report(out,{"train":70,"validation":20,"historical_test":20})
        self.assertIn("not known at an early-week",text)
        self.assertIn("Model 14 minus raw market",text)
        self.assertIn("2024–2025",text)

if __name__=="__main__":unittest.main()
