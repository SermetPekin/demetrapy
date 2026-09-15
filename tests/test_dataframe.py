import unittest
from unittest.mock import patch

import pandas as pd

from demetrapy import (
    AdjustmentComponents,
    AdjustmentForecasts,
    AdjustmentResult,
    DataFrameAdjustmentResult,
    OutputSeries,
    X13Config,
    adjust_dataframe,
)


def result_with_forecasts(
    values: tuple[float, ...],
    forecasts: tuple[float, ...],
    *,
    frequency: str,
    start_year: int,
    start_period: int,
    forecast_year: int,
    forecast_period: int,
    include_all_forecasts: bool = True,
) -> AdjustmentResult:
    history = OutputSeries(values, frequency, start_year, start_period)
    future = OutputSeries(forecasts, frequency, forecast_year, forecast_period)
    forecast_components = AdjustmentForecasts(
        observed=future if include_all_forecasts else None,
        calendar_adjusted=future if include_all_forecasts else None,
        seasonally_adjusted=future,
        trend=future if include_all_forecasts else None,
        seasonal=future if include_all_forecasts else None,
        irregular=future if include_all_forecasts else None,
    )
    return AdjustmentResult(
        components=AdjustmentComponents(
            history, history, history, history, history, history
        ),
        method="tramoseats",
        specification="RSA4",
        series={},
        diagnostics={},
        messages=(),
        forecasts=forecast_components,
    )


