# demetrapy

[![PyPI](https://img.shields.io/pypi/v/demetrapy)](https://pypi.org/project/demetrapy/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml/badge.svg)](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/demetrapy/badge/?version=latest)](https://demetrapy.readthedocs.io/en/latest/?badge=latest)

Run JDemetra+ TRAMO/SEATS directly from Python. `demetrapy` turns pandas data
into seasonally adjusted series, forecasts, diagnostics, and fitted-model
metadata without a desktop workspace or XML workflow.

## Why demetrapy

- Run TRAMO/SEATS across every numeric DataFrame column with one call.
- Receive components and forecasts as date-indexed pandas DataFrames.
- Inspect diagnostics, processing messages, and fitted ARIMA models in Python.
- Assign different user-defined calendar variables to each target series.
- Reproduce reviewed workflows with typed configuration or JSON.

## Install

Python 3.11+ and Java 9+ are required.

```bash
python -m pip install demetrapy
demetrapy check
```

To run the example notebook, install the optional Jupyter dependencies:

```bash
python -m pip install "demetrapy[notebook]"
```

The first adjustment downloads the pinned JDemetra+ 2.2.6 core JAR to
`~/.cache/demetrapy`. Set `DEMETRAPY_JAR` to use a local copy instead.

## TRAMO/SEATS in Python

This complete example adjusts ten synthetic monthly emissions series, requests
a one-year forecast, and keeps detailed model results:

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

adjusted = result.seasonally_adjusted  # date index x 10 series
forecasts = result.to_forecast_frame() # future component DataFrames
power_model = result.for_series("power").arima_model

print(adjusted.tail())
print(power_model.notation if power_model else "Model metadata unavailable")
```

`adjust_dataframe()` infers monthly, quarterly, half-yearly, or yearly
frequency from a regular `DatetimeIndex`. Each column is processed
independently and every result contains six components:

| Component | Alias | Meaning |
| --- | --- | --- |
| `observed` | `y` | input series |
| `calendar_adjusted` | `ycal` | calendar effects removed |
| `seasonally_adjusted` | `sa` | seasonal effects removed |
| `trend` | `t` | trend-cycle |
| `seasonal` | `s` | seasonal component |
| `irregular` | `i` | irregular component |

Use `to_forecast_frame()` for future values, `to_combined_frame()` for one
history-plus-forecast table, and `for_series(name)` to inspect one fitted
model's diagnostics and messages.

## Different Calendars for Different Series

Calendar variables live in a separate DataFrame. A mapping selects which pool
columns enter each target's model. Extra pool columns are allowed.

```python
result = adjust_dataframe(
    observations,
    calendar_pool=calendar_variables,
    user_defined_calendars={
        "power": ["heating_days", "working_days"],
        "transport": ["working_days", "holiday_days", "mobility_index"],
    },
    config=config,
)
```

See the complete 10-series example with extended TRAMO/SEATS parameters:
[examples/13_full_config_calendar_pool.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/13_full_config_calendar_pool.py).

## More Workflows

TRAMO/SEATS is the primary workflow. The same API also supports single
sequences, X13/X11, CSV automation, a command-line interface, and a Streamlit
dashboard.

A sequence has no dates, so its frequency and start must be explicit:

```python
from demetrapy import adjust

result = adjust(
    values,
    frequency="Quarterly",
    start_year=2010,
    start_period=1,
    method="tramoseats",
    spec="RSAfull",
)
```

For batch integration, CSV files use the same processing engine:

```python
from demetrapy import adjust_csv

result = adjust_csv("input.csv", config="tramoseats.json", output="adjusted.csv")
```

X13/X11 remains available through `X13Config` or `method="x13"` when that is
the required specification.

### Command Line

```bash
demetrapy input.csv --output adjusted.csv
demetrapy init-config --method tramoseats --output config.json
demetrapy validate config.json --data input.csv
demetrapy input.csv --config config.json --output adjusted.csv --audit audit/
```

### Dashboard

The included Streamlit dashboard runs the same X13 and TRAMO/SEATS engine as
the Python API. Start with a built-in monthly, quarterly, or calendar-adjusted
dataset, or upload your own files.

```bash
demetrapy-dashboard
```
<img width="850" alt="image" src="https://github.com/user-attachments/assets/e524932e-f7dd-49f0-b871-5096adf95c69" />

From the dashboard you can:

- adjust one or several target columns;
- upload JSON configuration and a separate calendar-variable pool;
- map different calendar variables to each target;
- inspect interactive components and forecasts;
- review diagnostics, processing messages, and fitted models;
- download result tables.

Ready-to-upload files are available in the
[dashboard example directory](https://github.com/SermetPekin/demetrapy/blob/main/examples/dashboard/README.md).

## Documentation

- [Read the documentation](https://demetrapy.readthedocs.io/en/latest/)
- [Quickstart](https://github.com/SermetPekin/demetrapy/blob/main/docs/QUICKSTART.md)
- [Usage](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md)
- [Configuration reference](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md)
- [Examples](https://github.com/SermetPekin/demetrapy/blob/main/examples/README.md)
- [Copy, run, inspect notebook](https://github.com/SermetPekin/demetrapy/blob/main/examples/14_copy_run_inspect.ipynb)
- [Windows and offline setup](https://github.com/SermetPekin/demetrapy/blob/main/docs/WINDOWS_USAGE.md)
- [Compatibility](https://github.com/SermetPekin/demetrapy/blob/main/docs/COMPATIBILITY.md)

`demetrapy` is an independent interface to JDemetra+ and is not an official
publication of the JDemetra+ project.
