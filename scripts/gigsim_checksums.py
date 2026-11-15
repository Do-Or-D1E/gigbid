#!/usr/bin/env python
"""Write or verify gigsim/CHECKSUMS.sha256.

The simulator is part of the evaluation harness, so CI fails when it changes. The checksum file covers
every gigsim/**/*.py, gigsim/**/*.md and gigsim/seed/* file (CHECKSUMS.sha256 itself and __pycache__ are
excluded). Text is hashed with CRLF normalised to LF so Windows and Linux checkouts agree.

    uv run python scripts/gigsim_checksums.py --write     # (re)generate the file
    uv run python scripts/gigsim_checksums.py --verify    # exit 1 on any difference (default)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "gigsim"
CHECKSUM_FILE = PKG / "CHECKSUMS.sha256"


def tracked_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in ("**/*.py", "**/*.md"):
        files.update(PKG.glob(pattern))
    seed = PKG / "seed"
    if seed.is_dir():
        files.update(p for p in seed.rglob("*") if p.is_file())
    return sorted(
        (p for p in files if "__pycache__" not in p.parts and p != CHECKSUM_FILE and p.is_file()),
        key=lambda p: p.relative_to(ROOT).as_posix(),
    )


def digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def compute() -> dict[str, str]:
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in tracked_files()}


def render(sums: dict[str, str]) -> str:
    return "".join(f"{h}  {name}\n" for name, h in sums.items())


def read_recorded() -> dict[str, str]:
    out: dict[str, str] = {}
    if not CHECKSUM_FILE.exists():
        return out
    for line in CHECKSUM_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, name = line.split("  ", 1)
            out[name] = h
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="write gigsim/CHECKSUMS.sha256")
    g.add_argument("--verify", action="store_true", help="verify against gigsim/CHECKSUMS.sha256 (default)")
    args = ap.parse_args(argv)

    current = compute()
    if args.write:
        CHECKSUM_FILE.write_text(render(current), encoding="utf-8", newline="\n")
        print(f"wrote {CHECKSUM_FILE.relative_to(ROOT).as_posix()} ({len(current)} files)")
        return 0

    recorded = read_recorded()
    if not recorded:
        print(f"ERROR: {CHECKSUM_FILE.relative_to(ROOT).as_posix()} missing or empty; run with --write", file=sys.stderr)
        return 1
    problems = []
    for name in sorted(set(current) | set(recorded)):
        if name not in recorded:
            problems.append(f"added:    {name}")
        elif name not in current:
            problems.append(f"removed:  {name}")
        elif current[name] != recorded[name]:
            problems.append(f"modified: {name}")
    if problems:
        print("GigSim checksum mismatch (the simulator must not change):", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    print(f"GigSim checksums OK ({len(current)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
