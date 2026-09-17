"""Modern CGV schedule fetch for OpenBell Mini (Yongsan special halls).

Primary: https://api.cgv.co.kr/cnm/atkt/searchMovScnInfo
(same shape as working OpenBell production code)
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any

YONGSAN_SITE_NO = "0013"
CO_CD = "A420"
RTCTL = "08"

API_SCN = "https://api.cgv.co.kr/cnm/atkt/searchMovScnInfo"
IFRAME = "https://www.cgv.co.kr/common/showtimes/iframeTheater.aspx"
MOBILE = "https://m.cgv.co.kr/Schedule/cont/ajaxMovieSchedule.aspx"

SPECIAL_KEYWORDS = ("IMAX", "4DX", "SCREENX", "스크린X", "아이맥스", "ULTRA")


def _headers(referer: str = "https://cgv.co.kr/") -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": referer,
        "Origin": "https://cgv.co.kr",
    }


def _get(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> tuple[int, bytes, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers or _headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, ""


def _post_form(url: str, data: dict[str, str], headers: dict[str, str], timeout: int = 15) -> tuple[int, bytes]:
    ctx = ssl.create_default_context()
    body = urllib.parse.urlencode(data).encode("utf-8")
    h = dict(headers)
    h["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""


def _extract_rows(data: Any) -> list[dict]:
    candidates: list = []
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict):
        for key in ("data", "DATA", "list", "result", "scnList"):
            v = data.get(key)
            if isinstance(v, list):
                candidates = v
                break
            if isinstance(v, dict):
                for k2 in ("list", "rows", "scnList", "data", "DATA"):
                    if isinstance(v.get(k2), list):
                        candidates = v[k2]
                        break
        if not candidates and isinstance(data.get("d"), dict):
            inner = data["d"]
            if isinstance(inner.get("DATA"), list):
                candidates = inner["DATA"]
    return [r for r in candidates if isinstance(r, dict)]


def _row_to_item(row: dict, ymd: str) -> dict | None:
    name = str(
        row.get("movNm") or row.get("movieNm") or row.get("MOVIE_NM")
        or row.get("movieName") or row.get("movName") or ""
    ).strip()
    hall = str(
        row.get("scnsNm") or row.get("screenNm") or row.get("RATING_NM")
        or row.get("screenType") or row.get("theabKorNm") or row.get("scnNm")
        or row.get("MOVIE_ATTR_NM") or ""
    ).strip()
    start_raw = str(
        row.get("scnsrtTm") or row.get("playStartTm") or row.get("startTm")
        or row.get("SCN_STR_TM") or row.get("playTime") or ""
    ).strip()
    start = start_raw
    digits = "".join(c for c in start_raw if c.isdigit())
    if len(digits) == 4:
        start = f"{digits[:2]}:{digits[2:]}"

    blob = f"{name} {hall}".upper()
    fmt = str(row.get("movieFormat") or row.get("MOVIE_ATTR_NM") or row.get("attrNm") or "")
    if not any(k.upper() in blob for k in SPECIAL_KEYWORDS) and not any(
        k.upper() in fmt.upper() for k in SPECIAL_KEYWORDS
    ):
        return None
    if not name and not hall:
        return None
    return {
        "date": ymd,
        "movie": name,
        "hall": hall or "SPECIAL",
        "start": start,
        "raw_key": f"{ymd}|{name}|{hall}|{start}",
    }


def fetch_from_api(ymd: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "coCd": CO_CD,
        "siteNo": YONGSAN_SITE_NO,
        "scnYmd": ymd,
        "rtctlScopCd": RTCTL,
    })
    url = f"{API_SCN}?{q}"
    status, body, ct = _get(url, _headers("https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013"))
    if status != 200:
        raise RuntimeError(f"API HTTP {status}")
    if body.lstrip()[:1] == b"<":
        raise RuntimeError("API returned HTML (blocked)")
    data = json.loads(body.decode("utf-8-sig"))
    items = []
    for row in _extract_rows(data):
        item = _row_to_item(row, ymd)
        if item:
            items.append(item)
    return items


def fetch_from_iframe(ymd: str) -> list[dict]:
    url = f"{IFRAME}?areacode=01&theatercode={YONGSAN_SITE_NO}&date={ymd}"
    status, body, _ = _get(url, {
        **_headers("https://www.cgv.co.kr/theaters/"),
        "Accept": "text/html,application/xhtml+xml",
    })
    if status != 200:
        raise RuntimeError(f"iframe HTTP {status}")
    return _parse_html_schedule(body.decode("utf-8", errors="replace"), ymd)


def fetch_from_mobile(ymd: str) -> list[dict]:
    status, body = _post_form(
        MOBILE,
        {"theaterCd": YONGSAN_SITE_NO, "playYMD": ymd},
        {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13; SM-S918N) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Mobile Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://m.cgv.co.kr/",
        },
    )
    if status != 200:
        raise RuntimeError(f"mobile HTTP {status}")
    return _parse_html_schedule(body.decode("utf-8", errors="replace"), ymd)


def _parse_html_schedule(html: str, ymd: str) -> list[dict]:
    items: list[dict] = []
    parts = re.split(r"(?i)(IMAX|4DX|SCREENX|스크린X|ULTRA\s*4DX)", html)
    hall = ""
    chunks: list[tuple[str, str]] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if re.fullmatch(r"(?i)IMAX|4DX|SCREENX|스크린X|ULTRA\s*4DX", p or ""):
            hall = p.upper().replace(" ", "")
            i += 1
            continue
        if hall:
            chunks.append((hall, p))
        i += 1
    if not chunks:
        if not any(k in html.upper() for k in ("IMAX", "4DX", "SCREENX")):
            return []
        chunks = [("SPECIAL", html)]

    time_re = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
    title_re = re.compile(r"<strong>([^<]{1,60})</strong>", re.I)
    for hall, chunk in chunks:
        titles = title_re.findall(chunk)
        times = [f"{m.group(1).zfill(2)}:{m.group(2)}" for m in time_re.finditer(chunk)]
        title = titles[0].strip() if titles else ""
        for t in times[:30]:
            items.append({
                "date": ymd, "movie": title, "hall": hall, "start": t,
                "raw_key": f"{ymd}|{title}|{hall}|{t}",
            })
    seen = set()
    out = []
    for it in items:
        if it["raw_key"] in seen:
            continue
        seen.add(it["raw_key"])
        out.append(it)
    return out


def fetch_day_schedule(show_date: date) -> list[dict]:
    ymd = show_date.strftime("%Y%m%d")
    errors: list[str] = []
    for name, fn in (("api", fetch_from_api), ("iframe", fetch_from_iframe), ("mobile", fetch_from_mobile)):
        try:
            return fn(ymd)
        except Exception as e:
            errors.append(f"{name}:{e}")
    raise RuntimeError("; ".join(errors))


def fetch_window_signature(days: int = 14) -> str:
    today = date.today()
    all_keys: list[str] = []
    errors: list[str] = []
    ok_days = 0
    for i in range(days):
        d = today + timedelta(days=i)
        try:
            rows = fetch_day_schedule(d)
            ok_days += 1
            for r in rows:
                all_keys.append(r["raw_key"])
        except Exception as e:
            errors.append(f"{d.isoformat()}:{e}")
    all_keys.sort()
    if ok_days == 0:
        raise RuntimeError("all days failed: " + "; ".join(errors[:5]))
    return "\n".join(all_keys)


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
