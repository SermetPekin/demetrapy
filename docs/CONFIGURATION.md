# Configuration Reference

This document describes how `demetrapy` configuration maps to JDemetra+
core 2.2.6. For runnable commands and DataFrame examples, see
[USAGE.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md).

## Processing Order

For TRAMO/SEATS, the main stages are:

1. Transform the input series.
2. Apply calendar effects, regressors, interventions, ramps, and outliers.
3. Select an ARIMA model automatically or apply explicit orders.
4. Estimate the regression and ARIMA parameters.
5. Pass the linearized series and fitted model to SEATS.
6. Decompose the series into trend, seasonal, irregular, and adjusted signals.

For X13, RegARIMA preprocessing is followed by X11 filter-based decomposition
instead of SEATS model-based decomposition.

## Package Defaults

Calling `adjust()` without overrides uses:

| Option | Default |
| --- | --- |
| `frequency` | `Monthly` |
| `method` | `x13` |
| `spec` | `RSA4` |
| `start_period` | `1` |
| `benchmarking` | `false` |
| `detailed` | `false` |

Nested processing values that are not supplied retain the values from the
selected JDemetra preset. For example, `method="tramoseats", spec="RSAfull"`
uses the complete JDemetra `RSAfull` defaults unless individual sections are
overridden.

## Compatible Groups

| Group | X13 | TRAMO/SEATS |
| --- | --- | --- |
| `preprocessing.transform` | Yes | Yes |
| `preprocessing.arima` | Yes | Yes |
| `preprocessing.automodel` | Yes | Yes |
| `preprocessing.estimate` | Yes | Yes |
| `calendar` and UserDefined calendars | Yes | Yes |
| `outlier_detection` | Yes | Yes |
| User variables and special variables | Yes | Yes |
| X11 options | Yes | No |
| `seats` | No | Yes |

Wrong-method options raise `ValueError` instead of being ignored.

## Preprocessing

The `preprocessing` object accepts four sections:

```python
preprocessing={
    "transform": {...},
    "arima": {...},       # or automodel
    "automodel": {...},
    "estimate": {...},
}
```

### Transformation

Common option:

| Option | Meaning |
| --- | --- |
| `function` | `None`, `Auto`, or `Log` |

X13 options:

| Option | Meaning |
| --- | --- |
| `aic_difference` | AIC difference used for automatic transformation |
| `constant` | Transformation constant |
| `adjust` | Length-of-period adjustment |

TRAMO options:

| Option | Meaning |
| --- | --- |
| `fct` | Transformation sensitivity factor |
| `units` | Apply unit scaling |
| `preliminary_check` | Run preliminary checks |

### Explicit ARIMA

```python
preprocessing={
    "arima": {
        "p": 0,
        "d": 1,
        "q": 1,
        "bp": 0,
        "bd": 1,
        "bq": 1,
        "mean": False,
    }
}
```

This represents:

```bash 
{ARIMA}(p,d,q)(bp,bd,bq)_s
```

where `s` is determined by the series frequency. Orders must be non-negative
integers and `mean` must be Boolean.

Explicit orders disable automatic model selection. If both `arima` and
`automodel` are present, `arima` takes precedence. Partial explicit models are
accepted; omitted orders retain their preset values. Supply all seven fields
for a model that is independent of the selected preset.

### Automatic Model Selection

Common options:

| Option | Meaning |
| --- | --- |
| `enabled` | Enable automatic model selection |
| `accept_default` | Allow the default candidate model |

X13 automodel options:

`check_mu`, `mixed`, `balanced`, `ljung_box_limit`, `arma_significance`,
`percent_rse`, `hannan_rissanen`, `percent_reduction_cv`,
`initial_unit_root_limit`, `final_unit_root_limit`, `cancelation_limit`, and
`unit_root_limit`.

TRAMO automodel options:

`pcr`, `ub1`, `ub2`, `cancel`, `tsig`, `pc`, and `ami_compare`.

