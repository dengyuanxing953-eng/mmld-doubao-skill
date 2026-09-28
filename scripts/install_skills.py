#!/usr/bin/env python3
"""Install this public skill bundle locally; backs up changed files, never deletes unknown files."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def merge_agent(existing, incoming):
    """Update single-line interface metadata, preserving policy/dependencies and extra fields."""
    values = dict(re.findall(r"^  (display_name|short_description|default_prompt): (.+)$", incoming, re.M))
    if not re.search(r"^interface:\s*$", existing, re.M):
        header = "interface:\n" + "".join(f"  {key}: {value}\n" for key, value in values.items())
        return header + existing
    result = existing
    for key, value in values.items():
        pattern = r"^  " + key + r":.*$"
        match = re.search(pattern, result, re.M)
        if match:
            if match.group(0).split(":", 1)[1].strip().startswith(("|", ">")):
                raise ValueError("multiline interface field requires manual merge: " + key)
            result = result[:match.start()] + f"  {key}: {value}" + result[match.end():]
        else:
            result = re.sub(r"^interface:\s*$", lambda m: m.group(0) + f"\n  {key}: {value}", result, count=1, flags=re.M)
    return result


def source_files():
    primary = [Path(p) for p in ("SKILL.md", "README.md", "manifest.json", "mmld_doubao_v2.py",
                                 "scripts/__init__.py", "scripts/mmld_doubao_v2.py", "agents/openai.yaml")]
    primary += [p.relative_to(ROOT) for p in (ROOT / "references").rglob("*") if p.is_file()]
    primary += [p.relative_to(ROOT) for p in (ROOT / "examples").rglob("*") if p.is_file()]
    result = {"doubao-skills": [(ROOT / p, p) for p in primary]}
    for name in ("geo-multiplatform-workflow", "geo-automonitor"):
        folder = ROOT / "skills" / name
        result[name] = [(p, p.relative_to(folder)) for p in folder.rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    return result


def plan_install(target, legacy_alias=False):
    target = target.resolve()
    sources = source_files()
    if legacy_alias:
        sources["mmld-doubao"] = sources["doubao-skills"]
    plan = []
    for name, items in sources.items():
        for source, rel in items:
            destination = (target / name / rel).resolve()
            if not destination.is_relative_to(target):
                raise ValueError("destination escapes target via symlink: " + str(destination))
            incoming = source.read_text(encoding="utf-8")
            if rel.as_posix() == "manifest.json":
                manifest = json.loads(incoming)
                manifest["companion_skills"] = ["../geo-multiplatform-workflow", "../geo-automonitor"]
                if name == "mmld-doubao":
                    manifest["name"] = name
                    manifest["alias_of"] = "doubao-skills"
                incoming = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            if name == "mmld-doubao":
                if rel.as_posix() == "SKILL.md":
                    incoming = incoming.replace("name: doubao-skills\n", "name: mmld-doubao\n", 1)
                    incoming = re.sub(r"^description: .+$", "description: 兼容已有MMLD-Doubao任务的豆包来源与内容规划，保留旧命令入口；新的跨AI来源研究优先使用doubao-skills。", incoming, count=1, flags=re.M)
                elif rel.as_posix() == "agents/openai.yaml":
                    incoming = incoming.replace("$doubao-skills", "$mmld-doubao")
            if destination.exists():
                old = destination.read_text(encoding="utf-8-sig")
                if rel.as_posix() == "agents/openai.yaml":
                    incoming = merge_agent(old, incoming)
                if old == incoming:
                    continue
            plan.append((destination, incoming))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="skills directory to update")
    parser.add_argument("--legacy-alias", action="store_true", help="also refresh existing mmld-doubao name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        plan = plan_install(args.target, args.legacy_alias)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = args.target.resolve()
    backup = target.parent / "skill-backups" / ("geo-" + stamp)
    if not args.dry_run:
        for dest, content in plan:
            if dest.exists():
                copy = backup / dest.relative_to(target)
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, copy)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
    print(json.dumps({"dry_run": args.dry_run, "files_changed": len(plan),
                      "backup": None if args.dry_run else str(backup),
                      "destinations": [str(p) for p, _ in plan]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
