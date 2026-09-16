"""Compare X13 and TRAMO/SEATS components on the same monthly series."""

import math
from pathlib import Path



import pandas as pd

from demetrapy import COMPACT_COMPONENTS, adjust_dataframe, load_monthly_retail


def comparison_metrics(left: pd.Series, right: pd.Series) -> dict[str, float]:
    difference = left - right
    return {
        "rmse": float(math.sqrt((difference**2).mean())),
        "max_absolute_difference": float(difference.abs().max()),
        "correlation": float(left.corr(right)),
    }


def main() -> None:
    data = load_monthly_retail()[["sales"]]
    results = {
        method: adjust_dataframe(data, method=method, spec="RSA4")
        .to_compact_frame()["sales"]
        for method in ("x13", "tramoseats")
    }
    comparison = pd.concat(
        {
            "x13": results["x13"],
            "tramoseats": results["tramoseats"],
            "difference": results["x13"] - results["tramoseats"],
        },
        axis=1,
    )
    metrics = pd.DataFrame(
        {
            component: comparison_metrics(
                results["x13"][component], results["tramoseats"][component]
            )
            for component in COMPACT_COMPONENTS
        }
    ).T.rename_axis("component")

    output_path = Path("method_comparison.csv")
    comparison.to_csv(output_path)
    print(metrics.round(6))
    print(f"\nSaved aligned results to {output_path.resolve()}")


if __name__ == "__main__":
    main()