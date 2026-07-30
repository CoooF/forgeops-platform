from __future__ import annotations

import logging
import sys

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from pythonjsonlogger.json import JsonFormatter


def configure_observability(service_name: str, log_level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(
            TracerProvider(resource=Resource.create({"service.name": service_name}))
        )