class DataFrameAdjustmentTest(unittest.TestCase):
    def test_quarterly_forecast_and_combined_frames_use_future_domain(self) -> None:
        index = pd.date_range("2022-04-01", periods=4, freq="QS")
        components = pd.DataFrame(
            {
                ("production", name): [1.0, 2.0, 3.0, 4.0]
                for name in (
                    "observed",
                    "calendar_adjusted",
                    "seasonally_adjusted",
                    "trend",
                    "seasonal",
                    "irregular",
                )
            },
            index=index,
        )
        components.columns = pd.MultiIndex.from_tuples(
            components.columns,
            names=["series", "component"],
        )
        result = DataFrameAdjustmentResult(
            components=components,
            results={
                "production": result_with_forecasts(
                    (1.0, 2.0, 3.0, 4.0),
                    (5.0, 6.0),
                    frequency="Quarterly",
                    start_year=2022,
                    start_period=2,
                    forecast_year=2023,
                    forecast_period=2,
                )
            },
        )

        forecasts = result.to_forecast_frame(compact=True)
        combined = result.to_combined_frame(compact=True)

        self.assertEqual(
            list(forecasts.index),
            [pd.Timestamp("2023-04-01"), pd.Timestamp("2023-07-01")],
        )
        self.assertEqual(combined.shape, (6, 6))
        self.assertEqual(
            combined[("production", "sa")].tolist(),
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        )
        pd.testing.assert_frame_equal(result.components, components)

    def test_forecast_frame_supports_partial_components_and_multiple_targets(self) -> None:
        index = pd.date_range("2024-01-01", periods=2, freq="MS")
        components = pd.DataFrame(
            {
                (target, name): [1.0, 2.0]
                for target in ("sales", "orders")
                for name in (
                    "observed",
                    "calendar_adjusted",
                    "seasonally_adjusted",
                    "trend",
                    "seasonal",
                    "irregular",
                )
            },
            index=index,
        )
        components.columns = pd.MultiIndex.from_tuples(
            components.columns,
            names=["series", "component"],
        )
        result = DataFrameAdjustmentResult(
            components=components,
            results={
                target: result_with_forecasts(
                    (1.0, 2.0),
                    values,
                    frequency="Monthly",
                    start_year=2024,
                    start_period=1,
                    forecast_year=2024,
                    forecast_period=3,
                    include_all_forecasts=target == "sales",
                )
                for target, values in {
                    "sales": (3.0, 4.0),
                    "orders": (30.0, 40.0),
                }.items()
            },
        )

        forecasts = result.to_forecast_frame()

        self.assertEqual(forecasts.shape, (2, 7))
        self.assertEqual(
            forecasts[("orders", "seasonally_adjusted")].tolist(),
            [30.0, 40.0],
        )
        self.assertNotIn(("orders", "observed"), forecasts.columns)

    def test_forecast_helpers_return_empty_or_history_without_forecasts(self) -> None:
        index = pd.date_range("2015-01-01", periods=120, freq="MS")
        data = pd.DataFrame(
            {"sales": [100 + position * 0.2 + position % 12 for position in range(120)]},
            index=index,
        )

        result = adjust_dataframe(data, method="x13", forecast_horizon=0)

        self.assertTrue(result.to_forecast_frame().empty)
        pd.testing.assert_frame_equal(result.to_combined_frame(), result.components)

    def test_infers_quarterly_frequency_with_typed_config(self) -> None:
        index = pd.date_range("2015-01-01", periods=8, freq="QS")
        data = pd.DataFrame({"production": range(8)}, index=index)

        with patch("demetrapy.dataframe.adjust") as mock_adjust:
            output = OutputSeries(tuple(range(8)), "Quarterly", 2015, 1)
            mock_adjust.return_value = AdjustmentResult(
                components=AdjustmentComponents(
                    output, output, output, output, output, output
                ),
                method="x13",
                specification="RSA4",
                series={},
                diagnostics={},
                messages=(),
            )

            adjust_dataframe(data, config=X13Config())

        self.assertEqual(mock_adjust.call_args.kwargs["frequency"], "Quarterly")
        self.assertEqual(mock_adjust.call_args.kwargs["start_period"], 1)

    def test_passes_method_specific_config_to_each_series(self) -> None:
        index = pd.date_range("2015-01-01", periods=24, freq="MS")
        data = pd.DataFrame({"sales": range(24)}, index=index)
        config = X13Config(spec="RSA5")

        with patch("demetrapy.dataframe.adjust") as mock_adjust:
            output = OutputSeries(tuple(range(24)), "Monthly", 2015, 1)
            mock_adjust.return_value = AdjustmentResult(
                components=AdjustmentComponents(
                    output, output, output, output, output, output
                ),
                method="x13",
                specification="RSA5",
                series={},
                diagnostics={},
                messages=(),
            )

            adjust_dataframe(data, config=config)

        self.assertIs(mock_adjust.call_args.kwargs["config"], config)
        self.assertEqual(mock_adjust.call_args.kwargs["frequency"], "Monthly")

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
            output = OutputSeries(tuple(values), "Monthly", 2015, 1)
            return AdjustmentResult(
                components=AdjustmentComponents(
                    output, output, output, output, output, output
                ),
                method=options["method"],
                specification="RSA4",
                series={},
                diagnostics={},
                messages=(),
            )

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

        self.assertIsInstance(result, DataFrameAdjustmentResult)
        self.assertEqual(result.components.columns.names, ["series", "component"])
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
                self.assertIsInstance(result, DataFrameAdjustmentResult)
                self.assertEqual(result.components.shape, (120, 6))
                self.assertEqual(
                    list(result.components["sales"].columns),
                    [
                        "observed",
                        "calendar_adjusted",
                        "seasonally_adjusted",
                        "trend",
                        "seasonal",
                        "irregular",
                    ],
                )
                self.assertEqual(
                    list(result.to_compact_frame()["sales"].columns),
                    ["y", "ycal", "sa", "t", "s", "i"],
                )
                self.assertEqual(result.seasonally_adjusted.shape, (120, 1))

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
        self.assertIsNotNone(result.detailed_series)
        assert result.detailed_series is not None
        self.assertIn(("sales", "final.sa"), result.detailed_series.columns)
        self.assertIn(("sales", "final.sa_f"), result.detailed_series.columns)
        self.assertEqual(
            result.detailed_series[("sales", "final.sa")].first_valid_index(),
            pd.Timestamp("2015-01-01"),
        )
        self.assertEqual(
            result.detailed_series[("sales", "final.sa_f")].first_valid_index(),
            pd.Timestamp("2025-01-01"),
        )
        self.assertEqual(
            result.detailed_series[("sales", "final.sa_f")].last_valid_index(),
            pd.Timestamp("2025-12-01"),
        )
        self.assertEqual(result.detailed_series[("sales", "final.sa")].count(), 120)
        self.assertEqual(result.detailed_series[("sales", "final.sa_f")].count(), 12)
        forecast_frame = result.to_forecast_frame()
        compact_forecasts = result.to_forecast_frame(compact=True)
        combined = result.to_combined_frame(compact=True)
        self.assertEqual(forecast_frame.shape, (12, 6))
        self.assertEqual(
            list(forecast_frame["sales"].columns),
            [
                "observed",
                "calendar_adjusted",
                "seasonally_adjusted",
                "trend",
                "seasonal",
                "irregular",
            ],
        )
        self.assertEqual(
            list(compact_forecasts["sales"].columns),
            ["y_f", "ycal_f", "sa_f", "t_f", "s_f", "i_f"],
        )
        self.assertEqual(combined.shape, (132, 6))
        self.assertEqual(combined[("sales", "sa")].count(), 132)
        self.assertEqual(combined.index[120], pd.Timestamp("2025-01-01"))
        series_result = result.for_series("sales")
        self.assertGreater(len(series_result.diagnostics), 50)
        self.assertIsNotNone(series_result.arima_model)
        assert series_result.arima_model is not None
        self.assertEqual(series_result.arima_model.period, 12)
        self.assertTrue(series_result.arima_model.automatic)


if __name__ == "__main__":
    unittest.main()
