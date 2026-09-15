# Usage

This guide covers the public workflows. Model options and accepted values are
listed in the [configuration reference](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md).

## Environment

`demetrapy` requires Python 3.11+ and Java 9+.

```bash
python -m pip install demetrapy
demetrapy check
```

`demetrapy check` reports Python, JPype, Java, architecture, and JDemetra+ JAR
readiness. Errors include a suggested fix. The first calculation downloads the
pinned JAR to `~/.cache/demetrapy`; use `DEMETRAPY_JAR` for a local copy.

Windows and offline installations are covered in
[WINDOWS_USAGE.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/WINDOWS_USAGE.md).

## DataFrames

Use a regular, increasing `DatetimeIndex`. Frequency is inferred from dates.

```python
from demetrapy import TramoSeatsConfig, adjust_dataframe

config = TramoSeatsConfig(
    spec="RSAfull",
    preprocessing={"automodel": {"enabled": True}},
    seats={"prediction_length": 12},
)
result = adjust_dataframe(data, config=config, detailed=True)
```

Each input column is processed independently. The common outputs are:

```python
observed = result.observed
calendar_adjusted = result.calendar_adjusted
seasonally_adjusted = result.seasonally_adjusted
trend = result.trend
seasonal = result.seasonal
irregular = result.irregular

compact = result.to_compact_frame()
forecasts = result.to_forecast_frame()
combined = result.to_combined_frame()
```

These are date-indexed DataFrames. For ten input columns, each historical
component has ten columns. Forecast component dates begin after the final
observation.

`detailed=True` adds raw JDemetra+ series, diagnostics, messages, and the fitted
ARIMA model:

```python
sales = result.for_series("sales")
print(sales.arima_model.notation)
print(sales.diagnostics)
print(sales.messages)
```

## User-Defined Calendar Variables

Keep observations and calendar variables in separate DataFrames. Both require
regular date indexes with the same frequency. The calendar pool must cover all
observation dates, but it may start earlier, end later, and contain unused
columns.

```python
mapping = {
    "power": ["heating_days", "cooling_days", "working_days"],
    "transport": ["working_days", "holiday_days", "mobility_index"],
    "industry": ["working_days", "industrial_days"],
}

result = adjust_dataframe(
    observations,
    calendar_pool=calendar_pool,
    user_defined_calendars=mapping,
    config=config,
)
```

Only mapped variables enter a target's model. An unmapped target uses no
user-defined calendar variables. Unknown target or variable names raise a
clear error.

The complete implementation is in
[examples/13_full_config_calendar_pool.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/13_full_config_calendar_pool.py).

## Sequences

Use `adjust()` for one sequence. Because values carry no dates, pass the
frequency and starting period explicitly when needed.

```python
from demetrapy import adjust

result = adjust(
    values,
    frequency="Quarterly",
    start_year=2020,
    start_period=1,
    method="x13",
    spec="RSA4",
    forecast_horizon=4,
    detailed=True,
)

sa = result.seasonally_adjusted.values
sa_forecast = result.forecasts.seasonally_adjusted
```

`start_period` is one-based. A forecast horizon counts observations: four
quarters is one year; twelve months is one year.

## Configuration Styles

Choose one style per call.

| Style | Use when |
| --- | --- |
| `X13Config` or `TramoSeatsConfig` | configuration lives in Python and is reused |
| Direct keyword arguments | the call is short and local |
| JSON or `AdjustmentConfig` | configuration is reviewed, stored, or shared with the CLI |

```python
from demetrapy import X13Config, adjust_dataframe

typed = adjust_dataframe(
    data,
    config=X13Config(spec="RSA4", forecast_horizon=12),
)

direct = adjust_dataframe(
    data,
    method="x13",
    spec="RSA4",
    forecast_horizon=12,
)
```

Do not combine `config=` with model-setting keyword arguments.

## CSV and CLI

The default CSV columns are `date` and `value`. Dates must be regular ISO
`YYYY-MM-DD` values; observations must be finite numbers.

```bash
demetrapy input.csv --output adjusted.csv
demetrapy input.csv --method tramoseats --spec RSAfull --output adjusted.csv
demetrapy input.csv --config config.json --output adjusted.csv
```

Useful options:

| Option | Purpose |
| --- | --- |
| `--data`, `-d` | explicit input path instead of the positional argument |
| `--config`, `-c` | JSON configuration |
| `--output`, `-o` | output CSV; omit for standard output |
| `--method` | `x13` or `tramoseats` |
| `--spec` | processor preset |
| `--frequency` | override inferred frequency |
| `--date-column` | input date column |
| `--value-column` | input value column |
| `--audit` | audit directory |
| `--plot-output` | save a static result plot |

The CLI processes one value column. Use `adjust_dataframe()` for several
targets.

### Create and Validate Configuration

```bash
demetrapy init-config --method x13 --output x13.json
demetrapy init-config --method tramoseats --output tramoseats.json
demetrapy validate config.json --data input.csv
demetrapy validate config.json --output normalized.json
```

Validation checks structure, method compatibility, presets, nested options,
and CSV data without starting Java.

### Audit Records

```bash
demetrapy input.csv --config config.json --output adjusted.csv --audit audit/
```

Each attempt writes a JSON manifest and appends the same record to
`audit/runs.jsonl`. Records include configuration, versions, file hashes,
diagnostics, messages, model metadata, row count, and period range. Observation
values and credentials are not stored.

## CSV from Python

`adjust_csv()` follows the same rules as the CLI and returns an
`AdjustmentResult`.

```python
from demetrapy import adjust_csv

result = adjust_csv(
    "input.csv",
    config="config.json",
    output="adjusted.csv",
    audit="audit/",
    detailed=True,
)
```

## Plotting and Dashboard

```python
from demetrapy import plot_adjustment

figure = plot_adjustment(result)
figure.savefig("adjustment.png", dpi=150)
```

For multi-series results, pass `target="column_name"`.

Launch the local dashboard with:

```bash
demetrapy-dashboard
```

It accepts observations, JSON configuration, and an optional calendar-pool
CSV, then exposes charts, diagnostics, model details, and downloads.

## Troubleshooting

Start with:

```bash
demetrapy check
```

| Problem | Action |
| --- | --- |
| Java is missing or too old | Install Java 9+ and verify `java -version` and `JAVA_HOME`. |
| `DEMETRAPY_JAR` is invalid | Unset it for automatic download or point it to a readable JAR. |
| CSV columns are missing | Set `--date-column` and `--value-column` to match the file. |
| Frequency mismatch | Remove the override or match it to the regular dates. |
| A model option is rejected | Check its engine and accepted values in the configuration reference. |

For runnable code, use the
[example catalog](https://github.com/SermetPekin/demetrapy/blob/main/examples/README.md).
