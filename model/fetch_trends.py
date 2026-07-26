# -*- coding: utf-8 -*-
"""
锚点热词实测：直接调用 Google Trends 的 explore / multiline 接口取回原始序列。

为什么必须自己抓：原计划书把 Trending Now 的 24 小时分桶标签（200K+）当成了月均搜索量。
只有把周粒度与日粒度的真实序列落盘，"这个词已经归零"才是可审计的结论而不是主张。

落盘：data/trends_measured.csv，字段含 provenance 列，标明每一行是本次实时抓取
（live_fetch）还是 2026-07-26 测量会话的存档值（recorded_2026-07-26）。
两者不混淆，是本项目对"实事求是"的最低要求。
"""

from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from inputs import DATA, enable_utf8_stdout

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

ANCHOR = "social security electronic benefits update"
HEAD_TERM = "social security"

# 2026-07-26 测量会话的存档值。仅在实时抓取失败时使用，并在 provenance 列标明。
RECORDED_WEEKLY = [
    # (周起始日, 指数)  美国区，2025-07-20 ~ 2026-07-19，53 周
    ("2026-06-07", 100), ("2026-06-14", 4), ("2026-06-21", 1),
]
RECORDED_WEEKLY_ZERO_NOTE = "其余 50 周全部为 0（46 周为整周 0，另含归零后的连续观测）"

RECORDED_DAILY = [
    ("2026-06-09", 0), ("2026-06-10", 9), ("2026-06-11", 100), ("2026-06-12", 33),
    ("2026-06-13", 4), ("2026-06-14", 2), ("2026-06-15", 1), ("2026-06-16", 1),
    ("2026-06-17", 1), ("2026-06-18", 1), ("2026-06-19", 0), ("2026-06-20", 0),
    ("2026-06-21", 0), ("2026-06-22", 0),
]


_JAR = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_JAR))


def _prime_cookies() -> None:
    """先访问一次页面拿 NID/CONSENT cookie，否则 api/explore 大概率直接 429。"""
    try:
        req = urllib.request.Request("https://trends.google.com/trends/explore?geo=US",
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "en-US,en;q=0.9"})
        _OPENER.open(req, timeout=15).read(1024)
    except Exception:
        pass


