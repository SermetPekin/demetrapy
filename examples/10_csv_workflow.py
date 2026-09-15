"""Create, validate, and run a complete file-based adjustment workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from demetrapy import adjust_csv, load_monthly_retail
from demetrapy.config import AdjustmentConfig


def main() -> None:
    output_directory = Path("csv_workflow_output")
    output_directory.mkdir(parents=True, exist_ok=True)
    input_path = output_directory / "monthly_sales.csv"
    config_path = output_directory / "x13.json"
    adjusted_path = output_directory / "monthly_sales_adjusted.csv"
    audit_directory = output_directory / "audit"

    input_frame = load_monthly_retail()[["sales"]].rename(columns={"sales": "value"})
    input_frame.to_csv(input_path)

    config = AdjustmentConfig.template("x13")
    config.validate()
    config_path.write_text(
        json.dumps(config.to_dict(omit_empty=True), indent=2) + "\n",
        encoding="utf-8",
    )

    result = adjust_csv(
        input_path,
        config=config_path,
        output=adjusted_path,
        audit=audit_directory,
        detailed=True,
    )
    adjusted = pd.read_csv(adjusted_path)
    audit_manifest_path = next(audit_directory.glob("*.json"))
    audit_manifest = json.loads(audit_manifest_path.read_text(encoding="utf-8"))

    print(f"Input rows: {len(input_frame)}")
    print(f"Adjusted rows: {len(adjusted)}")
    print(f"Output columns: {', '.join(adjusted.columns)}")
    print(f"Diagnostics: {len(result.diagnostics)}")
    print(f"Processing messages: {len(result.messages)}")
    print(f"Audit run: {audit_manifest['run_id']} ({audit_manifest['status']})")
    print(f"Input SHA-256: {audit_manifest['input']['sha256']}")
    print(f"Configuration SHA-256: {audit_manifest['configuration_sha256']}")
    if result.arima_model is not None:
        print(f"ARIMA model: {result.arima_model.notation}")

    try:
        AdjustmentConfig(
            method="tramoseats",
            spec="RSA4",
            forecast_horizon=12,
        ).validate()
    except ValueError as error:
        print(f"Rejected invalid configuration: {error}")
    else:
        raise AssertionError("invalid configuration should have been rejected")

    assert len(adjusted) == len(input_frame)
    assert list(adjusted.columns) == ["date", "y", "ycal", "sa", "t", "s", "i"]
    assert audit_manifest["status"] == "success"
    assert len((audit_directory / "runs.jsonl").read_text().splitlines()) == 1
    assert str(input_frame.iloc[0, 0]) not in audit_manifest_path.read_text(encoding="utf-8")
    print(f"Saved workflow files under {output_directory}/")


if __name__ == "__main__":
    main()