See
[03_x13_models.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/03_x13_models.py)
and
[04_tramoseats_models.py](https://github.com/SermetPekin/demetrapy/blob/main/examples/04_tramoseats_models.py)
for complete executable configurations.

### Estimation

Common option:

| Option | Meaning |
| --- | --- |
| `tolerance` | Numerical estimation tolerance |

TRAMO additionally supports:

| Option | Meaning |
| --- | --- |
| `exact_ml` | Use exact maximum likelihood |
| `unit_root_limit` | Unit-root boundary used during estimation |

## Calendar Configuration

Common calendar options include `type`, `test`, `stock_day`, `holidays`,
`custom_holidays`, and `easter`.

X13 additionally supports `length_of_period`. TRAMO additionally supports
`leap_year` and `automatic`. Supplying a method-specific option to the wrong
engine raises `ValueError`.

### UserDefined Calendars

Precomputed calendar variables are supplied through a separate DataFrame:

```python
result = adjust_dataframe(
    observations,
    calendar_pool=calendar_pool,
    user_defined_calendars={"sales": ["company_working_days"]},
    method="tramoseats",
    spec="RSAfull",
    detailed=True,
)
```

The complete pool is registered in the processing context, while only selected
columns are passed to JDemetra as UserDefined trading-day variables. Selecting
one disables built-in trading-days, working-days, and leap-year regressors.
Easter remains independent and opt-in.

Variable names must be unique within their group. The calendar pool must use
the same frequency as the target and cover every target period.

## Outlier Detection

Both engines accept `types`, `critical_value`, and `tc_rate`. Supported types
are `AO`, `LS`, `TC`, and `SO`.

X13 additionally supports `ls_run` and `max_iterations`. TRAMO additionally
supports `exact_ml`.

Prespecified outliers are separate:

```python
outliers=[{"type": "AO", "date": "2020-04-01"}]
```

## X11 Options

These top-level options apply only to X13:

- `decomposition_mode`
- `seasonal_filter`
- `henderson_filter_length`
- `lower_sigma`
- `upper_sigma`
- `forecast_horizon`
- `backcast_horizon`

## SEATS Options

The `seats` section applies only to TRAMO/SEATS:

| Option | Meaning |
| --- | --- |
| `approximation_mode` | SEATS approximation strategy |
| `estimation_method` | Signal extraction method |
| `xl_boundary` | Root boundary |
| `seasonal_tolerance` | Seasonal identification tolerance |
| `trend_boundary` | Trend root boundary |
| `seasonal_boundary` | Seasonal root boundary |
| `seasonal_boundary_at_pi` | Seasonal boundary at frequency $\pi$ |
| `prediction_length` | Number of forecast periods; `-1` means one year |

SEATS does not select the ARIMA model. It decomposes the model produced by the
TRAMO preprocessing stage.

## Detailed Results

`detailed=True` changes the information retained, not the calculation or the
returned Python object.

`adjust()` always returns an `AdjustmentResult` with named primary components.
`to_compact_dict()` returns the `y`, `ycal`, `sa`, `t`, `s`, and `i`
compatibility mapping. `forecasts` and `to_forecast_dict()` expose available
future-domain `y_f`, `ycal_f`, `sa_f`, `t_f`, `s_f`, and `i_f` series.
Detailed mode additionally populates:

- `series`: all available domain-aware JDemetra time series
- `diagnostics`: scalar diagnostics
- `messages`: processing information and failures
- `arima_model`: fitted orders, period, mean, and selection mode
- `method` and `specification`: requested processing identifiers

```python
result = adjust(
    values,
    start_year=2019,
    method="tramoseats",
    spec="RSAfull",
    detailed=True,
)

print(result.arima_model.notation)
print(result.arima_model.automatic)
forecast = result.series["final.sa_f"]
```

DataFrame results expose per-target details through `result.for_series(target)`;
for example, `result.for_series(target).arima_model` returns the fitted model.

## Complete Examples

- [Basic X13 and TRAMO/SEATS](https://github.com/SermetPekin/demetrapy/blob/main/examples/01_basic_models.py)
- [X13 configurations](https://github.com/SermetPekin/demetrapy/blob/main/examples/03_x13_models.py)
- [TRAMO/SEATS configurations](https://github.com/SermetPekin/demetrapy/blob/main/examples/04_tramoseats_models.py)
- [Quarterly models](https://github.com/SermetPekin/demetrapy/blob/main/examples/05_quarterly_models.py)
- [UserDefined calendars](https://github.com/SermetPekin/demetrapy/blob/main/examples/06_calendar_variables.py)
- [Method comparison](https://github.com/SermetPekin/demetrapy/blob/main/examples/07_compare_methods.py)
- [Advanced TRAMO/SEATS](https://github.com/SermetPekin/demetrapy/blob/main/examples/08_advanced_tramoseats.py)
