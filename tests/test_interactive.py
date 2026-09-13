import unittest

import pandas as pd

from demetrapy import AdjustmentResult, OutputSeries, plot_adjustment_interactive


class InteractivePlotTest(unittest.TestCase):
    def test_builds_interactive_component_and_forecast_traces(self) -> None:
        observed = OutputSeries(tuple(float(value) for value in range(24)), "Monthly", 2020, 1)
        forecast = OutputSeries(tuple(float(value) for value in range(12)), "Monthly", 2022, 1)
        result = AdjustmentResult(
            series={
                **{
                    f"final.{name}": observed
                    for name in ("y", "sa", "t", "s", "i")
                },
                **{
                    f"final.{name}_f": forecast
                    for name in ("y", "sa", "t", "s", "i")
                },
            },
            diagnostics={},
            messages=(),
            method="x13",
            specification="RSA4",
        )

        figure = plot_adjustment_interactive(result, title="Sales")

        self.assertEqual(len(figure.data), 10)
        self.assertEqual(figure.layout.hovermode, "x unified")
        self.assertEqual(figure.layout.title.text, "Sales")
        self.assertEqual(figure.data[2].line.dash, "dash")

    def test_requires_target_for_multi_series_dataframe(self) -> None:
        columns = pd.MultiIndex.from_product(
            [["sales", "orders"], ["y", "sa", "t", "s", "i"]]
        )
        frame = pd.DataFrame([[1.0] * len(columns)] * 3, columns=columns)

        with self.assertRaisesRegex(ValueError, "target is required"):
            plot_adjustment_interactive(frame)


if __name__ == "__main__":
    unittest.main()
