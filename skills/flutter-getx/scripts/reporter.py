"""Shared result reporting for the flutter-getx scripts.

Every script prints its human-readable progress through `out()` and records
what it did on the current `Result`. In normal use `out()` prints to stdout,
exactly as the scripts always have. When `getx --json` runs a script it calls
`set_json(True)`: progress moves to stderr, so stdout carries only the single
JSON object that `getx` prints from the collected `Result`.

Only the Python standard library is used.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_json_mode = False


class Result:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.modified: list[str] = []
        self.skipped: list[dict[str, str]] = []
        self.next: list[str] = []
        self.warnings: list[str] = []
        self.data: dict[str, Any] = {}
        self.error: str | None = None
        self.error_printed = False  # a script already showed the error to the user

    # -- recording helpers ------------------------------------------------
    def add_created(self, path: Any) -> None:
        _append_unique(self.created, _p(path))

    def add_modified(self, path: Any) -> None:
        p = _p(path)
        if p not in self.created:
            _append_unique(self.modified, p)

    def add_skipped(self, path: Any, reason: str) -> None:
        self.skipped.append({"path": _p(path), "reason": reason})

    def add_next(self, command: str) -> None:
        _append_unique(self.next, command)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def fail(self, message: str) -> None:
        if self.error is None:
            self.error = message

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ok": self.ok,
            "created": self.created,
            "modified": self.modified,
            "skipped": self.skipped,
            "next": self.next,
        }
        if self.warnings:
            d["warnings"] = self.warnings
        if self.data:
            d.update(self.data)
        if self.error is not None:
            d["error"] = self.error
        return d

    def merge(self, other: "Result") -> None:
        for p in other.created:
            self.add_created(p)
        for p in other.modified:
            self.add_modified(p)
        self.skipped.extend(other.skipped)
        for n in other.next:
            self.add_next(n)
        self.warnings.extend(other.warnings)
        self.data.update(other.data)
        if other.error and self.error is None:
            self.error = other.error


_current = Result()


def current() -> Result:
    return _current


def reset() -> Result:
    global _current
    _current = Result()
    return _current


def set_json(enabled: bool) -> None:
    global _json_mode
    _json_mode = enabled


def json_mode() -> bool:
    return _json_mode


def out(*args: Any, **kwargs: Any) -> None:
    """print() that moves to stderr while getx is producing JSON."""
    if _json_mode and kwargs.get("file") in (None, sys.stdout):
        kwargs["file"] = sys.stderr
    print(*args, **kwargs)


def _p(path: Any) -> str:
    return str(path) if not isinstance(path, Path) else path.as_posix()


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
