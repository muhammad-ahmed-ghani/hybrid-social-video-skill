#!/usr/bin/env python3
"""Validate a skill folder and pack it into a .skill file (a zip with the skill folder at its root).

Usage: python3 tools/package_skill.py [skill-dir] [out-dir]
       python3 tools/package_skill.py --check      fail if dist/ is out of date with the skill folder
Defaults: skills/social-explainer-reel  dist/
Stdlib only. The archive is reproducible: sorted entries, fixed timestamps.
"""
from __future__ import annotations

import fnmatch
import re
import sys
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "node_modules", ".git"}
EXCLUDE_GLOBS = ["*.pyc", ".DS_Store"]
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def read_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("SKILL.md has no YAML frontmatter")
    out: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z_][\w-]*:", line):
            key, _, val = line.partition(":")
            val = val.strip()
            out[key] = "" if val in (">-", ">", "|", "|-") else val
        elif key and line.startswith(" ") and key in out and not line.strip().endswith(":"):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def validate(skill_dir: Path) -> dict[str, str]:
    fm = read_frontmatter(skill_dir / "SKILL.md")
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValueError(f"name must be kebab-case and at most 64 chars: {name!r}")
    if name != skill_dir.name:
        raise ValueError(f"name {name!r} must match the folder name {skill_dir.name!r}")
    if not desc or len(desc) > 1024:
        raise ValueError(f"description must be 1 to 1024 chars, got {len(desc)}")
    if "<" in desc or ">" in desc:
        raise ValueError("description must not contain angle brackets")
    return fm


def excluded(path: Path) -> bool:
    return any(p in EXCLUDE_DIRS for p in path.parts) or any(fnmatch.fnmatch(path.name, g) for g in EXCLUDE_GLOBS)


def package(skill_dir: Path, out_dir: Path) -> Path:
    validate(skill_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{skill_dir.name}.skill"
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file() and not excluded(p.relative_to(skill_dir)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            info = zipfile.ZipInfo(f"{skill_dir.name}/{f.relative_to(skill_dir).as_posix()}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if f.suffix in (".py", ".sh") else 0o644) << 16
            z.writestr(info, f.read_bytes())
    return out


def contents(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as z:
        return {n: z.read(n) for n in z.namelist()}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    if sys.argv[1:] == ["--check"]:
        import tempfile
        skill = root / "skills" / "social-explainer-reel"
        with tempfile.TemporaryDirectory() as tmp:
            fresh = package(skill, Path(tmp))
            committed = root / "dist" / fresh.name
            if not committed.exists() or contents(fresh) != contents(committed):
                sys.exit(f"{committed} is out of date: run python3 tools/package_skill.py and commit it")
        print("dist is current")
        sys.exit(0)
    skill = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "skills" / "social-explainer-reel"
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "dist"
    try:
        result = package(skill.resolve(), dest)
    except ValueError as e:
        sys.exit(f"invalid skill: {e}")
    with zipfile.ZipFile(result) as z:
        n = len(z.namelist())
    print(f"packed {n} files -> {result} ({result.stat().st_size // 1024} KB)")
