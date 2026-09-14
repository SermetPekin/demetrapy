import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy.cli import run
from demetrapy.config import AdjustmentConfig
from demetrapy.engine import AdjustmentComponents, AdjustmentResult, OutputSeries
from demetrapy.readiness import ReadinessCheck


def adjustment_result(values_by_component, *, detailed=False):
    outputs = {
        name: OutputSeries(tuple(values), "Monthly", 2024, 1)
        for name, values in values_by_component.items()
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
        series={f"final.{name}": output for name, output in outputs.items()}
        if detailed
        else {},
        diagnostics={},
        messages=(),
    )


class ConfigTest(unittest.TestCase):
    def test_loads_engine_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"spec": "RSA5", "benchmarking": True}),
                encoding="utf-8",
            )
            config = AdjustmentConfig.load(path)

        self.assertEqual(config.spec, "RSA5")
        self.assertTrue(config.engine_options()["benchmarking"])

    def test_maps_user_variable_column_to_values(self) -> None:
        config = AdjustmentConfig(
            user_variables=[{"name": "promotion", "column": "promo"}]
        )

        variables = config.engine_options({"promo": [0.0, 1.0]})["user_variables"]

        self.assertEqual(variables, [{"name": "promotion", "values": [0.0, 1.0]}])

    def test_templates_are_valid(self) -> None:
        for method in ("x13", "tramoseats"):
            config = AdjustmentConfig.template(method)
            config.validate()
            self.assertEqual(config.method, method)

    def test_rejects_wrong_method_options_without_starting_java(self) -> None:
        with self.assertRaisesRegex(ValueError, "X11 options"):
            AdjustmentConfig(
                method="tramoseats", forecast_horizon=12
            ).validate()
        with self.assertRaisesRegex(ValueError, "seats options"):
            AdjustmentConfig(seats={"prediction_length": 12}).validate()

    def test_rejects_invalid_specification_and_nested_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported x13 specification"):
            AdjustmentConfig(spec="RSAfull").validate()
        with self.assertRaisesRegex(ValueError, "preprocessing sections"):
            AdjustmentConfig(preprocessing={"unknown": {}}).validate()


