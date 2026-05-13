#!/usr/bin/env python3
"""Lint YAML tool configs for dangerous patterns in install_hints.

Runs in CI on every PR that touches configs/tools/*.yaml.
Exits non-zero if any hint matches a blocked pattern.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Patterns that are never acceptable in install_hints.
_BLOCKED: list[tuple[str, str]] = [
    (r"rm\s+-[rf]", "destructive rm"),
    (r"\|\s*(ba)?sh\b", "piping to shell (curl|bash style RCE)"),
    (r"\|\s*python", "piping to python"),
    (r"`[^`]+`", "backtick subshell"),
    (r"\$\([^)]+\)", "subshell $()"),
    (r">\s*/etc/", "writing to /etc/"),
    (r">\s*/usr/", "writing to /usr/"),
    (r">\s*/root/", "writing to /root/"),
    (r"chmod\s+[0-7]*7[0-7]{2}", "world-writable chmod"),
    (r"base64\s+--decode\s*\|", "decode-and-pipe"),
    (r"eval\s+", "eval"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), label) for pat, label in _BLOCKED]


def _is_executable(hint: str) -> bool:
    """Mirror of install._is_executable — hints with shell operators are display-only."""
    stripped = hint.strip()
    if "&&" in stripped or "|" in stripped:
        return False
    _PREFIXES = (
        "pip ", "pip3 ", "git ", "cmake ", "curl ", "python ", "python3 ",
        "sudo ", "./", "docker ", "export ",
    )
    return any(stripped.startswith(p) for p in _PREFIXES)


def lint_file(path: Path) -> list[str]:
    errors: list[str] = []
    with open(path) as f:
        data = yaml.safe_load(f)

    chips: dict = data.get("chips", {})
    for chip, chip_data in chips.items():
        hints: list[str] = chip_data.get("install_hints", [])
        for hint in hints:
            if not _is_executable(hint):
                continue  # display-only hints are never auto-executed
            for pattern, label in _COMPILED:
                if pattern.search(hint):
                    errors.append(f"  [{path.name}] {chip}: {label!r} in hint: {hint!r}")
    return errors


def main() -> int:
    config_dir = Path(__file__).parent.parent / "configs" / "tools"
    yaml_files = sorted(config_dir.glob("*.yaml"))

    if not yaml_files:
        print("lint_configs: no YAML files found", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for path in yaml_files:
        all_errors.extend(lint_file(path))

    if all_errors:
        print("lint_configs: dangerous patterns found in install_hints:\n")
        for err in all_errors:
            print(err)
        print(f"\n{len(all_errors)} issue(s) found.")
        return 1

    print(f"lint_configs: {len(yaml_files)} configs OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
