import io
import json
import unittest

import pandas as pd

from demetrapy import adjust_dataframe, load_monthly_retail
from demetrapy.config import METHOD_SPECIFICATIONS
from demetrapy.dashboard import (
    _dashboard_preprocessing,
    _diagnostics_frame,
    _indexed_frame,
    _model_preprocessing,
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


if __name__ == "__main__":
    unittest.main()
