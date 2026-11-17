"""Offline integrity tests for Model 10B; no network, API quota, or private Drive."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import model10b_historical as m


class Model10BTests(unittest.TestCase):
    def cohort(self):
        rows = []
        # Sufficient training data and both winner classes, with no scores
        # or current-week statistics included in the model predictors.
        for season in range(2015, 2026):
            for i in range(24):
                p = 0.3 + 0.4 * (i / 23)
                row = {
                    "season": season, "week": i + 1,
                    "game_id": f"{season}_{i:02d}_AWAY_HOME",
                    "home_team": "HOME", "away_team": "AWAY",
                    "home_win": int(i % 3 != 0),
                    "split": ("train" if season <= 2021 else
                              "validation" if season <= 2023 else "historical_test"),
                    "market_close_no_vig_home_prob": p,
                    "market_logit": float(np.log(p / (1 - p))),
                }
                row.update({col: float((i + 1) / 25) for col in m.FEATURE_COLS})
                rows.append(row)
        return pd.DataFrame(rows)

    def test_complete_paired_forecast_output(self):
        cohort = self.cohort()
        with patch.object(m, "prepare", return_value=cohort):
            out = m.fit_and_evaluate(pd.DataFrame(), pd.DataFrame())
        self.assertEqual(len(out), len(cohort))
        self.assertEqual(out["game_id"].nunique(), len(cohort))
        for name, column in m.PROBABILITIES.items():
            self.assertTrue(out[column].between(0, 1).all())
            self.assertTrue(np.isfinite(out[name + "_brier"]).all())
            self.assertTrue(np.isfinite(out[name + "_logloss"]).all())
        report = m.summarize(out)
        self.assertIn("Historical stats + market", report)
        self.assertIn("closing", report.lower())

    def test_train_missing_rejected(self):
        rows = self.cohort()
        rows = rows[rows["season"] >= 2022]
        with patch.object(m, "prepare", return_value=rows):
            with self.assertRaisesRegex(ValueError, "Insufficient historical training"):
                m.fit_and_evaluate(pd.DataFrame(), pd.DataFrame())

    def test_ambiguous_games_rejected(self):
        rows = self.cohort()
        rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
        with patch.object(m, "prepare", return_value=rows):
            with self.assertRaisesRegex(ValueError, "Duplicate game IDs"):
                m.fit_and_evaluate(pd.DataFrame(), pd.DataFrame())


if __name__ == "__main__":
    unittest.main()
