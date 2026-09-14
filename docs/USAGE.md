# Usage Guide

For a consolidated description of processing stages, compatible configuration
groups, defaults, and every supported ARIMA/X11/SEATS option, see the
[configuration reference](CONFIGURATION.md).

## Installation

`demetrapy` requires Python 3.9+ and Java 8+.

For Command Prompt, proxy-restricted networks, and manual JAR installation, see
the [Windows usage guide](WINDOWS_USAGE.md).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Confirm that the command is available:

```bash
demetrapy --help
```

On its first adjustment, the package downloads JDemetra+ core 2.2.6 from
Maven Central and caches it in `~/.cache/demetrapy`. No JAR configuration is
normally needed. To use a JAR that already exists on your machine, set its
absolute path:

```bash
export DEMETRAPY_JAR="$HOME/lib/demetra-tstoolkit-2.2.6.jar"
```

Clear an incorrect override to restore automatic downloading:

```bash
unset DEMETRAPY_JAR
```

## Input CSV

The input must contain a regular time series with ISO `YYYY-MM-DD` dates and
numeric values. The default column names are `date` and `value`.

```csv
date,value
2019-01-01,101.2
2019-02-01,103.8
2019-03-01,107.1
```

Rows must be in chronological order. Supported frequencies are `Monthly`,
`Quarterly`, `HalfYearly`, and `Yearly`. The first date determines the starting
period.

## Basic Command

Run an X13 adjustment with the default monthly `RSA4` specification:

```bash
demetrapy input.csv --output adjusted.csv
```

The data file can instead be named explicitly with `--data` or `-d`:

```bash
demetrapy --data input.csv --output adjusted.csv
```

Without `--output`, the resulting CSV is written to standard output:

```bash
demetrapy input.csv
```

Use `--config` or `-c` to provide adjustment settings:

```bash
demetrapy input.csv --config examples/configs/x13_basic.json --output adjusted.csv
```

The fully named equivalent is:

```bash
demetrapy \
  --data input.csv \
  --config examples/configs/x13_basic.json \
  --output adjusted.csv
```

### Command-Line Parameters

| Parameter | Short form | Description |
| --- | --- | --- |
| positional `input` | | CSV data file; omit when using `--data` |
| `--data FILE` | `-d` | Explicit CSV data file |
| `--config FILE` | `-c` | JSON adjustment configuration |
| `--output FILE` | `-o` | Output CSV; defaults to standard output |
| `--method METHOD` | | `x13` or `tramoseats` |
| `--spec NAME` | | JDemetra+ preset such as `RSA4` or `RSAfull` |
| `--frequency NAME` | | `Monthly`, `Quarterly`, `HalfYearly`, or `Yearly` |
| `--date-column NAME` | | Input date-column name |
| `--value-column NAME` | | Input value-column name |
| `--plot` | | Display an interactive overview window |
| `--plot-output FILE` | | Save the overview as a PNG file |

Do not supply both positional `input` and `--data`. Command-line method,
specification, frequency, and column options override values from the JSON
configuration. Other advanced settings remain in the config file.

Run TRAMO/SEATS directly without a config file:

```bash
demetrapy \
  --data monthly_sales.csv \
  --method tramoseats \
  --spec RSAfull \
  --output monthly_sales_adjusted.csv
```

Process quarterly data with custom column names:

```bash
demetrapy \
  --data quarterly_sales.csv \
  --frequency Quarterly \
  --date-column period \
  --value-column sales \
  --output quarterly_sales_adjusted.csv
```

Override only the method and preset from an existing configuration:

```bash
demetrapy \
  --data input.csv \
  --config examples/configs/x13_basic.json \
  --method tramoseats \
  --spec RSA5 \
  --output adjusted.csv
```

Write CSV to standard output for use in a pipeline:

```bash
demetrapy --data input.csv --config examples/configs/x13_basic.json
```

Paths containing spaces should be quoted:

