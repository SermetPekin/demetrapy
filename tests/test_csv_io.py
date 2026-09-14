import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy import TramoSeatsConfig, adjust_csv
from demetrapy.config import AdjustmentConfig
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
    def test_accepts_method_specific_config(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result()
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            input_path.write_text(
                "date,value\n2024-01-01,10\n2024-02-01,20\n",
                encoding="utf-8",
            )

            adjust_csv(
                input_path,
                config=TramoSeatsConfig(
                    spec="RSAfull",
                    seats={"prediction_length": 12},
                ),
            )

        self.assertEqual(mock_adjust.call_args.kwargs["method"], "tramoseats")
        self.assertEqual(mock_adjust.call_args.kwargs["spec"], "RSAfull")
        self.assertEqual(
            mock_adjust.call_args.kwargs["seats"],
            {"prediction_length": 12},
        )

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

    def test_rejects_override_that_conflicts_with_typed_config(self) -> None:
        with self.assertRaisesRegex(ValueError, "method"):
            adjust_csv(
                "unused.csv",
                config=TramoSeatsConfig(),
                method="x13",
            )

    @patch("demetrapy.csv_io.adjust")
    def test_writes_success_manifest_and_history(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "adjusted.csv"
            audit_path = root / "audit"
            input_path.write_text(
                "date,value\n2024-01-01,10\n2024-02-01,20\n",
                encoding="utf-8",
            )

            adjust_csv(
                input_path,
                output=output_path,
                audit=audit_path,
            )
            manifest_path = next(
                path for path in audit_path.glob("*.json") if path.name != "runs.jsonl"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            history = [
                json.loads(line)
                for line in (audit_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(manifest["status"], "success")
        self.assertEqual(manifest["input"]["filename"], "input.csv")
        self.assertEqual(manifest["input"]["rows"], 2)
        self.assertEqual(len(manifest["input"]["sha256"]), 64)
        self.assertEqual(manifest["output"]["filename"], "adjusted.csv")
        self.assertEqual(len(manifest["output"]["sha256"]), 64)
        self.assertEqual(manifest["result"]["method"], "x13")
        self.assertEqual(history, [manifest])

    @patch("demetrapy.csv_io.adjust", side_effect=RuntimeError("processing failed"))
    def test_writes_failure_manifest_and_preserves_exception(self, mock_adjust) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            audit_path = root / "audit"
            input_path.write_text(
                "date,value\n2024-01-01,10\n2024-02-01,20\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "processing failed"):
                adjust_csv(input_path, audit=audit_path)
            manifest_path = next(audit_path.glob("*.json"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["exception"]["type"], "RuntimeError")
        self.assertEqual(manifest["exception"]["message"], "processing failed")
        self.assertIsNone(manifest["result"])

    @patch("demetrapy.csv_io.adjust")
    def test_redacts_inline_variable_values(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result()
        config = AdjustmentConfig(
            user_variables=[{"name": "promotion", "values": [0.0, 1.0]}]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            audit_path = root / "audit"
            input_path.write_text(
                "date,value\n2024-01-01,10\n2024-02-01,20\n",
                encoding="utf-8",
            )

            adjust_csv(input_path, config=config, audit=audit_path)
            manifest_path = next(audit_path.glob("*.json"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        values = manifest["configuration"]["user_variables"][0]["values"]
        self.assertTrue(values["redacted"])
        self.assertEqual(values["count"], 2)
        self.assertEqual(len(values["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()