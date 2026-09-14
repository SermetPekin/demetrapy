# Five-Minute Quickstart

## 1. Install

Install Python 3.9 or later, Java 8 or later, and `demetrapy`:

```bash
python -m pip install demetrapy
demetrapy --help
demetrapy check
```

The first adjustment downloads the pinned JDemetra+ core JAR and caches it in
`~/.cache/demetrapy`. The readiness check is read-only: it does not start Java,
download the JAR, or create files. A missing cached JAR is a warning because it
can be downloaded automatically on first use.

## 2. Create Input Data

Create `monthly_sales.csv` with a regular monthly series:

```csv
date,value
2023-01-01,108.2
2023-02-01,110.5
2023-03-01,116.1
2023-04-01,114.8
```

Real seasonal adjustment requires a substantially longer series; these rows
only show the file layout.

## 3. Create a Configuration

Generate an X13 starter configuration:

```bash
demetrapy init-config --method x13 --output x13.json
```

For TRAMO/SEATS, replace `x13` with `tramoseats`.

## 4. Validate Before Running

Check the configuration and input file without starting Java:

```bash
demetrapy validate x13.json --data monthly_sales.csv
```

Validation reports unsupported presets, wrong-engine options, malformed nested
settings, missing columns, invalid numbers, and an invalid first date.

## 5. Run the Adjustment

```bash
demetrapy monthly_sales.csv --config x13.json --output adjusted.csv
```

Add `--audit audit/` to write a JSON manifest for the run and append the same
record to `audit/runs.jsonl`.

The output contains observed (`y`), calendar-adjusted (`ycal`), seasonally
adjusted (`sa`), trend (`t`), seasonal (`s`), and irregular (`i`) series.

Python users can choose a JSON file, a typed object, or direct keywords. All
three calls below perform the same X13 adjustment.

Use JSON when configuration is shared with the CLI:

```python
from demetrapy import adjust_csv

result = adjust_csv(
    "monthly_sales.csv",
    config="x13.json",
    output="adjusted.csv",
    audit="audit/",
    detailed=True,
)

print(result.seasonally_adjusted.values)
print(result.diagnostics)
print(result.messages)
```

Use a typed object for discoverable, reusable Python configuration:

```python
from demetrapy import X13Config, adjust_csv

config = X13Config(spec="RSA4", forecast_horizon=12)
result = adjust_csv("monthly_sales.csv", config=config, output="adjusted.csv")
```

Use direct keywords for a short one-off call:

```python
result = adjust_csv(
    "monthly_sales.csv",
    output="adjusted.csv",
    method="x13",
    spec="RSA4",
    forecast_horizon=12,
)
```

Use only one configuration style in a call. Existing keyword and JSON calls
remain supported.

A complete runnable version using the built-in toy data is available in
[`examples/10_csv_workflow.py`](https://github.com/SermetPekin/demetrapy/blob/main/examples/10_csv_workflow.py).

For multiple DataFrame columns, use `adjust_dataframe()`. For fault-tolerant
multi-company processing with audit logs, run:

```bash
python examples/09_bulk_processing_audit.py
```

Continue with the
[usage guide](https://github.com/SermetPekin/demetrapy/blob/main/docs/USAGE.md)
or the
[configuration reference](https://github.com/SermetPekin/demetrapy/blob/main/docs/CONFIGURATION.md).