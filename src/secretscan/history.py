"""Offline, bounded Git reads. Merge commits are compared to their first parent."""

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

from secretscan.scanner import (
    DEFAULT_EXCLUDES,
    Result,
    ScanError,
    excluded,
    redact_metadata,
    scan_line,
)

MAX_GIT_OUTPUT = 8 * 1048576
GIT_TIMEOUT = 30
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def git_read(
    executable: str, cwd: Path, arguments: list[str], limit: int = MAX_GIT_OUTPUT
) -> bytes:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("GIT_") or k == "GIT_CEILING_DIRECTORIES"
    }
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_OPTIONAL_LOCKS="0",
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_LITERAL_PATHSPECS="1",
    )
    command = [
        executable,
        "--no-pager",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "protocol.allow=never",
        *arguments,
    ]
    try:
        with subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ) as process:
            timer = threading.Timer(GIT_TIMEOUT, process.kill)
            timer.start()
            try:
                content = process.stdout.read(limit + 1)
                if len(content) > limit:
                    process.kill()
                    raise ScanError("git output exceeds safe size limit")
                code = process.wait()
                if code:
                    raise ScanError(
                        "git read failed: check repository, HEAD and local objects"
                    )
                return content
            finally:
                timer.cancel()
    except OSError:
        raise ScanError("cannot execute system git") from None


def scan_history(
    root: Path,
    result: Result,
    *,
    max_commits: int = 200,
    minimum: str = "low",
    excludes: tuple[str, ...] = (),
    max_file_size: int = 1048576,
    baseline: set[str] | None = None,
    _sensitive: set[str] | None = None,
) -> None:
    sensitive = set() if _sensitive is None else _sensitive
    executable = shutil.which("git")
    if not executable:
        raise ScanError("git is required for --git-history")
    cwd = root if root.is_dir() else root.parent
    repo = Path(
        git_read(executable, cwd, ["rev-parse", "--show-toplevel"]).decode().strip()
    ).resolve()
    base = root if root.is_dir() else root.parent
    commits = (
        git_read(
            executable,
            cwd,
            ["rev-list", "--parents", f"--max-count={max_commits}", "HEAD"],
        )
        .decode()
        .splitlines()
    )
    result.git_history = True
    for entry in commits:
        commit, *parents = entry.split()
        revision = [parents[0], commit] if parents else ["--root", commit]
        names = (
            git_read(
                executable,
                repo,
                [
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-z",
                    "-r",
                    "--no-renames",
                    "--diff-filter=AM",
                    *revision,
                ],
            )
            .decode("utf-8", "replace")
            .split("\0")
        )
        for name in filter(None, names):
            path = repo / name
            if not path.is_relative_to(base) or (root.is_file() and path != root):
                continue
            relative = path.relative_to(base).as_posix()
            if excluded(relative, DEFAULT_EXCLUDES + excludes):
                result.skip("history-excluded")
                continue
            tree = git_read(
                executable, repo, ["ls-tree", "-l", "-z", commit, "--", name]
            )
            metadata = tree.split(b"\t", 1)[0].split()
            if metadata[0] not in (b"100644", b"100755"):
                result.skip("history-special")
                continue
            if int(metadata[3]) > max_file_size:
                result.skip("history-oversize")
                continue
            blob = git_read(
                executable,
                repo,
                ["cat-file", "blob", metadata[2].decode()],
                max_file_size,
            )
            if b"\0" in blob:
                result.skip("history-binary")
                continue
            patch = git_read(
                executable,
                repo,
                [
                    "diff-tree",
                    "--no-commit-id",
                    "-p",
                    "-r",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--text",
                    "--no-color",
                    "--no-renames",
                    "--unified=0",
                    *revision,
                    "--",
                    name,
                ],
            )
            number = None
            result.files_scanned += 1
            for line in patch.decode("utf-8", "replace").split("\n"):
                hunk = HUNK.match(line)
                if hunk:
                    number = int(hunk[1])
                elif number is not None and line.startswith("+"):
                    result.findings.extend(
                        scan_line(
                            line[1:],
                            relative,
                            number,
                            minimum,
                            baseline,
                            commit,
                            sensitive,
                        )
                    )
                    number += 1
                elif number is not None and line.startswith(" "):
                    number += 1
    redact_metadata(result, sensitive)
