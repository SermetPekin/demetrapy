"""Apply both engines to the same quarterly production dataset."""

import pandas as pd

from demetrapy import adjust_dataframe, load_quarterly_production


def main() -> None:
    data = load_quarterly_production()
    adjusted = {}

    for method in ("x13", "tramoseats"):
        result = adjust_dataframe(data, method=method, spec="RSA4")
        adjusted[method] = result.seasonally_adjusted["production"]

    comparison = pd.DataFrame(adjusted)
    comparison["difference"] = comparison["x13"] - comparison["tramoseats"]
    print(comparison.tail(8).round(3))


if __name__ == "__main__":
    main()