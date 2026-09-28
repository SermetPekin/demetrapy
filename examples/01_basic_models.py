"""Run typed X13 and TRAMO/SEATS configurations on the same series."""

from pathlib import Path
from tempfile import TemporaryDirectory

from demetrapy import TramoSeatsConfig, X13Config, adjust_dataframe, load_monthly_retail


def main() -> None:
    data = load_monthly_retail()

    configurations = (
        X13Config(spec="RSA4", forecast_horizon=12),
        TramoSeatsConfig(spec="RSA4", seats={"prediction_length": 12}),
    )
    for config in configurations:
        result = adjust_dataframe(data, config=config)
        sales = result.for_series("sales")

        # Recommended: date-indexed DataFrames containing only adjusted values.
        sa = result.sa
        ycal = result.ycal
        adjusted_forecast = result.adjusted_forecast

        # Explicit names for the same adjusted history and forecast components.
        explicit_adjusted = result.seasonally_adjusted
        explicit_forecast = result.to_forecast_frame().xs(
            "seasonally_adjusted",
            axis="columns",
            level="component",
        )

        # Tables containing every historical or forecast component.
        all_components = result.components
        all_forecasts = result.to_forecast_frame()
        compact_components = result.to_compact_frame()
        compact_forecasts = result.to_forecast_frame(compact=True)
        history_and_forecasts = result.to_combined_frame()

        # Generic selectors accept compact or descriptive component names.
        trend = result.component("t")
        trend_forecast = result.forecast("trend")
        complete_sa = result.combined("sa")
        status = result.status

        # Single-series objects and compact lists for non-pandas integrations.
        adjusted_values = sales.adjusted.values
        forecast_values = sales.adjusted_forecast.values
        compact_values = sales.to_compact_dict()["sa"]
        compact_forecast_values = sales.to_forecast_dict()["sa_f"]

        print(f"\n{sales.method.upper()} adjusted data")
        print("Input, SA, and YCAL shapes:", data.shape, sa.shape, ycal.shape)
        print("\nSeasonally adjusted")
        print(sa.tail(3).round(2))
        print("\nCalendar adjusted")
        print(ycal.tail(3).round(2))
        print("\nAdjusted forecast")
        print(adjusted_forecast.head(3).round(2))
        print("\nEquivalent adjusted DataFrames:", sa.equals(explicit_adjusted))
        print("Equivalent forecast DataFrames:", adjusted_forecast.equals(explicit_forecast))
        print(
            "Available table shapes:",
            {
                "all_components": all_components.shape,
                "all_forecasts": all_forecasts.shape,
                "compact_components": compact_components.shape,
                "compact_forecasts": compact_forecasts.shape,
                "history_and_forecasts": history_and_forecasts.shape,
                "trend": trend.shape,
                "trend_forecast": trend_forecast.shape,
                "complete_sa": complete_sa.shape,
            },
        )
        print("\nProcessing status")
        print(status.to_string(index=False))
        print(
            "Single-series value counts:",
            len(adjusted_values),
            len(forecast_values),
            len(compact_values),
            len(compact_forecast_values),
        )

        # Export one exact-shape CSV or multiple component sheets in XLSX.
        with TemporaryDirectory() as directory:
            output = Path(directory)
            csv_path = result.export(output / "sa.csv", components=["sa"])
            excel_path = result.export(
                output / "adjusted.xlsx",
                components=["sa", "ycal"],
            )
            print("Temporary exports:", csv_path.name, excel_path.name)


if __name__ == "__main__":
    main()