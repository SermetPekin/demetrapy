"""Streamlit dashboard for demetrapy."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from demetrapy.config import AdjustmentConfig
from demetrapy.dataframe import DataFrameAdjustmentResult, adjust_dataframe
from demetrapy.interactive import plot_adjustment_interactive


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
        data_upload = st.file_uploader("Series CSV (required)", type="csv")
        config_upload = st.file_uploader("Configuration JSON (optional)", type="json")
        calendar_upload = st.file_uploader("Calendar pool CSV (optional)", type="csv")

    if data_upload is None:
        st.info("Upload a series CSV to begin.")
        return

    try:
        raw_data = pd.read_csv(data_upload)
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
        presets = (
            ("RSAX11", "RSA0", "RSA1", "RSA2", "RSA3", "RSA4", "RSA5")
            if method == "x13"
            else ("RSA0", "RSA1", "RSA2", "RSA3", "RSA4", "RSA5", "RSAfull")
        )
        default_spec = config.spec if config.spec in presets else "RSA4"
        specification = st.selectbox(
            "Preset", presets, index=presets.index(default_spec)
        )
        configured_arima = (config.preprocessing or {}).get("arima", {})
        arima_mode = st.radio(
            "ARIMA model",
            ("Automatic", "Explicit"),
            index=1 if configured_arima else 0,
            horizontal=True,
        )
        explicit_arima = {}
        if arima_mode == "Explicit":
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

    calendar_raw = None
    calendar_date_column = None
    calendar_mapping: dict[Any, list[Any]] = {}
    if calendar_upload is not None:
        try:
            calendar_raw = pd.read_csv(calendar_upload)
        except (OSError, ValueError) as error:
            st.error(str(error))
            return
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
                    f"Calendar columns for {target}", calendar_columns
                )

    with st.sidebar:
        run_adjustment = st.button(
            "Run adjustment", type="primary", width="stretch"
        )

    if run_adjustment:
        if not targets:
            st.error("Select at least one target column.")
        else:
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
                    if calendar_raw is not None and calendar_date_column is not None
                    else None
                )
                ordinary_values = {
                    column: raw_data[column].astype(float).tolist()
                    for column in config.user_variable_columns()
                }
                options = config.engine_options(ordinary_values)
                for key in ("frequency", "method", "spec"):
                    options.pop(key, None)
                options["preprocessing"] = _model_preprocessing(
                    options.get("preprocessing"),
                    arima_mode,
                    explicit_arima,
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
                st.session_state["demetrapy_result"] = result
                st.session_state["demetrapy_targets"] = list(targets)
            except Exception as error:
                st.error(str(error))

    result = st.session_state.get("demetrapy_result")
    result_targets = st.session_state.get("demetrapy_targets", [])
    if not isinstance(result, DataFrameAdjustmentResult) or not result_targets:
        return

    selected_target = st.selectbox("Displayed series", result_targets)
    model = result.arima_models.get(selected_target)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Time-series outputs", len(result.series[selected_target].columns))
    metric_columns[1].metric("Diagnostics", len(result.diagnostics[selected_target]))
    metric_columns[2].metric("Messages", len(result.messages[selected_target]))
    metric_columns[3].metric("ARIMA model", model.notation if model else "Unavailable")
    if model is not None:
        st.caption(
            "ARIMA source: "
            + ("automatic model selection" if model.automatic else "explicit configuration")
        )

    overview_tab, data_tab, diagnostics_tab, messages_tab = st.tabs(
        ("Overview", "Series", "Diagnostics", "Messages")
    )
    with overview_tab:
        figure = plot_adjustment_interactive(result, target=selected_target)
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displaylogo": False, "scrollZoom": True},
        )
    with data_tab:
        output_names = list(result.series[selected_target].columns)
        defaults = [
            name
            for name in ("final.y", "final.sa", "final.t", "final.s", "final.i", "final.sa_f")
            if name in output_names
        ]
        selected_outputs = st.multiselect(
            "Outputs", output_names, default=defaults
        )
        displayed = result.series[selected_target][selected_outputs].dropna(how="all")
        st.dataframe(displayed, width="stretch")
        st.download_button(
            "Download displayed series",
            displayed.to_csv().encode("utf-8"),
            file_name=f"{selected_target}-seasonal-adjustment.csv",
            mime="text/csv",
        )
    with diagnostics_tab:
        diagnostics = _diagnostics_frame(result.diagnostics[selected_target], pd)
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
            for message in result.messages[selected_target]
        ]
        if message_rows:
            st.dataframe(pd.DataFrame(message_rows), width="stretch", hide_index=True)
        else:
            st.success("No processing messages.")


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
) -> dict[str, Any]:
    settings = dict(preprocessing or {})
    if mode == "Explicit":
        settings["arima"] = dict(explicit_arima)
        return settings
    settings.pop("arima", None)
    automodel = dict(settings.get("automodel") or {})
    automodel["enabled"] = True
    settings["automodel"] = automodel
    return settings


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
