# Examples

Run one script from the repository root:

```bash
uv run python examples/13_full_config_calendar_pool.py
```

Run the full set in isolated temporary directories:

```bash
uv run python examples/run_all.py
```

## Start Here

| Goal | Example |
| --- | --- |
| Adjust several DataFrame columns | `12_multi_variable_emissions.py` |
| Use a calendar pool with per-series mappings | `13_full_config_calendar_pool.py` |
| Inspect components, forecasts, diagnostics, and ARIMA | `02_detailed_results.py` |
| Compare X13 and TRAMO/SEATS | `07_compare_methods.py` |
| Build a CSV and audit workflow | `10_csv_workflow.py` |

## Catalog

| File | Focus |
| --- | --- |
| `01_basic_models.py` | typed X13 and TRAMO/SEATS configuration |
| `02_detailed_results.py` | history, forecasts, diagnostics, messages, and fitted model |
| `03_x13_models.py` | X11 filters, calendars, and outlier settings |
| `04_tramoseats_models.py` | automatic and explicit ARIMA with SEATS settings |
| `05_quarterly_models.py` | quarterly DataFrame, CSV, and sequence inputs |
| `06_calendar_variables.py` | separate calendar selections for two targets |
| `07_compare_methods.py` | component-level engine comparison |
| `08_advanced_tramoseats.py` | advanced TRAMO/SEATS and a user-defined calendar |
| `09_bulk_processing_audit.py` | fault-tolerant batch processing and audit records |
| `10_csv_workflow.py` | config generation, validation, CSV output, and audit |
| `11_quarterly_detailed_results.py` | quarterly detailed output and forward dates |
| `12_multi_variable_emissions.py` | six component DataFrames for ten monthly targets |
| `13_full_config_calendar_pool.py` | full parameters, shared variable pool, and target mappings |

## Built-In Data

The loaders return fresh, deterministic pandas objects:

| Loader | Shape and content |
| --- | --- |
| `load_monthly_emissions()` | 120 monthly dates x 10 emissions sectors |
| `load_emissions_with_calendars()` | emissions plus an 8-variable pool and mappings |
| `load_monthly_retail()` | 120 monthly dates x sales and orders |
| `load_retail_with_calendars()` | retail data plus a wider calendar pool |
| `load_quarterly_production()` | 80 quarterly dates x production |

The values are synthetic and intended for examples and tests.

## Configuration Files

| File | Focus |
| --- | --- |
| `configs/x13_basic.json` | basic X13/X11 options |
| `configs/x13_automatic_arima.json` | automatic model selection |
| `configs/x13_explicit_arima.json` | explicit seasonal ARIMA |
| `configs/tramoseats_full.json` | extended TRAMO/SEATS configuration |

The Python examples use typed objects or direct options. JSON is useful when a
configuration must also run through the CLI.
