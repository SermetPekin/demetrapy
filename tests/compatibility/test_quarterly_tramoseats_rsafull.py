from pathlib import Path

import pandas as pd

from demetrapy import TramoSeatsConfig, adjust_dataframe, load_quarterly_production


FIXTURE_DIRECTORY = (
    Path(__file__).parent / "fixtures" / "quarterly_tramoseats_rsafull"
)
HISTORICAL_COMPONENTS = ("y", "t", "sa", "s", "i", "ycal")
FORECAST_COMPONENTS = ("s_f", "sa_f", "ycal_f", "y_f")


def test_quarterly_rsafull_matches_jdemetra_reference() -> None:
    reference = pd.read_csv(
        FIXTURE_DIRECTORY / "demetra_expected.csv",
        parse_dates=["date"],
        index_col="date",
    )
    source = load_quarterly_production()

    result = adjust_dataframe(
        source,
        config=TramoSeatsConfig(spec="RSAfull"),
        detailed=True,
    )
    history = result.to_compact_frame()["production"]
    forecasts = result.to_forecast_frame(compact=True)["production"]

    expected_history = reference.loc[
        source.index, list(HISTORICAL_COMPONENTS)
    ].rename_axis(index="quarter", columns="component")
    expected_forecasts = reference.loc[
        forecasts.index, list(FORECAST_COMPONENTS)
    ].rename_axis(index="quarter", columns="component")

    pd.testing.assert_series_equal(
        source["production"],
        expected_history["y"].rename("production").rename_axis("quarter"),
        rtol=0,
        atol=1e-12,
        check_freq=False,
    )
    pd.testing.assert_frame_equal(
        history.loc[:, HISTORICAL_COMPONENTS],
        expected_history,
        check_exact=False,
        rtol=0,
        atol=1e-7,
        check_freq=False,
    )
    pd.testing.assert_frame_equal(
        forecasts.loc[:, FORECAST_COMPONENTS],
        expected_forecasts,
        check_exact=False,
        rtol=0,
        atol=1e-7,
        check_freq=False,
    )
    assert result.for_series("production").specification == "RSAfull"