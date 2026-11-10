"""Test venue classification and finalized-paper accounting."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_historical_venues import describe, venue_category

class VenueAuditTests(unittest.TestCase):
    def test_novig_is_a_real_exchange_venue(self):
        self.assertEqual(venue_category("novig"),"Exchange / prediction market")
        self.assertEqual(venue_category("draftkings"),"Other bookmaker / unclassified venue")

    def test_only_final_outcomes_contribute(self):
        records=[
            {"book":"novig","outcome_status":"FINAL","won":"1","paper_profit_per_unit":"2.0"},
            {"book":"draftkings","outcome_status":"FINAL","won":"0","paper_profit_per_unit":"-1.0"},
            {"book":"draftkings","outcome_status":"FUTURE_GAME","won":"","paper_profit_per_unit":""}
        ]
        info={row["category"]:row for row in describe(records)}
        self.assertEqual(info["All verified historical candidates"]["verified_selections"],2)
        self.assertAlmostEqual(info["All verified historical candidates"]["paper_roi"],.5)
        self.assertEqual(info["Exchange / prediction market"]["paper_wins"],1)

if __name__=="__main__":
    unittest.main()
