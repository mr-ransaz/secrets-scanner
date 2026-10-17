import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from helpers import lines, samples

from secretscan.cli import load_baseline, main, validate_destinations, write
from secretscan.rules import RULES, accepted, entropy, fingerprint, mask, placeholder
from secretscan.scanner import ScanError, scan, scan_line


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.id)
def test_rules(rule):
    matches = scan_line(lines()[rule.id], "sample.txt", 1)
    assert rule.id in {f.rule_id for f in matches}
    assert not scan_line("plain documented harmless words", "sample.txt", 1)
    for finding in matches:
        assert finding.column_end > finding.column_start >= 1
        assert finding.fingerprint == fingerprint(
            finding.rule_id, finding.file, samples()[rule.id]
        )
        assert samples()[rule.id] not in json.dumps(finding.__dict__)


@pytest.mark.parametrize(
    "value",
    [
        "change" + "me",
        "example",
        "your_value",
        "${VALUE}",
        "<value>",
        "password",
        "secret",
        "token",
    ],
)
def test_placeholders(value):
    assert placeholder(value)
    assert not scan_line('password = "' + value + '"', "x", 1)


def test_entropy_mask_fingerprint():
    assert entropy("") == 0
    assert entropy("aaaa") == 0
    assert entropy("abcd") == 2
    assert mask("abc") == "****"
    assert mask("abcdef") == "ab****ef"
    assert len(fingerprint("r", "p", "v")) == 64
    assert fingerprint("r", "p", "v") != fingerprint("r", "q", "v")
    assert fingerprint("r", "p", "v") != fingerprint("s", "p", "v")
    generic = next(r for r in RULES if r.id == "credential-assignment")
    high = RULES[-1]
    assert not accepted(generic, "abcdef12345")
    assert not accepted(generic, "a" * 12)
    assert accepted(generic, "a" * 24)
    assert not accepted(high, "a" * 24)
    assert not accepted(high, "aB3" * 8)
    assert not accepted(high, samples()["high-entropy"][:23])
    assert not accepted(high, samples()["high-entropy"] * 5)
    assert not accepted(high, "abcdefghijklmnopqrstuvwxyz0123456789")
    assert not accepted(high, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    assert not accepted(high, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    edge = samples()["high-entropy"][:24]
    assert entropy(edge + edge[:8]) == 4.5
    assert accepted(high, edge + edge[:8])
    assert entropy(edge + edge[:9]) < 4.5
    assert not accepted(high, edge + edge[:9])


def test_provider_boundaries_and_fine_grained():
    for key in ("aws-access-key", "github-token", "google-api-key"):
        value = samples()[key]
        assert key not in {f.rule_id for f in scan_line(value[:-1], "x", 1)}
        assert key not in {f.rule_id for f in scan_line(value + "z", "x", 1)}
    value = "github_" + "pat_" + "aB7_" * 21
    assert "github-token" in {f.rule_id for f in scan_line(value, "x", 1)}
    assert not scan_line("http://example.org/plain", "x", 1)


def test_ignore_baseline_severity():
    line = lines()["aws-access-key"]
    findings = scan_line(line, "x", 1)
    assert not scan_line(line + " secretscan:ignore", "x", 1)
    assert not scan_line(line, "x", 1, baseline={f.fingerprint for f in findings})
    assert scan_line(line, "x", 2, "high")
    assert not scan_line(lines()["jwt"], "x", 1, "high")


def test_files(tmp_path):
    (tmp_path / "plain.txt").write_bytes(b"harmless\xff\n")
    (tmp_path / "binary.txt").write_bytes(b"a\x00b")
    (tmp_path / "large.txt").write_bytes(b"a" * 101)
    (tmp_path / "omit.txt").write_text("harmless")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hidden").write_text(lines()["aws-access-key"])
    result = scan(tmp_path, max_file_size=100, excludes=("omit.*",))
    assert result.files_scanned == 1
    assert result.skipped == {"excluded": 2, "binary": 1, "oversize": 1}
    assert scan(tmp_path / "plain.txt").files_scanned == 1
    with pytest.raises(ScanError):
        scan(tmp_path / "missing")


def test_unreadable_and_special(tmp_path, monkeypatch):
    path = tmp_path / "file"
    path.touch()
    original = Path.open

    def deny(self, *args, **kwargs):
        if self == path:
            raise PermissionError("sensitive OS details")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny)
    assert scan(tmp_path).skipped == {"unreadable": 1}
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    assert scan(tmp_path).skipped == {"special": 1}


def test_symlinks(tmp_path, monkeypatch):
    # Exercise traversal without depending on Windows symlink privilege.
    folder = tmp_path / "loop"
    folder.mkdir()
    path = tmp_path / "outside"
    path.touch()
    monkeypatch.setattr(Path, "is_symlink", lambda self: self in {folder, path})
    result = scan(tmp_path)
    assert result.skipped == {"symlink": 2}
    assert result.files_scanned == 0
    assert main(["scan", str(folder)]) == 2


def test_walk_error(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        kwargs["onerror"](PermissionError())
        return iter(())

    monkeypatch.setattr("secretscan.scanner.os.walk", denied)
    assert scan(tmp_path).skipped == {"unreadable": 1}


def test_no_network(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    (tmp_path / "sample").write_text(lines()["aws-access-key"])
    assert scan(tmp_path).findings


def test_adversarial_runtime():
    start = time.monotonic()
    for value in ["a" * 1048576, "password " * 100000, "eyJ" + "a" * 500000 + "."]:
        assert not scan_line(value, "x", 1)
    assert time.monotonic() - start < 5


def test_cli_roundtrip(tmp_path, capsys):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "sample").write_text(lines()["aws-access-key"])
    baseline = tmp_path / "baseline.json"
    assert main(["scan", str(root), "--write-baseline", str(baseline)]) == 1
    text = capsys.readouterr().out
    assert "AK****Q2" in text
    assert samples()["aws-access-key"] not in text
    assert main(["scan", str(root), "--baseline", str(baseline), "--no-color"]) == 0
    output = tmp_path / "results.json"
    assert main(["scan", str(root), "--format", "json", "--output", str(output)]) == 1
    data = json.loads(output.read_text())
    assert data["files_scanned"] == 1
    assert set(data["findings"][0]) == {
        "rule_id",
        "severity",
        "file",
        "line",
        "column_start",
        "column_end",
        "masked_preview",
        "fingerprint",
        "commit",
    }
    assert main(["scan", str(root), "--format", "json"]) == 1
    capsys.readouterr()
    assert main(["rules"]) == 0
    assert "aws-access-key" in capsys.readouterr().out


@pytest.mark.parametrize(
    "arguments", [[], ["scan"], ["scan", "x", "--format", "invalid"], ["--unknown"]]
)
def test_usage_errors(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    assert "invalid arguments" in capsys.readouterr().err


def test_runtime_errors(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "missing")]) == 2
    assert main(["scan", str(tmp_path), "--max-file-size", "0"]) == 2
    assert main(["scan", str(tmp_path), "--output", str(tmp_path / "out")]) == 2
    assert "error" in capsys.readouterr().err
    assert (
        main(
            [
                "scan",
                str(tmp_path),
                "--format",
                "json",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )
    assert (
        main(
            [
                "scan",
                str(tmp_path),
                "--format",
                "json",
                "--allow-in-tree",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "scan",
                str(tmp_path),
                "--format",
                "json",
                "--allow-in-tree",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )
    assert (
        main(
            [
                "scan",
                str(tmp_path),
                "--format",
                "json",
                "--allow-in-tree",
                "--force",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )


def test_baseline_and_writes(tmp_path):
    assert load_baseline(None) == set()
    path = tmp_path / "baseline"
    for text in [
        "bad",
        "{}",
        "[]",
        '{"fingerprints":null}',
        '{"fingerprints":[1]}',
        '{"fingerprints":["bad"]}',
    ]:
        path.write_text(text)
        with pytest.raises(ScanError):
            load_baseline(path)
    with pytest.raises(ScanError):
        load_baseline(tmp_path / "missing")
    with pytest.raises(ScanError):
        write(tmp_path / "missing" / "out", "safe", False)
    with pytest.raises(ScanError):
        validate_destinations([path, path], tmp_path / "other", True, True)
    with pytest.raises(ScanError):
        validate_destinations([path], path, True, True)


def test_module_entry():
    run = subprocess.run(
        [sys.executable, "-m", "secretscan", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0
    assert run.stdout.strip() == "secretscan 0.1.0"


def test_repository_self_scan():
    root = Path(__file__).resolve().parents[1]
    tracked = (
        subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        )
        .stdout.decode()
        .split("\0")
    )
    for name in filter(None, tracked):
        assert not scan(root / name).findings, "tracked file has findings"
