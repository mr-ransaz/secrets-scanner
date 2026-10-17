"""Safe file traversal and masked-only result objects."""

import fnmatch
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from secretscan import __version__
from secretscan.rules import (
    LEVELS,
    RULES,
    accepted,
    fingerprint,
    mask,
    match_value,
    safe_label,
)

DEFAULT_EXCLUDES = (
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".work",
    ".pytest_cache",
    ".ruff_cache",
    "*.egg-info",
    ".coverage",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.pdf",
    "*.zip",
    "*.exe",
    "*.dll",
    "*.pyc",
    "*.whl",
    "*.gz",
    "*.ico",
    "*.mp4",
    "*.sqlite",
    "*.db",
)


class ScanError(Exception):
    """Public errors use constant messages, never raw external exceptions."""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int
    column_start: int
    column_end: int
    masked_preview: str
    fingerprint: str
    commit: str | None = None


@dataclass
class Result:
    root_name: str
    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    git_history: bool = False
    version: str = __version__
    time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        self.root_name = safe_label(self.root_name)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def to_dict(self) -> dict:
        return asdict(self)


def scan_line(
    text: str,
    path: str,
    number: int,
    minimum: str = "low",
    baseline: set[str] | None = None,
    commit: str | None = None,
) -> list[Finding]:
    if "secretscan:ignore" in text:
        return []
    findings = []
    for rule in RULES:
        if LEVELS[rule.severity] < LEVELS[minimum]:
            continue
        for match in rule.pattern.finditer(text):
            value, start, end = match_value(rule, match)
            if not accepted(rule, value):
                continue
            digest = fingerprint(rule.id, path, value)
            if baseline and digest in baseline:
                continue
            findings.append(
                Finding(
                    rule.id,
                    rule.severity,
                    safe_label(path),
                    number,
                    start + 1,
                    end + 1,
                    mask(value),
                    digest,
                    commit,
                )
            )
    return findings


def excluded(path: str, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatchcase(part.lower(), p.lower())
        or fnmatch.fnmatchcase(path.lower(), p.lower())
        for p in patterns
        for part in path.split("/")
    )


def scan(
    root: Path,
    *,
    minimum: str = "low",
    excludes: tuple[str, ...] = (),
    max_file_size: int = 1048576,
    baseline: set[str] | None = None,
) -> Result:
    if not root.exists():
        raise ScanError("scan path does not exist")
    result = Result(root.name)
    patterns = DEFAULT_EXCLUDES + excludes
    base = root if root.is_dir() else root.parent

    def read(path: Path) -> None:
        relative = path.relative_to(base).as_posix()
        if excluded(relative, patterns):
            result.skip("excluded")
            return
        try:
            if path.is_symlink() or path.is_junction():
                result.skip("symlink")
                return
            if not path.is_file():
                result.skip("special")
                return
            with path.open("rb") as stream:
                content = stream.read(max_file_size + 1)
            if len(content) > max_file_size:
                result.skip("oversize")
                return
            if b"\0" in content:
                result.skip("binary")
                return
            result.files_scanned += 1
            for number, line in enumerate(
                content.decode("utf-8", errors="replace").splitlines(), 1
            ):
                result.findings.extend(
                    scan_line(line, relative, number, minimum, baseline)
                )
        except OSError:
            result.skip("unreadable")

    if root.is_symlink() or root.is_junction() or root.is_file():
        read(root)
    else:

        def walk_error(_: OSError) -> None:
            result.skip("unreadable")

        for folder, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            kept = []
            for name in sorted(dirs):
                path = Path(folder) / name
                if excluded(path.relative_to(base).as_posix(), patterns):
                    result.skip("excluded")
                elif path.is_symlink() or path.is_junction():
                    result.skip("symlink")
                else:
                    kept.append(name)
            dirs[:] = kept
            for name in sorted(files):
                read(Path(folder) / name)
    return result
