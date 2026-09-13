# Retail Operations Case Study

This reproducible synthetic scenario represents a retailer adjusting monthly
sales and order volumes. It demonstrates the same workflow an analyst can use
when operational calendars differ across measures, without claiming that the
data belongs to a real organization.

## Scenario

- `sales` uses a retail trading-day variable.
- `orders` uses both retail and delivery trading-day variables.
- The registered calendar pool begins one year before the observations and
  extends one year beyond them.
- An unused calendar column proves that registration and selection are separate.
- TRAMO/SEATS produces 12 months of forecasts for both targets.

Run it from the repository root:

```bash
python -m pip install -e ".[examples]"
python examples/dataframe_user_variables_example.py
```

The run is successful when it reports both targets, non-empty diagnostics, and
a 12-observation `final.sa_f` forecast for sales. The example uses deterministic
inputs so changes can be compared between releases.

The browser version of the same multi-target workflow is described in
[dashboard/README.md](dashboard/README.md). It includes files for both X13 and
TRAMO/SEATS configurations.