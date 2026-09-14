import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demetrapy.cli import run
from demetrapy.config import AdjustmentConfig
from demetrapy.engine import AdjustmentComponents, AdjustmentResult, OutputSeries


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


class CliTest(unittest.TestCase):
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