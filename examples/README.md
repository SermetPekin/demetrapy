# Example Recipes

The examples use deterministic synthetic datasets from `demetrapy.datasets`.
This makes it easy to run several models on identical observations and compare
only the configuration choices.

## Toy Datasets

```python
from demetrapy import (
    load_monthly_retail,
    load_quarterly_production,
    load_retail_with_calendars,
)

monthly = load_monthly_retail()
quarterly = load_quarterly_production()
calendar_data = load_retail_with_calendars()
```

| Loader | Contents |
| --- | --- |
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
| `01_basic_models.py` | X13 and TRAMO/SEATS basics |
| `02_detailed_results.py` | components, forecasts, diagnostics, and CSV output |
| `03_x13_models.py` | X11 filters, calendars, and outlier settings |
| `04_tramoseats_models.py` | automatic and explicit ARIMA, calendars, and SEATS settings |
| `05_quarterly_models.py` | quarterly processing with both engines |
| `06_calendar_variables.py` | multiple targets with different calendar variables |
| `07_compare_methods.py` | component-level comparison metrics for both engines |
| `08_advanced_tramoseats.py` | full TRAMO/SEATS options with a UserDefined calendar |
| `09_bulk_processing_audit.py` | fault-tolerant company batch with success/failure audit files |

```bash
python examples/01_basic_models.py
python examples/03_x13_models.py
python examples/09_bulk_processing_audit.py
```

The bulk-processing example continues after an item fails. It writes a detailed
log with tracebacks, a CSV report with one row per job, and an adjusted CSV for
each successful job under `bulk_run_output/`. One invalid job is included to
demonstrate failure reporting.

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