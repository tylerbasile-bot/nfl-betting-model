"""Offline tests for independent prospective Model 13 market and result validation."""
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import model13_market_validation as tracker
import collect_model13_results as collector

class MarketValidationTests(unittest.TestCase):
    def setUp(self):
        self.freeze=datetime(2026,11,10,15,0,tzinfo=timezone.utc)
        self.kickoff=datetime(2026,11,15,18,0,tzinfo=timezone.utc)
        self.row={"event_id":"g","kickoff_utc":self.kickoff.isoformat(),
                  "selection_utc":self.freeze.isoformat(),
                  "home_team":"Home Team","away_team":"Away Team",
                  "selected_side":"HOME","book":"DraftKings","book_key":"draftkings",
                  "offered_odds":"390","reference_prob":"0.215","apparent_ev":"0.054"}
        self.later=datetime(2026,11,15,17,30,tzinfo=timezone.utc)

    def quotes(self,stale=False,after_kickoff=False):
        stamp=self.kickoff+timedelta(minutes=5) if after_kickoff else self.later
        books={}
        for i,key in enumerate(["draftkings","fanduel","betmgm","caesars","betrivers"]):
            books[key]={
                "captured":stamp,
                "updated":stamp-timedelta(minutes=20 if stale else 3),
                "prob":.25,
                "home_odds":290 if i==0 else 280,
                "away_odds":-400,
            }
        return {"g":{stamp.isoformat():books}}

    def test_later_and_near_kickoff_same_book(self):
        rows=tracker.build_rows([self.row],self.quotes(),[],self.freeze)
        self.assertEqual(len(rows),1)
        r=rows[0]
        self.assertEqual(r["near_kickoff_same_book_odds"],"290")
        self.assertEqual(r["latest_same_book_odds"],"290")
        self.assertAlmostEqual(float(r["near_kickoff_market_shift_pp"]),3.5,places=3)
        self.assertEqual(r["verified_result"],"PENDING_OR_UNVERIFIED")

    def test_stale_and_post_kickoff_observations_rejected(self):
        for quotes in [self.quotes(stale=True),self.quotes(after_kickoff=True)]:
            r=tracker.build_rows([self.row],quotes,[],self.kickoff+timedelta(days=1))[0]
            self.assertEqual(r["latest_market_utc"],"")
            self.assertEqual(r["near_kickoff_utc"],"")

    def test_verified_final_requires_source_and_correct_team(self):
        now=self.kickoff+timedelta(days=1)
        bad={"event_id":"g","status":"final","winner":"Home Team",
             "source":"unsourced","source_event_id":"123"}
        r=tracker.build_rows([self.row],{},[bad],now)[0]
        self.assertEqual(r["candidate_won"],"")
        good={**bad,"source":"espn_scoreboard"}
        r=tracker.build_rows([self.row],{},[good],now)[0]
        self.assertEqual(r["candidate_won"],1)
        self.assertAlmostEqual(float(r["paper_profit_per_unit"]),3.9)

    def test_no_final_before_kickoff(self):
        good={"event_id":"g","status":"final","winner":"Home Team",
              "source":"espn_scoreboard","source_event_id":"123"}
        r=tracker.build_rows([self.row],{},[good],self.freeze)[0]
        self.assertEqual(r["verified_result"],"PENDING_OR_UNVERIFIED")

class ScoreCollectorTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,16,18,0,tzinfo=timezone.utc)
        self.row={"event_id":"g","kickoff_utc":"2026-11-15T18:00:00+00:00",
                  "home_team":"Home Team","away_team":"Away Team"}

    def test_only_unmatched_past_selections(self):
        pending=collector.pending_candidates([self.row],[],self.now)
        self.assertEqual(len(pending),1)
        self.assertEqual(collector.pending_candidates([self.row],[{"event_id":"g","status":"final"}],self.now),[])

    def test_completed_game_exact_name_match(self):
        def fake(day):
            return {"events":[{"id":"provider-id","date":self.row["kickoff_utc"],
              "competitions":[{
                "status":{"type":{"completed":True,"name":"STATUS_FINAL"}},
                "competitors":[
                    {"homeAway":"home","score":"20","team":{"displayName":"Home Team"}},
                    {"homeAway":"away","score":"14","team":{"displayName":"Away Team"}}
                ]
              }]}]}
        matched=collector.collect([self.row],[],self.now,fetch=fake)
        self.assertEqual(len(matched),1)
        self.assertEqual(matched[0]["winner"],"Home Team")
        self.assertEqual(matched[0]["event_id"],"g")

if __name__=="__main__":unittest.main()
