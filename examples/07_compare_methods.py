"""Compare X13 and TRAMO/SEATS components on the same monthly series."""

from pathlib import Path

from demetrapy import (
    TramoSeatsConfig,
    X13Config,
    compare_adjustments,
    load_monthly_retail,
    plot_comparison,
)


def main() -> None:
    data = load_monthly_retail()[["sales"]]
    comparison = compare_adjustments(
        data,
        candidates={
            "x13-rsa4": X13Config(spec="RSA4"),
            "tramoseats-rsa4": TramoSeatsConfig(spec="RSA4"),
        },
    )

    output_path = Path("method_comparison.csv")
    comparison.components.to_csv(output_path)
    plot_path = Path("method_comparison.png")
    figure = plot_comparison(comparison, "sales")
    figure.savefig(plot_path, dpi=150)
    print(comparison.metrics.round(6).to_string(index=False))
    print("\nSeasonally adjusted values:")
    print(comparison.for_series("sales").tail().round(3))
    print(f"\nSaved aligned results to {output_path.resolve()}")
    print(f"Saved comparison plot to {plot_path.resolve()}")


if __name__ == "__main__":
    main()