# Usage Guide

## Installation

`seasonal-pri` requires Python 3.9+ and Java 8+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Confirm that the command is available:

```bash
seasonal-pri --help
```

On its first adjustment, the package downloads JDemetra+ core 2.2.6 from
Maven Central and caches it in `~/.cache/seasonal-pri`. To use an existing JAR:

```bash
export SEASONAL_PRI_JAR=/path/to/demetra-tstoolkit-2.2.6.jar
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
seasonal-pri input.csv --output adjusted.csv
```

Without `--output`, the resulting CSV is written to standard output:

```bash
seasonal-pri input.csv
```

Use `--config` or `-c` to provide adjustment settings:

```bash
seasonal-pri input.csv --config examples/config.json --output adjusted.csv
```

## Configuration

Configuration is a flat JSON object. Every key is optional.

```json
{
  "frequency": "Monthly",
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
| `spec` | `RSA4` | X13 preset: `RSAX11` or `RSA0` through `RSA5` |
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
from seasonal_pri import adjust

values = [101.2, 103.8, 107.1]
result = adjust(
    values,
    frequency="Monthly",
    start_year=2019,
    start_period=1,
    spec="RSA4",
)

seasonally_adjusted = result["sa"]
```

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
```

## Troubleshooting

- `CSV must contain columns`: set `date_column` and `value_column` to match the
  CSV header.
- `invalid number on CSV row`: ensure the configured value column contains only
  numeric observations.
- `unsupported frequency` or `unsupported X13 specification`: use the exact,
  case-sensitive values documented above.
- JVM startup or JAR download errors: verify `java -version`, network access to
  Maven Central, or set `SEASONAL_PRI_JAR` to a local JAR.