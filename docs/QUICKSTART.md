# Quickstart

## Install

Install Python 3.11+, Java 9+, and the package:

```bash
python -m pip install demetrapy
demetrapy check
```

The first adjustment downloads JDemetra+ 2.2.6 to
`~/.cache/demetrapy`. The readiness check itself is read-only.

## Python: Adjust Several Series

The built-in emissions dataset has ten monthly columns and a date index:

```python
from demetrapy import X13Config, adjust_dataframe, load_monthly_emissions

data = load_monthly_emissions()
result = adjust_dataframe(
    data,
    config=X13Config(spec="RSA4", forecast_horizon=12),
)

print(result.seasonally_adjusted.tail())
print(result.calendar_adjusted.tail())
print(result.to_forecast_frame().head())
```

The component attributes are DataFrames with the same ten columns. Forecasts
start after the last input date.

## CLI: Adjust a CSV

Input files use regular ISO dates and one numeric value column:

```csv
date,value
2019-01-01,101.2
2019-02-01,103.8
2019-03-01,107.1
```

Run the default X13 `RSA4` adjustment:

```bash
demetrapy input.csv --output adjusted.csv
```

For a reviewed configuration file:

```bash
demetrapy init-config --method tramoseats --output config.json
demetrapy validate config.json --data input.csv
demetrapy input.csv --config config.json --output adjusted.csv
```

The output columns are `y`, `ycal`, `sa`, `t`, `s`, and `i`.

## Next

- Use [USAGE.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md) for API and CLI workflows.
- Use [CONFIGURATION.md](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md) for model options.
- Browse the [examples](https://github.com/SermetPekin/demetrapy/blob/main/examples/README.md) for complete programs.
