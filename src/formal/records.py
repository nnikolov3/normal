"""Outcome records shared by validation checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A detected defect that fails the run."""

    check_id: str
    path: str
    detail: str


@dataclass(frozen=True)
class ExceptionRecord:
    """A check that could not run, recorded instead of silently skipped."""

    check_id: str
    path: str
    detail: str
