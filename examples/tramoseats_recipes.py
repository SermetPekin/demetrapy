"""Compare copy-ready TRAMO/SEATS configurations on one monthly dataset."""

from demetrapy import adjust_dataframe, load_monthly_retail


TRAMOSEATS_CONFIGURATIONS = {
    "automatic RSA4": {
        "method": "tramoseats",
        "spec": "RSA4",
        "preprocessing": {"automodel": {"enabled": True}},
        "seats": {"prediction_length": 12},
    },
    "explicit airline model": {
        "method": "tramoseats",
        "spec": "RSA4",
        "preprocessing": {
            "arima": {
                "p": 0,
                "d": 1,
                "q": 1,
                "bp": 0,
                "bd": 1,
                "bq": 1,
                "mean": False,
            }
        },
        "seats": {"prediction_length": 12},
    },
    "trading days and robust outliers": {
        "method": "tramoseats",
        "spec": "RSAfull",
        "calendar": {
            "type": "TradingDays",
            "leap_year": True,
            "test": "Separate_T",
        },
        "outlier_detection": {
            "types": ["AO", "LS", "TC"],
            "critical_value": 3.5,
            "tc_rate": 0.7,
        },
        "seats": {
            "approximation_mode": "Legacy",
            "estimation_method": "Burman",
            "prediction_length": 12,
        },
    },
}


def main() -> None:
    data = load_monthly_retail()[["sales"]]

    for name, configuration in TRAMOSEATS_CONFIGURATIONS.items():
        result = adjust_dataframe(data, detailed=True, **configuration)
        sales = result.for_series("sales")
        model = sales.arima_model
        adjusted = result.seasonally_adjusted["sales"].tail(3).round(2).tolist()
        print(f"\n{name}")
        print("Model:", model.notation if model else "unavailable")
        print("Last adjusted values:", adjusted)
        print("Forecast:", sales.to_forecast_dict()["sa_f"][:3])


if __name__ == "__main__":
    main()