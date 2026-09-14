import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy import (
    COMPACT_COMPONENTS,
    FORECAST_COMPONENTS,
    RESULT_SCHEMA_VERSION,
    X13Config,
)
from demetrapy.engine import AdjustmentResult, _jar_path, adjust


class PublicContractTest(unittest.TestCase):
    def test_compact_result_schema_is_versioned(self) -> None:
        self.assertEqual(RESULT_SCHEMA_VERSION, 2)
        self.assertEqual(COMPACT_COMPONENTS, ("y", "ycal", "sa", "t", "s", "i"))
        self.assertEqual(
            FORECAST_COMPONENTS,
            ("y_f", "ycal_f", "sa_f", "t_f", "s_f", "i_f"),
        )


class JarPathTest(unittest.TestCase):
    def test_rejects_missing_configured_jar(self) -> None:
        with patch.dict(os.environ, {"DEMETRAPY_JAR": "/path/to/missing.jar"}):
            with self.assertRaisesRegex(FileNotFoundError, "Unset it"):
                _jar_path()

    def test_accepts_existing_configured_jar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "demetra.jar"
            jar.touch()
            with patch.dict(os.environ, {"DEMETRAPY_JAR": str(jar)}):
                self.assertEqual(_jar_path(), jar)


class ProcessingTest(unittest.TestCase):
    def test_processes_method_specific_config(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        result = adjust(
            values,
            start_year=2015,
            config=X13Config(spec="RSA4", forecast_horizon=12),
        )

        self.assertEqual(result.method, "x13")
        self.assertEqual(result.specification, "RSA4")
        self.assertEqual(len(result.seasonally_adjusted.values), 120)

    def test_rejects_options_that_conflict_with_config(self) -> None:
        with self.assertRaisesRegex(ValueError, "spec"):
            adjust(
                [100.0] * 120,
                start_year=2015,
                config=X13Config(spec="RSA5"),
                spec="RSA3",
            )

    def test_rejects_start_period_outside_frequency(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 12 for Monthly"):
            adjust([100.0] * 120, start_year=2015, start_period=13)

        with self.assertRaisesRegex(ValueError, "calendar variable.*between 1 and 4"):
            adjust(
                [100.0] * 40,
                frequency="Quarterly",
                start_year=2015,
                calendar_variables=[
                    {
                        "name": "quarterly_td",
                        "values": [0.0] * 40,
                        "frequency": "Quarterly",
                        "start_year": 2015,
                        "start_period": 5,
                    }
                ],
            )

    def test_rejects_invalid_arima_orders_before_java_processing(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            adjust(
                values,
                start_year=2015,
                preprocessing={"arima": {"p": -1}},
            )
        with self.assertRaisesRegex(ValueError, "mean.*boolean"):
            adjust(
                values,
                start_year=2015,
                preprocessing={"arima": {"mean": 1}},
            )

    def test_rejects_variable_name_collisions_before_java_processing(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        with self.assertRaisesRegex(ValueError, "already registered: shared.value"):
            adjust(
                values,
                start_year=2015,
                user_variables=[
                    {"group": "shared", "name": "value", "values": [0.0] * 120}
                ],
                calendar_variables=[
                    {
                        "group": "shared",
                        "name": "value",
                        "values": [1.0] * 120,
                        "start_year": 2015,
                    }
                ],
            )

    def test_rejects_options_for_the_wrong_decomposition_method(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        with self.assertRaisesRegex(ValueError, "X11 options"):
            adjust(
                values,
                start_year=2015,
                method="tramoseats",
                decomposition_mode="Additive",
            )
        with self.assertRaisesRegex(ValueError, "seats options"):
            adjust(
                values,
                start_year=2015,
                method="x13",
                seats={"prediction_length": 12},
            )

    def test_rejects_wrong_method_and_unknown_calendar_options(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        cases = (
            ("x13", {"leap_year": True}),
            ("tramoseats", {"length_of_period": "LeapYear"}),
            ("tramoseats", {"easter": {"unknown": True}}),
        )
        for method, calendar in cases:
            with self.subTest(method=method, calendar=calendar):
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    adjust(
                        values,
                        start_year=2015,
                        method=method,
                        calendar=calendar,
                    )

    def test_accepts_none_calendar_type_for_both_methods(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2015,
                    method=method,
                    calendar={"type": "None"},
                )
                self.assertIsInstance(result, AdjustmentResult)
                self.assertEqual(tuple(result.to_compact_dict()), COMPACT_COMPONENTS)

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
                self.assertEqual(tuple(result.to_compact_dict()), COMPACT_COMPONENTS)
                self.assertTrue(
                    all(len(series) == 120 for series in result.to_compact_dict().values())
                )

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
                self.assertEqual(tuple(result.to_compact_dict()), COMPACT_COMPONENTS)
                self.assertTrue(
                    all(len(series) == 120 for series in result.to_compact_dict().values())
                )

    def test_result_type_and_named_components_do_not_depend_on_detail_level(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        compact = adjust(values, start_year=2015)
        detailed = adjust(values, start_year=2015, detailed=True)

        self.assertIsInstance(compact, AdjustmentResult)
        self.assertIsInstance(detailed, AdjustmentResult)
        self.assertEqual(compact.seasonally_adjusted, compact.components["sa"])
        self.assertEqual(
            compact.to_compact_dict()["sa"],
            list(compact.seasonally_adjusted.values),
        )
        self.assertEqual(compact.calendar_adjusted, compact.components["ycal"])
        self.assertEqual(tuple(compact.to_forecast_dict()), FORECAST_COMPONENTS)
        self.assertFalse(compact.series)
        self.assertIn("final.sa", detailed.series)

    def test_zero_horizon_exposes_no_forecasts(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        cases = {
            "x13": {"forecast_horizon": 0},
            "tramoseats": {"seats": {"prediction_length": 0}},
        }
        for method, options in cases.items():
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2015,
                    method=method,
                    **options,
                )
                self.assertEqual(result.to_forecast_dict(), {})

    def test_default_results_include_common_forecasts_for_both_engines(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(120)]

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(values, start_year=2015, method=method)

                self.assertEqual(tuple(result.to_forecast_dict()), FORECAST_COMPONENTS)
                self.assertTrue(
                    all(
                        len(values) == 12
                        for values in result.to_forecast_dict().values()
                    )
                )
                self.assertIsNotNone(result.forecasts.seasonal)

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

    def test_detailed_results_report_automatically_selected_arima_model(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(144)]

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2014,
                    method=method,
                    spec="RSA4",
                    detailed=True,
                )

                self.assertIsNotNone(result.arima_model)
                model = result.arima_model
                assert model is not None
                self.assertTrue(model.automatic)
                self.assertEqual(model.period, 12)
                self.assertRegex(
                    model.notation,
                    r"^ARIMA\(\d+,\d+,\d+\)\(\d+,\d+,\d+\)\[12\]$",
                )

    def test_detailed_results_report_explicit_arima_model(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(144)]
        orders = {
            "p": 0,
            "d": 1,
            "q": 1,
            "bp": 0,
            "bd": 1,
            "bq": 1,
            "mean": False,
        }

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    values,
                    start_year=2014,
                    method=method,
                    spec="RSA4",
                    preprocessing={
                        "arima": orders,
                        "automodel": {"enabled": True},
                    },
                    detailed=True,
                )

                self.assertIsNotNone(result.arima_model)
                model = result.arima_model
                assert model is not None
                self.assertFalse(model.automatic)
                self.assertEqual(model.notation, "ARIMA(0,1,1)(0,1,1)[12]")
                self.assertFalse(model.mean)

    def test_accepts_none_transform_enum(self) -> None:
        values = [100 + index * 0.2 + (index % 12) for index in range(144)]

        result = adjust(
            values,
            start_year=2014,
            method="tramoseats",
            spec="RSA4",
            preprocessing={"transform": {"function": "None"}},
        )

        self.assertEqual(tuple(result.to_compact_dict()), COMPACT_COMPONENTS)


if __name__ == "__main__":
    unittest.main()