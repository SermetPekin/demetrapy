from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Sequence

import jpype
import jpype.imports

JDEMETRA_VERSION = "2.2.6"
JAR_URL = (
    "https://repo1.maven.org/maven2/eu/europa/ec/joinup/sat/"
    f"demetra-tstoolkit/{JDEMETRA_VERSION}/demetra-tstoolkit-{JDEMETRA_VERSION}.jar"
)


def _jar_path() -> Path:
    configured = os.environ.get("SEASONAL_PRI_JAR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "seasonal-pri" / Path(JAR_URL).name


def _ensure_jvm() -> None:
    if jpype.isJVMStarted():
        return

    jar = _jar_path()
    if not jar.exists():
        jar.parent.mkdir(parents=True, exist_ok=True)
        temporary = jar.with_suffix(".tmp")
        urllib.request.urlretrieve(JAR_URL, temporary)
        temporary.replace(jar)
    jpype.startJVM(classpath=[str(jar)])


def adjust(
    values: Sequence[float],
    *,
    frequency: str = "Monthly",
    start_year: int,
    start_period: int = 1,
    spec: str = "RSA4",
    decomposition_mode: str | None = None,
    seasonal_filter: str | None = None,
    henderson_filter_length: int | None = None,
    lower_sigma: float | None = None,
    upper_sigma: float | None = None,
    forecast_horizon: int | None = None,
    backcast_horizon: int | None = None,
    benchmarking: bool = False,
) -> dict[str, list[float]]:
    """Seasonally adjust one regular series using a JDemetra+ X13 preset."""
    if not values:
        raise ValueError("values must not be empty")
    if start_period < 1:
        raise ValueError("start_period is one-based and must be positive")

    _ensure_jvm()
    TsData = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsData")
    TsFrequency = jpype.JClass("ec.tstoolkit.timeseries.simplets.TsFrequency")
    X13Specification = jpype.JClass("ec.satoolkit.x13.X13Specification")
    DecompositionMode = jpype.JClass("ec.satoolkit.DecompositionMode")
    SeasonalFilterOption = jpype.JClass("ec.satoolkit.x11.SeasonalFilterOption")
    X13ProcessingFactory = jpype.JClass(
        "ec.satoolkit.algorithm.implementation.X13ProcessingFactory"
    )

    try:
        java_frequency = getattr(TsFrequency, frequency)
    except AttributeError as error:
        raise ValueError(f"unsupported frequency: {frequency}") from error
    try:
        java_spec = getattr(X13Specification, spec).clone()
    except AttributeError as error:
        raise ValueError(f"unsupported X13 specification: {spec}") from error

    x11 = java_spec.getX11Specification()
    try:
        if decomposition_mode is not None:
            x11.setMode(getattr(DecompositionMode, decomposition_mode))
        if seasonal_filter is not None:
            x11.setSeasonalFilter(getattr(SeasonalFilterOption, seasonal_filter))
    except AttributeError as error:
        raise ValueError(f"unsupported X11 option: {error}") from error
    if henderson_filter_length is not None:
        x11.setHendersonFilterLength(henderson_filter_length)
    if lower_sigma is not None:
        x11.setLowerSigma(lower_sigma)
    if upper_sigma is not None:
        x11.setUpperSigma(upper_sigma)
    if forecast_horizon is not None:
        x11.setForecastHorizon(forecast_horizon)
    if backcast_horizon is not None:
        x11.setBackcastHorizon(backcast_horizon)
    java_spec.getBenchmarkingSpecification().setEnabled(benchmarking)

    data = TsData(
        java_frequency,
        start_year,
        start_period - 1,
        jpype.JArray(jpype.JDouble)(values),
        False,
    )
    results = X13ProcessingFactory.process(data, java_spec)

    output: dict[str, list[float]] = {}
    for name in ("y", "sa", "t", "s", "i"):
        series = results.getData(name, TsData.class_)
        if series is None:
            raise RuntimeError(f"JDemetra+ did not produce the '{name}' series")
        output[name] = [float(value) for value in series.internalStorage()]
    return output