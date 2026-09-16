"""Generate a self-contained interactive TRAMO/SEATS review report."""

from __future__ import annotations

from pathlib import Path

from demetrapy import TramoSeatsConfig, adjust_dataframe, load_monthly_emissions


if __name__ == "__main__":
    data = load_monthly_emissions()[["power", "transport", "industry"]]
    result = adjust_dataframe(
        data,
        config=TramoSeatsConfig(
            spec="RSAfull",
            preprocessing={"automodel": {"enabled": True}},
            seats={"prediction_length": 12},
        ),
        detailed=True,
    )

    output_path = result.to_html_report(
        Path("example_output") / "tramoseats_report.html",
        title="Monthly Emissions TRAMO/SEATS Review",
    )

    assert output_path.is_file()
    print(f"Saved interactive report to {output_path}")