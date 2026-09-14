# demetrapy

[![PyPI](https://img.shields.io/pypi/v/demetrapy)](https://pypi.org/project/demetrapy/)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml/badge.svg)](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml)

`demetrapy` exposes JDemetra+ X13 and TRAMO/SEATS through Python, pandas, a
command-line interface, and a Streamlit dashboard. It supports monthly through
yearly data, calendars, regressors, outliers, ARIMA models, and forecasts.

## Installation

`demetrapy` requires Python 3.9 or later and Java 8 or later.

```bash
python -m pip install demetrapy
```

For development from a clone:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The first calculation downloads the pinned `demetra-tstoolkit` 2.2.6 JAR from
Maven Central and stores it in `~/.cache/demetrapy`. Set `DEMETRAPY_JAR` to the
path of a local copy when automatic download is not suitable. The
[Windows guide](docs/WINDOWS_USAGE.md) covers Command Prompt and offline setup.

## Python interface

For a pandas object with a regular `DatetimeIndex`, `adjust_dataframe()`
infers the observation frequency and adjusts each column separately:

```python
import pandas as pd

from demetrapy import adjust_dataframe

data = pd.DataFrame(
	{"production": observations},
	index=pd.date_range("2015-01-01", periods=len(observations), freq="MS"),
)

result = adjust_dataframe(data, method="x13", spec="RSA4")
adjusted = result.seasonally_adjusted["production"]
```

The lower-level `adjust()` function accepts one regular sequence and an
explicit starting period:

```python
from demetrapy import adjust

result = adjust(
    values,
    frequency="Quarterly",
    start_year=2005,
    start_period=1,
    method="tramoseats",
    spec="RSA4",
)
adjusted = result.seasonally_adjusted.values
```

Both functions always return a stable result object. Their `components`
attribute exposes six named series used in routine work:

| Attribute | Compact alias | Series |
| --- | --- | --- |
| `observed` | `y` | observed series |
| `calendar_adjusted` | `ycal` | calendar-adjusted series |
| `seasonally_adjusted` | `sa` | seasonally adjusted series |
| `trend` | `t` | trend-cycle |
| `seasonal` | `s` | seasonal component |
| `irregular` | `i` | irregular component |

Use `to_compact_dict()` or `to_compact_frame()` when the short aliases are
needed. Forecasts preserve their own future domain under `result.forecasts`;
`to_forecast_dict()` provides `y_f`, `ycal_f`, `sa_f`, `t_f`, `s_f`, and
`i_f` when a forecast horizon is active:

```python
seasonal_forecast = result.forecasts.seasonal
forecast_values = result.to_forecast_dict()
```

Set `detailed=True` to additionally populate the full JDemetra+ result
dictionary, diagnostics, processing messages, backcasts, and fitted ARIMA
model:

```python
detailed = adjust(
    values,
    frequency="Monthly",
    start_year=2015,
    forecast_horizon=12,
    detailed=True,
)

print(detailed.arima_model.notation)
forecast = detailed.series["final.sa_f"]
```

## Command line

The command-line interface reads a regular CSV file with date and value
columns:

```csv
date,value
2019-01-01,101.2
2019-02-01,103.8
```

The default calculation is monthly X13 with the `RSA4` preset:

```bash
demetrapy input.csv --output adjusted.csv
```

A JSON file records a fuller specification:

```bash
demetrapy \
  --data input.csv \
	--config examples/configs/tramoseats_full.json \
  --output adjusted.csv
```

The output contains `y`, `ycal`, `sa`, `t`, `s`, and `i`. See the
[usage guide](docs/USAGE.md) for all options.

## Specifications and regressors

The package constructs an isolated JDemetra+ processing context for each
calculation. Preset defaults remain those of JDemetra+ unless an option is
overridden explicitly.

| Area | Available controls |
| --- | --- |
| Methods | X13 and TRAMO/SEATS presets |
| RegARIMA | transformation, explicit ARIMA, automatic model selection, estimation controls |
| Calendar | built-in trading days, working days, leap year, Easter, and UserDefined variables |
| Regression | user variables, fixed coefficients, interventions, and ramps |
| Outliers | prespecified and automatic detection |
| Decomposition | X11 filters and limits; SEATS approximation and boundary controls |
| Output | forecasts, backcasts, benchmarking, diagnostics, and processing messages |

UserDefined calendar variables use a separate pool; each target selects the
columns used by its equation.

See the [configuration reference](docs/CONFIGURATION.md) for supported values.

## Inspection

A static summary plot can be produced from the command line:

```bash
demetrapy --data input.csv --plot-output adjustment.png
```

The local dashboard is included in the standard installation:

```bash
demetrapy-dashboard
```

It accepts CSV and JSON files, includes built-in sample datasets, and provides
interactive results, diagnostics, model details, and downloads.

## Examples

See the [example guide](examples/README.md), or run every example:

```bash
python examples/run_all.py
```

## Reproducibility and compatibility

See [compatibility](docs/COMPATIBILITY.md) for supported Python, Java, and
JDemetra+ versions. CI tests both engines on Linux, Windows, and macOS.

```bash
python -m unittest discover -s tests
```

`demetrapy` is an independent interface to JDemetra+ and is not an official
publication of the JDemetra+ project.
