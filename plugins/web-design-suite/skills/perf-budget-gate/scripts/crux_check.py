#!/usr/bin/env python3
"""
crux_check.py — does the lab profile still describe the field?

`measure_vitals.mjs` is a regression detector against itself, on one machine
with one throttle profile. Whether that profile describes your users is a
question only field data answers. This reads the 75th percentile of real
page loads from the Chrome UX Report (CrUX) API, for an origin or one URL,
and holds it against the lab median from a `measure_vitals.mjs --report`
file.

The trigger (SKILL.md, references/ci-integration.md §8): a field p75 more
than 1.5x the lab median means the lab measures a page, a device or a network
your users do not have, and every budget derived from it aims at the wrong
target. Re-run the derivation in references/budgets.md §1 with the device
and connection the field shows.

Usage
-----
    set CRUX_API_KEY=...            (PowerShell: $env:CRUX_API_KEY = "...")
    python -m scripts.crux_check --origin https://example.com --lab vitals.json
    python -m scripts.crux_check --url https://example.com/pricing --lab vitals.json
    python -m scripts.crux_check --origin https://example.com --lab vitals.json \\
        --form-factor DESKTOP --json

    # offline, from a response saved earlier (or recorded for a test)
    python -m scripts.crux_check --origin https://example.com --lab vitals.json \\
        --response crux.json

The key comes from the CRUX_API_KEY environment variable and never from an
argument: an argument lands in shell history, process lists and CI logs. It
is sent only to the API, and never printed. Get one from the Google Cloud
console (the Chrome UX Report API); CRUX_API_URL points the query at another
endpoint, such as a proxy, over https (plain http only to this machine).

Compared, where both sides have a number: LCP, CLS, FCP, TTFB, and INP when
the lab run drove an interaction (--interact). TBT has no field counterpart.
A lab median of 0 has no ratio, and any field value above 0 is above it: a
lab CLS of 0 against a field CLS of 0.05 is a lab that misses the shifts.

Exit codes
----------
    0  every compared metric's field p75 is within the ratio of its lab median
    1  at least one is above it: the lab profile no longer describes the field
    2  bad arguments, no key, an unreadable or malformed lab file or response,
       a response for another page or device class, the API refused, or CrUX
       holds no data for the origin or URL

Standard library only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

API = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
RATIO = 1.5

# lab key in measure_vitals' report -> (CrUX metric, label, unit)
METRICS = {
    "lcp": ("largest_contentful_paint", "LCP", "ms"),
    "cls": ("cumulative_layout_shift", "CLS", ""),
    "inp": ("interaction_to_next_paint", "INP", "ms"),
    "fcp": ("first_contentful_paint", "FCP", "ms"),
    "ttfb": ("experimental_time_to_first_byte", "TTFB", "ms"),
}


class CheckError(Exception):
    """A problem the user can fix. Printed without a traceback; exit 2."""


def read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_bytes())       # bytes: a BOM or UTF-16 is fine
    except OSError as exc:
        raise CheckError(f"cannot read the {what} {path}: {exc.strerror or exc}") from None
    except ValueError as exc:
        raise CheckError(f"the {what} {path} is not JSON: {exc}") from None


def measurement(value: Any) -> Optional[float]:
    """A finite number of 0 or more (CLS arrives as a string, "0.05"), or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
        return float(value)
    return None


def lab_medians(report: Any) -> Dict[str, float]:
    stats = report.get("stats") if isinstance(report, dict) else None
    if not isinstance(stats, dict):
        raise CheckError("the lab file has no `stats`: write it with "
                         "`measure_vitals.mjs URL --report vitals.json`.")
    out = {}
    for key, (_, label, _) in METRICS.items():
        s = stats.get(key)
        median = s.get("median") if isinstance(s, dict) else s
        if median is None:                           # not measured, as INP without --interact
            continue
        out[key] = measurement(median)
        if out[key] is None:
            raise CheckError(f"the lab file's {label} median is {median!r}, not a finite "
                             f"number of 0 or more.")
    return out


