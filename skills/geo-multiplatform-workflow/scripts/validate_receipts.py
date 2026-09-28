#!/usr/bin/env python3
"""Validate local publishing evidence. Never contacts a publishing platform."""
from __future__ import annotations
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

STATES = {"prepared", "draft_confirmed", "submitted", "pending_review",
          "published_backend_confirmed", "public_body_verified", "blocked", "outcome_unknown"}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp needs an explicit time zone")
    return result


def public_url(value):
    if not isinstance(value, str):
        return False
    try:
        u = urlsplit(value)
        return bool(u.scheme in {"http", "https"} and u.hostname and not u.username
                    and not u.password and not re.search(
                        r"/(?:edit|preview|draft|builder|creator)(?:/|$)", u.path, re.I))
    except ValueError:
        return False


def evidence(row, field):
    value = row.get(field)
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value)


def validate(rows):
    if not isinstance(rows, list):
        return ["receipts must be an array"]
    errors = []
    for i, row in enumerate(rows):
        prefix = f"row {i}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: expected object")
            continue
        state = row.get("state")
        if state not in STATES:
            errors.append(f"{prefix}: unknown state")
        if not isinstance(row.get("platform"), str) or not row["platform"].strip():
            errors.append(f"{prefix}: missing platform")
        try:
            timestamp(row.get("observed_at"))
        except (ValueError, TypeError):
            errors.append(f"{prefix}: invalid observed_at")
        if state in {"blocked", "outcome_unknown"}:
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                errors.append(f"{prefix}: missing reason")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("content_hash", ""))):
            errors.append(f"{prefix}: content_hash must be a SHA-256 hex digest")
        scope = row.get("account_scope")
        if not isinstance(scope, str) or not scope.strip():
            errors.append(f"{prefix}: missing account_scope")
        elif state != "prepared" and scope in {"unknown", "not_verified"}:
            errors.append(f"{prefix}: account scope is unverified")
        required = {
            "draft_confirmed": ["draft_evidence"],
            "submitted": ["submission_evidence"],
            "pending_review": ["submission_evidence"],
            "published_backend_confirmed": ["backend_evidence"],
            "public_body_verified": ["backend_evidence", "readback_evidence"],
        }.get(state, [])
        for field in required:
            if not evidence(row, field):
                errors.append(f"{prefix}: missing {field}")
        if state in {"published_backend_confirmed", "public_body_verified"} and not public_url(row.get("public_url")):
            errors.append(f"{prefix}: public_url is missing or is an editor/preview URL")
        if state == "public_body_verified":
            expected, actual = row.get("expected_image_count"), row.get("observed_image_count")
            if any(type(n) is not int or n < 0 for n in (expected, actual)):
                errors.append(f"{prefix}: image counts must be nonnegative integers")
            elif actual != expected:
                errors.append(f"{prefix}: image count mismatch")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.file.read_text(encoding="utf-8-sig"))
        rows = data.get("receipts") if isinstance(data, dict) else data
        errors = validate(rows)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
