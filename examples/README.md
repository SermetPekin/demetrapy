# Examples

Run one script from the repository root:

```bash
uv run python examples/13_full_config_calendar_pool.py
```

Run the full set in isolated temporary directories:

```bash
uv run python examples/run_all.py
```

To run `14_copy_run_inspect.ipynb` from a cloned repository, install the
optional Jupyter dependencies and select the resulting `.venv` as its kernel:

```bash
python -m pip install -e ".[notebook]"
```

## Start Here

| Goal | Example |
| --- | --- |
| Explore TRAMO/SEATS interactively | `14_copy_run_inspect.ipynb` |
| Adjust ten DataFrame columns with TRAMO/SEATS | `12_multi_variable_emissions.py` |
| Use a calendar pool with per-series mappings | `13_full_config_calendar_pool.py` |
| Inspect components, forecasts, diagnostics, and ARIMA | `02_detailed_results.py` |
| Configure advanced TRAMO/SEATS models | `08_advanced_tramoseats.py` |

X13 comparisons, CSV automation, auditing, and quarterly workflows are also
included in the catalog below.

## Catalog

| File | Focus |
| --- | --- |
| `14_copy_run_inspect.ipynb` | runnable TRAMO/SEATS DataFrame, forecast, model, and chart walkthrough |
| `12_multi_variable_emissions.py` | six TRAMO/SEATS component DataFrames for ten monthly targets |
| `13_full_config_calendar_pool.py` | extended TRAMO/SEATS parameters, shared variable pool, and target mappings |
| `02_detailed_results.py` | history, forecasts, diagnostics, messages, and fitted model |
| `04_tramoseats_models.py` | automatic and explicit ARIMA with SEATS settings |
| `08_advanced_tramoseats.py` | advanced TRAMO/SEATS and a user-defined calendar |
| `06_calendar_variables.py` | separate calendar selections for two targets |
| `11_quarterly_detailed_results.py` | quarterly detailed output and forward dates |
| `05_quarterly_models.py` | quarterly DataFrame, CSV, and sequence inputs |
| `01_basic_models.py` | typed TRAMO/SEATS and X13 configuration |
| `07_compare_methods.py` | component-level TRAMO/SEATS and X13 comparison |
| `03_x13_models.py` | X13/X11 filters, calendars, and outlier settings |
| `09_bulk_processing_audit.py` | fault-tolerant batch processing and audit records |
| `10_csv_workflow.py` | config generation, validation, CSV output, and audit |

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
| `configs/tramoseats_full.json` | extended TRAMO/SEATS configuration |
| `configs/x13_basic.json` | basic X13/X11 options |
| `configs/x13_automatic_arima.json` | automatic model selection |
| `configs/x13_explicit_arima.json` | explicit seasonal ARIMA |

The Python examples use typed objects or direct options. JSON is useful when a
configuration must also run through the CLI.