def endpoint() -> str:
    """The query carries the key, so it goes over HTTPS, or plain HTTP to this
    machine only (a test server)."""
    url = os.environ.get("CRUX_API_URL", API)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https" or (
            parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1")):
        return url
    raise CheckError("CRUX_API_URL must be an https:// URL (or http:// to this machine): "
                     "the key travels in it.")


def query(target: Dict[str, str], form_factor: str) -> Any:
    key = os.environ.get("CRUX_API_KEY", "").strip()
    if not key:
        raise CheckError("set CRUX_API_KEY to a Chrome UX Report API key (an environment "
                         "variable, never an argument), or pass --response FILE.")
    body = dict(target)
    if form_factor != "ALL":
        body["formFactor"] = form_factor
    body["metrics"] = [m for m, _, _ in METRICS.values()]
    url = endpoint()
    req = urllib.request.Request(
        url + "?key=" + urllib.parse.quote(key, safe=""),
        data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read()).get("error", {}).get("message", "")
        except (ValueError, AttributeError, OSError):
            pass
        if exc.code == 404:
            raise CheckError(f"CrUX holds no data for {next(iter(target.values()))} "
                             f"({form_factor}): too little traffic, or not public. Try "
                             f"the origin, or --form-factor ALL.") from None
        raise CheckError(f"the CrUX API answered {exc.code}"
                         + (f": {detail}" if detail else "") + ".") from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", exc)
        raise CheckError(f"the CrUX API could not be reached: {reason}") from None


def canonical(url: str, kind: str) -> tuple:
    """Scheme and host without case. An origin's root slash is not a page, but
    a page's trailing slash is: `/offers` and `/offers/` are two records."""
    parts = urllib.parse.urlsplit(url.strip())
    path = parts.path
    if kind == "origin" or path == "/":
        path = path.rstrip("/")
    return (parts.scheme.lower(), parts.netloc.lower(), path, parts.query)


def check_record_key(response: Dict[str, Any], record: Dict[str, Any],
                     target: Dict[str, str], form_factor: str) -> None:
    """A saved response for another page or device class is refused: its
    numbers would be printed under the requested target."""
    key = record.get("key")
    if not isinstance(key, dict):
        raise CheckError("the CrUX response's record has no `key` naming its page.")
    kind, want = next(iter(target.items()))
    got = key.get(kind)
    details = response.get("urlNormalizationDetails")
    if details is not None and not isinstance(details, dict):
        raise CheckError("the CrUX response's `urlNormalizationDetails` is not an object.")
    original = (details or {}).get("originalUrl")
    if not isinstance(got, str) or canonical(want, kind) not in (
            canonical(got, kind),
            canonical(original, kind) if isinstance(original, str) else None):
        raise CheckError(f"the response is for {got or key}, not the {kind} {want}.")
    got_ff = key.get("formFactor")
    if got_ff != (None if form_factor == "ALL" else form_factor):
        raise CheckError(f"the response is for the {got_ff or 'ALL'} form factor, "
                         f"not {form_factor}.")


def field_p75(response: Any, target: Dict[str, str], form_factor: str) -> Dict[str, float]:
    record = response.get("record") if isinstance(response, dict) else None
    if not isinstance(record, dict):
        raise CheckError("the CrUX response has no `record`.")
    check_record_key(response, record, target, form_factor)
    metrics = record.get("metrics", {})
    if not isinstance(metrics, dict):
        raise CheckError("the CrUX response's `metrics` is not an object.")
    out = {}
    for key, (name, label, _) in METRICS.items():
        metric = metrics.get(name)
        if metric is None:                           # CrUX has no data for this one
            continue
        percentiles = metric.get("percentiles") if isinstance(metric, dict) else None
        if not isinstance(percentiles, dict):
            raise CheckError(f"the CrUX response's {name} has no `percentiles` object.")
        p75 = percentiles.get("p75")
        if p75 is None:
            continue
        out[key] = measurement(p75)
        if out[key] is None:
            raise CheckError(f"the CrUX response's {label} p75 is {p75!r}, not a finite "
                             f"number of 0 or more.")
    return out


