# Quickstart

## Install

Install Python 3.11+, Java 9+, and the package:

```bash
python -m pip install demetrapy
demetrapy check
```

The first adjustment downloads JDemetra+ 2.2.6 to
`~/.cache/demetrapy`. The readiness check itself is read-only.

## Run TRAMO/SEATS

The built-in synthetic emissions dataset has ten monthly columns and a date
index. One call runs TRAMO/SEATS independently for every series:

```python
from demetrapy import TramoSeatsConfig, adjust_dataframe, load_monthly_emissions

data = load_monthly_emissions()
result = adjust_dataframe(
    data,
    config=TramoSeatsConfig(
        spec="RSAfull",
        preprocessing={"automodel": {"enabled": True}},
        seats={"prediction_length": 12},
    ),
    detailed=True,
)

adjusted = result.seasonally_adjusted
forecasts = result.to_forecast_frame()

print(adjusted.tail())
print(forecasts.xs("seasonally_adjusted", axis="columns", level="component"))
```

The component attributes are date-indexed DataFrames with the same ten columns.
Forecasts begin after the last observation.

## Inspect the Fitted Model

Detailed mode preserves the fitted result for each DataFrame column:

```python
power = result.for_series("power")

print(power.specification)
print(power.arima_model.notation if power.arima_model else "unavailable")
print(power.diagnostics)
print(power.messages)
```

This keeps the adjustment, decomposition, diagnostics, and fitted-model
metadata in the same Python workflow.

## Use Your DataFrame

Replace the built-in data with a regular, increasing `DatetimeIndex`:

```python
import pandas as pd

observations = pd.DataFrame(
    {"sales": values},
    index=pd.date_range("2019-01-01", periods=len(values), freq="MS"),
)
result = adjust_dataframe(observations, config=TramoSeatsConfig(spec="RSAfull"))
```

Monthly, quarterly, half-yearly, and yearly frequencies are supported.

## Other Interfaces

X13/X11 is available through `X13Config`. For automated file processing, the
same package also provides a CLI and CSV API:

```bash
demetrapy init-config --method tramoseats --output config.json
demetrapy validate config.json --data input.csv
demetrapy input.csv --config config.json --output adjusted.csv
```

## Next

- Use [USAGE.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md) for DataFrame results, calendars, plotting, and secondary interfaces.
- Use [CONFIGURATION.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md) for model options.
- Browse the [examples](https://github.com/SermetPekin/demetrapy/blob/main/examples/README.md) for complete programs.
