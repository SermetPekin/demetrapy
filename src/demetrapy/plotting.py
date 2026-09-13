"""Optional Matplotlib visualizations for seasonal-adjustment results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .dataframe import DataFrameAdjustmentResult, _output_frame
from .engine import AdjustmentResult


def plot_adjustment(
    result: Any,
    *,
    target: Any | None = None,
    index: Sequence[Any] | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (12.0, 10.0),
) -> Any:
    """Return a GUI-style Matplotlib overview without displaying it."""
    plt, pd = _plot_dependencies()
    frame, target = _result_frame(result, target, index, pd)
    names = set(frame.columns)
    prefix = "final." if "final.y" in names else ""
    effects = [
        name
        for name in ("preprocessing.cal", "preprocessing.reg", "preprocessing.out")
        if name in names and frame[name].fillna(0).ne(0).any()
    ]
    row_count = 5 if effects else 4
    figure, axes = plt.subplots(
        row_count,
        1,
        figsize=figsize,
        sharex=True,
        layout="constrained",
        height_ratios=[2.0, 1.0, 1.0, 1.0, 1.0][:row_count],
    )

    _plot_if_present(axes[0], frame, f"{prefix}y", "Original", "#20252b")
    _plot_if_present(axes[0], frame, f"{prefix}sa", "Seasonally adjusted", "#00796b")
    _plot_if_present(
        axes[0], frame, f"{prefix}y_f", "Original forecast", "#20252b", "--"
    )
    _plot_if_present(
        axes[0], frame, f"{prefix}sa_f", "Adjusted forecast", "#00796b", "--"
    )
    axes[0].set_title(title or (str(target) if target is not None else "Seasonal adjustment"))
    axes[0].legend(loc="best", ncols=2)

    panels = (
        (axes[1], f"{prefix}t", f"{prefix}t_f", "Trend", "#0067a5"),
        (axes[2], f"{prefix}s", f"{prefix}s_f", "Seasonal", "#b54708"),
        (axes[3], f"{prefix}i", f"{prefix}i_f", "Irregular", "#8e3b76"),
    )
    for axis, observed, forecast, label, color in panels:
        _plot_if_present(axis, frame, observed, label, color)
        _plot_if_present(axis, frame, forecast, f"{label} forecast", color, "--")
        axis.set_ylabel(label)
        axis.axhline(0, color="#66717c", linewidth=1.0, zorder=0)

    if effects:
        colors = ("#6f42c1", "#7a4e00", "#3f5d67")
        for name, color in zip(effects, colors):
            _plot_if_present(axes[4], frame, name, name.removeprefix("preprocessing."), color)
        axes[4].set_ylabel("Effects")
        axes[4].axhline(0, color="#66717c", linewidth=1.0, zorder=0)
        axes[4].legend(loc="best", ncols=3)

    axes[-1].set_xlabel(frame.index.name or "Period")
    for axis in axes:
        axis.set_facecolor("#ffffff")
        axis.tick_params(colors="#252b31")
        axis.xaxis.label.set_color("#252b31")
        axis.yaxis.label.set_color("#252b31")
        axis.grid(axis="y", color="#c5ced6", linewidth=0.8)
        axis.spines["left"].set_color("#66717c")
        axis.spines["bottom"].set_color("#66717c")
        axis.spines[["top", "right"]].set_visible(False)
    figure.patch.set_facecolor("#f7f9fa")
    return figure


def _result_frame(
    result: Any,
    target: Any | None,
    index: Sequence[Any] | None,
    pd: Any,
) -> tuple[Any, Any | None]:
    if isinstance(result, DataFrameAdjustmentResult):
        frame = result.series
    elif isinstance(result, AdjustmentResult):
        frame = _output_frame(result, pd)
    else:
        frame = result
    if isinstance(frame, Mapping):
        plot_index = pd.to_datetime(index) if index is not None else index
        frame = pd.DataFrame(frame, index=plot_index)
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("result must be an adjustment mapping or DataFrame result")
    if isinstance(frame.columns, pd.MultiIndex):
        targets = list(dict.fromkeys(frame.columns.get_level_values(0)))
        if target is None:
            if len(targets) != 1:
                raise ValueError("target is required for a multi-series result")
            target = targets[0]
        if target not in targets:
            raise ValueError(f"unknown plot target: {target}")
        frame = frame[target]
    elif target is not None:
        raise ValueError("target is only valid for a multi-series result")
    return frame, target


def _plot_if_present(
    axis: Any,
    frame: Any,
    name: str,
    label: str,
    color: str,
    linestyle: str = "-",
) -> None:
    if name in frame and frame[name].notna().any():
        axis.plot(
            frame.index,
            frame[name],
            label=label,
            color=color,
            linestyle=linestyle,
            linewidth=2.0 if linestyle != "-" else 1.75,
        )


def _plot_dependencies() -> tuple[Any, Any]:
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError as error:
        raise ImportError(
            "a plotting dependency is missing; reinstall demetrapy"
        ) from error
    return plt, pd
