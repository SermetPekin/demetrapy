import io
import json
import unittest

import pandas as pd

from demetrapy.dashboard import (
    _diagnostics_frame,
    _indexed_frame,
    _model_preprocessing,
    _uploaded_config,
)


class Upload:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


class DashboardHelperTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
