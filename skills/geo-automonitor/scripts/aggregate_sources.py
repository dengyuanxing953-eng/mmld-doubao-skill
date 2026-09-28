#!/usr/bin/env python3
"""Summarize local AI observations without treating missing sources as zero."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

KINDS = {"natural", "url_seeded", "self_report", "other"}
STATUSES = {"answered", "blocked", "error"}
CAPTURES = {"complete", "partial", "not_captured"}
TRACKING = {"from", "enter_from", "spm", "source"}
SENSITIVE_QUERY = {"token", "access_token", "api_key", "password", "authkey", "signature"}
PLATFORMS = {
    "toutiao.com": "toutiao", "douyin.com": "douyin", "iesdouyin.com": "douyin",
    "zhihu.com": "zhihu", "sohu.com": "sohu", "bilibili.com": "bilibili",
    "mp.weixin.qq.com": "wechat", "baijiahao.baidu.com": "baijiahao",
    "qcc.com": "qcc", "shuidi.cn": "shuidi", "qixin.com": "qixin",
    "tianyancha.com": "tianyancha", "aiqicha.baidu.com": "aiqicha",
    "cctalk.com": "cctalk", "xfb315.com": "xfb315",
    "tousu.sina.com.cn": "blackcat", "tousu.sina.cn": "blackcat",
    "xiaoe-tech.com": "xiaoe", "xet.pomoho.com": "xiaoe",
    "zhipin.com": "boss", "liepin.com": "liepin", "zhaopin.com": "zhaopin",
    "51job.com": "51job", "smzdm.com": "smzdm", "xiaohongshu.com": "xiaohongshu",
    "news.qq.com": "qqnews", "new.qq.com": "qqnews", "baike.baidu.com": "baidu_baike",
}


def stamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp needs time zone")
    return dt


def host_matches(host, domain):
    return host == domain or host.endswith("." + domain)


def canonical_url(value):
    if not isinstance(value, str):
        raise ValueError("source url must be text")
    u = urlsplit(value)
    if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password:
        raise ValueError("source URL must be http(s) without credentials")
    host = u.hostname.lower()
    pairs = parse_qsl(u.query, keep_blank_values=True)
    if any(k.lower() in SENSITIVE_QUERY for k, _ in pairs):
        raise ValueError("credential-like query parameter; redact locally first")
    path = u.path or "/"
    if host_matches(host, "toutiao.com"):
        match = re.fullmatch(r"/(?:article|item|group)/(\d+)/?", path)
        if match:
            return "https://www.toutiao.com/item/" + match[1] + "/"
    if host_matches(host, "tousu.sina.com.cn") or host_matches(host, "tousu.sina.cn"):
        match = re.fullmatch(r"/complaint/view/(\d+)/?", path)
        if match:
            return "https://tousu.sina.com.cn/complaint/view/" + match[1] + "/"
    clean = sorted((k, v) for k, v in pairs if not k.lower().startswith("utm_") and k.lower() not in TRACKING)
    # Retain document-identifying parameters such as id, page and query.
    return urlunsplit((u.scheme.lower(), u.netloc.lower(), path, urlencode(clean), ""))


def platform_of(url):
    host = urlsplit(url).hostname or ""
    for domain in sorted(PLATFORMS, key=len, reverse=True):
        if host_matches(host, domain):
            return PLATFORMS[domain]
    return host


def latest_records(rows):
    if not isinstance(rows, list):
        raise ValueError("observations must be an array")
    latest = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("observation must be an object")
        for field in ("id", "engine", "surface", "mode", "question_id"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError("missing " + field)
        observed, updated = stamp(row.get("observed_at")), stamp(row.get("updated_at"))
        if updated < observed:
            raise ValueError("updated_at precedes observed_at")
        if row.get("status") not in STATUSES or row.get("capture") not in CAPTURES or row.get("prompt_kind") not in KINDS:
            raise ValueError("invalid status, capture or prompt_kind")
        sources = row.get("sources")
        if not isinstance(sources, list):
            raise ValueError("sources must be an array (empty if not captured)")
        declared = row.get("declared_source_count")
        if declared is not None and (type(declared) is not int or declared < 0):
            raise ValueError("declared_source_count must be null or nonnegative integer")
        if row["status"] != "answered" and (row["capture"] != "not_captured" or sources):
            raise ValueError("blocked/error observations cannot carry captured answer sources")
        if row["capture"] == "partial" and not sources:
            raise ValueError("partial capture needs at least one entry; otherwise use not_captured")
        if row["capture"] == "not_captured" and sources:
            raise ValueError("not_captured requires empty sources")
        if declared is not None and len(sources) > declared:
            raise ValueError("captured entries exceed declared source count")
        if row["capture"] == "complete" and declared is not None and len(sources) != declared:
            raise ValueError("complete capture must reconcile the declared source count")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("source must be an object")
            if source.get("url"):
                canonical_url(source["url"])
            elif not isinstance(source.get("label"), str) or not source["label"].strip():
                raise ValueError("source needs URL or label")
            if type(source.get("body_supported", False)) is not bool:
                raise ValueError("body_supported must be boolean")
            if source.get("body_supported") and not (source.get("url") and source.get("support_excerpt") and source.get("support_evidence")):
                raise ValueError("body support needs URL, excerpt and verification evidence")
        # Product/surface/question context is immutable for one observation ID.
        if row["id"] in latest:
            old = latest[row["id"]]
            for field in ("engine", "surface", "mode", "question_id", "prompt_kind"):
                if old[field] != row[field]:
                    raise ValueError("observation ID reused across incompatible conditions")
            old_time = stamp(old["updated_at"])
            if old_time == updated and old != row:
                raise ValueError("conflicting records have same ID and timestamp")
            if old_time > updated:
                continue
        latest[row["id"]] = row
    return list(latest.values())


def summarize(rows):
    records = latest_records(rows)
    buckets = {}
    for row in records:
        key = (row["engine"], row["surface"], row["mode"], row["prompt_kind"])
        buckets.setdefault(key, []).append(row)
    groups = []
    for key, subset in sorted(buckets.items()):
        valid = [r for r in subset if r["status"] == "answered"]
        complete = [r for r in valid if r["capture"] == "complete"]
        captured = [r for r in valid if r["capture"] != "not_captured"]
        urls, support_urls = set(), set()
        appearances, coverage = Counter(), Counter()
        raw_count = label_count = 0
        for r in captured:
            seen_platforms = set()
            for s in r["sources"]:
                if not s.get("url"):
                    label_count += 1
                    continue
                url = canonical_url(s["url"])
                platform = platform_of(url)
                raw_count += 1
                urls.add(url)
                appearances[platform] += 1
                seen_platforms.add(platform)
                if s.get("body_supported"):
                    support_urls.add(url)
            coverage.update(seen_platforms)
        dates = sorted({stamp(r["observed_at"]).date().isoformat() for r in valid})
        groups.append({
            "engine": key[0], "surface": key[1], "mode": key[2], "prompt_kind": key[3],
            "planned_observations": len(subset), "valid_answers": len(valid),
            "blocked": sum(r["status"] == "blocked" for r in subset),
            "errors": sum(r["status"] == "error" for r in subset),
            "complete_captures": len(complete),
            "partial_captures": sum(r["capture"] == "partial" for r in valid),
            "uncaptured_answers": sum(r["capture"] == "not_captured" for r in valid),
            "source_url_appearances": raw_count if captured else None,
            "unique_source_urls": len(urls) if captured else None,
            "label_only_entries": label_count if captured else None,
            "explicit_zero_source_answers": sum(not r["sources"] for r in complete),
            "platform_url_appearances": dict(sorted(appearances.items())),
            "platform_answer_coverage": dict(sorted(coverage.items())),
            "verified_support_unique_urls": len(support_urls) if captured else None,
            "observed_dates": dates,
            "stable_effect": None, "causal_effect": None,
        })
    return {"schema_version": 1, "retained_observations": len(records), "groups": groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.file.read_text(encoding="utf-8-sig"))
        rows = data.get("observations") if isinstance(data, dict) else data
        result = summarize(rows)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
