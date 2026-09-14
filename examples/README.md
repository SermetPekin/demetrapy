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

## Start Here

```bash
python examples/basic_models.py
```

This runs X13 and TRAMO/SEATS on the same `sales` series and shows historical
components and seasonally adjusted forecasts.

## Configuration Recipes

```bash
python examples/x13_recipes.py
python examples/tramoseats_recipes.py
```

The configuration dictionaries at the top of each file are designed to be
copied individually. They cover:

- X13 RSA4 defaults
- X13 multiplicative decomposition and explicit X11 filters
- X13 working-day regressors and automatic outlier detection
- TRAMO/SEATS automatic model selection
- TRAMO/SEATS with an explicit airline ARIMA model
- TRAMO/SEATS trading days, outliers, and SEATS controls

These configurations demonstrate API syntax. Model selection should still be
based on diagnostics and the properties of the user's series.

## Other Frequencies and Multiple Series

```bash
python examples/quarterly_models.py
python examples/calendar_dataframe.py
```

The quarterly example compares both engines on one production series. The
calendar example adjusts `sales` and `orders` together while selecting different
variables from the same wider calendar pool.

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