```bash
demetrapy --data "data/monthly sales.csv" --output "results/adjusted sales.csv"
```

The CLI processes one value column per invocation. Use `adjust_dataframe()`
from Python to process multiple target columns in one call.

## Toy Datasets and Recipes

Deterministic synthetic datasets are included for experimentation:

```python
from demetrapy import load_monthly_retail, load_quarterly_production

monthly = load_monthly_retail()
quarterly = load_quarterly_production()
```

Run the copy-ready model recipes from the repository root:

```bash
python examples/01_basic_models.py
python examples/02_detailed_results.py
python examples/03_x13_models.py
python examples/04_tramoseats_models.py
python examples/05_quarterly_models.py
python examples/06_calendar_variables.py
python examples/07_compare_methods.py
python examples/08_advanced_tramoseats.py
```

Each method-specific recipe applies several configurations to the same input,
so differences are attributable to model settings rather than different toy
data. See [the example catalog](../examples/README.md) for the dataset contents and
the configuration covered by each script.

## Plotting

Plotting support is included in the standard installation and does not change
seasonal-adjustment calculations.

Save a GUI-style overview containing original and adjusted series, trend,
seasonal, irregular, configured forecasts, and active effects:

```bash
demetrapy \
  --data input.csv \
  --config examples/configs/x13_basic.json \
  --output adjusted.csv \
  --plot-output adjustment.png
```

Display the plot instead of only saving it:

```bash
demetrapy --data input.csv --plot
```

Python callers receive the Matplotlib figure without displaying it:

```python
from demetrapy import plot_adjustment

figure = plot_adjustment(detailed_result, target="sales")
figure.savefig("sales-adjustment.png", dpi=150)
```

`target` is required when the result contains multiple target series.

## Streamlit Dashboard

Launch the included local dashboard:

```bash
demetrapy-dashboard
```

The dashboard accepts a series CSV, an optional JSON configuration, and an
optional user-defined calendar-pool CSV. It supports multiple target columns,
per-target calendar mappings, X13 and TRAMO/SEATS presets, interactive Plotly
charts, diagnostics, processing messages, and CSV downloads. Charts support
hover values, zooming, panning, and legend toggles. Processing still uses the
same in-memory JDemetra+ engine and does not create workspace XML.

Ready-to-upload files and the exact selections are provided in the
[dashboard example directory](../examples/dashboard/README.md). The fixture set
includes a multi-series CSV, a wider calendar pool, and separate X13 and
TRAMO/SEATS configurations with forecasts.

## Configuration

Configuration is a JSON object. Existing flat X11 keys remain supported, while
advanced preprocessing, calendar, regression, and SEATS settings use nested
objects. Every key is optional.

```json
{
  "frequency": "Monthly",
  "method": "x13",
  "spec": "RSA4",
  "date_column": "date",
  "value_column": "value",
  "decomposition_mode": "Multiplicative",
  "seasonal_filter": "S3X5",
  "henderson_filter_length": 13,
  "lower_sigma": 1.5,
  "upper_sigma": 2.5,
  "forecast_horizon": -1,
  "backcast_horizon": 0,
  "benchmarking": false
}
```

| Key | Default | Description |
| --- | --- | --- |
| `frequency` | `Monthly` | Observation frequency |
| `method` | `x13` | `x13` or `tramoseats` |
| `spec` | `RSA4` | X13: `RSAX11`, `RSA0`-`RSA5`; TRAMO/SEATS: `RSA0`-`RSA5`, `RSAfull` |
| `date_column` | `date` | Input CSV date column |
| `value_column` | `value` | Input CSV numeric column |
| `decomposition_mode` | preset value | X11 mode, such as `Additive` or `Multiplicative` |
| `seasonal_filter` | preset value | X11 filter, such as `S3X3`, `S3X5`, or `S3X9` |
| `henderson_filter_length` | preset value | Henderson trend filter length |
| `lower_sigma` | preset value | Lower outlier sigma limit |
| `upper_sigma` | preset value | Upper outlier sigma limit |
| `forecast_horizon` | preset value | Forecast periods; `-1` means one year |
| `backcast_horizon` | preset value | Backcast periods; `-1` means one year |
| `benchmarking` | `false` | Enable JDemetra+ benchmarking |

