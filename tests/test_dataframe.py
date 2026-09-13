import unittest
from unittest.mock import patch

import pandas as pd

from demetrapy import DataFrameAdjustmentResult, adjust_dataframe


class DataFrameAdjustmentTest(unittest.TestCase):
    def test_registers_full_pool_and_selects_per_target(self) -> None:
        target_index = pd.date_range("2015-01-01", periods=36, freq="MS")
        pool_index = pd.date_range("2014-01-01", periods=60, freq="MS")
        data = pd.DataFrame(
            {
                "sales": range(36),
                "orders": range(100, 136),
            },
            index=target_index,
        )
        pool = pd.DataFrame(
            {
                "weekday_a": [index % 5 for index in range(60)],
                "weekday_b": [index % 7 for index in range(60)],
                "unused": [index % 3 for index in range(60)],
            },
            index=pool_index,
        )
        calls = []

        def fake_adjust(values, **options):
            calls.append((values, options))
            return {name: list(values) for name in ("y", "sa", "t", "s", "i")}

        with patch("demetrapy.dataframe.adjust", side_effect=fake_adjust):
            result = adjust_dataframe(
                data,
                calendar_pool=pool,
                user_defined_calendars={
                    "sales": ["weekday_a"],
                    "orders": ["weekday_b"],
                },
                method="tramoseats",
            )

        self.assertEqual(result.columns.names, ["series", "component"])
        self.assertEqual(len(calls), 2)
        for _, options in calls:
            self.assertEqual(options["frequency"], "Monthly")
            self.assertEqual(options["start_year"], 2015)
            self.assertEqual(len(options["calendar_variables"]), 3)
            self.assertTrue(
                all(len(item["values"]) == 60 for item in options["calendar_variables"])
            )
            self.assertEqual(options["calendar_variables"][0]["start_year"], 2014)
        self.assertEqual(
            [item["selected"] for item in calls[0][1]["calendar_variables"]],
            [True, False, False],
        )
        self.assertEqual(
            [item["selected"] for item in calls[1][1]["calendar_variables"]],
            [False, True, False],
        )

    def test_rejects_calendar_pool_that_does_not_cover_target(self) -> None:
        data_index = pd.date_range("2015-01-01", periods=36, freq="MS")
        pool_index = pd.date_range("2015-02-01", periods=35, freq="MS")
        data = pd.DataFrame({"sales": range(36)}, index=data_index)
        pool = pd.DataFrame({"weekday": range(35)}, index=pool_index)

        with self.assertRaisesRegex(ValueError, "cover every target data period"):
            adjust_dataframe(
                data,
                calendar_pool=pool,
                user_defined_calendars={"sales": ["weekday"]},
            )

    def test_processes_wider_calendar_pool_with_both_engines(self) -> None:
        target_index = pd.date_range("2015-01-01", periods=120, freq="MS")
        pool_index = pd.date_range("2014-01-01", periods=144, freq="MS")
        data = pd.DataFrame(
            {
                "sales": [
                    100 + index * 0.2 + (index % 12)
                    for index in range(len(target_index))
                ]
            },
            index=target_index,
        )
        pool = pd.DataFrame(
            {
                "weighted_days": [
                    float((index * 7) % 11 - 5) for index in range(len(pool_index))
                ],
                "unused": [float(index % 3) for index in range(len(pool_index))],
            },
            index=pool_index,
        )

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust_dataframe(
                    data,
                    calendar_pool=pool,
                    user_defined_calendars={"sales": ["weighted_days"]},
                    method=method,
                )
                self.assertEqual(result.shape, (120, 5))
                self.assertEqual(
                    list(result["sales"].columns),
                    ["y", "sa", "t", "s", "i"],
                )

    def test_detailed_result_extends_dataframe_into_forecast_domain(self) -> None:
        target_index = pd.date_range("2015-01-01", periods=120, freq="MS")
        data = pd.DataFrame(
            {
                "sales": [
                    100 + index * 0.2 + (index % 12)
                    for index in range(len(target_index))
                ]
            },
            index=target_index,
        )

        result = adjust_dataframe(
            data,
            method="x13",
            forecast_horizon=12,
            detailed=True,
        )

        self.assertIsInstance(result, DataFrameAdjustmentResult)
        self.assertIn(("sales", "final.sa"), result.series.columns)
        self.assertIn(("sales", "final.sa_f"), result.series.columns)
        self.assertEqual(
            result.series[("sales", "final.sa")].first_valid_index(),
            pd.Timestamp("2015-01-01"),
        )
        self.assertEqual(
            result.series[("sales", "final.sa_f")].first_valid_index(),
            pd.Timestamp("2025-01-01"),
        )
        self.assertEqual(
            result.series[("sales", "final.sa_f")].last_valid_index(),
            pd.Timestamp("2025-12-01"),
        )
        self.assertEqual(result.series[("sales", "final.sa")].count(), 120)
        self.assertEqual(result.series[("sales", "final.sa_f")].count(), 12)
        self.assertGreater(len(result.diagnostics["sales"]), 50)
        self.assertIsNotNone(result.arima_models["sales"])
        self.assertEqual(result.arima_models["sales"].period, 12)
        self.assertTrue(result.arima_models["sales"].automatic)


if __name__ == "__main__":
    unittest.main()
