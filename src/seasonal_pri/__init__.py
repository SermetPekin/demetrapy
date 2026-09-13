"""Python access to JDemetra+ seasonal adjustment."""

from .engine import AdjustmentResult, OutputSeries, ProcessingMessage, adjust
from .dataframe import DataFrameAdjustmentResult, adjust_dataframe
from .interactive import plot_adjustment_interactive
from .plotting import plot_adjustment

__all__ = [
	"AdjustmentResult",
	"DataFrameAdjustmentResult",
	"OutputSeries",
	"ProcessingMessage",
	"adjust",
	"adjust_dataframe",
	"plot_adjustment",
	"plot_adjustment_interactive",
]