The flat X11 options apply only to `method: "x13"`. See
[`examples/configs/tramoseats_full.json`](../examples/configs/tramoseats_full.json) for a complete
TRAMO/SEATS example with calendar and regression variables.

### Preprocessing and SEATS

The shared `preprocessing` object accepts `transform`, `automodel`, `arima`, and
`estimate` sections. Explicit ARIMA orders use `p`, `d`, `q`, `bp`, `bd`, `bq`,
and `mean`; supplying them disables automodel. Transform functions are `None`,
`Auto`, or `Log`. Unknown keys are rejected rather than ignored.

Use automatic model selection and optionally tune its method-specific settings:

```json
{
  "preprocessing": {
    "automodel": {"enabled": true}
  }
}
```

Or specify a complete seasonal ARIMA model. Explicit orders always take
precedence if an uploaded configuration also contains automodel settings:

```json
{
  "preprocessing": {
    "arima": {
      "p": 0, "d": 1, "q": 1,
      "bp": 0, "bd": 1, "bq": 1,
      "mean": false
    }
  }
}
```

ARIMA fields may be supplied partially; omitted orders retain their values from
the selected preset before automatic model selection is disabled. Supply all
seven fields when the model must be fully reproducible independent of preset.

The same object can be passed as `preprocessing=` to `adjust()` or
`adjust_dataframe()`. See
[`examples/configs/x13_explicit_arima.json`](../examples/configs/x13_explicit_arima.json) for a runnable CLI
configuration. The dashboard exposes the same choice under **ARIMA model**.

Runnable Python examples are available for both modes:

```bash
python examples/03_x13_models.py
python examples/04_tramoseats_models.py
```

For CLI configuration, use
[`examples/configs/x13_automatic_arima.json`](../examples/configs/x13_automatic_arima.json)
or [`examples/configs/x13_explicit_arima.json`](../examples/configs/x13_explicit_arima.json).

Detailed results report the fitted model, including the orders selected by
automodel:

```python
result = adjust(
    values,
    start_year=2019,
    preprocessing={"automodel": {"enabled": True}},
    detailed=True,
)
print(result.arima_model.notation)
print(result.arima_model.automatic)
```

For a DataFrame result, use `result.for_series(target).arima_model`.

The complete CLI configuration in
[`examples/configs/tramoseats_full.json`](../examples/configs/tramoseats_full.json)
covers explicit ARIMA fields, TRAMO transform and estimation options, outlier
detection, and SEATS controls. UserDefined calendar handling is demonstrated in
[`examples/06_calendar_variables.py`](../examples/06_calendar_variables.py).

`outlier_detection.types` accepts `AO`, `LS`, `TC`, and `SO`, with optional
`critical_value` and `tc_rate`. For TRAMO/SEATS, `seats` accepts decomposition
settings including `approximation_mode`, `estimation_method`, boundaries, and
`prediction_length`.

### Calendar Variables

`calendar.type` is `None`, `WorkingDays`, or `TradingDays`. X13 uses
`length_of_period` and test values `None`, `Add`, or `Remove`. TRAMO uses
`leap_year`, `automatic`, and test values `None`, `Separate_T`, or `Joint_F`.
Both methods support `stock_day` and Easter settings.

Precomputed user-defined trading-day weights use the pandas API described
below. They are distinct from ordinary `user_variables`: selected calendar
columns are passed to JDemetra+ through `TradingDaysSpec.setUserVariables()`.
Selecting them disables built-in trading-days, working-days, and leap-year
regressors. Easter remains separate and is included only when explicitly set in
`calendar.easter`.

