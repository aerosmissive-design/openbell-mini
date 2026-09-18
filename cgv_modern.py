"""Modern CGV schedule fetch for OpenBell Mini (Yongsan special halls).

CGV official endpoints often return JS shells / bot walls from datacenter IPs.
Fallbacks: Naver Place theater page, public MCP timetable relay, HTML probe.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, timedelta
from typing import Any

YONGSAN_SITE_NO = "0013"
YONGSAN_PLACE_ID = "12298207"
CO_CD = "A420"

API_SCN = "https://api.cgv.co.kr/cnm/atkt/searchMovScnInfo"
IFRAME = "https://www.cgv.co.kr/common/showtimes/iframeTheater.aspx"
MOBILE = "https://m.cgv.co.kr/Schedule/cont/ajaxMovieSchedule.aspx"
MCP = "https://mcp.aka.page/api/cgv/timetable"
NAVER = f"https://m.place.naver.com/theater/{YONGSAN_PLACE_ID}/movie"

SPECIAL_RE = re.compile(
    r"IMAX\s*LASER|IMAX|4DX|SCREEN\s*X|스크린\s*X|아이맥스|ULTRA\s*4DX|SCREENX",
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


def _decode(body: bytes) -> str:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def _html_probe(html: str) -> str:
    title_m = re.search(r"<title[^>]*>([^<]{0,80})</title>", html, re.I)
    title = title_m.group(1).strip() if title_m else ""
    upper = html.upper()
    counts = {
        "IMAX": upper.count("IMAX"),
        "4DX": upper.count("4DX"),
        "SCREENX": upper.count("SCREENX"),
        "cloudflare": 1 if "cloudflare" in html.lower() or "cf-ray" in html.lower() else 0,
        "captcha": 1 if "captcha" in html.lower() else 0,
        "script": html.lower().count("<script"),
    }
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()[:120]
    return f"title={title!r} kw={counts} text={text!r}"


def _norm_hall(raw: str) -> str:
    s = re.sub(r"\s+", "", raw.upper())
    if "IMAX" in s or "아이맥스" in raw:
        return "IMAX"
    if "SCREENX" in s or "스크린X" in re.sub(r"\s+", "", raw):
        return "SCREENX"
    if "4DX" in s:
        return "4DX"
    return s or "SPECIAL"


def _parse_html_schedule(html: str, ymd: str) -> list[dict]:
    items: list[dict] = []
    if not html or not SPECIAL_RE.search(html):
        return items

    time_clock = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
    title_strong = re.compile(r"<strong>([^<]{1,80})</strong>", re.I)
    hall_re = re.compile(
        r"(IMAX\s*LASER|IMAX|아이맥스|ULTRA\s*4DX|4DX|SCREEN\s*X|SCREENX|스크린\s*X)",
        re.I,
    )

    for hm in hall_re.finditer(html):
        hall = _norm_hall(hm.group(1))
        start = max(0, hm.start() - 400)
        end = min(len(html), hm.end() + 1200)
        window = html[start:end]
        titles = title_strong.findall(window)
        title = ""
        for t in titles:
            t = t.strip()
            if t and len(t) < 60 and "네이버" not in t and "플레이스" not in t:
                title = t
                break
        times = [f"{m.group(1).zfill(2)}:{m.group(2)}" for m in time_clock.finditer(window)]
        seen_t = set()
        ordered = []
        for t in times:
            if t not in seen_t:
                seen_t.add(t)
                ordered.append(t)
        for t in ordered[:25]:
            items.append({
                "date": ymd,
                "movie": title,
                "hall": hall,
                "start": t,
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


def _hall_counts(items: list[dict]) -> str:
    c = Counter(it.get("hall", "?") for it in items)
    return ",".join(f"{k}:{v}" for k, v in sorted(c.items()))


def fetch_from_iframe(ymd: str) -> tuple[list[dict], str]:
    url = f"{IFRAME}?areacode=01&theatercode={YONGSAN_SITE_NO}&date={ymd}"
    status, body = _get(url, _headers("https://www.cgv.co.kr/theaters/?theaterCode=0013"))
    if status != 200:
        raise RuntimeError(f"iframe HTTP {status}")
    html = _decode(body)
    items = _parse_html_schedule(html, ymd)
    return items, f"iframe special={len(items)} halls={_hall_counts(items)} {_html_probe(html)}"


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
    html = _decode(body)
    items = _parse_html_schedule(html, ymd)
    return items, f"mobile special={len(items)} halls={_hall_counts(items)} {_html_probe(html)}"


def fetch_from_api(ymd: str) -> tuple[list[dict], str]:
    q = urllib.parse.urlencode({
        "coCd": CO_CD, "siteNo": YONGSAN_SITE_NO, "scnYmd": ymd, "rtctlScopCd": "08",
    })
    status, body = _get(
        f"{API_SCN}?{q}",
        {**_headers("https://cgv.co.kr/"), "Accept": "application/json", "Origin": "https://cgv.co.kr"},
    )
    if status != 200:
        raise RuntimeError(f"API HTTP {status}")
    if not body or body.lstrip()[:1] == b"<":
        raise RuntimeError("API HTML/blocked")
    data = json.loads(_decode(body))
    return [], f"api ok keys={list(data.keys())[:6] if isinstance(data, dict) else type(data)}"


def fetch_from_mcp(ymd: str) -> tuple[list[dict], str]:
    if len(ymd) == 8:
        play = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    else:
        play = ymd
    url = f"{MCP}?playDate={play}&theaterCode={YONGSAN_SITE_NO}&limit=200"
    status, body = _get(url, _headers("https://mcp.aka.page/"))
    if status != 200:
        raise RuntimeError(f"MCP HTTP {status}")
    data = json.loads(_decode(body))
    rows = data if isinstance(data, list) else data.get("data") or data.get("items") or []
    items = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        blob = " ".join(str(v) for v in row.values() if isinstance(v, (str, int)))
        if not SPECIAL_RE.search(blob):
            continue
        name = str(row.get("movieTitle") or row.get("movieNm") or row.get("title") or "")
        hall = _norm_hall(str(row.get("hallName") or row.get("screenNm") or row.get("hall") or "SPECIAL"))
        start = str(row.get("startTime") or row.get("playTime") or row.get("time") or "")
        items.append({
            "date": ymd.replace("-", ""),
            "movie": name,
            "hall": hall,
            "start": start,
            "raw_key": f"{ymd.replace('-', '')}|{name}|{hall}|{start}",
        })
    return items, f"mcp rows={len(rows) if isinstance(rows, list) else 0} special={len(items)} halls={_hall_counts(items)}"


def fetch_from_naver(ymd: str) -> tuple[list[dict], str]:
    status, body = _get(NAVER, {**_headers("https://m.place.naver.com/"), "Accept": "text/html"})
    if status != 200:
        raise RuntimeError(f"naver HTTP {status}")
    html = _decode(body)
    items = _parse_html_schedule(html, ymd)
    return items, f"naver special={len(items)} halls={_hall_counts(items)} {_html_probe(html)}"


def fetch_day_schedule(show_date: date) -> tuple[list[dict], str]:
    ymd = show_date.strftime("%Y%m%d")
    errors: list[str] = []
    for name, fn in (
        ("mcp", fetch_from_mcp),
        ("naver", fetch_from_naver),
        ("iframe", fetch_from_iframe),
        ("mobile", fetch_from_mobile),
        ("api", fetch_from_api),
    ):
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
    window = min(days, 7)
    for i in range(window):
        d = today + timedelta(days=i)
        try:
            rows, meta = fetch_day_schedule(d)
            ok_days += 1
            if i < 1:
                debug_bits.append(f"{d.isoformat()}:{meta}:n={len(rows)}")
            for r in rows:
                all_keys.append(r["raw_key"])
        except Exception as e:
            errors.append(f"{d.isoformat()}:{e}")
            if i < 1:
                debug_bits.append(f"{d.isoformat()}:ERR:{e}")
    all_keys.sort()
    if ok_days == 0:
        raise RuntimeError("all days failed: " + "; ".join(errors[:5]))
    return "\n".join(all_keys), " | ".join(debug_bits)


def booking_url(ymd: str) -> str:
    """CGV 용산 극장·날짜 예매 페이지 (회차 직링크는 movNo 필요 → 날짜 단위)."""
    ymd = ymd.replace("-", "")
    return (
        "https://cgv.co.kr/cnm/movieBook/cinema"
        f"?siteNo={YONGSAN_SITE_NO}&date={ymd}"
    )


def format_added_lines(prev_sig: str, new_sig: str) -> str:
    """Return HTML message body with per-line '바로 예매' links."""
    prev = set(prev_sig.splitlines()) if prev_sig else set()
    new = set(new_sig.splitlines()) if new_sig else set()
    added = sorted(new - prev)
    if not added:
        return ""
    lines = []
    for key in added:
        parts = key.split("|")
        if len(parts) >= 4:
            ymd, movie, hall, start = parts[0], parts[1], parts[2], parts[3]
            label = f"{ymd} {movie} {hall} {start}".strip()
            label = " ".join(label.split())
            url = booking_url(ymd)
            lines.append(f'{label} <a href="{url}">바로 예매</a>')
        else:
            lines.append(key)
    return "\n".join(lines)
