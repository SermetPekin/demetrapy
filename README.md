# seasonal-pri

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
the first run and cached in `~/.cache/seasonal-pri`. Set `SEASONAL_PRI_JAR` to
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
seasonal-pri input.csv --output adjusted.csv
```

The equivalent fully named form is:

```bash
seasonal-pri --data input.csv --config examples/config.json --output adjusted.csv
```

Or provide a JSON configuration. The full example includes TRAMO/SEATS,
calendar effects, user regressors, outliers, interventions, and ramps:

```bash
seasonal-pri input.csv --config examples/config.json --output adjusted.csv
seasonal-pri input.csv --config examples/full_config.json --output adjusted.csv
```

See the [usage guide](USAGE.md) for the complete input, configuration, output,
and Python API reference, or the [Windows usage guide](WINDOWS_USAGE.md) for
Command Prompt instructions.

The supported runtime matrix and result stability policy are documented in
[COMPATIBILITY.md](COMPATIBILITY.md).

The result contains the original (`y`), seasonally adjusted (`sa`), trend
(`t`), seasonal (`s`), and irregular (`i`) series.

Configuration supports X13 and TRAMO/SEATS presets, preprocessing and
decomposition overrides, built-in and custom calendars, CSV-backed user
variables, prespecified and automatically detected outliers, interventions,
ramps, and fixed coefficients.

The same engine is available from Python:

```python
from seasonal_pri import adjust

result = adjust(values, frequency="Monthly", start_year=2019, spec="RSA4")
seasonally_adjusted = result["sa"]
```

Opt into the complete JDemetra result dictionary, scalar diagnostics, and
processing messages with `detailed=True`. Returned time series retain their
own frequency and starting period, including forecasts and backcasts.

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

## Plots and Dashboard

Install optional visualization support:

```bash
python -m pip install -e ".[plots]"
seasonal-pri --data input.csv --plot-output adjustment.png
```

For an interactive local interface with CSV uploads, multi-series controls,
calendar mappings, Plotly charts, diagnostics, messages, and downloads:

```bash
python -m pip install -e ".[dashboard]"
seasonal-pri-dashboard
```

## Test

```bash
python -m unittest discover -s tests
```

CI runs the complete suite on Linux, Windows, and macOS with representative
Python 3.9-3.13 and Java 11/17 combinations.
