"""Interactive Plotly visualizations for detailed adjustment results."""

from __future__ import annotations

from typing import Any

from .plotting import _result_frame


def plot_adjustment_interactive(
    result: Any,
    *,
    target: Any | None = None,
    title: str | None = None,
) -> Any:
    """Return an interactive Plotly component overview."""
    go, make_subplots, pd = _dependencies()
    frame, target = _result_frame(result, target, None, pd)
    names = set(frame.columns)
    prefix = "final." if "final.y" in names else ""
    effects = [
        name
        for name in ("preprocessing.cal", "preprocessing.reg", "preprocessing.out")
        if name in names and frame[name].fillna(0).ne(0).any()
    ]
    row_count = 5 if effects else 4
    labels = ["Series", "Trend", "Seasonal", "Irregular"]
    if effects:
        labels.append("Effects")
    figure = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.045,
        row_heights=[0.36, 0.2, 0.2, 0.2, 0.18][:row_count],
        subplot_titles=labels,
    )

    traces = (
        (1, f"{prefix}y", "Original", "#20252b", "solid"),
        (1, f"{prefix}sa", "Seasonally adjusted", "#00796b", "solid"),
        (1, f"{prefix}y_f", "Original forecast", "#20252b", "dash"),
        (1, f"{prefix}sa_f", "Adjusted forecast", "#00796b", "dash"),
        (2, f"{prefix}t", "Trend", "#0067a5", "solid"),
        (2, f"{prefix}t_f", "Trend forecast", "#0067a5", "dash"),
        (3, f"{prefix}s", "Seasonal", "#b54708", "solid"),
        (3, f"{prefix}s_f", "Seasonal forecast", "#b54708", "dash"),
        (4, f"{prefix}i", "Irregular", "#8e3b76", "solid"),
        (4, f"{prefix}i_f", "Irregular forecast", "#8e3b76", "dash"),
    )
    for row, name, label, color, dash in traces:
        _add_trace(figure, go, frame, row, name, label, color, dash)

    if effects:
        effect_colors = ("#6f42c1", "#7a4e00", "#3f5d67")
        for name, color in zip(effects, effect_colors):
            _add_trace(
                figure,
                go,
                frame,
                5,
                name,
                name.removeprefix("preprocessing."),
                color,
                "solid",
            )

    for row in range(2, row_count + 1):
        figure.add_hline(y=0, line_color="#66717c", line_width=1, row=row, col=1)
    figure.update_xaxes(
        showgrid=True,
        gridcolor="#d3dae0",
        linecolor="#66717c",
        rangeslider_visible=False,
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#d3dae0",
        linecolor="#66717c",
        zeroline=False,
    )
    figure.update_layout(
        title={
            "text": title or (str(target) if target is not None else "Seasonal adjustment"),
            "x": 0.01,
            "xanchor": "left",
        },
        height=900 if effects else 780,
        margin={"l": 55, "r": 25, "t": 75, "b": 45},
        paper_bgcolor="#f7f9fa",
        plot_bgcolor="#ffffff",
        font={"color": "#182128", "family": "Avenir, Helvetica, sans-serif"},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#8fa19a",
            "borderwidth": 1,
        },
    )
    return figure


def _add_trace(
    figure: Any,
    go: Any,
    frame: Any,
    row: int,
    name: str,
    label: str,
    color: str,
    dash: str,
) -> None:
    if name not in frame or not frame[name].notna().any():
        return
    values = frame[name].dropna()
    figure.add_trace(
        go.Scatter(
            x=values.index,
            y=values,
            mode="lines",
            name=label,
            line={"color": color, "width": 2.4 if dash == "dash" else 2, "dash": dash},
            hovertemplate=f"{label}: %{{y:,.4g}}<extra></extra>",
        ),
        row=row,
        col=1,
    )


def _dependencies() -> tuple[Any, Any, Any]:
    try:
        import pandas as pd
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as error:
        raise ImportError(
            "interactive plotting requires pandas and plotly; install seasonal-pri[dashboard]"
        ) from error
    return go, make_subplots, pd
