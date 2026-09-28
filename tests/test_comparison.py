import os
import unittest
from unittest.mock import patch

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd

from demetrapy import (
    AdjustmentComponents,
    AdjustmentResult,
    DataFrameAdjustmentResult,
    OutputSeries,
    TramoSeatsConfig,
    X13Config,
    compare_adjustments,
    plot_comparison,
)


def adjustment_result(
    method: str,
    values: tuple[float, ...],
) -> DataFrameAdjustmentResult:
    index = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    components = pd.DataFrame(
        {
            ("sales", component): values
            for component in (
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
    output = OutputSeries(values, "Monthly", 2024, 1)
    result = AdjustmentResult(
        components=AdjustmentComponents(
            output, output, output, output, output, output
        ),
        method=method,
        specification="RSA4",
        series={},
        diagnostics={},
        messages=(),
    )
    return DataFrameAdjustmentResult(components=components, results={"sales": result})


class AdjustmentComparisonTest(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_compares_labeled_candidates_across_every_component(self) -> None:
        data = pd.DataFrame(
            {"sales": [10.0, 20.0, 30.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="MS"),
        )
        first = adjustment_result("x13", (10.0, 20.0, 30.0))
        second = adjustment_result("tramoseats", (12.0, 18.0, 33.0))

        with patch(
            "demetrapy.comparison.adjust_dataframe",
            side_effect=(first, second),
        ) as adjust_mock:
            comparison = compare_adjustments(
                data,
                {
                    "x13-rsa4": X13Config(spec="RSA4"),
                    "tramoseats-rsa4": TramoSeatsConfig(spec="RSA4"),
                },
                detailed=True,
            )

        self.assertEqual(adjust_mock.call_count, 2)
        self.assertTrue(all(call.kwargs["detailed"] for call in adjust_mock.call_args_list))
        self.assertEqual(
            comparison.components.columns.names,
            ["candidate", "series", "component"],
        )
        self.assertEqual(len(comparison.metrics), 6)
        seasonal = comparison.metrics.query("component == 'seasonally_adjusted'").iloc[0]
        self.assertAlmostEqual(seasonal["rmse"], (17 / 3) ** 0.5)
        self.assertEqual(seasonal["max_absolute_difference"], 3.0)
        self.assertAlmostEqual(seasonal["mean_difference"], -1.0)
        self.assertEqual(seasonal["observations"], 3)
        self.assertIs(comparison.for_candidate("x13-rsa4"), first)
        pd.testing.assert_frame_equal(
            comparison.for_series("sales"),
            pd.DataFrame(
                {
                    "x13-rsa4": [10.0, 20.0, 30.0],
                    "tramoseats-rsa4": [12.0, 18.0, 33.0],
                },
                index=data.index,
            ).rename_axis(columns="candidate"),
        )

        figure = plot_comparison(comparison, "sales")
        self.assertEqual(len(figure.axes), 2)
        self.assertEqual(
            figure.axes[0].get_legend_handles_labels()[1],
            ["x13-rsa4", "tramoseats-rsa4"],
        )
        self.assertEqual(
            figure.axes[1].get_legend_handles_labels()[1],
            ["tramoseats-rsa4 - x13-rsa4"],
        )

    def test_requires_two_typed_candidates(self) -> None:
        data = pd.DataFrame(
            {"sales": [1.0, 2.0, 3.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="MS"),
        )

        with self.assertRaisesRegex(ValueError, "at least two"):
            compare_adjustments(data, {"only": X13Config()})
        with self.assertRaisesRegex(TypeError, "must use a demetrapy configuration"):
            compare_adjustments(data, {"first": X13Config(), "second": object()})


if __name__ == "__main__":
    unittest.main()