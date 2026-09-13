import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seasonal_pri.engine import AdjustmentResult, _jar_path, adjust


class JarPathTest(unittest.TestCase):
    def test_rejects_missing_configured_jar(self) -> None:
        with patch.dict(os.environ, {"SEASONAL_PRI_JAR": "/path/to/missing.jar"}):
            with self.assertRaisesRegex(FileNotFoundError, "Unset it"):
                _jar_path()

    def test_accepts_existing_configured_jar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "demetra.jar"
            jar.touch()
            with patch.dict(os.environ, {"SEASONAL_PRI_JAR": str(jar)}):
                self.assertEqual(_jar_path(), jar)


class ProcessingTest(unittest.TestCase):
    def test_x13_and_tramoseats_accept_user_variables(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]
        variable = [1.0 if index == 60 else 0.0 for index in range(120)]

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2015,
                    method=method,
                    user_variables=[
                        {
                            "name": "campaign",
                            "values": variable,
                            "effect": "Irregular",
                            "coefficient": 0.08,
                        }
                    ],
                )
                self.assertEqual(set(result), {"y", "sa", "t", "s", "i"})
                self.assertTrue(all(len(series) == 120 for series in result.values()))

    def test_x13_and_tramoseats_accept_full_domain_calendar_variables(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]
        calendar_values = [float((index * 7) % 11 - 5) for index in range(144)]

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2015,
                    method=method,
                    calendar_variables=[
                        {
                            "name": "weighted_days",
                            "values": calendar_values,
                            "frequency": "Monthly",
                            "start_year": 2014,
                            "start_period": 1,
                        }
                    ],
                )
                self.assertEqual(set(result), {"y", "sa", "t", "s", "i"})
                self.assertTrue(all(len(series) == 120 for series in result.values()))

    def test_detailed_results_include_domain_aware_forecasts(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]
        cases = {
            "x13": {"forecast_horizon": 12, "backcast_horizon": 12},
            "tramoseats": {"seats": {"prediction_length": 12}},
        }

        for method, options in cases.items():
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2015,
                    method=method,
                    detailed=True,
                    **options,
                )
                self.assertIsInstance(result, AdjustmentResult)
                self.assertGreater(len(result.series), 50)
                self.assertGreater(len(result.diagnostics), 50)
                self.assertEqual(len(result.series["final.y"].values), 120)
                forecast = result.series["final.sa_f"]
                self.assertEqual(forecast.frequency, "Monthly")
                self.assertEqual((forecast.start_year, forecast.start_period), (2025, 1))
                self.assertEqual(len(forecast.values), 12)


if __name__ == "__main__":
    unittest.main()