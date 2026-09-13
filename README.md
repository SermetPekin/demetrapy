# seasonal-pri

A Python command-line interface for seasonal adjustment with
[JDemetra+ core](https://github.com/jdemetra/jdemetra-core). It calls the real
X13 implementation through JPype and does not require Maven or a Demetra+
desktop installation.

## Requirements

- Python 3.9 or newer
- Java 8 or newer

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The pinned `demetra-tstoolkit` 2.2.6 JAR is downloaded from Maven Central on
the first run and cached in `~/.cache/seasonal-pri`. Set `SEASONAL_PRI_JAR` to
use a local JAR instead.

## Use

Input is a regular monthly, quarterly, half-yearly, or yearly CSV series:

```csv
date,value
2019-01-01,101.2
2019-02-01,103.8
```

Run with defaults (`Monthly`, `RSA4`):

```bash
seasonal-pri input.csv --output adjusted.csv
```

Or provide a JSON configuration:

```bash
seasonal-pri input.csv --config examples/config.json --output adjusted.csv
```

See the [usage guide](USAGE.md) for the complete input, configuration, output,
and Python API reference.

The result contains the original (`y`), seasonally adjusted (`sa`), trend
(`t`), seasonal (`s`), and irregular (`i`) series.

Supported configuration keys are `frequency`, `spec`, `date_column`,
`value_column`, `decomposition_mode`, `seasonal_filter`,
`henderson_filter_length`, `lower_sigma`, `upper_sigma`, `forecast_horizon`,
`backcast_horizon`, and `benchmarking`. X13 presets are `RSAX11` and
`RSA0` through `RSA5`.

The same engine is available from Python:

```python
from seasonal_pri import adjust

result = adjust(values, frequency="Monthly", start_year=2019, spec="RSA4")
seasonally_adjusted = result["sa"]
```

## Test

```bash
python -m unittest discover -s tests
```
