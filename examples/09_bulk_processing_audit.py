"""Run independent adjustment jobs with durable success and failure records."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import pandas as pd

from demetrapy import (
    adjust_dataframe,
    load_monthly_retail,
    load_quarterly_production,
)


@dataclass(frozen=True)
class BatchJob:
    job_id: str
    company: str
    data: pd.DataFrame
    configuration: dict[str, Any]
    output_name: str


REPORT_FIELDS = (
    "run_id",
    "job_id",
    "company",
    "status",
    "started_at",
    "finished_at",
    "duration_seconds",
    "method",
    "specification",
    "input_rows",
    "output_rows",
    "diagnostic_count",
    "message_count",
    "warning_count",
    "error_message_count",
    "arima_models",
    "processing_messages",
    "output_file",
    "exception_type",
    "exception_message",
)


def create_jobs() -> list[BatchJob]:
    retail = load_monthly_retail()
    production = load_quarterly_production()
    return [
        BatchJob(
            job_id="retail-sales-x13",
            company="Northwind Retail",
            data=retail[["sales"]],
            configuration={
                "method": "x13",
                "spec": "RSA4",
                "calendar": {
                    "type": "WorkingDays",
                    "length_of_period": "LeapYear",
                    "test": "Add",
                },
                "forecast_horizon": 12,
            },
            output_name="northwind_sales.csv",
        ),
        BatchJob(
            job_id="retail-orders-tramoseats",
            company="Contoso Distribution",
            data=retail[["orders"]],
            configuration={
                "method": "tramoseats",
                "spec": "RSA4",
                "preprocessing": {"automodel": {"enabled": True}},
                "seats": {"prediction_length": 12},
            },
            output_name="contoso_orders.csv",
        ),
        BatchJob(
            job_id="production-quarterly-x13",
            company="Fabrikam Manufacturing",
            data=production,
            configuration={"method": "x13", "spec": "RSA4"},
            output_name="fabrikam_production.csv",
        ),
        BatchJob(
            job_id="invalid-dataframe-option",
            company="Configuration Failure Demo",
            data=retail[["sales"]],
            configuration={
                "method": "x13",
                "spec": "RSA4",
                "frequency": "Monthly",
            },
            output_name="invalid.csv",
        ),
    ]


def create_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("demetrapy.bulk_example")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    for handler in (
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def run_batch(jobs: list[BatchJob], output_directory: Path) -> list[dict[str, Any]]:
    output_directory.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())
    logger = create_logger(output_directory / "bulk_run.log")
    report_path = output_directory / "bulk_run_report.csv"
    records: list[dict[str, Any]] = []

    logger.info("BATCH_START run_id=%s jobs=%d", run_id, len(jobs))
    with report_path.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=REPORT_FIELDS)
        writer.writeheader()

        for job in jobs:
            started_at = datetime.now(timezone.utc)
            timer = perf_counter()
            logger.info(
                "JOB_START run_id=%s job_id=%s company=%r configuration=%s",
                run_id,
                job.job_id,
                job.company,
                json.dumps(job.configuration, sort_keys=True),
            )
            record = {
                "run_id": run_id,
                "job_id": job.job_id,
                "company": job.company,
                "status": "failed",
                "started_at": started_at.isoformat(),
                "method": job.configuration.get("method", "x13"),
                "specification": job.configuration.get("spec", "RSA4"),
                "input_rows": len(job.data),
                "output_rows": 0,
                "diagnostic_count": 0,
                "message_count": 0,
                "warning_count": 0,
                "error_message_count": 0,
                "arima_models": "[]",
                "processing_messages": "[]",
                "output_file": "",
                "exception_type": "",
                "exception_message": "",
            }

            try:
                result = adjust_dataframe(
                    job.data,
                    detailed=True,
                    **job.configuration,
                )
                output_path = output_directory / job.output_name
                adjusted = result.to_compact_frame()
                adjusted.to_csv(output_path)

                series_results = list(result.results.values())
                messages = [
                    {
                        "type": message.type,
                        "name": message.name,
                        "origin": message.origin,
                        "message": message.message,
                    }
                    for series_result in series_results
                    for message in series_result.messages
                ]
                message_types = [item["type"].lower() for item in messages]
                models = [
                    series_result.arima_model.notation
                    for series_result in series_results
                    if series_result.arima_model is not None
                ]
                record.update(
                    status="success",
                    output_rows=len(adjusted),
                    diagnostic_count=sum(
                        len(series_result.diagnostics)
                        for series_result in series_results
                    ),
                    message_count=len(messages),
                    warning_count=sum("warning" in item for item in message_types),
                    error_message_count=sum("error" in item for item in message_types),
                    arima_models=json.dumps(models),
                    processing_messages=json.dumps(messages),
                    output_file=str(output_path),
                )
                logger.info(
                    "JOB_SUCCESS run_id=%s job_id=%s rows=%d messages=%d output=%s",
                    run_id,
                    job.job_id,
                    len(adjusted),
                    len(messages),
                    output_path,
                )
            except Exception as error:
                record.update(
                    exception_type=type(error).__name__,
                    exception_message=str(error),
                )
                logger.exception(
                    "JOB_FAILED run_id=%s job_id=%s company=%r",
                    run_id,
                    job.job_id,
                    job.company,
                )

            record["finished_at"] = datetime.now(timezone.utc).isoformat()
            record["duration_seconds"] = round(perf_counter() - timer, 6)
            records.append(record)
            writer.writerow(record)
            report_file.flush()

    successful = sum(record["status"] == "success" for record in records)
    failed = len(records) - successful
    logger.info(
        "BATCH_END run_id=%s successful=%d failed=%d report=%s",
        run_id,
        successful,
        failed,
        report_path,
    )
    return records


def main() -> None:
    output_directory = Path("bulk_run_output")
    records = run_batch(create_jobs(), output_directory)
    successful = sum(record["status"] == "success" for record in records)
    failed = len(records) - successful

    print(f"\nBatch complete: {successful} successful, {failed} failed")
    print(f"Audit log: {output_directory / 'bulk_run.log'}")
    print(f"Run report: {output_directory / 'bulk_run_report.csv'}")

    assert successful == 3
    assert failed == 1


if __name__ == "__main__":
    main()