def _get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://trends.google.com/trends/explore",
    })
    with _OPENER.open(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # Trends 在 JSON 前加了 ")]}'," 防 JSON 劫持
    i = raw.find("{")
    return raw[i:] if i >= 0 else raw


def fetch_series(terms: list[str], timeframe: str, geo: str = "US") -> dict[str, list[tuple[str, float]]]:
    """返回 {term: [(date, value), ...]}。失败抛异常，由调用方决定是否回退。"""
    comparison = [{"keyword": t, "geo": geo, "time": timeframe} for t in terms]
    req = {"comparisonItem": comparison, "category": 0, "property": ""}
    explore = ("https://trends.google.com/trends/api/explore?hl=en-US&tz=-480"
               f"&req={urllib.parse.quote(json.dumps(req))}&geo={geo}")
    widgets = json.loads(_get(explore))["widgets"]
    ts = next(w for w in widgets if w.get("id") == "TIMESERIES")
    time.sleep(1.0)
    multiline = ("https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=-480"
                 f"&req={urllib.parse.quote(json.dumps(ts['request']))}"
                 f"&token={urllib.parse.quote(ts['token'])}")
    data = json.loads(_get(multiline))["default"]["timelineData"]
    out: dict[str, list[tuple[str, float]]] = {t: [] for t in terms}
    for point in data:
        stamp = int(point["time"])
        d = date(1970, 1, 1) + timedelta(seconds=stamp)
        for idx, t in enumerate(terms):
            out[t].append((d.isoformat(), float(point["value"][idx])))
    return out


def _rows_from_recorded() -> list[dict]:
    rows: list[dict] = []
    start = date(2025, 7, 20)
    recorded = dict(RECORDED_WEEKLY)
    for i in range(53):
        d = (start + timedelta(weeks=i)).isoformat()
        rows.append({
            "granularity": "weekly", "date": d, "term": ANCHOR,
            "value": recorded.get(d, 0), "geo": "US",
            "provenance": "recorded_2026-07-26",
        })
    for d, v in RECORDED_DAILY:
        rows.append({
            "granularity": "daily", "date": d, "term": ANCHOR,
            "value": v, "geo": "US", "provenance": "recorded_2026-07-26",
        })
    return rows


def collect() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    status = {"weekly": "", "daily": "", "errors": []}

    _prime_cookies()
    for attempt in range(2):
        try:
            weekly = fetch_series([ANCHOR], "today 12-m")
            for d, v in weekly[ANCHOR]:
                rows.append({"granularity": "weekly", "date": d, "term": ANCHOR,
                             "value": v, "geo": "US", "provenance": "live_fetch"})
            status["weekly"] = "live_fetch"
            break
        except Exception as e:
            status["errors"].append(f"weekly attempt{attempt + 1}: {type(e).__name__}: {e}")
            time.sleep(4)

    if status["weekly"] == "live_fetch":
        try:
            time.sleep(1.5)
            daily = fetch_series([ANCHOR], "2026-05-15 2026-07-15")
            for d, v in daily[ANCHOR]:
                rows.append({"granularity": "daily", "date": d, "term": ANCHOR,
                             "value": v, "geo": "US", "provenance": "live_fetch"})
            status["daily"] = "live_fetch"
        except Exception as e:
            status["errors"].append(f"daily: {type(e).__name__}: {e}")

    if not rows:
        rows = _rows_from_recorded()
        status["weekly"] = status["daily"] = "recorded_2026-07-26"

    return rows, status


def summarize(rows: list[dict]) -> dict:
    weekly = [r for r in rows if r["granularity"] == "weekly"]
    daily = [r for r in rows if r["granularity"] == "daily"]
    zero_weeks = sum(1 for r in weekly if float(r["value"]) == 0)
    vals = [float(r["value"]) for r in weekly]
    nonzero_daily = [r for r in daily if float(r["value"]) > 0]
    peak = max(daily, key=lambda r: float(r["value"])) if daily else None
    zero_since = ""
    for r in sorted(daily, key=lambda r: r["date"]):
        if peak and r["date"] > peak["date"] and float(r["value"]) == 0:
            zero_since = r["date"]
            break
    return {
        "weeks_observed": len(weekly),
        "weeks_at_zero": zero_weeks,
        "weekly_mean_index": round(sum(vals) / len(vals), 2) if vals else 0.0,
        "alive_days": len(nonzero_daily),
        "peak_date": peak["date"] if peak else "",
        "zero_since": zero_since,
        "provenance": sorted({r["provenance"] for r in rows}),
    }


def main() -> dict:
    enable_utf8_stdout()
    rows, status = collect()
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "trends_measured.csv"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["granularity", "date", "term", "value", "geo", "provenance"],
                       lineterminator="\n")
    w.writeheader()
    w.writerows(sorted(rows, key=lambda r: (r["granularity"], r["date"])))
    path.write_text("\ufeff" + buf.getvalue(), encoding="utf-8")

    summary = summarize(rows)
    summary["status"] = status
    (DATA / "trends_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已写入 {path}（{len(rows)} 行）")
    print(f"取数方式: weekly={status['weekly'] or '失败'} daily={status['daily'] or '失败'}")
    for e in status["errors"]:
        print(f"  抓取异常: {e}")
    print(f"53 周中为 0 的周数: {summary['weeks_at_zero']} / {summary['weeks_observed']}")
    print(f"周均热度指数: {summary['weekly_mean_index']}  存活天数: {summary['alive_days']}")
    print(f"峰值日: {summary['peak_date']}  归零起始: {summary['zero_since']}")
    return summary


if __name__ == "__main__":
    main()
