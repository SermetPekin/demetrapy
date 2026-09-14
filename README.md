# demetrapy

[![CI](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml/badge.svg)](https://github.com/SermetPekin/demetrapy/actions/workflows/ci.yml)

`demetrapy` is a Python toolkit for the seasonal-adjustment procedures in
[JDemetra+](https://github.com/jdemetra/jdemetra-core). It provides a Python
API for individual and pandas-based workflows, a command-line interface, and
an interactive dashboard. Calculations use the JDemetra+ X13 and TRAMO/SEATS
implementations through JPype; neither procedure is reimplemented in Python.

The package is intended for empirical work in which adjustment specifications
must be recorded, repeated, and applied to several series. It accepts regular
monthly, quarterly, half-yearly, and yearly observations. Calendar effects,
intervention variables, outliers, ARIMA specifications, forecasts, and the
principal decomposition options can be set in code or in a JSON file.

Seasonal adjustment is an inferential procedure, not merely a filter applied
to a column of numbers. Results depend on the transformation, regression
effects, ARIMA model, decomposition method, and span of the sample. Published
series should therefore be accompanied by their specification and revision
policy. `demetrapy` exposes JDemetra+ diagnostics and processing messages for
this purpose, but it does not decide whether a specification is economically
appropriate.

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
[Windows guide](https://github.com/SermetPekin/demetrapy/blob/main/WINDOWS_USAGE.md)
covers Command Prompt, proxy-restricted, and
offline installations.

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
adjusted = result[("production", "sa")]
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
adjusted = result["sa"]
```

By default, both functions return the five compact components used in routine
work:

| Name | Series |
| --- | --- |
| `y` | observed series |
| `sa` | seasonally adjusted series |
| `t` | trend-cycle |
| `s` | seasonal component |
| `i` | irregular component |

Set `detailed=True` when the calculation must retain the full JDemetra+ result
dictionary, diagnostics, processing messages, forecasts, backcasts, and fitted
ARIMA model:

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
  --config examples/full_config.json \
  --output adjusted.csv
```

The output contains `y`, `sa`, `t`, `s`, and `i`, aligned with the input dates.
See the [usage guide](https://github.com/SermetPekin/demetrapy/blob/main/USAGE.md)
for the complete command-line and Python API.

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

UserDefined trading-day variables follow the distinction made in the
JDemetra+ graphical interface: a calendar pool may contain several registered
series while each target selects only the variables relevant to its own
equation. The target observations and calendar pool may be supplied as
separate DataFrames, provided their frequencies agree and the calendar domain
covers the estimation sample.

The [configuration reference](https://github.com/SermetPekin/demetrapy/blob/main/CONFIGURATION.md)
documents processing order, valid option groups, preset behavior, and result
semantics.

## Inspection

A static summary plot can be produced from the command line:

```bash
demetrapy --data input.csv --plot-output adjustment.png
```

The local dashboard is included in the standard installation:

```bash
demetrapy-dashboard
```

It accepts observation, configuration, and calendar-pool files and reports
the adjusted series together with diagnostics, model information, processing
messages, and downloadable results. The dashboard is a convenient inspection
tool; it uses the same calculation path as the Python and command-line
interfaces.

## Examples

| Example | Subject |
| --- | --- |
| [automatic_arima_example.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/automatic_arima_example.py) | automatic model selection with both methods |
| [explicit_arima_example.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/explicit_arima_example.py) | prespecified seasonal ARIMA models |
| [quarterly_example.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/quarterly_example.py) | quarterly frequency inference and period-four seasonality |
| [compare_methods.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/compare_methods.py) | component-wise X13 and TRAMO/SEATS comparison |
| [dataframe_user_variables_example.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/dataframe_user_variables_example.py) | multiple targets and a separate calendar pool |
| [full_tramoseats_user_calendar_example.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/full_tramoseats_user_calendar_example.py) | detailed TRAMO/SEATS specification with UserDefined trading days |
| [RETAIL_CASE_STUDY.md](https://github.com/SermetPekin/demetrapy/blob/main/examples/RETAIL_CASE_STUDY.md) | reproducible multi-series case study |
| [dashboard files](https://github.com/SermetPekin/demetrapy/blob/main/examples/dashboard/README.md) | ready-to-upload dashboard inputs |

## Reproducibility and compatibility

The compact result schema is versioned, and the supported Python, Java, and
JDemetra+ combinations are stated in the
[compatibility policy](https://github.com/SermetPekin/demetrapy/blob/main/COMPATIBILITY.md).
Tests use both processing engines and include synthetic seasonal and calendar
effects with known structure. CI runs on Linux, Windows, and macOS.

```bash
python -m unittest discover -s tests
```

`demetrapy` is an independent interface to JDemetra+ and is not an official
publication of the JDemetra+ project.
