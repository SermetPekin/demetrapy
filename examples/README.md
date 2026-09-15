# Example Recipes

The examples use deterministic synthetic datasets from `demetrapy.datasets`.
This makes it easy to run several models on identical observations and compare
only the configuration choices.

## Toy Datasets

```python
from demetrapy import (
    load_emissions_with_calendars,
    load_monthly_emissions,
    load_monthly_retail,
    load_quarterly_production,
    load_retail_with_calendars,
)

emissions = load_monthly_emissions()
emissions_with_calendars = load_emissions_with_calendars()
monthly = load_monthly_retail()
quarterly = load_quarterly_production()
calendar_data = load_retail_with_calendars()
```

| Loader | Contents |
| --- | --- |
| `load_emissions_with_calendars()` | 10 emissions series, an 8-variable calendar pool, and per-series selections |
| `load_monthly_emissions()` | 120 monthly observations for 10 emissions sectors |
| `load_monthly_retail()` | 120 monthly observations for `sales` and `orders` |
| `load_quarterly_production()` | 80 quarterly `production` observations |
| `load_retail_with_calendars()` | Monthly observations, a 144-month calendar pool, and per-target selections |

Every call returns newly created pandas objects. The values are synthetic and
reproducible; they are intended for learning and tests, not economic analysis.

## Run Everything

```bash
python examples/run_all.py
```

The runner prints one status line per example and uses a temporary output
directory. Pass `--show-output` to display each example's results.

## Python Examples

Run them in order or copy the relevant configuration:

| File | Purpose |
| --- | --- |
| `01_basic_models.py` | typed X13 and TRAMO/SEATS configurations |
| `02_detailed_results.py` | complete TRAMO/SEATS history, forecast, combined, and diagnostic outputs |
| `03_x13_models.py` | X11 filters, calendars, and outlier settings |
| `04_tramoseats_models.py` | automatic and explicit ARIMA, calendars, and SEATS settings |
| `05_quarterly_models.py` | quarterly DataFrame/CSV inference and explicit sequence frequency |
| `06_calendar_variables.py` | multiple targets with different calendar variables |
| `07_compare_methods.py` | component-level comparison metrics for both engines |
| `08_advanced_tramoseats.py` | full TRAMO/SEATS options with a UserDefined calendar |
| `09_bulk_processing_audit.py` | fault-tolerant company batch with success/failure audit files |
| `10_csv_workflow.py` | configuration, `adjust_csv()`, output files, and structured audit records |
| `11_quarterly_detailed_results.py` | quarterly history, four-quarter forecast, combined output, and date validation |
| `12_multi_variable_emissions.py` | ten-variable monthly adjustment split into one DataFrame per component |
| `13_full_config_calendar_pool.py` | full TRAMO/SEATS parameters with per-series variables from one shared pool |

```bash
python examples/01_basic_models.py
python examples/03_x13_models.py
python examples/09_bulk_processing_audit.py
python examples/10_csv_workflow.py
```

The bulk-processing example continues after an item fails. It writes a detailed
log with tracebacks, a CSV report with one row per job, and an adjusted CSV for
each successful job under `bulk_run_output/`. One invalid job is included to
demonstrate failure reporting.

The CSV workflow example creates its input from the monthly toy dataset,
generates and validates an X13 configuration, processes the file with
`adjust_csv()`, writes a JSON audit manifest plus `runs.jsonl`, and demonstrates
how an invalid method-specific option is reported.

The examples intentionally show three equivalent configuration styles:

| Style | Examples |
| --- | --- |
| Typed `X13Config` and `TramoSeatsConfig` objects | `01_basic_models.py` |
| Direct keywords and reusable dictionaries | `03_x13_models.py`, `04_tramoseats_models.py` |
| JSON shared with the CLI | `10_csv_workflow.py`, `configs/` |

Typed objects favor discoverability, keywords favor short experiments, and
JSON favors operational or reviewed workflows. All three use the same
processors and return the same result types.

Example 05 also clarifies frequency ownership: DataFrame and CSV dates are
inspected automatically, while a raw sequence must pass `frequency="Quarterly"`
and its one-based starting quarter.

Example 02 is the complete result-access recipe. It shows readable and compact
historical DataFrames, forecast DataFrames, one concatenated seasonally
adjusted history-plus-forecast series, raw detailed outputs, diagnostics,
messages, and fitted ARIMA metadata from TRAMO/SEATS.

Example 11 applies the same detailed workflow to quarterly data. Its forecast
horizon is four observations, which represents one year for quarterly input.

Example 12 adjusts all ten emissions variables in one call, then separates the
result into observed, calendar-adjusted, seasonally adjusted, trend, seasonal,
and irregular DataFrames. Each historical frame has 10 columns and a monthly
date index; the equivalent forecast frames cover the following 12 months.

Example 13 adds a shared calendar-variable pool and a mapping from each input
column to its selected variables. Extra pool columns are deliberately left
unused to demonstrate that only selected variable names must be consumed.

The equivalent command-line workflow is:

```bash
demetrapy init-config --method x13 --output x13.json
demetrapy validate x13.json --data monthly_sales.csv
demetrapy monthly_sales.csv --config x13.json --output adjusted.csv --audit audit/
```

In Python, `adjust_csv()` returns the same stable result object as `adjust()`:

```python
from demetrapy import adjust_csv

result = adjust_csv(
    "monthly_sales.csv",
    config="x13.json",
    output="adjusted.csv",
    audit="audit/",
    detailed=True,
)
print(result.arima_model.notation)
```

The model dictionaries are examples of API syntax, not universal statistical
recommendations. Check diagnostics for real data.

## CLI Configurations

JSON examples are under `examples/configs/`:

| File | Purpose |
| --- | --- |
| `x13_basic.json` | basic X13 and X11 settings |
| `x13_automatic_arima.json` | X13 automatic model selection |
| `x13_explicit_arima.json` | X13 explicit airline model |
| `tramoseats_full.json` | extended TRAMO/SEATS configuration |

## Result Access

All recipes use the stable result API:

```python
result.components
result.seasonally_adjusted
result.to_compact_frame()

sales = result.for_series("sales")
sales.forecasts.seasonally_adjusted
sales.to_forecast_dict()["sa_f"]
```

Set `detailed=True` when raw JDemetra+ series, diagnostics, processing messages,
or the fitted ARIMA model are needed.