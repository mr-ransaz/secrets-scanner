"""Command line boundary: no external exception text is displayed."""

import argparse
import json
import re
import sys
from pathlib import Path

from secretscan import __version__
from secretscan.guided import bare_directory, guided_mode, run_guided
from secretscan.history import scan_history
from secretscan.reports import html_report, sarif
from secretscan.rules import RULES
from secretscan.scanner import Result, ScanError, scan


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "secretscan: error: invalid arguments; use --help\n")


def parser() -> Parser:
    cli = Parser(prog="secretscan", description="Offline defensive secret scanner")
    cli.add_argument("--version", action="version", version=f"secretscan {__version__}")
    commands = cli.add_subparsers(dest="command", required=True, parser_class=Parser)
    commands.add_parser("rules", help="list detection rules")
    command = commands.add_parser("scan", help="scan a file or directory")
    command.add_argument("path", type=Path)
    command.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    command.add_argument("--report", type=Path)
    command.add_argument("--git-history", action="store_true")
    command.add_argument("--max-commits", type=int, default=200)
    command.add_argument("--output", type=Path)
    command.add_argument(
        "--min-severity", choices=("low", "medium", "high"), default="low"
    )
    command.add_argument("--exclude", action="append", default=[])
    command.add_argument("--baseline", type=Path)
    command.add_argument("--write-baseline", type=Path)
    command.add_argument("--no-color", action="store_true")
    command.add_argument("--max-file-size", type=int, default=1048576)
    command.add_argument("--force", action="store_true")
    command.add_argument("--allow-in-tree", action="store_true")
    return cli


def load_baseline(path: Path | None) -> set[str]:
    if path is None:
        return set()
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
        values = content["fingerprints"]
        if not isinstance(values, list) or not all(
            isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in values
        ):
            raise ValueError
        return set(values)
    except OSError, ValueError, KeyError, TypeError:
        raise ScanError("cannot read baseline: expected fingerprint list") from None


def validate_destinations(
    paths: list[Path | None], root: Path, force: bool, allow_in_tree: bool
) -> None:
    seen = set()
    for path in paths:
        if path is None:
            continue
        resolved = path.resolve()
        if resolved in seen or resolved == root:
            raise ScanError(
                "output destinations conflict with each other or scan target"
            )
        seen.add(resolved)
        if root.is_dir() and resolved.is_relative_to(root) and not allow_in_tree:
            raise ScanError("output inside scan tree requires --allow-in-tree")
        if path.is_symlink() or path.is_junction() or (path.exists() and not force):
            raise ScanError("output exists; use --force for a regular file")
        if path.exists() and (not path.is_file() or path.stat().st_nlink > 1):
            raise ScanError("output must be a regular file without hard links")


def write(path: Path, content: str, force: bool) -> None:
    try:
        with path.open("w" if force else "x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    except OSError:
        raise ScanError("cannot write output file") from None


def text_output(result: Result) -> str:
    lines = [
        f"secretscan {result.version}: {result.files_scanned} files scanned, "
        f"{len(result.findings)} findings"
    ]
    lines.extend(
        f"{f.file}:{f.line}:{f.column_start} {f.severity} {f.rule_id} "
        f"{f.masked_preview} [{f.fingerprint[:12]}]"
        for f in result.findings
    )
    if result.skipped:
        lines.append(
            "Skipped: "
            + ", ".join(f"{k}={v}" for k, v in sorted(result.skipped.items()))
        )
    # Prevent terminal control sequences in hostile filenames.
    return (
        "\n".join(lines).encode("unicode_escape").decode("ascii").replace(r"\n", "\n")
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if guided_mode(arguments):
        return run_guided(arguments[0] if arguments else None)
    if bare_directory(arguments):
        print(
            "secretscan: error: use 'scan PATH' for a folder in a terminal; "
            "use --help for usage",
            file=sys.stderr,
        )
        return 2
    args = parser().parse_args(arguments)
    if args.command == "rules":
        for rule in RULES:
            print(f"{rule.id}\t{rule.severity}\t{rule.description}")
        return 0
    try:
        if args.max_file_size < 1 or args.max_commits < 1:
            raise ScanError("size and commit limits must be positive")
        if args.output and args.format == "text":
            raise ScanError("--output requires JSON or SARIF format")
        root = args.path.absolute()
        if root.is_symlink() or root.is_junction():
            raise ScanError("scan root must not be a symlink or junction")
        root = root.resolve()
        validate_destinations(
            [args.output, args.report, args.write_baseline],
            root,
            args.force,
            args.allow_in_tree,
        )
        baseline = load_baseline(args.baseline)
        sensitive = set()
        result = scan(
            root,
            minimum=args.min_severity,
            excludes=tuple(args.exclude),
            max_file_size=args.max_file_size,
            baseline=baseline,
            _sensitive=sensitive,
        )
        if args.git_history:
            scan_history(
                root,
                result,
                max_commits=args.max_commits,
                minimum=args.min_severity,
                excludes=tuple(args.exclude),
                max_file_size=args.max_file_size,
                baseline=baseline,
                _sensitive=sensitive,
            )
        output = (
            json.dumps(
                sarif(result) if args.format == "sarif" else result.to_dict(), indent=2
            )
            + "\n"
            if args.format != "text"
            else text_output(result)
        )
        if args.output:
            write(args.output, output, args.force)
        else:
            print(output, end="")
        if args.report:
            write(args.report, html_report(result), args.force)
        if args.write_baseline:
            data = {
                "fingerprints": sorted(
                    baseline | {f.fingerprint for f in result.findings}
                )
            }
            write(args.write_baseline, json.dumps(data, indent=2) + "\n", args.force)
        return int(bool(result.findings))
    except (ScanError, OSError, ValueError, OverflowError) as error:
        # Constant errors avoid leaking secret-bearing paths or OS exception details.
        message = (
            str(error)
            if isinstance(error, ScanError)
            else "cannot access scan or output path"
        )
        print(f"secretscan: error: {message}", file=sys.stderr)
        return 2
