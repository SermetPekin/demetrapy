import unittest

import pandas as pd

from demetrapy.datasets import (
    CalendarDataset,
    load_emissions_with_calendars,
    load_monthly_emissions,
    load_monthly_retail,
    load_quarterly_production,
    load_retail_with_calendars,
)


class DatasetTest(unittest.TestCase):
    def test_monthly_retail_is_deterministic_and_returns_fresh_data(self) -> None:
        first = load_monthly_retail()
        second = load_monthly_retail()

        pd.testing.assert_frame_equal(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(first.shape, (120, 2))
        self.assertEqual(list(first.columns), ["sales", "orders"])
        self.assertEqual(first.index.freqstr, "MS")

    def test_monthly_emissions_has_ten_deterministic_variables(self) -> None:
        first = load_monthly_emissions()
        second = load_monthly_emissions()

        pd.testing.assert_frame_equal(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(first.shape, (120, 10))
        self.assertEqual(first.index.name, "date")
        self.assertEqual(first.index.freqstr, "MS")
        self.assertTrue((first > 0).all().all())

    def test_emissions_calendar_pool_supports_per_column_selections(self) -> None:
        dataset = load_emissions_with_calendars()

        self.assertEqual(dataset.observations.shape, (120, 10))
        self.assertEqual(dataset.calendar_pool.shape, (144, 8))
        self.assertEqual(set(dataset.selections), set(dataset.observations.columns))
        selected = {
            variable
            for variables in dataset.selections.values()
            for variable in variables
        }
        self.assertEqual(
            set(dataset.calendar_pool.columns) - selected,
            {"unused_policy_index", "unused_fuel_price"},
        )
        self.assertTrue(selected.issubset(dataset.calendar_pool.columns))
        self.assertLess(
            dataset.calendar_pool.index.min(),
            dataset.observations.index.min(),
        )
        self.assertGreater(
            dataset.calendar_pool.index.max(),
            dataset.observations.index.max(),
        )

    def test_calendar_pool_covers_observations_and_documents_selections(self) -> None:
        dataset = load_retail_with_calendars()

        self.assertIsInstance(dataset, CalendarDataset)
        self.assertLess(dataset.calendar_pool.index.min(), dataset.observations.index.min())
        self.assertGreater(dataset.calendar_pool.index.max(), dataset.observations.index.max())
        self.assertEqual(dataset.selections["sales"], ("retail_days",))
        self.assertEqual(
            dataset.selections["orders"],
            ("retail_days", "delivery_days"),
        )

    def test_quarterly_production_has_regular_quarterly_index(self) -> None:
        data = load_quarterly_production()

        self.assertEqual(data.shape, (80, 1))
        self.assertEqual(list(data.columns), ["production"])
        self.assertEqual(data.index.freqstr, "QS-JAN")


if __name__ == "__main__":
    unittest.main()