"""Offline integrity tests for Model 13 Phase 2 candidate tracking."""
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import model13_phase2_validation as phase2

class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.pick={"event_id":"g","home_team":"Home","away_team":"Away",
                   "selected_side":"HOME","selection_utc":"2026-11-10T15:00:00+00:00",
                   "kickoff_utc":"2026-11-15T18:00:00+00:00","book":"DraftKings",
                   "book_key":"draftkings","offered_odds":"390","reference_prob":".20",
                   "break_even_prob":".2041","apparent_ev":".04"}
        self.final={"event_id":"g","status":"final","source":"espn_scoreboard",
                    "source_event_id":"espn123","winner":"Home"}
        self.v={"event_id":"g","latest_market_utc":"2026-11-12T18:00:00Z",
                "latest_same_book_utc":"2026-11-12T18:00:00Z",
                "near_kickoff_utc":"","near_kickoff_same_book_utc":"",
                "near_kickoff_market_shift_pp":"","near_kickoff_same_book_shift_pp":""}

    def test_no_results_no_calibration(self):
        d=phase2.build([self.pick],[self.v],[],[])
        self.assertEqual(d[0]["verified_final"],"NO")
        self.assertEqual(d[0]["outcome_brier"],"")
        txt=phase2.report(d,[],datetime(2026,11,11,tzinfo=timezone.utc))
        self.assertIn("No independently verified settled selections",txt)

    def test_verified_final_probability_scored(self):
        d=phase2.build([self.pick],[self.v],[self.final],[])
        self.assertEqual(d[0]["verified_final"],"YES")
        self.assertEqual(d[0]["win"],1)
        self.assertAlmostEqual(d[0]["outcome_brier"],.64)
        self.assertGreater(d[0]["outcome_logloss"],1)

    def test_manual_review_not_assumed(self):
        d=phase2.build([self.pick],[self.v],[],[])
        self.assertEqual(d[0]["manual_execution_status"],"UNREVIEWED")
        self.assertEqual(d[0]["manual_net_price"],"")
        self.assertEqual(d[0]["near_kickoff_reference"],"NO")

    def test_checked_price_requires_evidence(self):
        evidence={"event_id":"g","book_key":"draftkings","selected_side":"HOME",
                  "execution_status":"PRICE_CONFIRMED","checked_utc":"2026-11-10T15:00:00Z",
                  "evidence_reference":""}
        d=phase2.build([self.pick],[],[],[evidence])
        self.assertIn("NO_EXECUTION_EVIDENCE_REFERENCE",d[0]["data_quality_warning"])

    def test_manual_check_after_observation_flagged(self):
        evidence={"event_id":"g","book_key":"draftkings","selected_side":"HOME",
                  "execution_status":"PRICE_CONFIRMED","checked_utc":"2026-11-11T15:00:00Z",
                  "evidence_reference":"private-log-1"}
        d=phase2.build([self.pick],[],[],[evidence])
        self.assertIn("PRICE_CHECK_OUTSIDE_15_MINUTES_OF_BOOK_QUOTE",d[0]["data_quality_warning"])

    def test_confirmed_price_must_match_frozen_moneyline(self):
        evidence={"event_id":"g","book_key":"draftkings","selected_side":"HOME",
                  "execution_status":"PRICE_CONFIRMED","checked_utc":"2026-11-10T15:00:00Z",
                  "offered_odds_checked":"350","evidence_reference":"private-check"}
        d=phase2.build([self.pick],[],[],[evidence])
        self.assertIn("MANUAL_PRICE_DOES_NOT_MATCH_FROZEN_OFFER",d[0]["data_quality_warning"])

    def test_near_kickoff_check_matches_nearby_selected_book_quote(self):
        v={**self.v,"near_kickoff_same_book_utc":"2026-11-15T17:58:00Z",
           "near_kickoff_same_book_odds":"380"}
        evidence={"event_id":"g","book_key":"draftkings","selected_side":"HOME",
                  "execution_status":"PRICE_CONFIRMED","checked_utc":"2026-11-15T17:59:00Z",
                  "offered_odds_checked":"380","evidence_reference":"private-check"}
        d=phase2.build([self.pick],[v],[],[evidence])
        self.assertEqual(d[0]["manual_execution_status"],"PRICE_CONFIRMED")
        self.assertEqual(d[0]["data_quality_warning"],"NONE")

    def test_negative_results_score_correctly(self):
        lost={**self.final,"winner":"Away"}
        d=phase2.build([self.pick],[self.v],[lost],[])
        self.assertEqual(d[0]["win"],0)
        self.assertAlmostEqual(d[0]["outcome_brier"],.04)

if __name__=="__main__":
    unittest.main()
