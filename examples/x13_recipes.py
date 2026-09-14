"""Compare copy-ready X13 configurations on one monthly dataset."""

from demetrapy import adjust_dataframe, load_monthly_retail


X13_CONFIGURATIONS = {
    "default RSA4": {
        "method": "x13",
        "spec": "RSA4",
        "forecast_horizon": 12,
    },
    "multiplicative X11": {
        "method": "x13",
        "spec": "RSA4",
        "decomposition_mode": "Multiplicative",
        "seasonal_filter": "S3X5",
        "henderson_filter_length": 13,
        "lower_sigma": 1.5,
        "upper_sigma": 2.5,
        "forecast_horizon": 12,
    },
    "working days and outliers": {
        "method": "x13",
        "spec": "RSA4",
        "calendar": {
            "type": "WorkingDays",
            "length_of_period": "LeapYear",
            "test": "Add",
        },
        "outlier_detection": {
            "types": ["AO", "LS", "TC"],
            "critical_value": 3.5,
        },
        "forecast_horizon": 12,
    },
}


data = load_monthly_retail()[["sales"]]

for name, configuration in X13_CONFIGURATIONS.items():
    result = adjust_dataframe(data, **configuration)
    sales = result.for_series("sales")
    print(f"\n{name}")
    print("Last adjusted values:", result.seasonally_adjusted["sales"].tail(3).round(2).tolist())
    print("Forecast:", sales.to_forecast_dict()["sa_f"][:3])