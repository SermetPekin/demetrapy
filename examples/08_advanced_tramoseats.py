"""Run an advanced TRAMO/SEATS model with a UserDefined calendar."""

import argparse

from demetrapy import adjust_dataframe, load_retail_with_calendars


EXPLICIT_ARIMA = {
    "p": 0,
    "d": 1,
    "q": 1,
    "bp": 0,
    "bd": 1,
    "bq": 1,
    "mean": False,
}

TRAMO_AUTOMODEL = {
    "enabled": True,
    "accept_default": False,
    "pcr": 0.95,
    "ub1": 0.97,
    "ub2": 0.91,
    "cancel": 0.05,
    "tsig": 1.0,
    "pc": 0.12,
    "ami_compare": False,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-model", action="store_true")
    arguments = parser.parse_args()
    dataset = load_retail_with_calendars()

    result = adjust_dataframe(
        dataset.observations[["sales"]],
        calendar_pool=dataset.calendar_pool,
        user_defined_calendars={"sales": dataset.selections["sales"]},
        method="tramoseats",
        spec="RSAfull",
        preprocessing={
            "transform": {
                "function": "None",
                "fct": 0.95,
                "units": False,
                "preliminary_check": True,
            },
            **(
                {"automodel": TRAMO_AUTOMODEL}
                if arguments.auto_model
                else {"arima": EXPLICIT_ARIMA}
            ),
            "estimate": {
                "tolerance": 1e-7,
                "exact_ml": True,
                "unit_root_limit": 0.96,
            },
        },
        outlier_detection={
            "types": ["AO", "LS", "TC"],
            "critical_value": 3.5,
            "tc_rate": 0.7,
            "exact_ml": True,
        },
        seats={
            "approximation_mode": "Legacy",
            "estimation_method": "Burman",
            "xl_boundary": 0.95,
            "seasonal_tolerance": 2.0,
            "trend_boundary": 0.5,
            "seasonal_boundary": 0.8,
            "seasonal_boundary_at_pi": 0.8,
            "prediction_length": 12,
        },
        detailed=True,
    )

    sales = result.for_series("sales")
    model = sales.arima_model
    print("Calendar:", dataset.selections["sales"])
    print("Model:", model.notation if model else "unavailable")
    print("Automatic:", model.automatic if model else "unavailable")
    print("Diagnostics:", len(sales.diagnostics))
    print("Forecast:", sales.to_forecast_dict()["sa_f"])


if __name__ == "__main__":
    main()