"""Adjust synthetic tourism using shared calendar variables."""

from demetrapy import adjust_dataframe, load_tourism_with_calendars


def main() -> None:
    dataset = load_tourism_with_calendars()
    result = adjust_dataframe(
        dataset.observations,
        calendar_pool=dataset.calendar_pool,
        user_defined_calendars=dataset.selections,
        method="tramoseats",
        spec="RSA4",
        seats={"prediction_length": 12},
    )

    print("Calendar selections:")
    for target, variables in dataset.selections.items():
        print(f"  {target}: {variables}")
    print("\nCalendar-adjusted tourism:")
    print(result.calendar_adjusted.tail(6).round(2))
    print("\nSeasonally adjusted tourism:")
    print(result.seasonally_adjusted.tail(6).round(2))


if __name__ == "__main__":
    main()