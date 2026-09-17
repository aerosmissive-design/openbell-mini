"""Modern CGV schedule fetch for OpenBell Mini (Yongsan special halls)."""
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

SPECIAL_RE = re.compile(
    r"IMAX|4DX|SCREEN\s*X|스크린\s*X|아이맥스|ULTRA\s*4DX|SCREENX",
    re.I,
)


def _headers(referer: str = "https://www.cgv.co.kr/") -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json,text/plain,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": referer,
        "Origin": "https://www.cgv.co.kr",
    }


def _get(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> tuple[int, bytes]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers or _headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if hasattr(e, "read") else b"")


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
        return e.code, (e.read() if hasattr(e, "read") else b"")


def _html_probe(html: str) -> str:
    upper = html.upper()
    counts = {
        "IMAX": upper.count("IMAX"),
        "4DX": upper.count("4DX"),
        "SCREENX": upper.count("SCREENX") + upper.count("SCREEN X"),
        "아이맥스": html.count("아이맥스"),
        "스크린X": html.count("스크린X") + html.count("스크린 X"),
        "data-playstarttime": html.lower().count("data-playstarttime"),
        "col-times": html.lower().count("col-times"),
        "type-hall": html.lower().count("type-hall"),
    }
    sample = ""
    m = re.search(r".{0,40}IMAX.{0,40}", html, re.I)
    if m:
        sample = re.sub(r"\s+", " ", m.group(0))[:80]
    return f"kw={counts} sample={sample!r}"


def _parse_html_schedule(html: str, ymd: str) -> list[dict]:
    items: list[dict] = []
    if not html:
        return items

    blocks = re.split(r'<div[^>]*col-times', html, flags=re.I)
    if len(blocks) <= 1:
        blocks = re.split(r'class=["\'][^"\']*col-times', html, flags=re.I)
    chunks = blocks[1:] if len(blocks) > 1 else []
    if not chunks:
        chunks = [html]

    time_attr = re.compile(r'data-playstarttime=["\'](\d{4})["\']', re.I)
    time_clock = re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\b')
    title_strong = re.compile(r'<strong>([^<]{1,80})</strong>', re.I)
    hall_re = re.compile(
        r'(ULTRA\s*4DX|SCREEN\s*X|SCREENX|4DX|IMAX|아이맥스|스크린\s*X|DOLBY\s*ATMOS)',
        re.I,
    )

    for block in chunks:
        titles = title_strong.findall(block)
        title = titles[0].strip() if titles else ""
        hall_parts = re.split(r'(?i)(type-hall|info-hall|info-timetable|상영관)', block)
        parts = hall_parts if len(hall_parts) > 1 else [block]
        for part in parts:
            hm = hall_re.search(part)
            if not hm:
                continue
            hall = re.sub(r'\s+', ' ', hm.group(1)).strip().upper()
            times_attr = [f"{m.group(1)[:2]}:{m.group(1)[2:]}" for m in time_attr.finditer(part)]
            times_clock = [f"{m.group(1).zfill(2)}:{m.group(2)}" for m in time_clock.finditer(part)]
            times = times_attr if times_attr else times_clock
            for t in times[:40]:
                items.append({
                    "date": ymd, "movie": title, "hall": hall, "start": t,
                    "raw_key": f"{ymd}|{title}|{hall}|{t}",
                })

    if not items:
        for m in hall_re.finditer(html):
            hall = re.sub(r'\s+', ' ', m.group(1)).strip().upper()
            window = html[max(0, m.start() - 200): m.end() + 800]
            times = [f"{tm.group(1).zfill(2)}:{tm.group(2)}" for tm in time_clock.finditer(window)]
            titles = title_strong.findall(window)
            title = titles[0].strip() if titles else ""
            for t in times[:15]:
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


