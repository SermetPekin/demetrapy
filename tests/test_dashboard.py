import io
import json
import unittest
from datetime import date, datetime

import pandas as pd

from demetrapy import adjust_dataframe, load_monthly_retail
from demetrapy.config import AdjustmentConfig, METHOD_SPECIFICATIONS
from demetrapy.dashboard import (
    _PASTED_MONTHLY_EXAMPLE,
    _dashboard_engine_options,
    _dashboard_preprocessing,
    _diagnostics_frame,
    _input_profile,
    _history_comparison,
    _indexed_frame,
    _method_comparison,
    _model_preprocessing,
    _pasted_frame,
    _python_script,
    _remove_history_runs,
    _clear_run_history,
    _run_snapshot,
    _sample_inputs,
    _uploaded_config,
)


class Upload:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


class DashboardHelperTest(unittest.TestCase):
    def test_every_x13_menu_preset_runs_through_dashboard_options(self) -> None:
        frame = load_monthly_retail()[["sales"]]

        for specification in METHOD_SPECIFICATIONS["x13"]:
            with self.subTest(specification=specification):
                preprocessing = _dashboard_preprocessing(
                    specification,
                    None,
                    "Automatic",
                    {},
                )
                result = adjust_dataframe(
                    frame,
                    method="x13",
                    spec=specification,
                    preprocessing=preprocessing,
                    detailed=True,
                )

                self.assertEqual(result.components.shape, (120, 6))
                self.assertIn(
                    ("sales", "final.sa"),
                    result.detailed_series.columns,
                )
                self.assertEqual(
                    result.for_series("sales").specification,
                    specification,
                )

    def test_loads_monthly_and_quarterly_samples(self) -> None:
        monthly, monthly_calendar, monthly_mapping = _sample_inputs(
            "Monthly retail"
        )
        quarterly, quarterly_calendar, quarterly_mapping = _sample_inputs(
            "Quarterly production"
        )

        self.assertEqual(list(monthly.columns), ["date", "sales", "orders"])
        self.assertIsNone(monthly_calendar)
        self.assertEqual(monthly_mapping, {})
        self.assertEqual(list(quarterly.columns), ["quarter", "production"])
        self.assertIsNone(quarterly_calendar)
        self.assertEqual(quarterly_mapping, {})

    def test_loads_calendar_sample_with_default_selections(self) -> None:
        observations, calendar_pool, mapping = _sample_inputs(
            "Retail with calendars"
        )

        self.assertEqual(list(observations.columns), ["date", "sales", "orders"])
        self.assertIsNotNone(calendar_pool)
        self.assertEqual(mapping["sales"], ["retail_days"])
        self.assertEqual(mapping["orders"], ["retail_days", "delivery_days"])

    def test_rejects_unknown_sample(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown sample dataset"):
            _sample_inputs("missing")

    def test_loads_uploaded_configuration(self) -> None:
        upload = Upload(json.dumps({"method": "tramoseats", "spec": "RSAfull"}).encode())

        config = _uploaded_config(upload)

        self.assertEqual(config.method, "tramoseats")
        self.assertEqual(config.spec, "RSAfull")

    def test_builds_datetime_indexed_target_frame(self) -> None:
        raw = pd.read_csv(
            io.StringIO("period,sales,orders\n2024-01-01,10,3\n2024-02-01,12,4\n")
        )

        frame = _indexed_frame(raw, "period", ["sales", "orders"], pd)

        self.assertIsInstance(frame.index, pd.DatetimeIndex)
        self.assertEqual(list(frame.columns), ["sales", "orders"])
        self.assertEqual(frame.index.name, "period")

    def test_parses_comma_separated_pasted_series_with_header(self) -> None:
        raw = _pasted_frame(
            "sales,orders\n10.5,3\n12,4\n11.5,5",
            "Monthly",
            date(2024, 2, 17),
            pd,
        )

        self.assertEqual(list(raw.columns), ["date", "sales", "orders"])
        self.assertEqual(raw["sales"].tolist(), [10.5, 12.0, 11.5])
        self.assertEqual(
            raw["date"].tolist(),
            [
                pd.Timestamp("2024-02-01"),
                pd.Timestamp("2024-03-01"),
                pd.Timestamp("2024-04-01"),
            ],
        )

    def test_builtin_pasted_example_has_four_years_of_monthly_data(self) -> None:
        raw = _pasted_frame(
            _PASTED_MONTHLY_EXAMPLE,
            "Monthly",
            date(2015, 1, 1),
            pd,
        )

        self.assertEqual(raw.shape, (48, 2))
        self.assertEqual(raw.columns.tolist(), ["date", "sales"])
        self.assertEqual(raw["date"].iloc[-1], pd.Timestamp("2018-12-01"))

    def test_parses_space_separated_quarterly_values_without_header(self) -> None:
        raw = _pasted_frame(
            "10 3\n12 4\n11 5",
            "Quarterly",
            date(2023, 4, 1),
            pd,
        )

        self.assertEqual(list(raw.columns), ["date", "series_1", "series_2"])
        self.assertEqual(
            raw["date"].tolist(),
            [
                pd.Timestamp("2023-04-01"),
                pd.Timestamp("2023-07-01"),
                pd.Timestamp("2023-10-01"),
            ],
        )

    def test_rejects_inconsistent_pasted_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "same number of values"):
            _pasted_frame("10 3\n12\n11 5", "Monthly", date(2024, 1, 1), pd)

    def test_rejects_missing_selected_column(self) -> None:
        raw = pd.DataFrame({"date": ["2024-01-01"], "sales": [10]})

        with self.assertRaisesRegex(ValueError, "missing columns"):
            _indexed_frame(raw, "date", ["orders"], pd)

    def test_normalizes_mixed_diagnostics_for_arrow(self) -> None:
        diagnostics = _diagnostics_frame(
            {"likelihood": 12.5, "method": "tramoseats", "converged": True},
            pd,
        )

        self.assertEqual(
            diagnostics["Value"].tolist(), ["12.5", "tramoseats", "True"]
        )

    def test_generates_reproducible_python_script_for_latest_run(self) -> None:
        frame = pd.DataFrame(
            {"sales": [10.5, 11.25]},
            index=pd.date_range("2024-01-01", periods=2, freq="MS", name="date"),
        )
        calendar_pool = pd.DataFrame(
            {"working_days": [22.0, 20.0]},
            index=frame.index,
        )
        options = {
            "preprocessing": {"transform": {"function": "Log"}},
            "seats": {"prediction_length": 12},
        }

        script = _python_script(
            frame,
            method="tramoseats",
            specification="RSAfull",
            options=options,
            calendar_pool=calendar_pool,
            calendar_mapping={"sales": ["working_days"]},
        )

        compile(script, "demetrapy-latest-run.py", "exec")
        self.assertIn("2024-01-01T00:00:00,10.5", script)
        self.assertIn("method='tramoseats'", script)
        self.assertIn("spec='RSAfull'", script)
        self.assertIn("'prediction_length': 12", script)
        self.assertIn("'sales': ['working_days']", script)
        self.assertIn("demetrapy-components.csv", script)

    def test_model_preprocessing_switches_between_explicit_and_auto(self) -> None:
        explicit = _model_preprocessing(
            {"transform": {"function": "Log"}, "automodel": {"pcr": 0.95}},
            "Explicit",
            {"p": 1, "d": 1, "q": 0, "bp": 0, "bd": 1, "bq": 1},
        )
        automatic = _model_preprocessing(explicit, "Automatic", {})

        self.assertEqual(explicit["arima"]["p"], 1)
        self.assertEqual(explicit["transform"], {"function": "Log"})
        self.assertNotIn("arima", automatic)
        self.assertEqual(automatic["automodel"], {"pcr": 0.95, "enabled": True})

    def test_x11_only_preset_omits_preprocessing(self) -> None:
        preprocessing = _dashboard_preprocessing(
            "RSAX11",
            {"automodel": {"enabled": True}},
            "Automatic",
            {},
        )

        self.assertIsNone(preprocessing)

    def test_regarima_preset_keeps_selected_preprocessing(self) -> None:
        preprocessing = _dashboard_preprocessing(
            "RSA4",
            {"automodel": {"pcr": 0.95}},
            "Automatic",
            {},
        )

        self.assertEqual(
            preprocessing,
            {"automodel": {"pcr": 0.95, "enabled": True}},
        )

    def test_profiles_frequency_range_and_invalid_values(self) -> None:
        raw = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-02-01", "bad"],
                "sales": [10, float("inf"), None],
            }
        )

        profile = _input_profile(raw, "date", ["sales"], pd)

        self.assertEqual(profile["frequency"], "Monthly")
        self.assertEqual(profile["missing"], 2)
        self.assertEqual(profile["nonfinite"], 1)
        self.assertEqual(profile["recommended_minimum"], 36)

    def test_builds_x13_dashboard_options_without_losing_uploaded_settings(self) -> None:
        config = AdjustmentConfig(
            method="x13",
            preprocessing={"automodel": {"mixed": False}},
            calendar={"type": "TradingDays"},
            outlier_detection={"critical_value": 3.5},
        )

        options = _dashboard_engine_options(
            config,
            {},
            method="x13",
            specification="RSA4",
            arima_mode="Automatic",
            explicit_arima={},
            transform_function="Log",
            forecast_horizon=18,
            customize_outliers=True,
            outlier_types=["AO", "TC"],
        )

        self.assertEqual(options["forecast_horizon"], 18)
        self.assertEqual(options["calendar"], {"type": "TradingDays"})
        self.assertEqual(options["preprocessing"]["transform"], {"function": "Log"})
        self.assertEqual(
            options["outlier_detection"],
            {"critical_value": 3.5, "types": ["AO", "TC"]},
        )
        self.assertNotIn("seats", options)

    def test_builds_clean_tramoseats_options_from_x13_config(self) -> None:
        config = AdjustmentConfig(
            method="x13",
            forecast_horizon=24,
            seasonal_filter="S3X5",
            calendar={"type": "TradingDays"},
        )

        options = _dashboard_engine_options(
            config,
            {},
            method="tramoseats",
            specification="RSA4",
            arima_mode="Automatic",
            explicit_arima={},
            transform_function="Auto",
            forecast_horizon=8,
            customize_outliers=False,
            outlier_types=[],
        )

        self.assertEqual(options["seats"], {"prediction_length": 8})
        self.assertIsNone(options["calendar"])
        self.assertIsNone(options["outlier_detection"])
        for name in ("forecast_horizon", "seasonal_filter"):
            self.assertNotIn(name, options)

    def test_rsax11_discards_model_and_outlier_preprocessing(self) -> None:
        options = _dashboard_engine_options(
            AdjustmentConfig(outlier_detection={"types": ["AO"]}),
            {},
            method="x13",
            specification="RSAX11",
            arima_mode="Automatic",
            explicit_arima={},
            transform_function="Log",
            forecast_horizon=12,
            customize_outliers=True,
            outlier_types=["AO"],
        )

        self.assertIsNone(options["preprocessing"])
        self.assertIsNone(options["outlier_detection"])

    def test_compares_x13_and_tramoseats_adjusted_series(self) -> None:
        frame = load_monthly_retail()[["sales"]]
        x13 = adjust_dataframe(frame, method="x13", spec="RSA4")
        tramoseats = adjust_dataframe(frame, method="tramoseats", spec="RSA4")

        comparison, metrics = _method_comparison(
            x13,
            tramoseats,
            "sales",
            pd,
        )

        self.assertEqual(
            comparison.columns.tolist(),
            ["x13", "tramoseats", "difference"],
        )
        self.assertEqual(
            metrics["Metric"].tolist(),
            ["RMSE", "Maximum absolute difference", "Correlation"],
        )
        self.assertGreater(metrics.loc[0, "Value"], 0)

    def test_snapshots_and_compares_session_runs(self) -> None:
        frame = load_monthly_retail()[["sales"]]
        x13 = adjust_dataframe(frame, method="x13", spec="RSA4")
        tramoseats = adjust_dataframe(frame, method="tramoseats", spec="RSA4")
        common = {
            "targets": ["sales"],
            "arima_mode": "Automatic",
            "transform_function": "Auto",
            "forecast_horizon": 12,
            "detect_outliers": True,
            "outlier_types": ["AO", "LS", "TC"],
            "timestamp": datetime(2026, 9, 25, 14, 30),
        }
        first = _run_snapshot(
            1,
            x13,
            method="x13",
            specification="RSA4",
            **common,
        )
        second = _run_snapshot(
            2,
            tramoseats,
            method="tramoseats",
            specification="RSA4",
            **common,
        )

        comparison, metrics, settings = _history_comparison(
            first,
            second,
            "sales",
            pd,
        )

        self.assertEqual(first["label"], "Run 1 · x13/RSA4 · 14:30:00")
        self.assertEqual(first["settings"]["Outliers"], "AO, LS, TC")
        self.assertEqual(comparison.columns[-1], "difference")
        self.assertEqual(metrics["Metric"].iloc[0], "RMSE")
        self.assertEqual(settings["Setting"].iloc[0], "Method")
        self.assertTrue(
            settings.drop(columns="Setting").map(lambda value: isinstance(value, str)).all().all()
        )

        state = {
            "demetrapy_run_history": [first, second],
            "demetrapy_history_selection": [first["label"], second["label"]],
        }
        _remove_history_runs(state, [first["label"]])
        self.assertEqual(state["demetrapy_run_history"], [second])
        self.assertEqual(state["demetrapy_history_selection"], [])
        _clear_run_history(state)
        self.assertEqual(state["demetrapy_run_history"], [])


if __name__ == "__main__":
    unittest.main()
