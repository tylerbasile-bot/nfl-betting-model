"""Offline guardrails for Model 13 candidate freezing and QB/OL injury extraction."""
import csv
import os
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import model13
import collect_injuries

class Model13Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.orig=os.getcwd()
        os.chdir(self.temp.name)
        self.now=datetime(2026,11,10,15,0,tzinfo=timezone.utc)
        self.kickoff=self.now+timedelta(days=3)

    def tearDown(self):
        os.chdir(self.orig)
        self.temp.cleanup()

    def quotes(self,stamp=None):
        stamp=stamp or self.now
        books={}
        for i in range(6):
            books[f"book{i}"]={
                "prob":.55,"home_odds":-135,"away_odds":110,
                "book_name":f"Book {i}","captured":stamp,
                "kickoff":self.kickoff,
                "home_team":"Home Team","away_team":"Away Team"
            }
        books["book0"]["home_odds"]=-110
        return {"game":{stamp.isoformat():books}}

    def test_one_frozen_candidate_and_later_no_duplicates(self):
        candidates=model13.choose_candidates(self.quotes(),[],self.now+timedelta(minutes=1))
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["selected_side"],"HOME")
        self.assertEqual(candidates[0]["research_status"],"UNVERIFIED_MARKET_DISCREPANCY_ONLY")
        self.assertEqual(model13.choose_candidates(self.quotes(),candidates,self.now+timedelta(minutes=1)),[])

    def test_stale_snapshot_not_backfilled(self):
        old=self.now-timedelta(hours=2)
        self.assertEqual(model13.choose_candidates(self.quotes(old),[],self.now),[])

    def test_paper_win_not_scored_before_kickoff(self):
        chosen=model13.choose_candidates(self.quotes(),[],self.now)
        before=model13.evaluate(chosen,self.quotes(),{"game":"Home Team"},self.now)
        self.assertEqual(before[0]["result"],"PENDING")
        after=model13.evaluate(chosen,self.quotes(),{"game":"Home Team"},self.kickoff+timedelta(hours=1))
        self.assertEqual(after[0]["result"],"VERIFIED_FINAL")
        self.assertEqual(after[0]["candidate_won"],1)

    def test_injury_filter_and_provenance(self):
        raw="season,week,team,gsis_id,full_name,position,report_primary_injury,report_status,practice_status,date_modified\n2026,10,NYG,a,Player One,QB,Knee,Questionable,Limited,2026-11-10T00:00:00Z\n2026,10,NYG,b,Player Two,C,Ankle,Out,DNP,2026-11-10T00:00:00Z\n2026,10,NYG,c,Player Three,WR,Ankle,Out,DNP,2026-11-10T00:00:00Z\n"
        rows=collect_injuries.select_rows(raw,self.now.isoformat(),"https://example.com")
        self.assertEqual(len(rows),2)
        self.assertEqual(set(r["group"] for r in rows),{"QB","OL"})
        self.assertTrue(all(r["observed_utc"]==self.now.isoformat() for r in rows))

if __name__=="__main__":
    unittest.main()
