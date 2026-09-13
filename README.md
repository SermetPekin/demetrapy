# demetrapy

[![CI](https://github.com/SermetPekin/seasonal-pri/actions/workflows/ci.yml/badge.svg)](https://github.com/SermetPekin/seasonal-pri/actions/workflows/ci.yml)

A Python command-line interface for seasonal adjustment with
[JDemetra+ core](https://github.com/jdemetra/jdemetra-core). It calls the real
X13 and TRAMO/SEATS implementations through JPype and does not require Maven or
a Demetra+ desktop installation.

## Requirements

- Python 3.9 or newer
- Java 8 or newer

## Install

Windows users should follow the [Windows usage guide](WINDOWS_USAGE.md), which
also covers proxy-restricted and fully offline JAR installation.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The pinned `demetra-tstoolkit` 2.2.6 JAR is downloaded from Maven Central on
the first run and cached in `~/.cache/demetrapy`. Set `DEMETRAPY_JAR` to
use a local JAR instead.

## Use

Input is a regular monthly, quarterly, half-yearly, or yearly CSV series:

```csv
date,value
2019-01-01,101.2
2019-02-01,103.8
```

Run with defaults (`Monthly`, `RSA4`):

```bash
demetrapy input.csv --output adjusted.csv
```

The equivalent fully named form is:

```bash
demetrapy --data input.csv --config examples/config.json --output adjusted.csv
```

Or provide a JSON configuration. The full example includes TRAMO/SEATS,
calendar effects, user regressors, outliers, interventions, and ramps:

```bash
demetrapy input.csv --config examples/config.json --output adjusted.csv
demetrapy input.csv --config examples/full_config.json --output adjusted.csv
```

See the [usage guide](USAGE.md) for the complete input, configuration, output,
and Python API reference, or the [Windows usage guide](WINDOWS_USAGE.md) for
Command Prompt instructions.

The supported runtime matrix and result stability policy are documented in
[COMPATIBILITY.md](COMPATIBILITY.md).
See [CONFIGURATION.md](CONFIGURATION.md) for processing order, compatible
option groups, defaults, ARIMA controls, calendars, X11, SEATS, and detailed
result semantics.

The result contains the original (`y`), seasonally adjusted (`sa`), trend
(`t`), seasonal (`s`), and irregular (`i`) series.

Configuration supports X13 and TRAMO/SEATS presets, preprocessing and
decomposition overrides, built-in and custom calendars, CSV-backed user
variables, prespecified and automatically detected outliers, interventions,
ramps, and fixed coefficients.

The same engine is available from Python:

```python
from demetrapy import adjust

result = adjust(values, frequency="Monthly", start_year=2019, spec="RSA4")
seasonally_adjusted = result["sa"]
```

Opt into the complete JDemetra result dictionary, scalar diagnostics, and
processing messages with `detailed=True`. Returned time series retain their
own frequency and starting period, including forecasts and backcasts.
Detailed results also expose the fitted ARIMA orders and whether automatic
model selection was used through `result.arima_model`.
See [automatic_arima_example.py](examples/automatic_arima_example.py) and
[explicit_arima_example.py](examples/explicit_arima_example.py) for runnable
examples with both processing engines.
The [full TRAMO/SEATS UserDefined calendar example](examples/full_tramoseats_user_calendar_example.py)
combines a separate calendar pool, explicit seasonal ARIMA model, all supported
TRAMO estimation controls, outlier detection, forecasts, and SEATS options.
The [quarterly example](examples/quarterly_example.py) demonstrates frequency
inference and compares X13 with TRAMO/SEATS using a seasonal period of four.

```python
detailed = adjust(
	values,
	frequency="Monthly",
	start_year=2019,
	forecast_horizon=12,
	detailed=True,
)
forecast = detailed.series["final.sa_f"]
```

See [examples/dataframe_user_variables_example.py](examples/dataframe_user_variables_example.py)
for a pandas example that keeps observations and a broad user-defined calendar
pool in separate DataFrames. `adjust_dataframe()` infers their frequency and
domains, validates coverage, and lets each target select different calendar
columns using the same semantics as GUI `Trading Days > UserDefined`.
The [retail operations case study](examples/RETAIL_CASE_STUDY.md) turns that
example into a reproducible multi-target adjustment and forecasting workflow.

To run X13 and TRAMO/SEATS against the same deterministic series, compare every
compact component, and write aligned results to `method_comparison.csv`:

```bash
python examples/compare_methods.py
```

## Plots and Dashboard

Plotting support is included in the standard installation:

```bash
demetrapy --data input.csv --plot-output adjustment.png
```

For an interactive local interface with CSV uploads, multi-series controls,
calendar mappings, Plotly charts, diagnostics, messages, and downloads:

```bash
demetrapy-dashboard
```

## Test

```bash
python -m unittest discover -s tests
```

CI runs the complete suite on Linux, Windows, and macOS with representative
Python 3.9-3.13 and Java 11/17 combinations.
