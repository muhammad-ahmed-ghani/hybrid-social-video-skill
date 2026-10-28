#!/usr/bin/env python3
"""fx_assets.py - fetch, verify and locate the third-party files the person-aware effects use.

    python3 fx_assets.py status            # what is cached, what is missing
    python3 fx_assets.py fetch [name ...]  # download (default: everything), resumable, size and sha256 checked
    python3 fx_assets.py path modnet       # print the cached path (exit 1 if absent)

The list is data/assets.json. Files go to ~/.cache/social-explainer-reel (override with the SER_CACHE environment variable), never into the
skill. A file that is the wrong size or hash is deleted and refused, so a moved or tampered upstream file can never be used; the callers
fall back (a system font, a cruder matte). Offline is a valid state. Exit 0 ok | 1 something missing or refused | 2 usage.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CATALOG = SKILL_DIR / "data" / "assets.json"


def cache_dir() -> Path:
    return Path(os.environ.get("SER_CACHE") or (Path.home() / ".cache" / "social-explainer-reel"))


def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))["assets"]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verified(name: str) -> Path | None:
    """The cached file if it exists and matches its pinned size and hash, else None (a bad file is removed)."""
    spec = catalog()[name]
    p = cache_dir() / spec["file"]
    if not p.is_file():
        return None
    if p.stat().st_size != spec["bytes"] or _sha(p) != spec["sha256"]:
        try:
            p.unlink()
        except OSError:
            pass
        return None
    return p


def _download(spec: dict, dest: Path, tries: int = 4) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    for _ in range(tries):
        have = part.stat().st_size if part.exists() else 0
        if have > spec["bytes"]:
            part.unlink()
            have = 0
        req = urllib.request.Request(spec["url"], headers={"User-Agent": "social-explainer-reel-skill", **({"Range": f"bytes={have}-"} if have else {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if have and r.status != 206:      # the server ignored the range: start over
                    have = 0
                with open(part, "ab" if have else "wb") as fh:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
        except Exception:                         # network drop: the loop resumes from the bytes already on disk
            continue
        if part.exists() and part.stat().st_size == spec["bytes"]:
            part.replace(dest)
            return True
    return False


def ensure(name: str, quiet: bool = True) -> Path | None:
    """Return the verified path, downloading it first if needed. None when offline or refused."""
    if name not in catalog():
        return None
    got = verified(name)
    if got:
        return got
    spec = catalog()[name]
    dest = cache_dir() / spec["file"]
    if not quiet:
        print(f"fetching {name} ({spec['bytes'] // 1024} KB, {spec['licence']}) ...", file=sys.stderr)
    if not _download(spec, dest):
        return None
    return verified(name)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("status", "fetch", "path"):
        print(__doc__)
        return 2
    cmd, names = argv[0], argv[1:]
    cat = catalog()
    for n in names:
        if n not in cat:
            print(f"unknown asset: {n}. known: {', '.join(cat)}", file=sys.stderr)
            return 2
    names = names or list(cat)
    if cmd == "path":
        p = verified(names[0])
        print(p or "")
        return 0 if p else 1
    bad = 0
    for n in names:
        p = ensure(n, quiet=False) if cmd == "fetch" else verified(n)
        state = "ok " if p else "MISSING"
        bad += 0 if p else 1
        print(f"{state:8}{n:24}{cat[n]['kind']:6}{cat[n]['licence']:11}{p or ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