Custom calendars are declared inline. Fixed holidays use one-based month/day;
moving holidays use a JDemetra `DayEvent` such as `EasterMonday`, `GoodFriday`,
or `Christmas`:

```json
{
  "calendar": {
    "type": "TradingDays",
    "holidays": "company",
    "custom_holidays": [
      {"month": 1, "day": 1},
      {"event": "EasterMonday", "offset": 0, "weight": 1.0}
    ]
  }
}
```

### User and Special Variables

A CLI user variable names a numeric CSV column. `effect` is `Undefined`,
`Series`, `Trend`, `Seasonal`, `SeasonallyAdjusted`, or `Irregular`. Lag bounds
are inclusive. An optional `coefficient` fixes the coefficient instead of
estimating it.

```json
{
  "user_variables": [
    {"name": "promotion", "column": "promotion", "effect": "Irregular"}
  ],
  "outliers": [{"type": "AO", "date": "2020-04-01"}],
  "interventions": [
    seasonally_adjusted = result.seasonally_adjusted.values
      "name": "closure",
      "sequences": [{"start": "2020-03-01", "end": "2020-05-31"}]
    }
  ],
  "ramps": [{"start": "2021-01-01", "end": "2021-12-31"}]
}
```

`fixed_coefficients` also accepts JDemetra regression names. User-variable
names use `group@name` in that map; the default group is `user`.

For a CSV with custom columns:

```json
{
  "date_column": "period",
  "value_column": "sales",
  "frequency": "Quarterly"
}
```

```csv
period,sales
2023-01-01,425.1
2023-04-01,449.7
2023-07-01,438.2
2023-10-01,471.0
```

## Output CSV

The output preserves the input dates and contains these series:

| Column | Meaning |
| --- | --- |
| `y` | Original series |
| `sa` | Seasonally adjusted series |
| `t` | Trend component |
| `s` | Seasonal component |
| `i` | Irregular component |

```csv
date,y,sa,t,s,i
2019-01-01,101.2,103.4,102.9,0.9787,1.0049
```

## Python API

The same engine can be called directly. `start_period` is one-based, so January
or the first quarter is `1`.

```python
from demetrapy import adjust

values = [101.2, 103.8, 107.1]
result = adjust(
    values,
    frequency="Monthly",
    start_year=2019,
    start_period=1,
    spec="RSA4",
)

seasonally_adjusted = result.seasonally_adjusted.values
```

### Detailed Results

`adjust()` always returns an `AdjustmentResult`. Its named component
attributes are available at every detail level, and `to_compact_dict()`
provides the `y`, `ycal`, `sa`, `t`, `s`, and `i` compatibility mapping.
`result.forecasts` exposes domain-aware forecasts, and
`result.to_forecast_dict()` provides the available `y_f`, `ycal_f`, `sa_f`,
`t_f`, `s_f`, and `i_f` values. A zero forecast horizon produces no forecast
entries. Set `detailed=True` to additionally populate:

| Attribute | Content |
| --- | --- |
| `series` | Every `TsData` output exposed by the selected JDemetra processor |
| `diagnostics` | Boolean, numeric, and text values from the result dictionary |
| `messages` | Structured processing information, warnings, and errors |
| `method` | The selected processor |
| `specification` | The selected preset name |

Each item in `series` preserves `values`, `frequency`, `start_year`, and
one-based `start_period`. Common final outputs are `final.y`, `final.sa`,
`final.t`, `final.s`, and `final.i`; forecast names add `_f`, such as
`final.sa_f`. Preprocessing outputs include calendar, trading-day, regression,
outlier, residual, linearized, and forecast effects where the processor
provides them.

```python
detailed = adjust(
  values,
  frequency="Monthly",
  start_year=2019,
  method="x13",
  forecast_horizon=12,
  backcast_horizon=12,
  detailed=True,
)

sa_forecast = detailed.series["final.sa_f"]
print(sa_forecast.start_year, sa_forecast.start_period)
print(detailed.diagnostics)
print(detailed.messages)
```

