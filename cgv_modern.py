"""Minimal modern CGV schedule fetch for OpenBell Mini (Yongsan special halls).

Uses the public booking API shape used by working open-source bots.
Cloudflare may block datacenter IPs; Railway often works better.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any

YONGSAN_SITE_NO = "0013"
CO_CD = "A420"
RTCTL = "08"
API_SCH = "https://cgv.co.kr/api/v1/booking/searchSchByMov"
API_SCN = "https://cgv.co.kr/cnm/atkt/searchMovScnInfo"
BOOKING_REFERER = "https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013"

SPECIAL_KEYWORDS = ("IMAX", "4DX", "SCREENX", "스크린X", "아이맥스")


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "OpenBellMini/1.0 (+https://github.com/aerosmissive-design/openbell-mini)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": BOOKING_REFERER,
        "Origin": "https://cgv.co.kr",
    }


def _get_json(url: str, timeout: int = 15) -> Any:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            ct = resp.headers.get("Content-Type", "")
            if "json" not in ct.lower() and body.lstrip()[:1] == b"<":
                raise RuntimeError("CGV returned HTML (likely Cloudflare block)")
            return json.loads(body.decode("utf-8-sig"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"CGV HTTP {e.code}") from e


def fetch_day_schedule(show_date: date) -> list[dict]:
    ymd = show_date.strftime("%Y%m%d")
    q = urllib.parse.urlencode(
        {
            "coCd": CO_CD,
            "siteNo": YONGSAN_SITE_NO,
            "scnYmd": ymd,
            "rtctlScopCd": RTCTL,
        }
    )
    url = f"{API_SCN}?{q}"
    try:
        data = _get_json(url)
    except Exception:
        data = _get_json(f"{API_SCH}?{q}")

    rows = []
    candidates = []
    if isinstance(data, dict):
        for key in ("data", "DATA", "list", "result"):
            v = data.get(key)
            if isinstance(v, list):
                candidates = v
                break
            if isinstance(v, dict):
                for k2 in ("list", "rows", "scnList", "data"):
                    if isinstance(v.get(k2), list):
                        candidates = v[k2]
                        break
        if not candidates and isinstance(data.get("d"), dict):
            inner = data["d"]
            if isinstance(inner.get("DATA"), list):
                candidates = inner["DATA"]
    elif isinstance(data, list):
        candidates = data

    for row in candidates:
        if not isinstance(row, dict):
            continue
        name = str(
            row.get("movNm")
            or row.get("movieNm")
            or row.get("MOVIE_NM")
            or row.get("movieName")
            or ""
        )
        hall = str(
            row.get("scnsNm")
            or row.get("screenNm")
            or row.get("RATING_NM")
            or row.get("screenType")
            or row.get("theabKorNm")
            or ""
        )
        start = str(
            row.get("scnsrtTm")
            or row.get("playStartTm")
            or row.get("startTm")
            or row.get("SCN_STR_TM")
            or ""
        )
        blob = f"{name} {hall}".upper()
        if not any(k.upper() in blob for k in SPECIAL_KEYWORDS):
            fmt = str(row.get("movieFormat") or row.get("MOVIE_ATTR_NM") or "")
            if not any(k.upper() in fmt.upper() for k in SPECIAL_KEYWORDS):
                continue
        rows.append(
            {
                "date": ymd,
                "movie": name,
                "hall": hall,
                "start": start,
                "raw_key": f"{ymd}|{name}|{hall}|{start}",
            }
        )
    return rows


def fetch_window_signature(days: int = 14) -> str:
    today = date.today()
    all_keys: list[str] = []
    errors: list[str] = []
    for i in range(days):
        d = today + timedelta(days=i)
        try:
            rows = fetch_day_schedule(d)
            for r in rows:
                all_keys.append(r["raw_key"])
        except Exception as e:
            errors.append(f"{d.isoformat()}:{e}")
    all_keys.sort()
    sig = "\n".join(all_keys)
    if errors and not all_keys:
        raise RuntimeError("all days failed: " + "; ".join(errors[:3]))
    return sig


def format_added_lines(prev_sig: str, new_sig: str) -> str:
    prev = set(prev_sig.splitlines()) if prev_sig else set()
    new = set(new_sig.splitlines()) if new_sig else set()
    added = sorted(new - prev)
    if not added:
        return ""
    lines = []
    for key in added:
        parts = key.split("|")
        if len(parts) >= 4:
            lines.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}")
        else:
            lines.append(key)
    return "\n".join(lines)
