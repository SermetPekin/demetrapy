"""Adjust two series with different selections from one calendar pool."""

from demetrapy import adjust_dataframe, load_retail_with_calendars


dataset = load_retail_with_calendars()
result = adjust_dataframe(
    dataset.observations,
    calendar_pool=dataset.calendar_pool,
    user_defined_calendars=dataset.selections,
    method="tramoseats",
    spec="RSA4",
    seats={"prediction_length": 12},
)

print("Calendar selections:", dataset.selections)
print("\nSeasonally adjusted values:")
print(result.seasonally_adjusted.tail(6).round(2))
print("\nSales forecast:")
print(result.for_series("sales").to_forecast_dict()["sa_f"])