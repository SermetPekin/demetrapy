# demetrapy

[![PyPI](https://img.shields.io/pypi/v/demetrapy)](https://pypi.org/project/demetrapy/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml/badge.svg)](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml)

Seasonal adjustment with JDemetra+ from Python. `demetrapy` runs X13 and
TRAMO/SEATS on sequences, pandas objects, or CSV files and returns components,
forecasts, diagnostics, and fitted model details in Python-native structures.

## Why demetrapy

- Adjust every numeric column in a DataFrame with one call.
- Keep real date indexes on historical and forecast output.
- Assign different user-defined calendar variables to each target series.
- Use typed Python configuration, direct options, or the same JSON as the CLI.
- Inspect the full JDemetra+ result without working with workspace XML.

## Install

Python 3.11+ and Java 9+ are required.

```bash
python -m pip install demetrapy
demetrapy check
```

The first adjustment downloads the pinned JDemetra+ 2.2.6 core JAR to
`~/.cache/demetrapy`. Set `DEMETRAPY_JAR` to use a local copy instead.

## Adjust a DataFrame

`adjust_dataframe()` infers monthly, quarterly, half-yearly, or yearly
frequency from a regular `DatetimeIndex`. Each input column is adjusted
independently.

```python
from demetrapy import TramoSeatsConfig, adjust_dataframe, load_monthly_emissions

data = load_monthly_emissions()  # 120 dates x 10 sector columns
config = TramoSeatsConfig(
    spec="RSAfull",
    preprocessing={"automodel": {"enabled": True}},
    seats={"prediction_length": 12},
)

result = adjust_dataframe(data, config=config)

sa = result.seasonally_adjusted             # 120 x 10
calendar_adjusted = result.calendar_adjusted
forecasts = result.to_forecast_frame()      # future dates
combined = result.to_combined_frame()       # history + forecasts
```

Every result contains six components:

| Component | Alias | Meaning |
| --- | --- | --- |
| `observed` | `y` | input series |
| `calendar_adjusted` | `ycal` | calendar effects removed |
| `seasonally_adjusted` | `sa` | seasonal effects removed |
| `trend` | `t` | trend-cycle |
| `seasonal` | `s` | seasonal component |
| `irregular` | `i` | irregular component |

Use `to_compact_frame()` for aliases and `for_series(name)` for one column's
model, diagnostics, messages, and low-level outputs.

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

See the complete 10-series example with full TRAMO/SEATS parameters:
[examples/13_full_config_calendar_pool.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/13_full_config_calendar_pool.py).

## Other Inputs

A sequence has no dates, so its frequency and start must be explicit:

```python
from demetrapy import adjust

result = adjust(
    values,
    frequency="Quarterly",
    start_year=2010,
    start_period=1,
    method="x13",
    spec="RSA4",
)
```

CSV files use the same engine:

```python
from demetrapy import adjust_csv

result = adjust_csv("input.csv", config="x13.json", output="adjusted.csv")
```

## Command Line

```bash
demetrapy input.csv --output adjusted.csv
demetrapy init-config --method tramoseats --output config.json
demetrapy validate config.json --data input.csv
demetrapy input.csv --config config.json --output adjusted.csv --audit audit/
```

The dashboard provides interactive charts, diagnostics, model details, and
downloads:

```bash
demetrapy-dashboard
```

## Documentation

- [Quickstart](https://github.com/SermetPekin/demetrapy/blob/main/docs/QUICKSTART.md)
- [Usage](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md)
- [Configuration reference](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md)
- [Examples](https://github.com/SermetPekin/demetrapy/blob/main/examples/README.md)
- [Windows and offline setup](https://github.com/SermetPekin/demetrapy/blob/main/docs/WINDOWS_USAGE.md)
- [Compatibility](https://github.com/SermetPekin/demetrapy/blob/main/docs/COMPATIBILITY.md)

`demetrapy` is an independent interface to JDemetra+ and is not an official
publication of the JDemetra+ project.
