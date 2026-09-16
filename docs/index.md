# demetrapy

Run JDemetra+ TRAMO/SEATS directly from Python. `demetrapy` brings
model-based seasonal adjustment into ordinary pandas workflows without a
desktop workspace or XML exchange.

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
model = result.for_series("power").arima_model
```

Work with all six JDemetra+ components as date-indexed DataFrames, assign
calendar variables by target, and inspect forecasts, diagnostics, processing
messages, and fitted ARIMA metadata using Python objects. X13/X11, sequences,
CSV automation, a CLI, and a dashboard are also available when needed.

```{toctree}
:maxdepth: 2
:caption: Guides

QUICKSTART
USAGE
CONFIGURATION
WINDOWS_USAGE
COMPATIBILITY
api
```

## Start exploring

- Follow the [quickstart](https://github.com/SermetPekin/demetrapy/blob/main/docs/QUICKSTART.md) for a complete TRAMO/SEATS run.
- Open the [copy, run, inspect notebook](https://github.com/SermetPekin/demetrapy/blob/main/examples/14_copy_run_inspect.ipynb).
- Browse the [example catalog](https://github.com/SermetPekin/demetrapy/tree/main/examples).