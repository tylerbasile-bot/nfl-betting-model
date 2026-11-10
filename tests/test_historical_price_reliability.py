"""Regression tests: historical reliability audit never changes frozen data."""
import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_historical_price_reliability as audit
import backtest_free_odds_gap as historical

class HistoricalReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.now=pd.Timestamp("2026-10-19T04:00:00Z")
        self.kickoff=self.now+pd.Timedelta(hours=36)
        rows=[]
        for book in ["draftkings","fanduel","betmgm","betrivers","caesars","novig"]:
            for side,price in (("home",390 if book=="draftkings" else 280),("away",-400)):
                rows.append({"snapshot_ts":self.now,"commence_time":self.kickoff,
                             "book":book,"side":side,"american_odds":price,
                             "game_id":"g","home":"Home","away":"Away"})
        self.pairs=historical.pair_quotes(pd.DataFrame(rows))
        self.pick={
            "game_id":"g","away":"Away","home":"Home","book":"draftkings",
            "selected_side":"HOME","kickoff_utc":self.kickoff.isoformat(),
            "selection_utc":self.now.isoformat(),"offered_odds":"390",
            "reference_prob":str(self.pairs.loc[
                self.pairs["book"]!="draftkings","home_prob"].median()),
            "apparent_ev":"0.05"
        }

    def test_reliability_uses_other_books_only(self):
        result=audit.reliability([self.pick],self.pairs)[0]
        self.assertEqual(result["other_books"],5)
        self.assertEqual(result["synchronized_quote_check"],"YES")
        self.assertEqual(result["reference_recomputed_matches_frozen"],"YES")
        self.assertEqual(result["lead_bucket"],"24-48H")
        self.assertGreater(result["discrepancy_pp"],0)

    def test_missing_original_book_not_silently_scored(self):
        subset=self.pairs[self.pairs["book"]!="draftkings"].copy()
        result=audit.reliability([self.pick],subset)[0]
        self.assertIn("MISSING_SYNCHRONIZED",result["reliability_warning"])

    def test_novig_and_unknown_excluded_from_strict_replay(self):
        self.assertEqual(audit.venue("novig"),"EXCHANGE_OR_PREDICTION_MARKET")
        self.assertEqual(audit.venue("pinnacle"),"UNKNOWN_OR_UNVERIFIED")
        self.assertEqual(audit.venue("draftkings"),"ALLOWLIST_SPORTSBOOK")
        original={"game_id":"g","home":"Home","away":"Away","kickoff_utc":self.kickoff.isoformat(),
                  "outcome_status":"FINAL","home_score":"21","away_score":"14",
                  "won":"0","paper_profit_per_unit":"-1"}
        picks,stats=audit.sportsbook_replay(self.pairs,[original])
        self.assertEqual(stats["games_with_5_books"],1)
        self.assertEqual(len(picks),1)
        self.assertEqual(picks[0]["book"],"draftkings")
        self.assertEqual(picks[0]["won"],1)
        self.assertAlmostEqual(picks[0]["paper_profit_per_unit"],3.9)

    def test_leave_one_out_and_missing_finals(self):
        records=[
            {"game_id":"a","outcome_status":"FINAL","home_score":"24","away_score":"21",
             "paper_profit_per_unit":"3.0"},
            {"game_id":"b","outcome_status":"FINAL","home_score":"10","away_score":"20",
             "paper_profit_per_unit":"-1"},
            {"game_id":"c","outcome_status":"FUTURE_GAME","home_score":"","away_score":"",
             "paper_profit_per_unit":""},
        ]
        stats=audit.leave_one_out(records)
        self.assertEqual(stats["n"],2)
        self.assertAlmostEqual(stats["original_roi"],1.0)
        self.assertAlmostEqual(stats["minimum_roi"],-1)
        self.assertAlmostEqual(stats["maximum_roi"],3)

if __name__=="__main__":
    unittest.main()
