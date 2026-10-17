import html
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import lines, samples

from secretscan.cli import main
from secretscan.history import git_read, scan_history
from secretscan.reports import html_report, sarif
from secretscan.scanner import Result, ScanError, scan_line


def git(repo, *arguments):
    env = dict(
        os.environ,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_NAME="Synthetic Test",
        GIT_AUTHOR_EMAIL="test@example.org",
        GIT_COMMITTER_NAME="Synthetic Test",
        GIT_COMMITTER_EMAIL="test@example.org",
        GIT_AUTHOR_DATE="2026-01-01T00:00:00+0000",
        GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000",
    )
    run = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=", *arguments],
        cwd=repo,
        env=env,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, "temporary Git command failed"
    return run.stdout.decode().strip()


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "--initial-branch=main")
    sub = repo / "folder"
    sub.mkdir()
    (sub / "a&b.txt").write_text("harmless\n" + lines()["aws-access-key"] + "\n")
    (repo / "binary.txt").write_bytes(b"\0binary")
    (repo / "large.txt").write_text("a" * 201)
    (repo / "image.png").write_text("not scanned")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial synthetic fixture")
    first = git(repo, "rev-parse", "HEAD")
    (sub / "a&b.txt").write_text("harmless\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "remove synthetic fixture")
    return repo, first


def test_history_real(repository, capsys):
    repo, first = repository
    result = Result(repo.name)
    scan_history(repo, result, max_file_size=200)
    assert result.git_history
    assert result.skipped == {
        "history-binary": 1,
        "history-excluded": 1,
        "history-oversize": 1,
    }
    finding = next(f for f in result.findings if f.rule_id == "aws-access-key")
    assert (finding.file, finding.line, finding.commit) == ("folder/a&b.txt", 2, first)
    assert main(["scan", str(repo), "--git-history", "--format", "json"]) == 1
    assert samples()["aws-access-key"] not in capsys.readouterr().out
    limited = Result(repo.name)
    scan_history(repo, limited, max_commits=1)
    assert not limited.findings
    subset = Result("folder")
    scan_history(repo / "folder", subset)
    assert {f.file for f in subset.findings} == {"a&b.txt"}
    single = Result("single")
    scan_history(repo / "folder" / "a&b.txt", single)
    assert {f.file for f in single.findings} == {"a&b.txt"}
    known = Result("known")
    scan_history(
        repo,
        known,
        baseline={f.fingerprint for f in result.findings},
        excludes=("large.txt",),
    )
    assert not known.findings


def test_history_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert main(["scan", str(tmp_path), "--git-history"]) == 2
    assert "git read failed" in capsys.readouterr().err
    assert main(["scan", str(tmp_path), "--max-commits", "0"]) == 2
    monkeypatch.setattr("secretscan.history.shutil.which", lambda _: None)
    assert main(["scan", str(tmp_path), "--git-history"]) == 2
    assert "git is required" in capsys.readouterr().err
    with pytest.raises(ScanError, match="execute system git"):
        git_read(str(tmp_path / "missing-executable"), tmp_path, [])


def test_history_merge_and_special(repository):
    repo, first = repository
    git(repo, "checkout", "-b", "feature")
    (repo / "branch.txt").write_text(lines()["google-api-key"])
    git(repo, "add", ".")
    git(repo, "commit", "-m", "branch synthetic fixture")
    branch_commit = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "main")
    (repo / "other.txt").write_text("harmless")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "main fixture")
    git(repo, "merge", "--no-ff", "feature", "-m", "merge fixture")
    blob = git(repo, "rev-parse", f"{first}:folder/a&b.txt")
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},link")
    git(repo, "commit", "-m", "synthetic link entry")
    result = Result("repo")
    scan_history(repo, result)
    assert any(f.commit == branch_commit for f in result.findings)
    assert result.skipped["history-special"] == 1


def test_git_bounded_output(tmp_path):
    with pytest.raises(ScanError, match="size limit"):
        git_read("git", tmp_path, ["--version"], limit=1)


def test_git_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr("secretscan.history.GIT_TIMEOUT", 0.05)
    original = subprocess.Popen

    def sleeping_process(command, **kwargs):
        return original([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)

    monkeypatch.setattr("secretscan.history.subprocess.Popen", sleeping_process)
    with pytest.raises(ScanError, match="git read failed"):
        git_read(sys.executable, tmp_path, ["-c", "import time; time.sleep(5)"])


def test_html_hostile_and_sarif(tmp_path, capsys):
    hostile = '<img src=x onerror="alert(1)">&'
    result = Result(hostile)
    result.findings = scan_line(lines()["aws-access-key"], hostile + ".txt", 3)
    report = html_report(result)
    assert hostile not in report
    assert html.escape(hostile, quote=True) in report
    assert samples()["aws-access-key"] not in report
    assert "<script src=" not in report
    assert "https://" not in report and "http://" not in report
    data = sarif(result)
    assert data["version"] == "2.1.0"
    assert "$schema" in data
    run = data["runs"][0]
    assert run["columnKind"] == "unicodeCodePoints"
    assert run["tool"]["driver"]["name"] == "secretscan"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    for finding in run["results"]:
        assert finding["ruleId"] in rule_ids
        assert finding["level"] in {"error", "warning", "note"}
        assert finding["message"]["text"]
        assert len(finding["partialFingerprints"]["secretscan/v1"]) == 64
        location = finding["locations"][0]["physicalLocation"]
        assert location["region"]["startLine"] == 3
        assert location["region"]["endColumn"] > location["region"]["startColumn"]
        assert "%3C" in location["artifactLocation"]["uri"]
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "hostile&name.txt").write_text(lines()["aws-access-key"] + hostile)
    report_path = tmp_path / "report.html"
    out = tmp_path / "results.sarif"
    assert (
        main(
            [
                "scan",
                str(tree),
                "--report",
                str(report_path),
                "--format",
                "sarif",
                "--output",
                str(out),
            ]
        )
        == 1
    )
    assert "hostile&amp;name.txt" in report_path.read_text()
    assert hostile not in report_path.read_text()
    assert json.loads(out.read_text())["version"] == "2.1.0"
    assert main(["scan", str(tree), "--report", str(report_path)]) == 2
    assert "output exists" in capsys.readouterr().err
    assert not html_report(Result("empty")).count("<td>")


def test_smoke_subprocess():
    root = Path(__file__).resolve().parents[1]
    run = subprocess.run(
        [sys.executable, str(root / "scripts" / "smoke_test.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, "live smoke failed"
    assert "masking: PASS" in run.stdout