class CliTest(unittest.TestCase):
    @patch("demetrapy.cli.adjust")
    def test_audit_option_writes_manifest(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result(
            {name: [10.0, 20.0] for name in ("y", "ycal", "sa", "t", "s", "i")}
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            audit_path = root / "audit"
            input_path.write_text("date,value\n2024-01-01,10\n2024-02-01,20\n")

            exit_code = run(
                [
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--audit",
                    str(audit_path),
                ]
            )

            manifest = json.loads(next(audit_path.glob("*.json")).read_text())

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["status"], "success")

    @patch("demetrapy.cli.run_readiness_checks")
    def test_check_reports_ready_environment(self, mock_checks) -> None:
        mock_checks.return_value = (
            ReadinessCheck("Python", "OK", "3.11 (64-bit)"),
            ReadinessCheck("Java", "OK", "17 (aarch64)"),
        )

        self.assertEqual(run(["check"]), 0)

    @patch("demetrapy.cli.run_readiness_checks")
    def test_check_returns_two_for_blocking_error(self, mock_checks) -> None:
        mock_checks.return_value = (
            ReadinessCheck(
                "Java",
                "ERROR",
                "not found",
                "Install Java 8 or later.",
            ),
        )

        self.assertEqual(run(["check"]), 2)

    def test_validates_config_without_running_adjustment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            normalized_path = Path(directory) / "normalized.json"
            config_path.write_text(
                json.dumps({"method": "x13", "spec": "RSA4"}),
                encoding="utf-8",
            )

            with patch("demetrapy.cli.adjust") as mock_adjust:
                exit_code = run(
                    ["validate", str(config_path), "--output", str(normalized_path)]
                )

            normalized = json.loads(normalized_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(normalized["frequency"], "Monthly")
        mock_adjust.assert_not_called()

    def test_validate_rejects_wrong_method_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "method": "tramoseats",
                        "spec": "RSA4",
                        "forecast_horizon": 12,
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(run(["validate", str(config_path)]), 2)

    def test_init_config_writes_valid_template_and_protects_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "x13.json"

            self.assertEqual(
                run(
                    [
                        "init-config",
                        "--method",
                        "x13",
                        "--output",
                        str(output_path),
                    ]
                ),
                0,
            )
            config = AdjustmentConfig.load(output_path)
            second_exit_code = run(
                [
                    "init-config",
                    "--method",
                    "x13",
                    "--output",
                    str(output_path),
                ]
            )

        self.assertEqual(config.method, "x13")
        self.assertEqual(second_exit_code, 2)

    @patch("demetrapy.cli.adjust")
    def test_writes_adjusted_csv(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result({
            "y": [10.0, 20.0],
            "ycal": [10.0, 20.0],
            "sa": [11.0, 19.0],
            "t": [12.0, 18.0],
            "s": [-1.0, 1.0],
            "i": [-1.0, 1.0],
        })
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "output.csv"
            input_path.write_text("date,value\n2024-01-01,10\n2024-02-01,20\n")

            exit_code = run([str(input_path), "--output", str(output_path)])
            with output_path.open(newline="") as stream:
                rows = list(csv.reader(stream))

        self.assertEqual(exit_code, 0)
        self.assertEqual(rows[0], ["date", "y", "ycal", "sa", "t", "s", "i"])
        self.assertEqual(
            rows[1],
            ["2024-01-01", "10.0", "10.0", "11.0", "12.0", "-1.0", "-1.0"],
        )
        mock_adjust.assert_called_once_with(
            [10.0, 20.0],
            start_year=2024,
            start_period=1,
            frequency="Monthly",
            method="x13",
            spec="RSA4",
            decomposition_mode=None,
            seasonal_filter=None,
            henderson_filter_length=None,
            lower_sigma=None,
            upper_sigma=None,
            forecast_horizon=None,
            backcast_horizon=None,
            benchmarking=False,
            calendar=None,
            user_variables=[],
            outliers=[],
            interventions=[],
            ramps=[],
            fixed_coefficients={},
            preprocessing=None,
            outlier_detection=None,
            seats=None,
        )

    def test_rejects_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            input_path.write_text("when,amount\n2024-01-01,10\n")
            self.assertEqual(run([str(input_path)]), 2)

    @patch("demetrapy.cli.adjust")
    def test_named_data_and_cli_options_override_config(self, mock_adjust) -> None:
        mock_adjust.return_value = adjustment_result(
            {
                name: [10.0, 20.0]
                for name in ("y", "ycal", "sa", "t", "s", "i")
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            data_path = Path(directory) / "quarterly.csv"
            config_path = Path(directory) / "config.json"
            output_path = Path(directory) / "output.csv"
            data_path.write_text("period,sales\n2024-01-01,10\n2024-04-01,20\n")
            config_path.write_text(json.dumps({"method": "x13", "spec": "RSA4"}))

            exit_code = run(
                [
                    "--data",
                    str(data_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_path),
                    "--method",
                    "tramoseats",
                    "--spec",
                    "RSAfull",
                    "--frequency",
                    "Quarterly",
                    "--date-column",
                    "period",
                    "--value-column",
                    "sales",
                ]
            )

        self.assertEqual(exit_code, 0)
        options = mock_adjust.call_args.kwargs
        self.assertEqual(options["method"], "tramoseats")
        self.assertEqual(options["spec"], "RSAfull")
        self.assertEqual(options["frequency"], "Quarterly")
        self.assertEqual(options["start_period"], 1)

    def test_rejects_two_data_file_arguments(self) -> None:
        self.assertEqual(run(["first.csv", "--data", "second.csv"]), 2)

    @patch("demetrapy.cli.plot_adjustment")
    @patch("demetrapy.cli.adjust")
    def test_plot_output_uses_detailed_result(self, mock_adjust, mock_plot) -> None:
        mock_adjust.return_value = adjustment_result(
            {
                name: [10.0, 20.0]
                for name in ("y", "ycal", "sa", "t", "s", "i")
            },
            detailed=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.csv"
            output_path = Path(directory) / "output.csv"
            plot_path = Path(directory) / "plot.png"
            input_path.write_text("date,value\n2024-01-01,10\n2024-02-01,20\n")

            exit_code = run(
                [
                    "--data",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--plot-output",
                    str(plot_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(mock_adjust.call_args.kwargs["detailed"])
        mock_plot.assert_called_once()
        mock_plot.return_value.savefig.assert_called_once_with(plot_path, dpi=150)


if __name__ == "__main__":
    unittest.main()