import re
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

import pandas as pd

from demetrapy import (
    AdjustmentComponents,
    AdjustmentResult,
    ArimaModel,
    DataFrameAdjustmentResult,
    OutputSeries,
    ProcessingMessage,
)


def batch_result(*, detailed: bool = True, log: bool = False) -> DataFrameAdjustmentResult:
    index = pd.date_range("2020-01-01", periods=3, freq="MS")
    output = OutputSeries((10.0, 12.0, 11.0), "Monthly", 2020, 1)
    target_result = AdjustmentResult(
        components=AdjustmentComponents(
            output, output, output, output, output, output
        ),
        method="tramoseats",
        specification="RSAfull",
        series={},
        diagnostics={"preprocessing.log": log, "quality": "Good"},
        messages=(ProcessingMessage("Info", "model", "tramoseats", "fitted"),),
        arima_model=ArimaModel(0, 1, 1, 0, 1, 1, 12, False, True),
    )
    names = ("final.y", "final.sa", "final.t", "final.s", "final.i")
    detailed_series = None
    if detailed:
        values = {
            ("sales", name): [10.0, 12.0, 11.0]
            for name in names
        }
        values[("sales", "decomposition.si_cmp")] = (
            [1.1, 0.9, 1.0] if log else [1.0, -1.0, 0.0]
        )
        detailed_series = pd.DataFrame(values, index=index)
        detailed_series.columns = pd.MultiIndex.from_tuples(
            detailed_series.columns,
            names=("series", "output"),
        )
    components = pd.DataFrame(
        {
            ("sales", name): [10.0, 12.0, 11.0]
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
        names=("series", "component"),
    )
    return DataFrameAdjustmentResult(
        components=components,
        results={"sales": target_result},
        detailed_series=detailed_series,
    )


class HtmlReportTest(unittest.TestCase):
    def test_writes_self_contained_additive_report(self) -> None:
        with TemporaryDirectory() as directory:
            path = batch_result().to_html_report(
                Path(directory) / "reports" / "batch.html",
                title="Monthly Review",
            )
            html = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "batch.html")
        self.assertIn("Monthly Review", html)
        self.assertIn("SI component (original - trend)", html)
        self.assertIn("ARIMA(0,1,1)(0,1,1)[12]", html)
        self.assertIn("Plotly.newPlot", html)
        self.assertIsNone(re.search(r'<script[^>]+src=["\']https?://', html))

    def test_labels_log_transformed_si_as_ratio(self) -> None:
        with TemporaryDirectory() as directory:
            path = batch_result(log=True).to_html_report(Path(directory) / "report.html")
            html = path.read_text(encoding="utf-8")

        self.assertIn("SI ratio (original / trend)", html)

    def test_requires_detailed_results(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "detailed=True"):
                batch_result(detailed=False).to_html_report(
                    Path(directory) / "report.html"
                )


if __name__ == "__main__":
    unittest.main()