def fetch_from_api(ymd: str) -> tuple[list[dict], str]:
    q = urllib.parse.urlencode({
        "coCd": CO_CD, "siteNo": YONGSAN_SITE_NO, "scnYmd": ymd, "rtctlScopCd": RTCTL,
    })
    url = f"{API_SCN}?{q}"
    status, body = _get(url, {
        **_headers("https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013"),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://cgv.co.kr",
    })
    if status != 200:
        raise RuntimeError(f"API HTTP {status}")
    if not body or body.lstrip()[:1] == b"<":
        raise RuntimeError("API returned HTML/empty (blocked)")
    data = json.loads(body.decode("utf-8-sig", errors="replace"))
    top = list(data.keys())[:8] if isinstance(data, dict) else type(data).__name__
    items = []
    rows: list[dict] = []
    if isinstance(data, dict):
        for key in ("data", "DATA", "list", "result", "scnList"):
            v = data.get(key)
            if isinstance(v, list):
                rows = [x for x in v if isinstance(x, dict)]
                break
            if isinstance(v, dict):
                for k2 in ("list", "rows", "scnList", "data", "DATA"):
                    if isinstance(v.get(k2), list):
                        rows = [x for x in v[k2] if isinstance(x, dict)]
                        break
    elif isinstance(data, list):
        rows = [x for x in data if isinstance(x, dict)]
    for row in rows:
        blob = " ".join(str(v) for v in row.values() if isinstance(v, (str, int)))
        if not SPECIAL_RE.search(blob):
            continue
        name = str(row.get("movNm") or row.get("movieNm") or row.get("MOVIE_NM") or "")
        hall = str(row.get("scnsNm") or row.get("RATING_NM") or row.get("MOVIE_ATTR_NM") or "")
        start_raw = str(row.get("scnsrtTm") or row.get("playStartTm") or row.get("SCN_STR_TM") or "")
        digits = "".join(c for c in start_raw if c.isdigit())
        start = f"{digits[:2]}:{digits[2:]}" if len(digits) == 4 else start_raw
        items.append({
            "date": ymd, "movie": name, "hall": hall or "SPECIAL", "start": start,
            "raw_key": f"{ymd}|{name}|{hall}|{start}",
        })
    return items, f"api keys={top} rows={len(rows)} special={len(items)}"


def fetch_from_iframe(ymd: str) -> tuple[list[dict], str]:
    url = f"{IFRAME}?areacode=01&theatercode={YONGSAN_SITE_NO}&date={ymd}"
    status, body = _get(url, _headers("https://www.cgv.co.kr/theaters/?theaterCode=0013"))
    if status != 200:
        raise RuntimeError(f"iframe HTTP {status}")
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError:
        html = body.decode("euc-kr", errors="replace")
    items = _parse_html_schedule(html, ymd)
    probe = _html_probe(html)
    return items, f"iframe special={len(items)} html_len={len(html)} {probe}"


def fetch_from_mobile(ymd: str) -> tuple[list[dict], str]:
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
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError:
        html = body.decode("euc-kr", errors="replace")
    items = _parse_html_schedule(html, ymd)
    probe = _html_probe(html)
    return items, f"mobile special={len(items)} html_len={len(html)} {probe}"


def fetch_day_schedule(show_date: date) -> tuple[list[dict], str]:
    ymd = show_date.strftime("%Y%m%d")
    errors: list[str] = []
    for name, fn in (("iframe", fetch_from_iframe), ("mobile", fetch_from_mobile), ("api", fetch_from_api)):
        try:
            items, meta = fn(ymd)
            if items:
                return items, f"{name}:{meta}"
            errors.append(f"{name}:empty({meta})")
        except Exception as e:
            errors.append(f"{name}:{e}")
    if any("empty" in e for e in errors):
        return [], ";".join(errors)
    raise RuntimeError("; ".join(errors))


def fetch_window_signature(days: int = 14) -> tuple[str, str]:
    today = date.today()
    all_keys: list[str] = []
    errors: list[str] = []
    ok_days = 0
    debug_bits: list[str] = []
    for i in range(days):
        d = today + timedelta(days=i)
        try:
            rows, meta = fetch_day_schedule(d)
            ok_days += 1
            if i < 2:
                debug_bits.append(f"{d.isoformat()}:{meta}:n={len(rows)}")
            for r in rows:
                all_keys.append(r["raw_key"])
        except Exception as e:
            errors.append(f"{d.isoformat()}:{e}")
            if i < 2:
                debug_bits.append(f"{d.isoformat()}:ERR:{e}")
    all_keys.sort()
    if ok_days == 0:
        raise RuntimeError("all days failed: " + "; ".join(errors[:5]))
    return "\n".join(all_keys), " | ".join(debug_bits)


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
