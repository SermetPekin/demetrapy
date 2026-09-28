"""Streamlit dashboard for demetrapy."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any

from demetrapy.config import AdjustmentConfig, METHOD_SPECIFICATIONS, X11_OPTIONS
from demetrapy.dataframe import DataFrameAdjustmentResult, adjust_dataframe
from demetrapy.datasets import (
    load_industrial_production_with_calendars,
    load_monthly_industrial_production,
    load_monthly_retail,
    load_monthly_tourism,
    load_quarterly_production,
    load_retail_with_calendars,
    load_tourism_with_calendars,
)
from demetrapy.interactive import plot_adjustment_interactive


_DATA_SOURCES = (
    "Upload CSV",
    "Paste values",
    "Monthly retail",
    "Monthly tourism",
    "Monthly industrial production",
    "Quarterly production",
    "Retail with calendars",
    "Tourism with calendars",
    "Industrial production with calendars",
)

_PASTED_FREQUENCIES = ("Monthly", "Quarterly", "HalfYearly", "Yearly")

_PASTED_MONTHLY_EXAMPLE = """sales
100.2
104.1
108.8
112.3
109.7
106.4
102.5
99.1
97.3
98.4
101.6
105.9
101.1
105.3
109.6
113.0
110.8
107.2
103.1
100.4
98.0
99.5
102.8
107.1
102.4
106.0
110.7
114.2
111.5
108.3
104.0
101.2
99.4
100.1
103.5
108.0
103.2
107.4
111.6
115.1
112.7
109.0
105.2
102.1
100.3
101.4
104.6
109.2"""


def main() -> None:
    try:
        import pandas as pd
        import streamlit as st
    except ImportError as error:
        raise ImportError(
            "a dashboard dependency is missing; reinstall demetrapy"
        ) from error

    st.set_page_config(
        page_title="demetrapy", page_icon=":chart_with_upwards_trend:", layout="wide"
    )
    st.markdown(
        """
        <style>
                :root { --brand: #005f57; --ink: #182128; --border: #8fa19a; }
                .stApp { background: #f7f9f8; color: var(--ink); }
                [data-testid="stSidebar"] { background: #e4ece8; color: var(--ink); }
                [data-testid="stSidebar"] hr { border-color: var(--border); }
                [data-testid="stSidebar"] h1,
                [data-testid="stSidebar"] h2,
                [data-testid="stSidebar"] h3,
                [data-testid="stSidebar"] p,
                [data-testid="stSidebar"] label,
                [data-testid="stSidebar"] span {
                    color: var(--ink) !important;
                }
                [data-testid="stSidebar"] [data-baseweb="select"] > div,
                [data-testid="stFileUploaderDropzone"] {
                    background: #ffffff;
                    border-color: var(--border);
                    color: var(--ink);
                }
        h1, h2, h3 { letter-spacing: 0; }
        h1 { color: var(--ink); font-family: Georgia, serif; }
        [data-testid="stMetricValue"] { color: var(--brand); }
                .stButton > button[kind="primary"] {
                    background: var(--brand); border-color: #00443e; color: #ffffff;
                }
                [data-testid="stSidebar"] .stButton > button[kind="primary"] *,
                [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * {
                    color: #ffffff !important;
                }
                .stTabs [role="tablist"] { gap: 8px; }
                .stTabs [role="tab"] {
                    background: #dce7e2 !important;
                    border: 1px solid #71877e !important;
                    border-radius: 4px;
                    color: #182128 !important;
                    opacity: 1 !important;
                    padding: 8px 16px;
                    visibility: visible !important;
                }
                .stTabs [role="tab"] *,
                .stTabs [role="tab"] p,
                .stTabs [role="tab"] span {
                    color: #182128 !important;
                    opacity: 1 !important;
                    visibility: visible !important;
                }
                .stTabs [role="tab"][aria-selected="true"],
                .stTabs [role="tab"][aria-selected="true"] *,
                .stTabs [role="tab"][aria-selected="true"] p,
                .stTabs [role="tab"][aria-selected="true"] span {
                    background: var(--brand) !important;
                    border-color: #00443e !important;
                    color: #ffffff !important;
                    font-weight: 700;
                }
                .stTabs [data-baseweb="tab-highlight"] {
                    display: none;
                }
                .stDownloadButton > button,
                .stButton > button[kind="secondary"] {
                    background: #ffffff !important;
                    border: 1px solid #71877e !important;
                    color: var(--ink) !important;
                    opacity: 1 !important;
                }
                .stDownloadButton > button *,
                .stButton > button[kind="secondary"] * {
                    color: var(--ink) !important;
                    opacity: 1 !important;
                }
                [data-baseweb="select"] > div, [data-baseweb="input"] > div {
                    border-color: var(--border);
                }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("demetrapy")

    with st.sidebar:
        st.subheader("Inputs")
        data_source = st.selectbox("Data source", _DATA_SOURCES)
        data_upload = (
            st.file_uploader("Series CSV", type="csv")
            if data_source == "Upload CSV"
            else None
        )
        pasted_values = (
            st.text_area(
                "Series values",
                value=_PASTED_MONTHLY_EXAMPLE,
                help=(
                    "Enter one observation per row. Separate multiple series "
                    "with commas or spaces. A header row is optional; replace "
                    "the example values with your own data."
                ),
                height=240,
            )
            if data_source == "Paste values"
            else ""
        )
        pasted_frequency = (
            st.selectbox("Frequency", _PASTED_FREQUENCIES)
            if data_source == "Paste values"
            else "Monthly"
        )
        pasted_start = (
            st.date_input(
                "Start period",
                value=date(2015, 1, 1),
                help="The generated series begins on the first day of this period.",
            )
            if data_source == "Paste values"
            else date(2015, 1, 1)
        )
        config_upload = st.file_uploader("Configuration JSON (optional)", type="json")
        calendar_upload = (
            st.file_uploader("Calendar pool CSV (optional)", type="csv")
            if data_source == "Upload CSV"
            else None
        )

    if data_source == "Upload CSV" and data_upload is None:
        st.info("Upload a series CSV to begin.")
        return
    if data_source == "Paste values" and not pasted_values.strip():
        st.info("Paste series values to begin.")
        return

    try:
        if data_source == "Upload CSV":
            raw_data = pd.read_csv(data_upload)
            calendar_raw = pd.read_csv(calendar_upload) if calendar_upload else None
            sample_mapping: dict[Any, list[Any]] = {}
        elif data_source == "Paste values":
            raw_data = _pasted_frame(
                pasted_values,
                pasted_frequency,
                pasted_start,
                pd,
            )
            calendar_raw = None
            sample_mapping = {}
        else:
            raw_data, calendar_raw, sample_mapping = _sample_inputs(data_source)
        config = _uploaded_config(config_upload)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        st.error(str(error))
        return

    if raw_data.empty:
        st.error("Series CSV contains no observations.")
        return

    columns = list(raw_data.columns)
    configured_date = config.date_column if config.date_column in columns else columns[0]
    numeric_columns = [
        column
        for column in columns
        if column != configured_date and pd.api.types.is_numeric_dtype(raw_data[column])
    ]

    with st.sidebar:
        st.subheader("Series")
        date_column = st.selectbox(
            "Date column", columns, index=columns.index(configured_date)
        )
        targets = st.multiselect(
            "Target columns",
            [column for column in numeric_columns if column != date_column],
            default=[config.value_column]
            if config.value_column in numeric_columns
            else numeric_columns[:1],
        )
        st.subheader("Specification")
        method = st.radio(
            "Method",
            ("x13", "tramoseats"),
            index=0 if config.method == "x13" else 1,
            horizontal=True,
        )
        presets = METHOD_SPECIFICATIONS[method]
        default_spec = config.spec if config.spec in presets else "RSA4"
        specification = st.selectbox(
            "Preset", presets, index=presets.index(default_spec)
        )
        configured_arima = (config.preprocessing or {}).get("arima", {})
        arima_mode = "Automatic"
        explicit_arima = {}
        if specification == "RSAX11":
            st.caption("RSAX11 applies X11 decomposition without RegARIMA preprocessing.")
        else:
            arima_mode = st.radio(
                "ARIMA model",
                ("Automatic", "Explicit"),
                index=1 if configured_arima else 0,
                horizontal=True,
            )
        if specification != "RSAX11" and arima_mode == "Explicit":
            st.caption("Regular orders")
            regular_orders = st.columns(3)
            explicit_arima.update(
                {
                    name: int(
                        column.number_input(
                            name,
                            min_value=0,
                            max_value=5,
                            value=int(configured_arima.get(name, default)),
                        )
                    )
                    for name, default, column in zip(
                        ("p", "d", "q"), (0, 1, 1), regular_orders
                    )
                }
            )
            st.caption("Seasonal orders")
            seasonal_orders = st.columns(3)
            explicit_arima.update(
                {
                    name: int(
                        column.number_input(
                            name.upper(),
                            min_value=0,
                            max_value=2,
                            value=int(configured_arima.get(name, default)),
                        )
                    )
                    for name, default, column in zip(
                        ("bp", "bd", "bq"), (0, 1, 1), seasonal_orders
                    )
                }
            )
            explicit_arima["mean"] = st.checkbox(
                "Include mean",
                value=bool(configured_arima.get("mean", False)),
            )
        st.subheader("Processing")
        configured_transform = (config.preprocessing or {}).get("transform", {}).get(
            "function", "Auto"
        )
        transform_choices = ("Auto", "Log", "None")
        transform_function = st.selectbox(
            "Transformation",
            transform_choices,
            index=(
                transform_choices.index(configured_transform)
                if configured_transform in transform_choices
                else 0
            ),
            disabled=specification == "RSAX11",
        )
        configured_outlier_detection = (
            config.outlier_detection if config.method == method else None
        )
        detect_outliers = st.checkbox(
            "Detect outliers",
            value=configured_outlier_detection is not None,
            disabled=specification == "RSAX11",
        )
        outlier_types = st.multiselect(
            "Outlier types",
            ("AO", "LS", "TC"),
            default=(
                configured_outlier_detection.get("types", [])
                if configured_outlier_detection is not None
                else ["AO", "LS", "TC"]
            ),
            disabled=specification == "RSAX11" or not detect_outliers,
        )
        configured_forecast = (
            config.forecast_horizon
            if method == "x13"
            else (config.seats or {}).get("prediction_length")
        )
        forecast_horizon = int(
            st.number_input(
                "Forecast periods",
                min_value=0,
                max_value=120,
                value=int(configured_forecast if configured_forecast is not None else 12),
            )
        )

    profile = _input_profile(raw_data, date_column, targets, pd) if targets else None
    with st.expander("Data preview", expanded=False):
        if profile is None:
            st.warning("Select at least one target column to validate the input.")
        else:
            preview_metrics = st.columns(3)
            preview_metrics[0].metric("Observations", profile["observations"])
            preview_metrics[1].metric("Series", profile["series"])
            preview_metrics[2].metric("Frequency", profile["frequency"])
            date_range = (
                f"{profile['start']:%Y-%m} to {profile['end']:%Y-%m}"
                if profile["start"] is not None and profile["end"] is not None
                else "Unavailable"
            )
            st.caption(f"Date range: {date_range}")
            if profile["missing"] or profile["nonfinite"]:
                st.error(
                    f"Validation found {profile['missing']} missing or invalid values and "
                    f"{profile['nonfinite']} non-finite values."
                )
            elif profile["frequency"] == "Irregular":
                st.warning("Dates are not regularly spaced at a supported frequency.")
            elif (
                profile["recommended_minimum"] is not None
                and profile["observations"] < profile["recommended_minimum"]
            ):
                st.warning(
                    f"Only {profile['observations']} observations are available; "
                    f"at least {profile['recommended_minimum']} are recommended for "
                    f"{profile['frequency'].lower()} adjustment."
                )
            else:
                st.success("Validation passed: dates and selected values are complete.")
            st.dataframe(
                raw_data[[date_column, *targets]].head(12),
                width="stretch",
                hide_index=True,
            )

    calendar_date_column = None
    calendar_mapping: dict[Any, list[Any]] = {}
    if calendar_raw is not None:
        with st.sidebar:
            st.subheader("UserDefined calendar")
            calendar_date_column = st.selectbox(
                "Calendar date column", list(calendar_raw.columns)
            )
            calendar_columns = [
                column for column in calendar_raw.columns if column != calendar_date_column
            ]
            for target in targets:
                calendar_mapping[target] = st.multiselect(
                    f"Calendar columns for {target}",
                    calendar_columns,
                    default=[
                        column
                        for column in sample_mapping.get(target, ())
                        if column in calendar_columns
                    ],
                )

    with st.sidebar:
        run_adjustment = st.button(
            "Run adjustment",
            type="primary",
            width="stretch",
            disabled=(
                profile is None
                or bool(profile["missing"])
                or bool(profile["nonfinite"])
                or profile["frequency"] == "Irregular"
            ),
        )

    if run_adjustment:
        if not targets:
            st.error("Select at least one target column.")
        else:
            with st.status(
                "Recalculating adjustment...", expanded=False
            ) as calculation_status:
                try:
                    frame = _indexed_frame(raw_data, date_column, targets, pd)
                    calendar_pool = (
                        _indexed_frame(
                            calendar_raw,
                            calendar_date_column,
                            [
                                column
                                for column in calendar_raw.columns
                                if column != calendar_date_column
                            ],
                            pd,
                        )
                        if calendar_raw is not None
                        and calendar_date_column is not None
                        else None
                    )
                    ordinary_values = {
                        column: raw_data[column].astype(float).tolist()
                        for column in config.user_variable_columns()
                    }
                    options = _dashboard_engine_options(
                        config,
                        ordinary_values,
                        method=method,
                        specification=specification,
                        arima_mode=arima_mode,
                        explicit_arima=explicit_arima,
                        transform_function=transform_function,
                        forecast_horizon=forecast_horizon,
                        customize_outliers=detect_outliers,
                        outlier_types=outlier_types,
                    )
                    result = adjust_dataframe(
                        frame,
                        calendar_pool=calendar_pool,
                        user_defined_calendars=calendar_mapping,
                        method=method,
                        spec=specification,
                        detailed=True,
                        **options,
                    )
                    report_bytes = _html_report_bytes(result)
                    run_number = st.session_state.get("demetrapy_run_number", 0) + 1
                    history = list(st.session_state.get("demetrapy_run_history", []))
                    snapshot = _run_snapshot(
                        run_number,
                        result,
                        list(targets),
                        method=method,
                        specification=specification,
                        arima_mode=arima_mode,
                        transform_function=transform_function,
                        forecast_horizon=forecast_horizon,
                        detect_outliers=detect_outliers,
                        outlier_types=outlier_types,
                    )
                    history.append(snapshot)
                    st.session_state["demetrapy_result"] = result
                    st.session_state["demetrapy_targets"] = list(targets)
                    st.session_state["demetrapy_report"] = report_bytes
                    st.session_state["demetrapy_run_history"] = history[-10:]
                    st.session_state["demetrapy_history_selection"] = [
                        item["label"] for item in history[-2:]
                    ]
                    st.session_state["demetrapy_comparison"] = None
                    st.session_state["demetrapy_run_context"] = {
                        "frame": frame,
                        "calendar_pool": calendar_pool,
                        "calendar_mapping": calendar_mapping,
                        "method": method,
                        "specification": specification,
                        "options": options,
                        "arima_mode": arima_mode,
                        "explicit_arima": explicit_arima,
                        "transform_function": transform_function,
                        "forecast_horizon": forecast_horizon,
                        "detect_outliers": detect_outliers,
                        "outlier_types": outlier_types,
                    }
                    st.session_state["demetrapy_run_number"] = run_number
                    calculation_status.update(
                        label=f"Recalculated · run {run_number}", state="complete"
                    )
                except Exception as error:
                    calculation_status.update(
                        label="Recalculation failed", state="error"
                    )
                    st.error(str(error))

    result = st.session_state.get("demetrapy_result")
    result_targets = st.session_state.get("demetrapy_targets", [])
    if not isinstance(result, DataFrameAdjustmentResult) or not result_targets:
        return

    selected_target = st.selectbox("Displayed series", result_targets)
    target_result = result.for_series(selected_target)
    detailed_series = result.detailed_series
    if detailed_series is None:
        st.error("Detailed output is unavailable. Run the adjustment again.")
        return
    target_series = detailed_series[selected_target]
    model = target_result.arima_model
    metric_columns = st.columns(3)
    metric_columns[0].metric("Time-series outputs", len(target_series.columns))
    metric_columns[1].metric("Diagnostics", len(target_result.diagnostics))
    metric_columns[2].metric("Messages", len(target_result.messages))
    if model is not None:
        st.caption(
            f"ARIMA model: {model.notation} · Source: "
            + ("automatic model selection" if model.automatic else "explicit configuration")
        )
    else:
        st.caption("ARIMA model: unavailable")

    (
        overview_tab,
        data_tab,
        diagnostics_tab,
        messages_tab,
        summary_tab,
        history_tab,
        comparison_tab,
    ) = st.tabs(
        (
            "Overview",
            "Series",
            "Diagnostics",
            "Messages",
            "Batch Summary",
            "Run History",
            "Compare Methods",
        )
    )
    with overview_tab:
        figure = plot_adjustment_interactive(
            result,
            target=selected_target,
            title=(
                f"{selected_target} · {target_result.method} "
                f"{target_result.specification}"
            ),
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displaylogo": False, "scrollZoom": True},
        )
    with data_tab:
        output_names = list(target_series.columns)
        defaults = [
            name
            for name in (
                "final.y",
                "preprocessing.ycal",
                "final.sa",
                "final.t",
                "final.s",
                "final.i",
                "final.y_f",
                "preprocessing.ycal_f",
                "final.sa_f",
                "final.t_f",
                "final.s_f",
                "final.i_f",
            )
            if name in output_names
        ]
        selected_outputs = st.multiselect(
            "Outputs", output_names, default=defaults
        )
        displayed = target_series[selected_outputs].dropna(how="all")
        st.dataframe(displayed, width="stretch")
        st.download_button(
            "Download displayed series",
            displayed.to_csv().encode("utf-8"),
            file_name=f"{selected_target}-seasonal-adjustment.csv",
            mime="text/csv",
        )
    with diagnostics_tab:
        diagnostics = _diagnostics_frame(target_result.diagnostics, pd)
        st.dataframe(diagnostics, width="stretch", hide_index=True)
        st.download_button(
            "Download diagnostics",
            diagnostics.to_csv(index=False).encode("utf-8"),
            file_name=f"{selected_target}-diagnostics.csv",
            mime="text/csv",
        )
    with messages_tab:
        message_rows = [
            {
                "Type": message.type,
                "Name": message.name,
                "Origin": message.origin,
                "Message": message.message,
            }
            for message in target_result.messages
        ]
        if message_rows:
            st.dataframe(pd.DataFrame(message_rows), width="stretch", hide_index=True)
        else:
            st.success("No processing messages.")
    with summary_tab:
        summary = result.to_summary_frame()
        st.dataframe(summary, width="stretch", hide_index=True)
        summary_downloads = st.columns(3)
        summary_downloads[0].download_button(
            "Download batch summary",
            summary.to_csv(index=False).encode("utf-8"),
            file_name="demetrapy-batch-summary.csv",
            mime="text/csv",
            width="stretch",
        )
        report_bytes = st.session_state.get("demetrapy_report")
        if isinstance(report_bytes, bytes):
            summary_downloads[1].download_button(
                "Download HTML report",
                report_bytes,
                file_name="demetrapy-seasonal-adjustment-report.html",
                mime="text/html",
                width="stretch",
            )
        run_context = st.session_state.get("demetrapy_run_context")
        script_context_keys = {
            "frame",
            "calendar_pool",
            "calendar_mapping",
            "method",
            "specification",
            "options",
        }
        if (
            isinstance(run_context, dict)
            and script_context_keys.issubset(run_context)
        ):
            summary_downloads[2].download_button(
                "Download Python script",
                _python_script(
                    run_context["frame"],
                    method=run_context["method"],
                    specification=run_context["specification"],
                    options=run_context["options"],
                    calendar_pool=run_context["calendar_pool"],
                    calendar_mapping=run_context["calendar_mapping"],
                ).encode("utf-8"),
                file_name="demetrapy-latest-run.py",
                mime="text/x-python",
                width="stretch",
            )
    with history_tab:
        history = list(st.session_state.get("demetrapy_run_history", []))
        if not history:
            st.info("Successful adjustments from this browser session will appear here.")
        else:
            st.caption(
                f"{len(history)} saved run{'s' if len(history) != 1 else ''} · "
                "the 10 most recent runs are retained for this session."
            )
            history_rows = []
            for snapshot in reversed(history):
                history_rows.append(
                    {
                        "Run": snapshot["run_number"],
                        "Time": snapshot["created"].strftime("%H:%M:%S"),
                        **snapshot["settings"],
                        "Series": ", ".join(str(item) for item in snapshot["targets"]),
                    }
                )
            st.dataframe(pd.DataFrame(history_rows), width="stretch", hide_index=True)

            by_label = {snapshot["label"]: snapshot for snapshot in history}
            selected_runs = st.multiselect(
                "Runs to compare",
                list(reversed(by_label)),
                default=list(reversed(by_label))[:2],
                max_selections=2,
                key="demetrapy_history_selection",
            )
            action_columns = st.columns(2)
            action_columns[0].button(
                "Remove selected",
                disabled=not selected_runs,
                width="stretch",
                on_click=_remove_history_runs,
                args=(st.session_state, selected_runs),
            )
            action_columns[1].button(
                "Clear history",
                width="stretch",
                on_click=_clear_run_history,
                args=(st.session_state,),
            )

            if len(selected_runs) == 2:
                left, right = (by_label[label] for label in selected_runs)
                common_targets = [
                    target for target in left["targets"] if target in right["targets"]
                ]
                if common_targets:
                    history_target = st.selectbox(
                        "Series to compare",
                        common_targets,
                        key="demetrapy_history_target",
                    )
                    history_comparison, history_metrics, history_settings = (
                        _history_comparison(left, right, history_target, pd)
                    )
                    st.dataframe(history_settings, width="stretch", hide_index=True)
                    st.dataframe(history_metrics, width="stretch", hide_index=True)
                    st.line_chart(history_comparison.iloc[:, :2])
                    st.download_button(
                        "Download run comparison",
                        history_comparison.to_csv().encode("utf-8"),
                        file_name=f"{history_target}-run-comparison.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("The selected runs do not share a target series.")
    with comparison_tab:
        st.caption(
            "Compare X13 and TRAMO/SEATS seasonally adjusted series using "
            "the shared RSA4 preset and the current processing controls."
        )
        run_context = st.session_state.get("demetrapy_run_context")
        if st.button("Run method comparison", disabled=not isinstance(run_context, dict)):
            try:
                comparison_results = []
                with st.spinner("Running X13 and TRAMO/SEATS..."):
                    for comparison_method in ("x13", "tramoseats"):
                        comparison_options = _dashboard_engine_options(
                            AdjustmentConfig(),
                            {},
                            method=comparison_method,
                            specification="RSA4",
                            arima_mode=run_context["arima_mode"],
                            explicit_arima=run_context["explicit_arima"],
                            transform_function=run_context["transform_function"],
                            forecast_horizon=run_context["forecast_horizon"],
                            customize_outliers=run_context["detect_outliers"],
                            outlier_types=run_context["outlier_types"],
                        )
                        comparison_results.append(
                            adjust_dataframe(
                                run_context["frame"],
                                calendar_pool=run_context["calendar_pool"],
                                user_defined_calendars=run_context["calendar_mapping"],
                                method=comparison_method,
                                spec="RSA4",
                                **comparison_options,
                            )
                        )
                st.session_state["demetrapy_comparison"] = comparison_results
            except Exception as error:
                st.error(str(error))
        comparison_results = st.session_state.get("demetrapy_comparison")
        if (
            isinstance(comparison_results, list)
            and len(comparison_results) == 2
        ):
            comparison, comparison_metrics = _method_comparison(
                comparison_results[0],
                comparison_results[1],
                selected_target,
                pd,
            )
            st.dataframe(comparison_metrics, width="stretch", hide_index=True)
            st.line_chart(comparison[["x13", "tramoseats"]])
            st.download_button(
                "Download comparison",
                comparison.to_csv().encode("utf-8"),
                file_name=f"{selected_target}-method-comparison.csv",
                mime="text/csv",
            )


def _uploaded_config(upload: Any | None) -> AdjustmentConfig:
    if upload is None:
        return AdjustmentConfig()
    payload = json.loads(upload.getvalue().decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("configuration must be a JSON object")
    try:
        return AdjustmentConfig(**payload)
    except TypeError as error:
        raise ValueError(f"invalid configuration: {error}") from error


def _python_script(
    frame: Any,
    *,
    method: str,
    specification: str,
    options: dict[str, Any],
    calendar_pool: Any | None = None,
    calendar_mapping: dict[Any, list[Any]] | None = None,
) -> str:
    data_csv = frame.to_csv(date_format="%Y-%m-%dT%H:%M:%S")
    calendar_csv = (
        calendar_pool.to_csv(date_format="%Y-%m-%dT%H:%M:%S")
        if calendar_pool is not None
        else None
    )
    calendar_setup = (
        "calendar_pool = None"
        if calendar_csv is None
        else (
            f"CALENDAR_CSV = {calendar_csv!r}\n"
            "calendar_pool = pd.read_csv(\n"
            "    StringIO(CALENDAR_CSV), index_col=0, parse_dates=[0]\n"
            ")"
        )
    )
    mapping = calendar_mapping or {}
    return f'''"""Reproduce the latest successful demetrapy dashboard run."""

from io import StringIO

import pandas as pd

from demetrapy import adjust_dataframe


DATA_CSV = {data_csv!r}
OPTIONS = {options!r}
CALENDAR_MAPPING = {mapping!r}

frame = pd.read_csv(StringIO(DATA_CSV), index_col=0, parse_dates=[0])
{calendar_setup}

result = adjust_dataframe(
    frame,
    calendar_pool=calendar_pool,
    user_defined_calendars=CALENDAR_MAPPING,
    method={method!r},
    spec={specification!r},
    detailed=True,
    **OPTIONS,
)

result.to_compact_frame().to_csv("demetrapy-components.csv")
result.to_forecast_frame(compact=True).to_csv("demetrapy-forecasts.csv")
result.to_summary_frame().to_csv("demetrapy-summary.csv", index=False)
'''


def _sample_inputs(
    name: str,
) -> tuple[Any, Any | None, dict[Any, list[Any]]]:
    if name == "Monthly retail":
        return load_monthly_retail().reset_index(), None, {}
    if name == "Monthly tourism":
        return load_monthly_tourism().reset_index(), None, {}
    if name == "Monthly industrial production":
        return load_monthly_industrial_production().reset_index(), None, {}
    if name == "Quarterly production":
        return load_quarterly_production().reset_index(), None, {}
    if name == "Retail with calendars":
        dataset = load_retail_with_calendars()
    elif name == "Tourism with calendars":
        dataset = load_tourism_with_calendars()
    elif name == "Industrial production with calendars":
        dataset = load_industrial_production_with_calendars()
    else:
        raise ValueError(f"unknown sample dataset: {name}")
    return (
        dataset.observations.reset_index(),
        dataset.calendar_pool.reset_index(),
        {
            target: list(columns)
            for target, columns in dataset.selections.items()
        },
    )


def _pasted_frame(
    text: str,
    frequency: str,
    start_date: Any,
    pd: Any,
) -> Any:
    rows = [
        re.split(r"\s*,\s*|\s+", line.strip())
        for line in text.splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("pasted data contains no observations")
    width = len(rows[0])
    if not width or any(len(row) != width for row in rows):
        raise ValueError("every pasted row must contain the same number of values")

    first_row_is_numeric = [_is_number(value) for value in rows[0]]
    if all(first_row_is_numeric):
        columns = (
            ["value"]
            if width == 1
            else [f"series_{index}" for index in range(1, width + 1)]
        )
        value_rows = rows
    elif any(first_row_is_numeric):
        raise ValueError("the optional header row must contain only column names")
    else:
        columns = rows[0]
        value_rows = rows[1:]
        if len(columns) != len(set(columns)):
            raise ValueError("pasted column names must be unique")

    if len(value_rows) < 3:
        raise ValueError("pasted data needs at least three observations")
    try:
        values = [[float(value) for value in row] for row in value_rows]
    except ValueError as error:
        raise ValueError("pasted observations must contain only numbers") from error

    month_step = {
        "Monthly": 1,
        "Quarterly": 3,
        "HalfYearly": 6,
        "Yearly": 12,
    }.get(frequency)
    if month_step is None:
        raise ValueError(f"unsupported pasted-data frequency: {frequency}")
    start = pd.Timestamp(start_date).replace(day=1)
    dates = pd.DatetimeIndex(
        [
            start + pd.DateOffset(months=month_step * index)
            for index in range(len(values))
        ],
        name="date",
    )
    frame = pd.DataFrame(values, columns=columns, index=dates)
    return frame.reset_index()


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _indexed_frame(raw: Any, date_column: Any, value_columns: list[Any], pd: Any) -> Any:
    if raw is None or date_column not in raw:
        raise ValueError("date column is missing")
    missing = set(value_columns) - set(raw.columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(str(item) for item in missing))}")
    frame = raw[[date_column, *value_columns]].copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="raise")
    return frame.set_index(date_column)


def _diagnostics_frame(diagnostics: Any, pd: Any) -> Any:
    return pd.DataFrame(
        ((name, str(value)) for name, value in diagnostics.items()),
        columns=("Diagnostic", "Value"),
    )


def _model_preprocessing(
    preprocessing: Any,
    mode: str,
    explicit_arima: dict[str, Any],
    transform_function: str | None = None,
) -> dict[str, Any]:
    settings = dict(preprocessing or {})
    if transform_function is not None:
        transform = dict(settings.get("transform") or {})
        transform["function"] = transform_function
        settings["transform"] = transform
    if mode == "Explicit":
        settings["arima"] = dict(explicit_arima)
        return settings
    settings.pop("arima", None)
    automodel = dict(settings.get("automodel") or {})
    automodel["enabled"] = True
    settings["automodel"] = automodel
    return settings


def _dashboard_preprocessing(
    specification: str,
    preprocessing: Any,
    mode: str,
    explicit_arima: dict[str, Any],
    transform_function: str | None = None,
) -> dict[str, Any] | None:
    if specification == "RSAX11":
        return None
    return _model_preprocessing(
        preprocessing,
        mode,
        explicit_arima,
        transform_function,
    )


def _dashboard_engine_options(
    config: AdjustmentConfig,
    ordinary_values: dict[str, list[float]],
    *,
    method: str,
    specification: str,
    arima_mode: str,
    explicit_arima: dict[str, Any],
    transform_function: str,
    forecast_horizon: int,
    customize_outliers: bool,
    outlier_types: list[str],
) -> dict[str, Any]:
    options = config.engine_options(ordinary_values)
    for key in ("frequency", "method", "spec"):
        options.pop(key, None)

    if config.method != method:
        options["preprocessing"] = None
        options["calendar"] = None
        options["outlier_detection"] = None
        options["seats"] = None

    options["preprocessing"] = _dashboard_preprocessing(
        specification,
        options.get("preprocessing"),
        arima_mode,
        explicit_arima,
        transform_function,
    )
    if specification == "RSAX11":
        options["outlier_detection"] = None
    elif customize_outliers:
        outlier_detection = dict(options.get("outlier_detection") or {})
        outlier_detection["types"] = list(outlier_types)
        options["outlier_detection"] = outlier_detection
    elif not customize_outliers:
        options["outlier_detection"] = None

    if method == "x13":
        options["forecast_horizon"] = forecast_horizon
        options.pop("seats", None)
    else:
        for key in X11_OPTIONS:
            options.pop(key, None)
        seats = dict(options.get("seats") or {})
        seats["prediction_length"] = forecast_horizon
        options["seats"] = seats
    return options


def _input_profile(
    raw: Any,
    date_column: Any,
    targets: list[Any],
    pd: Any,
) -> dict[str, Any]:
    dates = pd.to_datetime(raw[date_column], errors="coerce")
    values = raw[targets].apply(pd.to_numeric, errors="coerce")
    valid_dates = dates.dropna()
    month_steps = set(
        valid_dates.dt.year.to_numpy()[1:] * 12
        + valid_dates.dt.month.to_numpy()[1:]
        - valid_dates.dt.year.to_numpy()[:-1] * 12
        - valid_dates.dt.month.to_numpy()[:-1]
    )
    frequency = {
        1: "Monthly",
        3: "Quarterly",
        6: "HalfYearly",
        12: "Yearly",
    }.get(next(iter(month_steps)), "Irregular") if len(month_steps) == 1 else "Irregular"
    minimums = {"Monthly": 36, "Quarterly": 12, "HalfYearly": 6, "Yearly": 3}
    return {
        "observations": len(raw),
        "series": len(targets),
        "frequency": frequency,
        "missing": int(values.isna().sum().sum() + dates.isna().sum()),
        "nonfinite": int(values.isin([float("inf"), float("-inf")]).sum().sum()),
        "start": valid_dates.min() if not valid_dates.empty else None,
        "end": valid_dates.max() if not valid_dates.empty else None,
        "recommended_minimum": minimums.get(frequency),
    }


def _method_comparison(
    first: DataFrameAdjustmentResult,
    second: DataFrameAdjustmentResult,
    target: Any,
    pd: Any,
) -> tuple[Any, Any]:
    by_method = {
        first.for_series(target).method: first.to_compact_frame()[target]["sa"],
        second.for_series(target).method: second.to_compact_frame()[target]["sa"],
    }
    comparison = pd.concat(by_method, axis=1).dropna()
    difference = comparison["x13"] - comparison["tramoseats"]
    comparison["difference"] = difference
    metrics = pd.DataFrame(
        {
            "Metric": ("RMSE", "Maximum absolute difference", "Correlation"),
            "Value": (
                float((difference.pow(2).mean()) ** 0.5),
                float(difference.abs().max()),
                float(comparison["x13"].corr(comparison["tramoseats"])),
            ),
        }
    )
    return comparison, metrics


def _run_snapshot(
    run_number: int,
    result: DataFrameAdjustmentResult,
    targets: list[Any],
    *,
    method: str,
    specification: str,
    arima_mode: str,
    transform_function: str,
    forecast_horizon: int,
    detect_outliers: bool,
    outlier_types: list[str],
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    created = timestamp or datetime.now()
    label = f"Run {run_number} · {method}/{specification} · {created:%H:%M:%S}"
    return {
        "run_number": run_number,
        "label": label,
        "created": created,
        "result": result,
        "targets": list(targets),
        "settings": {
            "Method": method,
            "Preset": specification,
            "ARIMA": arima_mode,
            "Transformation": transform_function,
            "Forecast periods": forecast_horizon,
            "Outliers": ", ".join(outlier_types) if detect_outliers else "Disabled",
        },
    }


def _history_comparison(
    left: dict[str, Any],
    right: dict[str, Any],
    target: Any,
    pd: Any,
) -> tuple[Any, Any, Any]:
    left_series = left["result"].to_compact_frame()[target]["sa"]
    right_series = right["result"].to_compact_frame()[target]["sa"]
    comparison = pd.concat(
        {left["label"]: left_series, right["label"]: right_series},
        axis=1,
    ).dropna()
    difference = comparison.iloc[:, 0] - comparison.iloc[:, 1]
    comparison["difference"] = difference
    metrics = pd.DataFrame(
        {
            "Metric": ("RMSE", "Maximum absolute difference", "Correlation"),
            "Value": (
                float((difference.pow(2).mean()) ** 0.5),
                float(difference.abs().max()),
                float(comparison.iloc[:, 0].corr(comparison.iloc[:, 1])),
            ),
        }
    )
    setting_names = list(left["settings"])
    settings = pd.DataFrame(
        {
            "Setting": setting_names,
            left["label"]: [str(left["settings"][name]) for name in setting_names],
            right["label"]: [str(right["settings"].get(name, "")) for name in setting_names],
        }
    )
    return comparison, metrics, settings


def _remove_history_runs(state: Any, labels: list[str]) -> None:
    selected = set(labels)
    state["demetrapy_run_history"] = [
        snapshot
        for snapshot in state.get("demetrapy_run_history", [])
        if snapshot["label"] not in selected
    ]
    state["demetrapy_history_selection"] = []


def _clear_run_history(state: Any) -> None:
    state["demetrapy_run_history"] = []
    state["demetrapy_history_selection"] = []


def _html_report_bytes(result: DataFrameAdjustmentResult) -> bytes:
    with TemporaryDirectory() as directory:
        path = result.to_html_report(
            Path(directory) / "demetrapy-report.html",
            title="demetrapy Seasonal Adjustment Review",
        )
        return path.read_bytes()


def launch() -> None:
    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError as error:
        raise ImportError(
            "a dashboard dependency is missing; reinstall demetrapy"
        ) from error
    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).resolve()),
        "--theme.base=light",
        "--theme.primaryColor=#005f57",
        "--theme.backgroundColor=#f7f9f8",
        "--theme.secondaryBackgroundColor=#e4ece8",
        "--theme.textColor=#182128",
        *sys.argv[1:],
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