def compare(lab: Dict[str, float], field: Dict[str, float], ratio: float) -> List[Dict[str, Any]]:
    rows = []
    for key, (_, label, unit) in METRICS.items():
        if key not in lab or key not in field:
            continue
        # A lab median of 0 has no ratio, and any field value above 0 is
        # above it: a lab CLS of 0 against a field CLS of 0.05 means the lab
        # misses shifts the users get (Codex on #46).
        row = {"metric": key, "label": label, "unit": unit, "lab": lab[key],
               "field": field[key],
               "ratio": round(field[key] / lab[key], 2) if lab[key] > 0 else None,
               "verdict": "above" if field[key] > ratio * lab[key] else "within"}
        rows.append(row)
    return rows


def fmt(value: float, unit: str) -> str:
    return f"{value:.3f}" if not unit else f"{value:.0f}{unit}"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.crux_check",
        description="Hold the field p75 from the Chrome UX Report against "
                    "measure_vitals' lab median. The API key comes from CRUX_API_KEY.")
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--origin", help="an origin, such as https://example.com")
    where.add_argument("--url", help="one page's URL")
    ap.add_argument("--lab", required=True, help="measure_vitals.mjs --report FILE")
    ap.add_argument("--form-factor", default="PHONE", type=str.upper,
                    choices=("PHONE", "DESKTOP", "TABLET", "ALL"),
                    help="the device class to compare with (default PHONE, "
                         "like measure_vitals' viewport)")
    ap.add_argument("--ratio", type=float, default=RATIO,
                    help=f"how far the field may sit above the lab (default {RATIO})")
    ap.add_argument("--response", metavar="FILE",
                    help="read a saved API response instead of calling the API")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    argv = sys.argv[1:] if argv is None else argv
    # Refused before argparse, which would echo the value into the log.
    if any(a.split("=", 1)[0] in ("--key", "--api-key") for a in argv):
        print("crux_check: the API key is read from CRUX_API_KEY, never from an argument, "
              "which lands in shell history and CI logs.", file=sys.stderr)
        return 2
    args = ap.parse_args(argv)

    try:
        if not (math.isfinite(args.ratio) and args.ratio > 0):
            raise CheckError("--ratio must be a finite number above 0")
        lab_report = read_json(Path(args.lab), "lab file")
        lab = lab_medians(lab_report)
        target = {"origin": args.origin} if args.origin else {"url": args.url}
        response = (read_json(Path(args.response), "response")
                    if args.response else query(target, args.form_factor))
        field = field_p75(response, target, args.form_factor)
        rows = compare(lab, field, args.ratio)
        if not rows:
            raise CheckError("no metric has both a lab median and a field p75 to compare.")
    except CheckError as exc:
        print(f"crux_check: {exc}", file=sys.stderr)
        return 2

    above = [r for r in rows if r["verdict"] == "above"]
    period = ((response.get("record") or {}).get("collectionPeriod") or {})
    if args.json:
        print(json.dumps({"target": target, "formFactor": args.form_factor,
                          "ratio": args.ratio, "throttle": lab_report.get("throttle"),
                          "collectionPeriod": period, "rows": rows,
                          "above": [r["metric"] for r in above]}, indent=2))
    else:
        print(f"crux_check: {next(iter(target.values()))}, {args.form_factor.lower()}, "
              f"field p75 against the lab median ({lab_report.get('throttle', 'unknown')} "
              f"throttle); trigger above {args.ratio}x")
        for r in rows:
            ratio = f"{r['ratio']:.2f}x" if r["ratio"] is not None else "from 0"
            print(f"  {r['label']:<5} field {fmt(r['field'], r['unit']):>8}  "
                  f"lab {fmt(r['lab'], r['unit']):>8}  {ratio:>6}  {r['verdict']}")
        if above:
            print(f"  {len(above)} metric(s) above {args.ratio}x: the lab no longer describes "
                  f"the field. Re-derive the profile (references/budgets.md §1).")
        else:
            print("  The lab profile still describes the field.")
    return 1 if above else 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if getattr(_stream, "encoding", "utf-8").lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
