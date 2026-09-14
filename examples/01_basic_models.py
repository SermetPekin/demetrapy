"""Run typed X13 and TRAMO/SEATS configurations on the same series."""

from demetrapy import TramoSeatsConfig, X13Config, adjust_dataframe, load_monthly_retail


def main() -> None:
    data = load_monthly_retail()[["sales"]]

    configurations = (
        X13Config(spec="RSA4", forecast_horizon=12),
        TramoSeatsConfig(spec="RSA4", seats={"prediction_length": 12}),
    )
    for config in configurations:
        result = adjust_dataframe(data, config=config)
        sales = result.for_series("sales")
        print(f"\n{result.for_series('sales').method.upper()}")
        print(result.to_compact_frame()["sales"].tail(3).round(2))
        print("Seasonally adjusted forecast:")
        print(sales.to_forecast_dict()["sa_f"])


if __name__ == "__main__":
    main()