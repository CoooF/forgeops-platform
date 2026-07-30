from __future__ import annotations

import base64
import json
import multiprocessing
import os
import time
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = int(os.environ.get("FORGEOPS_SMOKE_PORT", "18080"))
BASE_URL = f"http://{HOST}:{PORT}"
DATABASE_PATH = ROOT / ".local" / "standalone-smoke.db"
DATABASE_URL = f"sqlite+pysqlite:///{DATABASE_PATH}"
HEADERS = {
    "Content-Type": "application/json",
    "X-ForgeOps-Actor": "standalone-smoke",
    "X-Trace-ID": "standalone-smoke-trace",
}


def run_server() -> None:
    import uvicorn

    from forgeops.api import create_app
    from forgeops.config import Settings

    settings = Settings(database_url=DATABASE_URL, object_store_path=str(ROOT / ".local/objects"))
    uvicorn.run(create_app(settings), host=HOST, port=PORT, log_level="warning")


def request_json(path: str, *, method: str = "GET", body: object | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    request = Request(  # noqa: S310 - fixed loopback URL
        f"{BASE_URL}{path}", data=data, headers=HEADERS, method=method
    )
    with urlopen(request, timeout=5) as response:  # noqa: S310 - fixed loopback URL
        return json.loads(response.read())


def wait_until_ready() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            response = request_json("/health/ready")
            if response == {"status": "ready", "database": "migrated"}:
                return
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("standalone API did not become ready")


def start_server() -> BaseProcess:
    process = multiprocessing.get_context("spawn").Process(target=run_server)
    process.start()
    wait_until_ready()
    return process


def stop_server(process: BaseProcess) -> None:
    process.terminate()
    process.join(timeout=10)
    if process.is_alive():
        raise RuntimeError("standalone API did not terminate")


def manifest_submission() -> dict[str, object]:
    package_root = ROOT / "scenario-packages/steel-cord-scheduling"
    return {
        "manifest": json.loads((package_root / "manifest.json").read_text()),
        "artifactPayloadBase64": base64.b64encode(
            (package_root / "artifact.json").read_bytes()
        ).decode(),
    }


def main() -> None:
    os.environ["FORGEOPS_DATABASE_URL"] = DATABASE_URL
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")

    first = start_server()
    try:
        status = request_json("/v1/platform/status")
        installed = request_json(
            "/v1/scenario-package-installations",
            method="POST",
            body=manifest_submission(),
        )
        installation_id = installed["installationId"]
    finally:
        stop_server(first)

    second = start_server()
    try:
        installations = request_json("/v1/scenario-package-installations")
        persisted = any(item["installationId"] == installation_id for item in installations)
        if not persisted:
            raise RuntimeError("installation state was not persisted across API restart")
    finally:
        stop_server(second)

    evidence = {
        "testId": "TEST-OPS-API-SMOKE-001",
        "requirementIds": ["REQ-PKG-001", "REQ-OPS-001"],
        "scope": status["scope"],
        "enterpriseApproval": status["enterpriseApproval"],
        "installationId": installation_id,
        "persistedAcrossRestart": persisted,
        "database": str(DATABASE_PATH.relative_to(ROOT)),
        "passed": True,
    }
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
