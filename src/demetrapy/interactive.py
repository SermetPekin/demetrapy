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
        (1, f"{prefix}y", "Original", "#53616b", "solid", 1.6),
        (1, f"{prefix}sa", "Seasonally adjusted", "#00796b", "solid", 2.8),
        (1, f"{prefix}y_f", "Original forecast", "#53616b", "dot", 2.0),
        (1, f"{prefix}sa_f", "Adjusted forecast", "#00796b", "dot", 2.6),
        (2, f"{prefix}t", "Trend", "#0067a5", "solid", 2.4),
        (2, f"{prefix}t_f", "Trend forecast", "#0067a5", "dot", 2.4),
        (3, f"{prefix}s", "Seasonal", "#b54708", "solid", 2.0),
        (3, f"{prefix}s_f", "Seasonal forecast", "#b54708", "dot", 2.2),
        (4, f"{prefix}i", "Irregular", "#8e3b76", "solid", 1.8),
        (4, f"{prefix}i_f", "Irregular forecast", "#8e3b76", "dot", 2.0),
    )
    for row, name, label, color, dash, width in traces:
        _add_trace(figure, go, frame, row, name, label, color, dash, width)

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
                2.0,
            )

    forecast_names = [name for name in frame if str(name).endswith("_f")]
    forecast_values = [
        frame[name].dropna() for name in forecast_names if frame[name].notna().any()
    ]
    if forecast_values:
        forecast_start = min(values.index.min() for values in forecast_values)
        forecast_end = max(values.index.max() for values in forecast_values)
        for row in range(1, row_count + 1):
            figure.add_vrect(
                x0=forecast_start,
                x1=forecast_end,
                fillcolor="#dbece7",
                opacity=0.38,
                line_width=0,
                layer="below",
                row=row,
                col=1,
            )
            figure.add_vline(
                x=forecast_start,
                line_color="#397368",
                line_dash="dot",
                line_width=1.2,
                row=row,
                col=1,
            )
        figure.add_annotation(
            x=forecast_start,
            y=1.01,
            xref="x",
            yref="paper",
            text="Forecast",
            showarrow=False,
            xanchor="left",
            font={"size": 11, "color": "#285d54"},
        )

    for row in range(2, row_count + 1):
        figure.add_hline(y=0, line_color="#66717c", line_width=1, row=row, col=1)
    figure.update_xaxes(
        showgrid=True,
        gridcolor="#e2e7e5",
        linecolor="#81908a",
        rangeslider_visible=False,
        tickformat="%b\n%Y",
        hoverformat="%B %Y",
        showticklabels=True,
        showline=True,
        ticks="outside",
        tickcolor="#81908a",
    )
    figure.update_xaxes(title_text="Date", row=row_count, col=1)
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#e2e7e5",
        linecolor="#81908a",
        zeroline=False,
        showline=False,
        tickformat=",.4~g",
    )
    figure.update_layout(
        title={
            "text": title or (str(target) if target is not None else "Seasonal adjustment"),
            "x": 0.01,
            "xanchor": "left",
        },
        height=900 if effects else 780,
        margin={"l": 62, "r": 25, "t": 88, "b": 58},
        paper_bgcolor="#f7f9f8",
        plot_bgcolor="#ffffff",
        font={"color": "#182128", "family": "Avenir, Helvetica, sans-serif"},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#ffffff", "font_color": "#182128"},
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
    for annotation in figure.layout.annotations[:row_count]:
        annotation.update(
            x=0.01,
            xanchor="left",
            font={"size": 12, "color": "#41514b"},
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
    width: float,
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
            line={"color": color, "width": width, "dash": dash},
            hovertemplate=(
                f"<b>{label}</b><br>Date: %{{x|%B %Y}}<br>Value: %{{y:,.4g}}"
                "<extra></extra>"
            ),
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
            "a plotting dependency is missing; reinstall demetrapy"
        ) from error
    return go, make_subplots, pd
