"""Offline Model 11 validation: no wagering signal, no retroactive predictions, safe final-score mapping."""
import csv
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import model11
import collect_results

class Model11Tests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.original=os.getcwd()
        os.chdir(self.root.name)
        self.now=datetime(2026,11,10,15,0,tzinfo=timezone.utc)
        self.kickoff=self.now+timedelta(days=3)

    def tearDown(self):
        os.chdir(self.original)
        self.root.cleanup()

    def make_snapshot(self):
        return {
            "event-x":{
                self.now.isoformat():{
                    f"book-{i}":{
                        "prob":0.55+i*.002,
                        "home_odds":-125-i,
                        "away_odds":110+i,
                        "book_name":f"Book {i}",
                        "captured":self.now,
                        "kickoff":self.kickoff,
                        "home_team":"Home Team",
                        "away_team":"Away Team",
                    } for i in range(4)
                }
            }
        }

    def row(self,when=None):
        return {
            "event_id":"event-x",
            "forecast_utc":(when or self.now).isoformat(),
            "trained_through_utc":"2025-12-31T00:00:00+00:00",
            "model_id":"heldout_calibration",
            "model_version":"v1",
            "home_probability":"0.58",
        }

    def frozen(self):
        return [{
            "event_id":"event-x",
            "home_team":"Home Team","away_team":"Away Team",
            "kickoff_utc":self.kickoff.isoformat(),
        }]

    def test_requires_independent_forecast(self):
        self.assertEqual(model11.lock_new([],[],self.frozen(),self.make_snapshot(),self.now),[])

    def test_accept_once_and_never_overwrite(self):
        add=model11.lock_new([self.row()],[],self.frozen(),self.make_snapshot(),self.now+timedelta(minutes=1))
        self.assertEqual(len(add),1)
        self.assertEqual(add[0]["research_status"],"UNVALIDATED_RESEARCH_ONLY")
        self.assertEqual(model11.lock_new([self.row()],add,self.frozen(),self.make_snapshot(),self.now+timedelta(minutes=1)),[])

    def test_refuses_stale_or_backfilled_forecasts(self):
        too_old=self.row(self.now-timedelta(hours=2))
        self.assertEqual(model11.lock_new([too_old],[],self.frozen(),self.make_snapshot(),self.now),[])
        future=self.row(self.now+timedelta(minutes=30))
        self.assertEqual(model11.lock_new([future],[],self.frozen(),self.make_snapshot(),self.now),[])

    def test_no_result_before_kickoff(self):
        quote=self.make_snapshot()
        locked=model11.lock_new([self.row()],[],self.frozen(),quote,self.now)
        audit=model11.calculate_audit(locked,quote,{"event-x":"Home Team"},self.now)
        self.assertEqual(audit[0]["result"],"NOT_FINAL")
        self.assertEqual(audit[0]["realized_paper_profit_per_dollar"],"")

    def test_scoreboard_exact_match_and_final_only(self):
        event={
            "id":"espn-123",
            "date":self.kickoff.isoformat(),
            "competitions":[{
                "status":{"type":{"name":"STATUS_FINAL","completed":True}},
                "competitors":[
                    {"homeAway":"home","team":{"displayName":"Home Team"},"score":"21"},
                    {"homeAway":"away","team":{"displayName":"Away Team"},"score":"17"},
                ],
            }],
        }
        date=self.kickoff.date()
        games={date:{"events":[event]}}
        wins=collect_results.match_finals(self.frozen(),games,self.kickoff+timedelta(hours=4))
        self.assertEqual(len(wins),1)
        self.assertEqual(wins[0]["winner"],"Home Team")
        event["competitions"][0]["status"]["type"]["completed"]=False
        self.assertEqual(collect_results.match_finals(self.frozen(),games,self.kickoff+timedelta(hours=4)),[])

if __name__=="__main__":
    unittest.main()
