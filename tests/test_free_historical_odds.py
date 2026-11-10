"""Offline synthetic checks for free Odds Gap historical snapshot replay."""
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import backtest_free_odds_gap as mod

class FreeHistoricalOddsTests(unittest.TestCase):
    def setUp(self):
        self.now=pd.Timestamp("2026-10-19T04:00:00Z")
        self.kickoff=self.now+pd.Timedelta(days=2)

    def sample(self, books=5, early=True, later=True):
        rows=[]
        def add(ts,changed=False):
            for i in range(books):
                for side,odds in (("home",390 if i==0 and not changed else 280 if i==0 else 280),
                                  ("away",-400)):
                    rows.append({"snapshot_ts":ts,"commence_time":self.kickoff,
                                 "book":f"book{i}","side":side,"american_odds":odds,
                                 "game_id":"g","home":"Home","away":"Away"})
        if early:add(self.now)
        if later:add(self.kickoff-pd.Timedelta(minutes=35),True)
        raw=pd.DataFrame(rows)
        raw["snapshot_ts"]=pd.to_datetime(raw["snapshot_ts"],utc=True)
        raw["commence_time"]=pd.to_datetime(raw["commence_time"],utc=True)
        return mod.pair_quotes(raw)

    def test_one_candidate_with_later_same_book_quote(self):
        pairs=self.sample()
        chosen,_=mod.replay(pairs)
        self.assertEqual(len(chosen),1)
        self.assertEqual(chosen.iloc[0]["book"],"book0")
        self.assertEqual(chosen.iloc[0]["selected_side"],"HOME")
        self.assertEqual(chosen.iloc[0]["same_book_near_kickoff_odds"],280)
        self.assertGreater(chosen.iloc[0]["same_book_implied_shift_pp"],0)

    def test_requires_five_books(self):
        selected,_=mod.replay(self.sample(books=4))
        self.assertEqual(len(selected),0)

    def test_refuses_selection_less_than_12_hours_before_kickoff(self):
        frame=self.sample(early=False)
        selected,_=mod.replay(frame)
        self.assertEqual(len(selected),0)

    def test_refuses_asynchronous_quotes(self):
        raw=self.sample()
        # Move a book to a different observation instant, never blend quotes.
        idx=raw["book"]=="book4"
        raw.loc[idx,"snapshot_ts"]=raw.loc[idx,"snapshot_ts"]+pd.Timedelta(minutes=1)
        selected,_=mod.replay(raw)
        self.assertEqual(len(selected),0)

if __name__=="__main__": unittest.main()
