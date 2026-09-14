import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy import adjust_csv
from demetrapy.engine import AdjustmentComponents, AdjustmentResult, OutputSeries


def adjustment_result() -> AdjustmentResult:
    outputs = {
        name: OutputSeries(values, "Monthly", 2024, 1)
        for name, values in {
            "y": (10.0, 20.0),
            "ycal": (10.0, 20.0),
            "sa": (11.0, 19.0),
            "t": (12.0, 18.0),
            "s": (-1.0, 1.0),
            "i": (-1.0, 1.0),
        }.items()
    }
    return AdjustmentResult(
        components=AdjustmentComponents(
            observed=outputs["y"],
            calendar_adjusted=outputs["ycal"],
            seasonally_adjusted=outputs["sa"],
            trend=outputs["t"],
            seasonal=outputs["s"],
            irregular=outputs["i"],
        ),
        method="x13",
        specification="RSA4",
        series={},
        diagnostics={},
        messages=(),
    )


class AdjustCsvTest(unittest.TestCase):
    @patch("demetrapy.csv_io.adjust")
    def test_returns_result_and_writes_compact_csv(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result()
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "adjusted.csv"
            input_path.write_text(
                "date,value\n2024-01-01,10\n2024-02-01,20\n",
                encoding="utf-8",
            )

            result = adjust_csv(
                input_path,
                output=output_path,
                forecast_horizon=12,
            )
            with output_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.reader(stream))

        self.assertIs(result, mock_adjust.return_value)
        self.assertEqual(rows[0], ["date", "y", "ycal", "sa", "t", "s", "i"])
        self.assertEqual(mock_adjust.call_args.kwargs["forecast_horizon"], 12)

    def test_rejects_unknown_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid config override"):
            adjust_csv("unused.csv", unknown_option=True)


if __name__ == "__main__":
    unittest.main()