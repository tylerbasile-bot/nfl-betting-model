"""Offline regression tests for timestamped injury changes and quota gate."""
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import injury_changes
import near_kickoff_gate
import model13

class TrackingUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,10,15,0,tzinfo=timezone.utc)

    def report(self,status,practice,observed="2026-11-10T12:00:00+00:00"):
        return {
            "observed_utc":observed,"season":"2026","week":"10",
            "team":"NYG","gsis_id":"a","full_name":"Example Player",
            "position":"QB","group":"QB","report_primary_injury":"Knee",
            "report_status":status,"practice_status":practice,
            "source_date_modified":"2026-11-10","source_url":"test"
        }

    def test_injury_status_changed_across_observations(self):
        early=[self.report("Questionable","Limited")]
        later=[self.report("Out","DNP","2026-11-11T12:00:00+00:00")]
        changes=injury_changes.compare(early,later)
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["change_type"],"REPORTED_STATUS_CHANGED")
        self.assertEqual(changes[0]["prior_report_status"],"Questionable")

    def test_missing_injury_entry_not_assumed_recovered(self):
        early=[self.report("Questionable","Limited")]
        self.assertEqual(injury_changes.compare(early,[]),[])

    def test_gate_only_near_kickoff_and_respects_existing_snapshot(self):
        upcoming=[{
            "event_id":"event",
            "kickoff_utc":(self.now+timedelta(minutes=40)).isoformat()
        }]
        self.assertEqual(near_kickoff_gate.eligible(self.now,upcoming,[]),["event"])
        previous=[{"event_id":"event",
                   "snapshot_utc":(self.now-timedelta(minutes=10)).isoformat()}]
        self.assertEqual(near_kickoff_gate.eligible(self.now,upcoming,previous),[])
        previous[0]["snapshot_utc"]=(self.now-timedelta(minutes=35)).isoformat()
        self.assertEqual(near_kickoff_gate.eligible(self.now,upcoming,previous),["event"])

    def test_gate_rejects_distant_kickoff(self):
        distant=[{"event_id":"event",
                   "kickoff_utc":(self.now+timedelta(hours=12)).isoformat()}]
        self.assertEqual(near_kickoff_gate.eligible(self.now,distant,[]),[])

    def test_same_book_move_does_not_modify_frozen_selection(self):
        earlier=self.now
        kickoff=self.now+timedelta(hours=24)
        q={
            "prob":.22,"home_odds":390,"away_odds":-490,
            "book_name":"Test Book","captured":earlier,
            "kickoff":kickoff,"home_team":"Home","away_team":"Away"
        }
        def books(changed):
            return {f"b{i}":dict(q,home_odds=(300 if changed and i==0 else 390),
                               book_name=f"Book {i}") for i in range(5)}
        odds={
            "ev":{
                earlier.isoformat():books(False),
                (kickoff-timedelta(minutes=40)).isoformat():books(True)
            }
        }
        locked=[{
            "event_id":"ev","kickoff_utc":kickoff.isoformat(),
            "home_team":"Home","away_team":"Away","selected_side":"HOME",
            "book":"Book 0","book_key":"b0","offered_odds":"390",
            "selection_utc":earlier.isoformat(),"reference_prob":"0.22",
            "break_even_prob":"0.20408","apparent_ev":"0.078",
            "reference_books":"4","research_status":"UNVERIFIED_MARKET_DISCREPANCY_ONLY"
        }]
        evaluated=model13.evaluate(locked,odds,{},earlier)
        self.assertEqual(evaluated[0]["same_book_near_kickoff_odds"],300)
        self.assertGreater(float(evaluated[0]["same_book_implied_shift_pp"]),0)
        self.assertEqual(locked[0]["offered_odds"],"390")

if __name__=="__main__":
    unittest.main()
