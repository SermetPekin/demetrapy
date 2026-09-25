import unittest

import pandas as pd

from demetrapy import (
    AdjustmentComponents,
    AdjustmentResult,
    OutputSeries,
    plot_adjustment_interactive,
)


class InteractivePlotTest(unittest.TestCase):
    def test_builds_interactive_component_and_forecast_traces(self) -> None:
        observed = OutputSeries(tuple(float(value) for value in range(24)), "Monthly", 2020, 1)
        forecast = OutputSeries(tuple(float(value) for value in range(12)), "Monthly", 2022, 1)
        result = AdjustmentResult(
            components=AdjustmentComponents(
                observed, observed, observed, observed, observed, observed
            ),
            method="x13",
            specification="RSA4",
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
        )

        figure = plot_adjustment_interactive(result, title="Sales")

        self.assertEqual(len(figure.data), 10)
        self.assertEqual(figure.layout.hovermode, "x unified")
        self.assertEqual(figure.layout.title.text, "Sales")
        self.assertEqual(figure.data[2].line.dash, "dot")
        self.assertEqual(figure.layout.xaxis4.title.text, "Date")
        self.assertEqual(figure.layout.xaxis4.tickformat, "%b\n%Y")
        self.assertTrue(figure.layout.xaxis.showticklabels)
        self.assertIn("Date: %{x|%B %Y}", figure.data[0].hovertemplate)
        self.assertGreaterEqual(len(figure.layout.shapes), 8)
        self.assertEqual(figure.layout.annotations[-1].text, "Forecast")
        self.assertEqual(figure.layout.annotations[0].xanchor, "left")

    def test_requires_target_for_multi_series_dataframe(self) -> None:
        columns = pd.MultiIndex.from_product(
            [["sales", "orders"], ["y", "sa", "t", "s", "i"]]
        )
        frame = pd.DataFrame([[1.0] * len(columns)] * 3, columns=columns)

        with self.assertRaisesRegex(ValueError, "target is required"):
            plot_adjustment_interactive(frame)


if __name__ == "__main__":
    unittest.main()
