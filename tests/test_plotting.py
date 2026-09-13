import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd

from seasonal_pri import AdjustmentResult, OutputSeries, plot_adjustment


class PlottingTest(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_plots_compact_result_and_writes_png(self) -> None:
        index = pd.date_range("2020-01-01", periods=24, freq="MS")
        result = {
            "y": range(24),
            "sa": [value + 0.5 for value in range(24)],
            "t": [value + 0.25 for value in range(24)],
            "s": [value % 12 for value in range(24)],
            "i": [0.0] * 24,
        }

        figure = plot_adjustment(result, index=index, title="Sales")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plot.png"
            figure.savefig(path)
            self.assertGreater(path.stat().st_size, 1000)

        self.assertEqual(len(figure.axes), 4)
        self.assertEqual(figure.axes[0].get_title(), "Sales")

    def test_detailed_result_adds_active_effects_panel(self) -> None:
        observed = OutputSeries(tuple(float(value) for value in range(24)), "Monthly", 2020, 1)
        forecast = OutputSeries(tuple(float(value) for value in range(12)), "Monthly", 2022, 1)
        effect = OutputSeries(tuple(float(value % 2) for value in range(24)), "Monthly", 2020, 1)
        result = AdjustmentResult(
            series={
                "final.y": observed,
                "final.sa": observed,
                "final.t": observed,
                "final.s": observed,
                "final.i": observed,
                "final.sa_f": forecast,
                "preprocessing.cal": effect,
            },
            diagnostics={},
            messages=(),
            method="x13",
            specification="RSA4",
        )

        figure = plot_adjustment(result)

        self.assertEqual(len(figure.axes), 5)
        self.assertIn("Adjusted forecast", figure.axes[0].get_legend_handles_labels()[1])

    def test_requires_target_for_multi_series_dataframe(self) -> None:
        columns = pd.MultiIndex.from_product(
            [["sales", "orders"], ["y", "sa", "t", "s", "i"]]
        )
        frame = pd.DataFrame([[1.0] * len(columns)] * 3, columns=columns)

        with self.assertRaisesRegex(ValueError, "target is required"):
            plot_adjustment(frame)


if __name__ == "__main__":
    unittest.main()
