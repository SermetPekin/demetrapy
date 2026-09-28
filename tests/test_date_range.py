import unittest
from typing import Any, cast

import pandas as pd

from demetrapy import DateRange, DateRangeMonth, DateRangeQuarter


class DateRangeTest(unittest.TestCase):
    def test_base_supports_monthly_and_quarterly_frequencies(self) -> None:
        self.assertEqual(DateRange(periods=3, freq="M").dates.freqstr, "MS")
        self.assertEqual(DateRange(periods=3, freq="Q").dates.freqstr, "QS-JAN")

    def test_month_range_uses_month_starts(self) -> None:
        date_range = DateRangeMonth("2024-02-15", 3)

        expected = pd.date_range("2024-03-01", periods=3, freq="MS")
        pd.testing.assert_index_equal(date_range.dates, expected)
        self.assertEqual(date_range.freq, "Monthly")

    def test_quarter_range_uses_quarter_starts(self) -> None:
        date_range = DateRangeQuarter("2024-02-15", 3)

        expected = pd.date_range("2024-02-15", periods=3, freq="QS")
        pd.testing.assert_index_equal(date_range.dates, expected)
        self.assertEqual(date_range.freq, "Quarterly")

    def test_specialized_ranges_reject_other_frequencies(self) -> None:
        with self.assertRaisesRegex(ValueError, "DateRangeMonth"):
            DateRangeMonth(freq=cast(Any, "Quarterly"))
        with self.assertRaisesRegex(ValueError, "DateRangeQuarter"):
            DateRangeQuarter(freq=cast(Any, "Monthly"))


if __name__ == "__main__":
    unittest.main()