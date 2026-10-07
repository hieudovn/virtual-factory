#!/usr/bin/env python3
"""DDAY-B3 — deterministic browser evidence for the Bottled Water 2D skin.

Task: DDAY-B3 (SA Issue #104 / PR #101).

Drives the real page in a real browser against the real app, and captures:

  01 target-line normal operation (line running, bottles on the line)
  02 paused state
  03 stopped-after-reset state
  04 inspection checkpoint selected (station inspector open, PASS badge)
  05 bottle selected (unit inspector open)
  06 failing inspection -> reject observed on the line
  07 station inspector during a reject

Plus a machine-readable vocabulary scan of the fully rendered page, so the
"no foreign-line visual vocabulary" claim is verified against what the browser
actually rendered rather than against the source files.

Usage:
    python capture_visual_evidence.py --port 8123 [--fail-port 8124]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CHROMIUM = Path(
    r"C:\Users\dotru\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
)
EVIDENCE_DIR = Path(__file__).resolve().parent
SHOTS = EVIDENCE_DIR / "screenshots"

INSPECTION = "BW-FP-INS01"
FORBIDDEN = ("assy", "tipa", "pre-assy", "sso2", "rso2", "ap05_jam")
FORBIDDEN_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN]
FORBIDDEN_PATTERNS.append(re.compile(r"\bAP\d{2}\b"))

SCAN_SCRIPT = """
() => {
  const text = [];
  document.querySelectorAll('*').forEach((el) => {
    if (el.children.length === 0 && el.textContent.trim()) text.push(el.textContent.trim());
  });
  const assets = [];
  document.querySelectorAll('link[href], script[src]').forEach((el) => {
    assets.push(el.getAttribute('href') || el.getAttribute('src'));
  });
  const svgText = Array.from(document.querySelectorAll('svg text')).map((t) => t.textContent);
  return {
    visibleText: text,
    svgText,
    assetRefs: assets,
    bodyClasses: document.body.className,
    svgViewBox: document.getElementById('bw-svg').getAttribute('viewBox'),
    stationCount: document.querySelectorAll('#bw-stations .bw-station').length,
    bottleCount: document.querySelectorAll('#bw-bottles .bw-bottle').length,
    buttons: Array.from(document.querySelectorAll('button')).map((b) => b.textContent.trim()),
    facts: {
      run: document.getElementById('bw-run-state').textContent,
      operating: document.getElementById('bw-operating-state').textContent,
      time: document.getElementById('bw-sim-time').textContent,
      dwell: document.getElementById('bw-dwell').textContent,
      total: document.getElementById('bw-total').textContent,
      good: document.getElementById('bw-good').textContent,
      reject: document.getElementById('bw-reject').textContent,
      onLine: document.getElementById('bw-on-line').textContent,
      inspection: document.getElementById('bw-inspection').textContent,
      simNote: document.getElementById('bw-sim-note').textContent,
    },
    popupOpen: !document.getElementById('bw-popup').classList.contains('bw-hidden'),
    popupTitle: document.getElementById('bw-popup-title').textContent,
    popupBody: document.getElementById('bw-popup-body').innerText,
    eventCount: document.getElementById('bw-events-count').textContent,
  };
}
"""


def scan(page) -> dict:
    return page.evaluate(SCAN_SCRIPT)


def vocabulary_hits(payload: dict) -> list[str]:
    hits: list[str] = []
    for group in ("visibleText", "svgText", "assetRefs"):
        for text in payload.get(group, []):
            for pattern in FORBIDDEN_PATTERNS:
                match = pattern.search(text)
                if match:
                    hits.append(f"{group}: {match.group(0)!r} in {text!r}")
    body = payload.get("popupBody", "")
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(body)
        if match:
            hits.append(f"popupBody: {match.group(0)!r}")
    return hits


def shot(page, name: str) -> str:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / name
    page.screenshot(path=str(path))
    return f"{name} ({path.stat().st_size} bytes)"


def reset_line(port: int) -> None:
    """Put the line into its known initial state before UI interaction."""
    import urllib.request

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/bottled-water-demo/reset", method="POST")
    with urllib.request.urlopen(request, timeout=20):
        pass


def click_target(page, selector: str, expect_closest: str) -> dict:
    """Click an SVG target at its real on-screen location and prove the hit.

    Coordinate click (a genuine user-level click) plus a
    document.elementFromPoint proof. Playwright's actionability scan is
    unreliable on a continuously re-transformed SVG scene, where a group's
    bounding-box centre can legitimately fall outside the drawn shape.
    """
    box = page.locator(selector).first.bounding_box()
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    proof = page.evaluate(
        "([x, y, sel]) => { const el = document.elementFromPoint(x, y);"
        " const near = el && el.closest ? el.closest(sel) : null;"
        " return { tag: el ? el.tagName : 'none',"
        " cls: el ? (el.getAttribute('class') || '') : '',"
        " matched: !!near }; }",
        [cx, cy, expect_closest],
    )
    page.mouse.click(cx, cy)
    page.wait_for_timeout(900)
    proof["point"] = {"x": round(cx), "y": round(cy)}
    return proof


def click_bottle(page) -> dict:
    return click_target(page, "#bw-bottles .bw-bottle .bw-bottle-hit", ".bw-bottle")


def click_station(page, station_id: str) -> dict:
    return click_target(
        page,
        f'#bw-stations .bw-station[data-station-id="{station_id}"] .bw-hit',
        ".bw-station",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--fail-port", type=int, default=8124)
    parser.add_argument("--url-suffix", default="")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    report: dict = {"screenshots": [], "states": {}, "vocabulary": {}}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(CHROMIUM))
        reset_line(args.port)
        page = browser.new_page(viewport={"width": 1600, "height": 940})
        page.goto(f"http://127.0.0.1:{args.port}/bottled-water-demo",
                  wait_until="networkidle")

        # ── 01 normal operation ───────────────────────────────────────────
        page.click("#bw-btn-start")
        page.wait_for_timeout(9000)
        report["states"]["running"] = scan(page)
        report["screenshots"].append(shot(page, "01-target-line-running.png"))

        # ── 02 paused ─────────────────────────────────────────────────────
        page.click("#bw-btn-pause")
        page.wait_for_timeout(900)
        report["states"]["paused"] = scan(page)
        report["screenshots"].append(shot(page, "02-paused.png"))
        page.wait_for_timeout(2200)
        report["states"]["paused_after_wait"] = scan(page)

        # ── 04 inspection station inspector (paused: no motion race) ──────
        report["stationClickProof"] = click_station(page, INSPECTION)
        page.wait_for_timeout(400)
        report["states"]["inspection_inspector"] = scan(page)
        report["screenshots"].append(shot(page, "04-inspection-station.png"))

        # ── 05 unit inspector ─────────────────────────────────────────────
        report["bottleClickProof"] = click_bottle(page)
        report["states"]["unit_inspector"] = scan(page)
        report["screenshots"].append(shot(page, "05-bottle-inspector.png"))
        page.click("#bw-popup-close")
        page.wait_for_timeout(400)

        # ── 03 stopped / reset state ──────────────────────────────────────
        page.click("#bw-btn-stop")
        page.wait_for_timeout(700)
        report["states"]["stopped"] = scan(page)
        report["screenshots"].append(shot(page, "03-stopped.png"))

        page.click("#bw-btn-reset")
        page.wait_for_timeout(900)
        report["states"]["reset"] = scan(page)
        report["screenshots"].append(shot(page, "03b-after-reset.png"))

        # ── resume proof: the line continues from the preserved state ─────
        page.click("#bw-btn-start")
        page.wait_for_timeout(1500)
        report["states"]["resumed"] = scan(page)

        page.close()

        # ── 06/07 failing inspection on the second server ─────────────────
        reset_line(args.fail_port)
        fail_page = browser.new_page(viewport={"width": 1600, "height": 940})
        fail_page.goto(f"http://127.0.0.1:{args.fail_port}/bottled-water-demo",
                       wait_until="networkidle")
        fail_page.click("#bw-btn-start")
        fail_page.wait_for_timeout(11000)
        report["states"]["reject_running"] = scan(fail_page)
        report["screenshots"].append(shot(fail_page, "06-reject-running.png"))

        fail_page.click("#bw-btn-pause")
        fail_page.wait_for_timeout(800)
        report["rejectStationClickProof"] = click_station(fail_page, INSPECTION)
        fail_page.wait_for_timeout(400)
        report["states"]["reject_inspector"] = scan(fail_page)
        report["screenshots"].append(shot(fail_page, "07-reject-inspection.png"))
        fail_page.close()

        browser.close()

    # ── vocabulary scan over every captured state ────────────────────────
    for name, payload in report["states"].items():
        report["vocabulary"][name] = {
            "stringsScanned": len(payload.get("visibleText", []))
            + len(payload.get("svgText", [])) + len(payload.get("assetRefs", [])),
            "hits": vocabulary_hits(payload),
        }
    report["vocabularyClean"] = all(
        not entry["hits"] for entry in report["vocabulary"].values())

    out = EVIDENCE_DIR / "browser-evidence.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"wrote {out.name}")
    for shot_name in report["screenshots"]:
        print(f"  shot: {shot_name}")
    print(f"vocabulary clean: {report['vocabularyClean']}")
    for name, entry in report["vocabulary"].items():
        print(f"  {name}: {entry['stringsScanned']} strings, {len(entry['hits'])} hits")

    facts = report["states"]["running"]["facts"]
    print("running facts:", json.dumps(facts))
    return 0 if report["vocabularyClean"] else 1


if __name__ == "__main__":
    sys.exit(main())
