import inspect
import unittest

from demetrapy.config import TramoSeatsConfig, X13Config, normalize_config


class MethodConfigTest(unittest.TestCase):
    def test_x13_config_normalizes_to_existing_contract(self) -> None:
        config = X13Config(spec="RSA5", seasonal_filter="S3X5")

        normalized = normalize_config(config)

        self.assertEqual(normalized.method, "x13")
        self.assertEqual(normalized.spec, "RSA5")
        self.assertEqual(normalized.seasonal_filter, "S3X5")
        self.assertNotIn("seats", inspect.signature(X13Config).parameters)

    def test_tramoseats_config_normalizes_to_existing_contract(self) -> None:
        config = TramoSeatsConfig(
            spec="RSAfull",
            seats={"prediction_length": 12},
        )

        normalized = normalize_config(config)

        self.assertEqual(normalized.method, "tramoseats")
        self.assertEqual(normalized.spec, "RSAfull")
        self.assertEqual(normalized.seats, {"prediction_length": 12})
        self.assertNotIn("seasonal_filter", inspect.signature(TramoSeatsConfig).parameters)

    def test_method_specific_config_validates_on_conversion(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported x13 specification"):
            X13Config(spec="RSAfull").to_adjustment_config()


if __name__ == "__main__":
    unittest.main()