"""Unit tests for Model 10's immutable forecast and result isolation."""
import csv
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import model10

class Model10Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.tmp.name)
        self.now = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)
        self.kickoff = self.now + timedelta(days=2)

    def tearDown(self):
        os.chdir(self.previous)
        self.tmp.cleanup()

    def add_snapshot(self, timestamp, price_offset=0):
        path = Path("data/odds/2026-11-10.csv")
        path.parent.mkdir(parents=True,exist_ok=True)
        fields = [
            "snapshot_utc","event_id","kickoff_utc","home_team","away_team",
            "sportsbook_key","sportsbook","book_last_update",
            "home_moneyline","away_moneyline","home_no_vig"
        ]
        with path.open("a",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            if stream.tell()==0:
                writer.writeheader()
            for i in range(4):
                writer.writerow({
                    "snapshot_utc":timestamp.isoformat(),
                    "event_id":"test-event-1",
                    "kickoff_utc":self.kickoff.isoformat(),
                    "home_team":"Home Team","away_team":"Away Team",
                    "sportsbook_key":f"book-{i}","sportsbook":f"Book {i}",
                    "book_last_update":(timestamp-timedelta(seconds=20)).isoformat(),
                    "home_moneyline":-120-price_offset-i,
                    "away_moneyline":100+price_offset+i,
                    "home_no_vig":".55"
                })

    def test_forecast_frozen_and_future_results_do_not_change_it(self):
        self.add_snapshot(self.now-timedelta(minutes=1))
        model10.main(self.now)
        first=model10.read_ledger()
        self.assertEqual(len(first),1)
        frozen=first[0]["home_probability"]
        self.add_snapshot(self.now+timedelta(hours=2),price_offset=25)
        model10.main(self.now+timedelta(hours=2,minutes=1))
        self.assertEqual(len(model10.read_ledger()),1)
        self.assertEqual(model10.read_ledger()[0]["home_probability"],frozen)
        with open("data/results.csv","w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=["event_id","status","winner"])
            writer.writeheader()
            writer.writerow({"event_id":"test-event-1","status":"final","winner":"Home Team"})
        model10.main(self.now+timedelta(hours=3))
        with open("reports/model10_evaluation.csv",newline="",encoding="utf-8") as stream:
            report=list(csv.DictReader(stream))
        self.assertEqual(report[0]["home_win"],"1")
        self.assertNotEqual(report[0]["latest_market_shift_pp"],"")
        self.assertEqual(len(model10.read_ledger()),1)

    def test_old_snapshot_not_backfilled_as_prospective(self):
        self.add_snapshot(self.now-timedelta(hours=3))
        model10.main(self.now)
        self.assertEqual(len(model10.read_ledger()),0)

    def test_too_close_to_kickoff_rejected(self):
        self.kickoff=self.now+timedelta(hours=3)
        self.add_snapshot(self.now-timedelta(minutes=1))
        model10.main(self.now)
        self.assertEqual(len(model10.read_ledger()),0)

if __name__ == "__main__":
    unittest.main()
