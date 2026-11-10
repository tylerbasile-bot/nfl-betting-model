"""Offline tests for retrospective strict sportsbook and timing checks."""
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import backtest_free_odds_gap as base
import evaluate_historical_timing as study

class HistoricalTimingTests(unittest.TestCase):
    def setUp(self):
        self.now=pd.Timestamp("2026-10-25T17:00:00Z")
        self.books=["draftkings","fanduel","betmgm","betrivers","caesars","novig"]
        rows=[]
        # Each distinct snapshot is a complete bookmaker panel, with one
        # visibly favorable home moneyline at DraftKings only.
        for ahead in (100,60,40,20,8):
            stamp=self.now-pd.Timedelta(hours=ahead)
            for book in self.books:
                for side,price in [("home",390 if book=="draftkings" else 280),
                                   ("away",-390)]:
                    rows.append({
                        "game_id":"g1","home":"Home Team","away":"Away Team",
                        "snapshot_ts":stamp,"commence_time":self.now,
                        "book":book,"side":side,"american_odds":price
                    })
        self.pairs=base.pair_quotes(pd.DataFrame(rows))
        self.espn={
            "events":[{
                "id":"espn1","date":self.now.isoformat(),
                "competitions":[{
                    "status":{"type":{"completed":True,"name":"STATUS_FINAL"}},
                    "competitors":[
                        {"homeAway":"home","score":"27","team":{"displayName":"Home Team"}},
                        {"homeAway":"away","score":"20","team":{"displayName":"Away Team"}}
                    ]
                }]
            }]
        }

    def test_explicit_windows_choose_first_in_window_and_no_under12h(self):
        picks,metrics=study.create_scenarios(self.pairs)
        indexed={r["scenario"]:r for r in picks}
        expected={"STRICT_ALL_AVAILABLE":100,
                  "STRICT_WITHIN_72H":60,
                  "STRICT_WITHIN_48H":40,
                  "STRICT_WITHIN_24H":20,
                  "ALL_VENUES_WITHIN_72H":60,
                  "ALL_VENUES_WITHIN_48H":40,
                  "ALL_VENUES_WITHIN_24H":20}
        self.assertEqual(set(indexed),set(expected))
        for name,lead in expected.items():
            self.assertAlmostEqual(
                (pd.Timestamp(indexed[name]["kickoff_utc"])-pd.Timestamp(indexed[name]["selection_utc"])).total_seconds()/3600,lead)
        self.assertEqual(len(metrics),7)

    def test_all_scenarios_independently_score_verified_final(self):
        picks,metrics=study.create_scenarios(self.pairs)
        scored=study.score_scenarios(picks,{self.now.date():self.espn},self.now.to_pydatetime()+timedelta(days=2))
        study.summarize(metrics,scored)
        self.assertTrue(all(m["unverified_or_pending"]==0 for m in metrics))
        self.assertTrue(all(m["wins"]==1 for m in metrics))
        self.assertTrue(all(m["paper_roi"]>0 for m in metrics))

    def test_missing_final_suppresses_roi_even_for_partially_matched_scenario(self):
        picks,metrics=study.create_scenarios(self.pairs)
        # One independent game without a scoreboard match, in the same scenario.
        other=dict(picks[0])
        other.update(game_id="g2",home="Other Home",away="Other Away")
        picks.append(other)
        metrics[0]["selected_games"]+=1
        scored=study.score_scenarios(picks,{self.now.date():self.espn},self.now.to_pydatetime()+timedelta(days=2))
        study.summarize(metrics,scored)
        self.assertEqual(metrics[0]["unverified_or_pending"],1)
        self.assertEqual(metrics[0]["paper_roi"],"")

    def test_scoreboard_days_around_kickoff(self):
        picks,_=study.create_scenarios(self.pairs)
        days=study.dates_for(picks,self.now.to_pydatetime()+timedelta(days=2))
        self.assertEqual(len(days),3)

if __name__=="__main__":
    unittest.main()
