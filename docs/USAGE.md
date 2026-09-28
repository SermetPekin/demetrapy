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
sa = result.sa
ycal = result.ycal
trend = result.component("t")
sa_forecast = result.forecast("sa")
complete_sa = result.combined("sa")
status = result.status

compact = result.to_compact_frame()
forecasts = result.to_forecast_frame()
combined = result.to_combined_frame()
summary = result.to_summary_frame()
```

Component selectors accept compact names (`y`, `ycal`, `sa`, `t`, `s`, `i`)
or their descriptive names. They return date-indexed DataFrames; historical
components have the same index and columns as the input. Forecast dates begin
after the final observation. `status` is the concise property form of
`to_summary_frame()`.

Export one component to a plain CSV or several components to separate XLSX
sheets:

```python
result.export("adjusted.csv", components=["sa"])
result.export("adjusted.xlsx", components=["sa", "ycal"])
```

The summary has one row per input series and stable columns for method,
specification, ARIMA notation, automatic selection, diagnostic and message
counts, and the number of seasonally adjusted forecast periods:

```python
review = summary[
    ["series", "arima", "diagnostic_count", "message_count", "forecast_periods"]
]
```

ARIMA fields are nullable when detailed fitted-model metadata is unavailable.

### Interactive HTML Report

Detailed batch results can be exported as one self-contained HTML file:

```python
report_path = result.to_html_report(
    "tramoseats_report.html",
    title="Monthly Sales TRAMO/SEATS Review",
)
```

The report includes the batch summary, interactive original-versus-adjusted
and component charts, JDemetra+'s SI output, fitted ARIMA metadata,
diagnostics, and processing messages for every series. Plotly is embedded in
the file, so the report can be opened without a server or internet connection.
For additive results, SI is shown as original minus trend; for log-transformed
results, it is shown as the original-to-trend ratio. Report generation requires
`detailed=True`.

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

## Plotting

Plot one fitted result without leaving the Python workflow:

```python
from demetrapy import plot_adjustment

figure = plot_adjustment(result, target="power")
figure.savefig("adjustment.png", dpi=150)
```

Omit `target` for a single-series result. Use `plot_adjustment_interactive()`
for an interactive Plotly figure.

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
    method="tramoseats",
    spec="RSAfull",
    seats={"prediction_length": 4},
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
| `TramoSeatsConfig` or `X13Config` | configuration lives in Python and is reused |
| Direct keyword arguments | the call is short and local |
| JSON or `AdjustmentConfig` | configuration is reviewed, stored, or shared with the CLI |

```python
from demetrapy import TramoSeatsConfig, adjust_dataframe

typed = adjust_dataframe(
    data,
    config=TramoSeatsConfig(
        spec="RSAfull",
        seats={"prediction_length": 12},
    ),
)

direct = adjust_dataframe(
    data,
    method="tramoseats",
    spec="RSAfull",
    seats={"prediction_length": 12},
)
```

Do not combine `config=` with model-setting keyword arguments.

## File Automation and CLI

Use this interface when files are the integration boundary. For interactive
analysis and multiple series, prefer `adjust_dataframe()`.

The default CSV columns are `date` and `value`. Dates must be regular ISO
`YYYY-MM-DD` values; observations must be finite numbers.

```bash
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
demetrapy init-config --method tramoseats --output tramoseats.json
demetrapy init-config --method x13 --output x13.json
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

## Dashboard

Launch the local dashboard with:

```bash
demetrapy-dashboard
```

It accepts uploaded observations, pasted numeric values, JSON configuration,
and an optional calendar-pool CSV. Before processing, it previews the selected
data and checks its date range, frequency, missing values, non-finite values,
and recommended history length. For pasted data, enter one observation per row
with comma- or space-separated series, then select the frequency and start
period. Column names are optional.

The processing controls select the transformation, AO/LS/TC outlier detection,
forecast horizon, and automatic or explicit ARIMA model. Results include
interactive charts, diagnostics, messages, a multi-series batch summary,
downloadable CSV files, and a self-contained HTML report. The **Batch Summary**
tab can also download a Python script containing the latest successful run's
selected data, calendar inputs, and engine configuration. Running the script
repeats the adjustment and writes component, forecast, and summary CSV files.
The **Compare Methods** tab runs X13 and TRAMO/SEATS with their shared RSA4
preset and reports RMSE, maximum absolute difference, and correlation.

Interactive component charts show formatted dates on every panel, full dates in
hover details, and a shaded forecast region. The **Run History** tab retains the
10 most recent successful adjustments in the current browser session. Select
two runs to compare their settings and seasonally adjusted series, review RMSE,
maximum absolute difference, and correlation, or download the aligned values.

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
