#!/usr/bin/env python3
"""Headless Chrome captures for the DDAY-B6 whole-factory overview."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
HOST = "127.0.0.1"
PORT = 18766
BASE = f"http://{HOST}:{PORT}"


def _http(method: str, path: str):
    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
        if path.endswith("/overview") or path == "/bottled-water-demo":
            return raw
        return json.loads(raw.decode("utf-8"))


def _wait_http(timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=2)
            return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("API did not become ready")


def _chrome() -> str:
    for candidate in (
        "google-chrome",
        "chromium",
        "chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ):
        path = shutil.which(candidate) if "/" not in candidate else candidate
        if path and Path(path).exists():
            return path
    raise RuntimeError("chrome/chromium not found")


def _screenshot(chrome: str, url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="bw-b6-chrome-"))
    try:
        try:
            subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--hide-scrollbars",
                    "--window-size=1600,1000",
                    "--remote-debugging-port=0",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=4000",
                    f"--screenshot={dest}",
                    url,
                ],
                check=False,
                timeout=25,
                cwd=REPO,
            )
        except subprocess.TimeoutExpired:
            pass
        if not dest.is_file() or dest.stat().st_size < 1000:
            raise RuntimeError(f"screenshot missing or empty: {dest}")
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _wait_phase(field: str, phase: str, timeout_s: float = 40.0) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        last = _http("GET", "/bottled-water-demo/factory")
        current = ((last.get(field) or {}).get("phase"))
        if current == phase:
            return last
        time.sleep(0.1)
    raise RuntimeError(f"did not reach {field}={phase}: {last.get(field)}")


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    server = subprocess.Popen(
        [
            sys.executable, "-c",
            (
                "from virtual_factory.ui.api import create_app; "
                "import uvicorn; "
                "app = create_app(factory_autorun=True, "
                "factory_tick_interval_s=0.01); "
                f"uvicorn.run(app, host='{HOST}', port={PORT}, log_level='warning')"
            ),
        ],
        cwd=REPO,
        env=env,
    )
    try:
        _wait_http()
        _http("POST", "/bottled-water-demo/reset")
        chrome = _chrome()
        _screenshot(chrome, f"{BASE}/bottled-water-demo/overview",
                    HERE / "10-visual-overview-stopped.png")
        _http("POST", "/bottled-water-demo/start")
        _wait_phase("scenario", "WARNING")
        _http("POST", "/bottled-water-demo/pause")
        time.sleep(0.3)
        _screenshot(chrome, f"{BASE}/bottled-water-demo/overview",
                    HERE / "10-visual-overview-abnormal.png")
        _screenshot(chrome, f"{BASE}/bottled-water-demo",
                    HERE / "10-visual-fp-drilldown.png")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
