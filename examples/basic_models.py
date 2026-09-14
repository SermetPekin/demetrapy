"""Run X13 and TRAMO/SEATS on the same monthly retail series."""

from demetrapy import adjust_dataframe, load_monthly_retail


def main() -> None:
    data = load_monthly_retail()[["sales"]]

    for method in ("x13", "tramoseats"):
        result = adjust_dataframe(
            data,
            method=method,
            spec="RSA4",
            forecast_horizon=12 if method == "x13" else None,
            seats={"prediction_length": 12} if method == "tramoseats" else None,
        )
        sales = result.for_series("sales")
        print(f"\n{method.upper()}")
        print(result.to_compact_frame()["sales"].tail(3).round(2))
        print("Seasonally adjusted forecast:")
        print(sales.to_forecast_dict()["sa_f"])


if __name__ == "__main__":
    main()