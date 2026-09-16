"""Summarize a multi-series TRAMO/SEATS run for batch review."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from demetrapy import TramoSeatsConfig, adjust_dataframe, load_monthly_emissions


def build_batch_summary(data: pd.DataFrame) -> pd.DataFrame:
    result = adjust_dataframe(
        data,
        config=TramoSeatsConfig(
            spec="RSAfull",
            preprocessing={"automodel": {"enabled": True}},
            seats={"prediction_length": 12},
        ),
        detailed=True,
    )
    return result.to_summary_frame()


if __name__ == "__main__":
    output_directory = Path("example_output")
    output_directory.mkdir(exist_ok=True)

    summary = build_batch_summary(load_monthly_emissions())
    follow_up = summary.loc[
        (summary["message_count"] > 0) | summary["arima"].isna()
    ]

    assert len(summary) == 10
    assert summary["forecast_periods"].eq(12).all()
    assert summary["method"].eq("tramoseats").all()

    print("TRAMO/SEATS batch summary:")
    print(summary.to_string(index=False))
    print(f"\nSeries with messages or missing model metadata: {len(follow_up)}")
    if not follow_up.empty:
        print(
            follow_up[["series", "arima", "message_count"]].to_string(index=False)
        )

    output_path = output_directory / "batch_summary.csv"
    summary.to_csv(output_path, index=False)
    print(f"\nSaved {output_path}")