Forecast configuration is method-specific. X13 uses `forecast_horizon` and
`backcast_horizon`. TRAMO/SEATS uses `seats={"prediction_length": 12}`.

TRAMO/SEATS and a Python-supplied regressor use the same function:

```python
result = adjust(
  values,
  frequency="Monthly",
  start_year=2019,
  method="tramoseats",
  spec="RSAfull",
  user_variables=[{
    "name": "promotion",
    "values": promotion_values,
    "effect": "Irregular",
  }],
  calendar={"type": "WorkingDays", "leap_year": True},
)
```

### User-Defined Calendar DataFrame

[The DataFrame variable-pool example](../examples/06_calendar_variables.py)
keeps target series and precomputed calendar weights in separate DataFrames.
The calendar pool may begin before and end after the targets. A dictionary maps
each target column to the pool columns it uses:

```python
from demetrapy import adjust_dataframe

selected_calendars = {
  "sales": ["retail_td"],
  "orders": ["retail_td", "delivery_td"],
}

adjusted = adjust_dataframe(
  observations,
  calendar_pool=calendar_weights,
  user_defined_calendars=selected_calendars,
  method="tramoseats",
  spec="RSA4",
)
```

Both inputs require unique, increasing, regular `DatetimeIndex` values. The API
infers monthly, quarterly, half-yearly, or yearly frequency and starting
periods; verifies matching frequencies, finite numeric values, and complete
target coverage; and preserves the full supplied calendar domain and values in
JDemetra+'s in-memory `ProcessingContext`. All pool columns are registered, but
only mapped columns enter each target's trading-day specification. Unmapped
targets use no user-defined calendar regressors.

The returned `DataFrameAdjustmentResult.components` has two-level columns
`(series, component)`, where each target has `observed`,
`calendar_adjusted`, `seasonally_adjusted`, `trend`, `seasonal`, and
`irregular`. `to_compact_frame()` provides the `y`, `ycal`, `sa`, `t`, `s`,
and `i` aliases. Per-target forecasts are available through
`result.for_series(target).forecasts`. This path bypasses JDemetra+ workspace
XML; no workspace file is generated or interpreted.

`adjust_dataframe()` always returns the same wrapper. With `detailed=True`,
its `detailed_series` attribute contains every JDemetra time-series output,
with columns `(target, output)`. Use `for_series(target)` for that target's
diagnostics, messages, and fitted model:

```python
detailed = adjust_dataframe(
  observations,
  method="x13",
  forecast_horizon=12,
  detailed=True,
)

sa = detailed.detailed_series[("sales", "final.sa")].dropna()
sa_forecast = detailed.detailed_series[("sales", "final.sa_f")].dropna()
sales_diagnostics = detailed.for_series("sales").diagnostics
```

Because every output keeps its own domain, the DataFrame uses the union of all
returned dates. Internal preprocessing series may begin earlier or end later
than `final.*_f`; use each named column's non-null span for its exact domain.

Common X11 options are accepted as keyword arguments:

```python
result = adjust(
    values,
    frequency="Monthly",
    start_year=2019,
    spec="RSA5",
    decomposition_mode="Multiplicative",
    seasonal_filter="S3X5",
    forecast_horizon=-1,
    benchmarking=True,
)
For a DataFrame result, use `result.for_series(target).arima_model`.
## Troubleshooting

- `CSV must contain columns`: set `date_column` and `value_column` to match the
  CSV header.
- `invalid number on CSV row`: ensure the configured value column contains only
  numeric observations.
- `unsupported frequency`, specification, enum, or option: use the exact,
  case-sensitive values documented above.
- `DEMETRAPY_JAR does not point to a file`: run `unset DEMETRAPY_JAR` to
  use the automatic download, or set it to an existing local JAR.
- JVM startup or JAR download errors: verify `java -version` and network access
  to Maven Central.