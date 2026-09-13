import math
import random
import unittest

from demetrapy import adjust


class SyntheticSeasonalityTest(unittest.TestCase):
    def test_engines_recover_known_additive_seasonality(self) -> None:
        random_source = random.Random(20260914)
        seasonal_pattern = (
            -8.0,
            -5.0,
            -2.0,
            1.0,
            4.0,
            7.0,
            9.0,
            6.0,
            2.0,
            -1.0,
            -4.0,
            -9.0,
        )
        observation_count = 240
        trend = [100.0 + 0.2 * index for index in range(observation_count)]
        irregular = [
            random_source.gauss(0.0, 1.25) for _ in range(observation_count)
        ]
        expected_adjusted = [
            trend[index] + irregular[index] for index in range(observation_count)
        ]
        observations = [
            expected_adjusted[index] + seasonal_pattern[index % 12]
            for index in range(observation_count)
        ]
        interior = range(36, observation_count - 36)

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                result = adjust(
                    observations,
                    start_year=2005,
                    method=method,
                    spec="RSA4",
                )
                adjusted_rmse = _rmse(
                    [result["sa"][index] for index in interior],
                    [expected_adjusted[index] for index in interior],
                )
                recovered_pattern = _monthly_means(
                    [
                        observations[index] - result["sa"][index]
                        for index in interior
                    ],
                    [index % 12 for index in interior],
                )

                self.assertLess(adjusted_rmse, 1.0)
                self.assertGreater(
                    _correlation(recovered_pattern, seasonal_pattern),
                    0.98,
                )

    def test_engines_remove_selected_user_defined_calendar_effect(self) -> None:
        random_source = random.Random(20260914)
        seasonal_pattern = (
            -6.0,
            -4.0,
            -1.0,
            2.0,
            5.0,
            8.0,
            7.0,
            4.0,
            1.0,
            -2.0,
            -5.0,
            -9.0,
        )
        observation_count = 240
        calendar_weights = [
            random_source.gauss(0.0, 1.0) for _ in range(observation_count)
        ]
        irregular = [
            random_source.gauss(0.0, 0.8) for _ in range(observation_count)
        ]
        expected_adjusted = [
            120.0 + 0.15 * index + irregular[index]
            for index in range(observation_count)
        ]
        observations = [
            expected_adjusted[index]
            + seasonal_pattern[index % 12]
            + 4.0 * calendar_weights[index]
            for index in range(observation_count)
        ]
        interior = range(36, observation_count - 36)

        for method in ("x13", "tramoseats"):
            with self.subTest(method=method):
                selected = adjust(
                    observations,
                    start_year=2005,
                    method=method,
                    spec="RSA4",
                    calendar_variables=[
                        {
                            "name": "synthetic_td",
                            "values": calendar_weights,
                            "start_year": 2005,
                        }
                    ],
                )
                unselected = adjust(
                    observations,
                    start_year=2005,
                    method=method,
                    spec="RSA4",
                    calendar_variables=[
                        {
                            "name": "synthetic_td",
                            "values": calendar_weights,
                            "start_year": 2005,
                            "selected": False,
                        }
                    ],
                )
                expected_interior = [expected_adjusted[index] for index in interior]
                selected_rmse = _rmse(
                    [selected["sa"][index] for index in interior],
                    expected_interior,
                )
                unselected_rmse = _rmse(
                    [unselected["sa"][index] for index in interior],
                    expected_interior,
                )

                self.assertLess(selected_rmse, 0.75)
                self.assertLess(selected_rmse, unselected_rmse * 0.2)


def _rmse(actual: list[float], expected: list[float]) -> float:
    return math.sqrt(
        sum((actual_value - expected_value) ** 2 for actual_value, expected_value in zip(actual, expected))
        / len(actual)
    )


def _monthly_means(values: list[float], months: list[int]) -> list[float]:
    means = []
    for month in range(12):
        monthly_values = [
            value for value, value_month in zip(values, months) if value_month == month
        ]
        means.append(sum(monthly_values) / len(monthly_values))
    overall_mean = sum(means) / len(means)
    return [value - overall_mean for value in means]


def _correlation(left: list[float], right: tuple[float, ...]) -> float:
    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right))
    denominator = math.sqrt(
        sum(value**2 for value in left) * sum(value**2 for value in right)
    )
    return numerator / denominator


if __name__ == "__main__":
    unittest.main()