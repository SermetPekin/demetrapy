# Dashboard Example Files

Launch the dashboard from the repository root:

```bash
python -m pip install -e ".[dashboard]"
seasonal-pri-dashboard
```

Use these files in the sidebar:

| Dashboard input | Example file |
| --- | --- |
| Series CSV | `monthly_series.csv` |
| Configuration JSON | `x13_config.json` or `tramoseats_config.json` |
| Calendar pool CSV | `calendar_pool.csv` |

Select `date` for both date columns and select `sales` and `orders` as targets.
For a UserDefined calendar test, map `retail_td` to `sales` and `delivery_td`
to `orders`, then run the adjustment.

`monthly_series.csv` contains five years of synthetic monthly observations.
`calendar_pool.csv` covers seven years, including the full target period, and
contains an unused column to demonstrate that only selected variables enter
each target specification. The X13 and TRAMO/SEATS configurations both request
12 forecast periods using their method-specific settings.
