import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seasonal_pri.cli import run
from seasonal_pri.config import AdjustmentConfig


class ConfigTest(unittest.TestCase):
    def test_loads_engine_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"spec": "RSA5", "benchmarking": True}),
                encoding="utf-8",
            )
            config = AdjustmentConfig.load(path)

        self.assertEqual(config.spec, "RSA5")
        self.assertTrue(config.engine_options()["benchmarking"])


class CliTest(unittest.TestCase):
    @patch("seasonal_pri.cli.adjust")
    def test_writes_adjusted_csv(self, mock_adjust) -> None:
        mock_adjust.return_value = {
            "y": [10.0, 20.0],
            "sa": [11.0, 19.0],
            "t": [12.0, 18.0],
            "s": [-1.0, 1.0],
            "i": [-1.0, 1.0],
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "output.csv"
            input_path.write_text("date,value\n2024-01-01,10\n2024-02-01,20\n")

            exit_code = run([str(input_path), "--output", str(output_path)])
            with output_path.open(newline="") as stream:
                rows = list(csv.reader(stream))

        self.assertEqual(exit_code, 0)
        self.assertEqual(rows[0], ["date", "y", "sa", "t", "s", "i"])
        self.assertEqual(rows[1], ["2024-01-01", "10.0", "11.0", "12.0", "-1.0", "-1.0"])
        mock_adjust.assert_called_once_with(
            [10.0, 20.0],
            start_year=2024,
            start_period=1,
            frequency="Monthly",
            spec="RSA4",
            decomposition_mode=None,
            seasonal_filter=None,
            henderson_filter_length=None,
            lower_sigma=None,
            upper_sigma=None,
            forecast_horizon=None,
            backcast_horizon=None,
            benchmarking=False,
        )

    def test_rejects_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            input_path.write_text("when,amount\n2024-01-01,10\n")
            self.assertEqual(run([str(input_path)]), 2)


if __name__ == "__main__":
    unittest.main()