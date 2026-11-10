"""Synthetic final score matching checks for historical paper study."""
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import evaluate_free_historical_odds as mod

class HistoricalScoreTests(unittest.TestCase):
    def setUp(self):
        self.kickoff=datetime(2026,10,25,17,0,tzinfo=timezone.utc)
        self.now=self.kickoff+timedelta(days=5)
        self.pick={"game_id":"g","away":"Away Team","home":"Home Team",
                   "kickoff_utc":self.kickoff.isoformat(),
                   "selection_utc":(self.kickoff-timedelta(days=1)).isoformat(),
                   "selected_side":"HOME","book":"book","offered_odds":"390",
                   "reference_prob":"0.215","apparent_ev":"0.053"}
    def scoreboard(self,home="Home Team",complete=True):
        return {"events":[{"id":"espn1","date":self.kickoff.isoformat(),
            "competitions":[{"status":{"type":{"completed":complete,"name":"STATUS_FINAL" if complete else "STATUS_SCHEDULED"}},
                "competitors":[
                    {"homeAway":"home","score":"24","team":{"displayName":home}},
                    {"homeAway":"away","score":"20","team":{"displayName":"Away Team"}}]}]}]}

    def test_confirmed_win_and_units(self):
        out=mod.evaluate([self.pick],{self.kickoff.date():self.scoreboard()},self.now)[0]
        self.assertEqual(out["outcome_status"],"FINAL")
        self.assertEqual(out["won"],1)
        self.assertAlmostEqual(out["paper_profit_per_unit"],3.9)

    def test_wrong_team_not_matched(self):
        out=mod.evaluate([self.pick],{self.kickoff.date():self.scoreboard(home="Different")},self.now)[0]
        self.assertEqual(out["outcome_status"],"NO_VERIFIED_FINAL")
        self.assertEqual(out["paper_profit_per_unit"],"")

    def test_future_game_not_scored(self):
        out=mod.evaluate([self.pick],{self.kickoff.date():self.scoreboard()},self.kickoff-timedelta(hours=2))[0]
        self.assertEqual(out["outcome_status"],"FUTURE_GAME")

    def test_incomplete_game_not_scored(self):
        out=mod.evaluate([self.pick],{self.kickoff.date():self.scoreboard(complete=False)},self.now)[0]
        self.assertEqual(out["outcome_status"],"NO_VERIFIED_FINAL")

if __name__=="__main__":
    unittest.main()
