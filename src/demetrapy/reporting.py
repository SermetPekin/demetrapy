"""Self-contained HTML reports for multi-series adjustment results."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .interactive import plot_adjustment_interactive


def write_html_report(
    result: Any,
    path: str | Path,
    *,
    title: str = "TRAMO/SEATS Batch Report",
) -> Path:
    """Write an offline interactive report for a detailed DataFrame result."""
    if result.detailed_series is None:
        raise ValueError("HTML reports require an adjustment run with detailed=True")
    if not result.results:
        raise ValueError("HTML reports require at least one result series")

    pd, go = _dependencies()
    sections = []
    include_plotly = True
    for target, series_result in result.results.items():
        component_figure = plot_adjustment_interactive(
            result,
            target=target,
            title=f"{target}: components and forecasts",
        )
        component_figure.update_layout(
            height=component_figure.layout.height + 110,
            margin={"l": 55, "r": 25, "t": 75, "b": 155},
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.08,
                "xanchor": "left",
                "x": 0,
            },
        )
        component_html = component_figure.to_html(
            full_html=False,
            include_plotlyjs=include_plotly,
            config={"displaylogo": False, "responsive": True},
        )
        include_plotly = False

        target_frame = result.detailed_series[target]
        si_figure, si_label = _si_figure(target_frame, series_result, target, go)
        si_html = si_figure.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={"displaylogo": False, "responsive": True},
        )
        diagnostics = pd.DataFrame(
            series_result.diagnostics.items(),
            columns=("Diagnostic", "Value"),
        )
        messages = pd.DataFrame(
            (
                {
                    "Type": message.type,
                    "Name": message.name,
                    "Origin": message.origin,
                    "Message": message.message,
                }
                for message in series_result.messages
            ),
            columns=("Type", "Name", "Origin", "Message"),
        )
        model = series_result.arima_model
        model_text = model.notation if model is not None else "Unavailable"
        model_source = (
            "automatic selection"
            if model is not None and model.automatic
            else "explicit or unavailable"
        )
        sections.append(
            f"""
            <section>
              <h2>{escape(str(target))}</h2>
              <p class="model"><strong>Model:</strong> {escape(model_text)}
              <span>{escape(model_source)}</span></p>
              {component_html}
              <p><strong>SI interpretation:</strong> {escape(si_label)}</p>
              {si_html}
              <details>
                <summary>Diagnostics ({len(diagnostics)})</summary>
                {_table(diagnostics)}
              </details>
              <details>
                <summary>Processing messages ({len(messages)})</summary>
                {_table(messages) if not messages.empty else '<p>No processing messages.</p>'}
              </details>
            </section>
            """
        )

    summary = result.to_summary_frame()
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Avenir, Helvetica, sans-serif; }}
    body {{ margin: 0; color: #182128; background: #f4f6f5; }}
    header {{ padding: 2rem max(1.5rem, 6vw); background: #12372a; color: white; }}
    header p {{ margin-bottom: 0; color: #d7e5df; }}
    main {{ width: min(1200px, calc(100% - 2rem)); margin: 2rem auto; }}
    section {{ margin: 2rem 0; padding: 1.25rem; background: white; border: 1px solid #d8dfdc; }}
    h1, h2 {{ letter-spacing: 0; }}
    .model span {{ margin-left: 0.75rem; color: #53635d; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
    th, td {{ padding: 0.55rem; border-bottom: 1px solid #d8dfdc; text-align: left; }}
    th {{ background: #edf2ef; }}
    details {{ margin-top: 1rem; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    @media (max-width: 700px) {{ main {{ width: calc(100% - 1rem); }} section {{ padding: 0.75rem; overflow-x: auto; }} }}
  </style>
</head>
<body>
  <header><h1>{escape(title)}</h1><p>Interactive JDemetra+ seasonal-adjustment review</p></header>
  <main>
    <section><h2>Batch summary</h2>{_table(summary)}</section>
    {''.join(sections)}
  </main>
</body>
</html>
"""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output


def _si_figure(frame: Any, result: Any, target: Any, go: Any) -> tuple[Any, str]:
    name = "decomposition.si_cmp"
    if name not in frame or not frame[name].notna().any():
        raise ValueError(f"SI output is unavailable for series: {target}")
    values = frame[name].dropna()
    multiplicative = bool(result.diagnostics.get("preprocessing.log", False))
    label = "SI ratio (original / trend)" if multiplicative else "SI component (original - trend)"
    baseline = 1 if multiplicative else 0
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=values.index,
            y=values,
            mode="lines",
            name=label,
            line={"color": "#b54708", "width": 2},
            hovertemplate=f"{label}: %{{y:,.4g}}<extra></extra>",
        )
    )
    figure.add_hline(y=baseline, line_color="#66717c", line_width=1)
    figure.update_layout(
        title={"text": f"{target}: {label}", "x": 0.01, "xanchor": "left"},
        height=360,
        margin={"l": 55, "r": 25, "t": 65, "b": 45},
        paper_bgcolor="#f7f9fa",
        plot_bgcolor="#ffffff",
        font={"color": "#182128", "family": "Avenir, Helvetica, sans-serif"},
        hovermode="x unified",
    )
    figure.update_xaxes(showgrid=True, gridcolor="#d3dae0")
    figure.update_yaxes(showgrid=True, gridcolor="#d3dae0", zeroline=False)
    return figure, label


def _table(frame: Any) -> str:
    return frame.to_html(index=False, border=0, classes="dataframe", na_rep="")


def _dependencies() -> tuple[Any, Any]:
    try:
        import pandas as pd
        import plotly.graph_objects as go
    except ImportError as error:
        raise ImportError("a reporting dependency is missing; reinstall demetrapy") from error
    return pd, go