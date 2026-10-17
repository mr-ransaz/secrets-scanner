"""Exercise an installed CLI or executable with temporary synthetic input."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_checks(command: list[str], work: Path) -> None:
    secret = "AKIA" + "7ZQ2" * 4
    tree = work / "tree"
    tree.mkdir(parents=True)
    sample = tree / "sample.txt"
    baseline = work / "baseline.json"
    report = work / "report.html"

    def invoke(arguments: list[str], expected: int) -> str:
        process = subprocess.run(
            command + arguments,
            cwd=work,
            capture_output=True,
            input="",
            text=True,
            timeout=60,
            check=False,
        )
        if secret in process.stdout or secret in process.stderr:
            raise RuntimeError("masking check failed")
        if process.returncode != expected:
            raise RuntimeError("exit code check failed")
        return process.stdout

    if invoke(["--version"], 0).strip() != "secretscan 0.1.0":
        raise RuntimeError("version check failed")
    if "aws-access-key" not in invoke(["rules"], 0):
        raise RuntimeError("rules check failed")
    sample.write_text("harmless\n", encoding="utf-8")
    invoke(["scan", str(tree)], 0)
    sample.write_text(secret + "\n", encoding="utf-8")
    text = invoke(["scan", str(tree), "--no-color"], 1)
    if "AK****Q2" not in text:
        raise RuntimeError("text check failed")
    data = json.loads(invoke(["scan", str(tree), "--format", "json"], 1))
    if not data["findings"] or data["findings"][0]["rule_id"] != "aws-access-key":
        raise RuntimeError("JSON check failed")
    output = work / "results.sarif"
    invoke(
        [
            "scan",
            str(tree),
            "--format",
            "sarif",
            "--output",
            str(output),
            "--report",
            str(report),
            "--write-baseline",
            str(baseline),
        ],
        1,
    )
    sarif = json.loads(output.read_text(encoding="utf-8"))
    if sarif["version"] != "2.1.0" or not sarif["runs"][0]["results"]:
        raise RuntimeError("SARIF check failed")
    for artifact in (output, report, baseline):
        if secret in artifact.read_text(encoding="utf-8"):
            raise RuntimeError("artifact masking check failed")
    if "AK****Q2" not in report.read_text(encoding="utf-8"):
        raise RuntimeError("HTML check failed")
    invoke(["scan", str(tree), "--baseline", str(baseline)], 0)
    invoke(["scan", str(tree), "--report", str(report)], 2)
    invoke(["scan", str(work / "missing")], 2)
    invoke(["scan", str(tree), "--unknown"], 2)


def run_startup_checks(command: list[str], work: Path) -> None:
    for arguments in ([], [str(work / "tree")], [str(work / "missing")]):
        process = subprocess.run(
            command + arguments,
            cwd=work,
            input="\n",
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        text = process.stdout + process.stderr
        if process.returncode != 2 or "use --help" not in text:
            raise RuntimeError("redirected startup did not preserve CLI usage errors")
        if any(
            prompt in text
            for prompt in ("Folder path", "Open HTML report", "Press Enter")
        ):
            raise RuntimeError("redirected startup prompted for input")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--python", type=Path)
    args = parser.parse_args()
    command = (
        [str(args.exe.resolve())]
        if args.exe
        else [
            str(args.python.resolve()) if args.python else sys.executable,
            "-m",
            "secretscan",
        ]
    )
    parent = Path(__file__).resolve().parents[1] / ".work" / "smoke"
    parent.mkdir(parents=True, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(prefix="run-", dir=parent)
    try:
        run_checks(command, Path(scratch.name))
        run_startup_checks(command, Path(scratch.name))
        print("smoke: text/json/sarif/html, exits 0/1/2, baseline, masking: PASS")
        print("startup: redirected no-args/folder/missing, exit 2, no prompts: PASS")
        return 0
    except OSError, ValueError, RuntimeError, subprocess.SubprocessError:
        print("smoke: FAIL (no raw process output displayed)", file=sys.stderr)
        return 1
    finally:
        scratch.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
