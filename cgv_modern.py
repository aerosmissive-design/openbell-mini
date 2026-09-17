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


def _walk_lists(obj: Any, depth: int = 0) -> list[dict]:
    found: list[dict] = []
    if depth > 6:
        return found
    if isinstance(obj, list):
        for item in obj:
            found.extend(_walk_lists(item, depth + 1))
    elif isinstance(obj, dict):
        keys = {str(k).lower() for k in obj.keys()}
        has_movie = bool(keys & {"movnm", "movienm", "movie_nm", "movname", "movieno", "movno", "moviecode"})
        has_time = bool(keys & {"scnsrttm", "playstarttm", "starttm", "scn_str_tm", "playtime", "starttime"})
        has_hall = bool(keys & {"scnsnm", "screennm", "rating_nm", "theabkornm", "scnnm", "movie_attr_nm"})
        if has_movie or has_time or has_hall:
            found.append(obj)
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found.extend(_walk_lists(v, depth + 1))
    return found


def _pick(row: dict, *names: str) -> str:
    lower_map = {str(k).lower(): v for k, v in row.items()}
    for n in names:
        v = lower_map.get(n.lower())
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _norm_time(raw: str) -> str:
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 4:
        return f"{digits[:2]}:{digits[2:]}"
    m = re.search(r"([01]?\d|2[0-3]):([0-5]\d)", raw)
    if m:
        return f"{m.group(1).zfill(2)}:{m.group(2)}"
    return raw.strip()


def _is_special(text: str) -> bool:
    return bool(SPECIAL_RE.search(text or ""))


def _row_to_item(row: dict, ymd: str) -> dict | None:
    name = _pick(row, "movNm", "movieNm", "MOVIE_NM", "movieName", "movName", "movie_nm")
    hall = _pick(
        row,
        "scnsNm", "screenNm", "RATING_NM", "screenType", "theabKorNm",
        "scnNm", "MOVIE_ATTR_NM", "attrNm", "movieFormat", "formatNm",
        "scrnNm", "screen_nm",
    )
    start = _norm_time(
        _pick(row, "scnsrtTm", "playStartTm", "startTm", "SCN_STR_TM", "playTime", "startTime", "play_start_tm")
    )
    blob = f"{name} {hall}"
    extra = " ".join(str(v) for v in row.values() if isinstance(v, str))
    if not (_is_special(blob) or _is_special(extra)):
        return None
    if not start and not name:
        return None
    hall_label = hall if hall else ("IMAX" if _is_special(extra) else "SPECIAL")
    return {
        "date": ymd,
        "movie": name,
        "hall": hall_label,
        "start": start,
        "raw_key": f"{ymd}|{name}|{hall_label}|{start}",
    }


def fetch_from_api(ymd: str) -> tuple[list[dict], str]:
    q = urllib.parse.urlencode({
        "coCd": CO_CD,
        "siteNo": YONGSAN_SITE_NO,
        "scnYmd": ymd,
        "rtctlScopCd": RTCTL,
    })
    url = f"{API_SCN}?{q}"
    status, body = _get(url, _headers("https://cgv.co.kr/cnm/movieBook/cinema?siteNo=0013"))
    if status != 200:
        raise RuntimeError(f"API HTTP {status}")
    if not body or body.lstrip()[:1] == b"<":
        raise RuntimeError("API returned HTML/empty (blocked)")
    data = json.loads(body.decode("utf-8-sig", errors="replace"))
    rows = _walk_lists(data)
    items = []
    for row in rows:
        item = _row_to_item(row, ymd)
        if item:
            items.append(item)
    meta = f"api rows={len(rows)} special={len(items)} body_len={len(body)}"
    return items, meta


def fetch_from_iframe(ymd: str) -> tuple[list[dict], str]:
    url = f"{IFRAME}?areacode=01&theatercode={YONGSAN_SITE_NO}&date={ymd}"
    status, body = _get(url, {
        **_headers("https://www.cgv.co.kr/theaters/"),
        "Accept": "text/html,application/xhtml+xml",
    })
    if status != 200:
        raise RuntimeError(f"iframe HTTP {status}")
    html = body.decode("utf-8", errors="replace")
    items = _parse_html_schedule(html, ymd)
    return items, f"iframe special={len(items)} html_len={len(html)}"


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
    html = body.decode("utf-8", errors="replace")
    items = _parse_html_schedule(html, ymd)
    return items, f"mobile special={len(items)} html_len={len(html)}"


def _parse_html_schedule(html: str, ymd: str) -> list[dict]:
    items: list[dict] = []
    if not SPECIAL_RE.search(html):
        return []
    parts = re.split(r"(?i)(IMAX|4DX|SCREENX|SCREEN\s*X|스크린\s*X|ULTRA\s*4DX)", html)
    hall = ""
    chunks: list[tuple[str, str]] = []
    for p in parts:
        if re.fullmatch(r"(?i)IMAX|4DX|SCREENX|SCREEN\s*X|스크린\s*X|ULTRA\s*4DX", p or ""):
            hall = re.sub(r"\s+", "", p.upper())
            continue
        if hall:
            chunks.append((hall, p))
    if not chunks:
        chunks = [("SPECIAL", html)]

    time_re = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
    title_re = re.compile(r"<strong>([^<]{1,80})</strong>", re.I)
    title_re2 = re.compile(r"class=[\"'][^\"']*movie[^\"']*[\"'][^>]*>([^<]{1,80})<", re.I)

    for hall, chunk in chunks:
        titles = title_re.findall(chunk) or title_re2.findall(chunk)
        times = [f"{m.group(1).zfill(2)}:{m.group(2)}" for m in time_re.finditer(chunk)]
        title = titles[0].strip() if titles else ""
        for t in times[:40]:
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


def fetch_day_schedule(show_date: date) -> tuple[list[dict], str]:
    ymd = show_date.strftime("%Y%m%d")
    errors: list[str] = []
    for name, fn in (("api", fetch_from_api), ("iframe", fetch_from_iframe), ("mobile", fetch_from_mobile)):
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
            if i < 3:
                debug_bits.append(f"{d.isoformat()}:{meta}:n={len(rows)}")
            for r in rows:
                all_keys.append(r["raw_key"])
        except Exception as e:
            errors.append(f"{d.isoformat()}:{e}")
            if i < 3:
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
