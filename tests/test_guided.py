import json
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from helpers import samples

from secretscan import guided
from secretscan.cli import main
from secretscan.guided import report_directories
from secretscan.scanner import ScanError


@pytest.mark.parametrize(
    "pids,expected",
    [([], False), (["self"], True), (["self", "other"], False), (["other"], False)],
)
def test_console_ownership(monkeypatch, pids, expected):
    monkeypatch.setattr(sys, "platform", "win32")
    ids = {os.getpid() if p == "self" else -1 for p in pids}
    monkeypatch.setattr(guided, "console_processes", lambda: ids)
    assert guided.owns_console() is expected


def test_console_platform_failure_and_frozen_pair(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert not guided.owns_console()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        guided, "console_processes", Mock(side_effect=OSError("private detail"))
    )
    assert not guided.owns_console()
    monkeypatch.setattr(guided, "console_processes", Mock(side_effect=RuntimeError()))
    assert not guided.owns_console()
    monkeypatch.setattr(
        guided, "console_processes", lambda: {os.getpid(), os.getppid()}
    )
    assert not guided.owns_console()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(guided, "parent_is_same_executable", lambda: True)
    assert guided.owns_console()
    monkeypatch.setattr(guided, "parent_is_same_executable", lambda: False)
    assert not guided.owns_console()


def kernel_mock(monkeypatch, count=1):
    def processes(buffer, capacity):
        buffer[0] = os.getpid()
        return count

    def query(handle, flags, buffer, length):
        buffer.value = sys.executable
        return True

    kernel = SimpleNamespace(
        GetConsoleProcessList=Mock(side_effect=processes),
        OpenProcess=Mock(return_value=123),
        QueryFullProcessImageNameW=Mock(side_effect=query),
        CloseHandle=Mock(return_value=True),
    )
    monkeypatch.setattr(
        guided.ctypes, "WinDLL", Mock(return_value=kernel), raising=False
    )
    return kernel


@pytest.mark.parametrize(
    "count,expected", [(0, set()), (1, {os.getpid()}), (65, set())]
)
def test_console_api(monkeypatch, count, expected):
    kernel = kernel_mock(monkeypatch, count)
    assert guided.console_processes() == expected
    assert kernel.GetConsoleProcessList.call_args.args[1] == 64


def test_parent_api(monkeypatch, tmp_path):
    kernel = kernel_mock(monkeypatch)
    assert guided.parent_is_same_executable()
    kernel.CloseHandle.assert_called_once_with(123)
    kernel.QueryFullProcessImageNameW.side_effect = None
    kernel.QueryFullProcessImageNameW.return_value = False
    assert not guided.parent_is_same_executable()
    assert kernel.CloseHandle.call_count == 2
    kernel.OpenProcess.return_value = 0
    assert not guided.parent_is_same_executable()
    assert kernel.CloseHandle.call_count == 2
    kernel.OpenProcess.return_value = 123

    def different(handle, flags, buffer, length):
        buffer.value = str(tmp_path / "terminal.exe")
        return True

    kernel.QueryFullProcessImageNameW.side_effect = different
    assert not guided.parent_is_same_executable()


@pytest.mark.parametrize(
    "stdin,stdout,owned,arguments,expected",
    [
        (True, True, True, [], True),
        (True, True, False, [], False),
        (False, True, True, [], False),
        (True, False, True, [], False),
        (True, True, True, ["directory"], True),
        (True, True, False, ["directory"], False),
        (False, True, True, ["directory"], False),
        (True, True, True, ["missing"], False),
        (True, True, True, ["file"], False),
        (True, True, True, ["scan", "directory"], False),
        (True, True, True, ["rules"], False),
        (True, True, True, ["--version"], False),
        (True, True, True, ["--help"], False),
        (True, True, True, [""], False),
    ],
)
def test_mode_selection(
    tmp_path, monkeypatch, stdin, stdout, owned, arguments, expected
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "directory").mkdir()
    (tmp_path / "file").touch()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: stdin)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: stdout)
    probe = Mock(return_value=owned)
    monkeypatch.setattr(guided, "owns_console", probe)
    assert guided.guided_mode(arguments) is expected
    if not stdin or not stdout or (arguments and arguments != ["directory"]):
        probe.assert_not_called()


def test_stream_and_directory_failures(monkeypatch):
    monkeypatch.setattr(sys, "stdin", None)
    assert not guided.interactive_streams()
    monkeypatch.setattr(Path, "is_dir", Mock(side_effect=OSError("private detail")))
    assert not guided.bare_directory(["folder"])


@pytest.fixture
def guided_tree(tmp_path, monkeypatch):
    root = tmp_path / "input folder"
    root.mkdir()
    (root / "sample.txt").write_text(samples()["aws-access-key"], encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guided, "interactive_streams", lambda: True)
    monkeypatch.setattr(guided, "owns_console", lambda: True)
    monkeypatch.setattr(
        guided, "report_directories", lambda: ((tmp_path, "test directory"),)
    )
    return root


def inputs(monkeypatch, answers):
    prompts = []
    sequence = iter(answers)

    def respond(prompt):
        prompts.append(prompt)
        answer = next(sequence)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr("builtins.input", respond)
    return prompts


def test_interactive_scan(guided_tree, tmp_path, monkeypatch, capsys):
    prompts = inputs(monkeypatch, ['"' + str(guided_tree) + '"', "N", ""])
    browser = Mock()
    monkeypatch.setattr(guided.webbrowser, "open", browser)
    assert main([]) == 1
    output = capsys.readouterr().out
    assert "secretscan 0.1.0 - guided mode" in output
    assert "Read-only scan, offline, masked output" in output
    assert "1 files scanned, 1 findings" in output
    assert "AK****Q2" in output
    assert samples()["aws-access-key"] not in output
    reports = list(tmp_path.glob("secretscan-report-*.html"))
    assert len(reports) == 1
    assert not reports[0].is_relative_to(guided_tree)
    assert samples()["aws-access-key"] not in reports[0].read_text(encoding="utf-8")
    assert prompts[-1] == "Press Enter to exit..."
    browser.assert_not_called()


def test_drag_drop_and_open(guided_tree, tmp_path, monkeypatch):
    prompts = inputs(monkeypatch, ["y", ""])
    browser = Mock(return_value=True)
    monkeypatch.setattr(guided.webbrowser, "open", browser)
    assert main([str(guided_tree)]) == 1
    assert len(prompts) == 2
    report = next(tmp_path.glob("secretscan-report-*.html"))
    browser.assert_called_once_with(report.as_uri(), new=2)


def test_enter_current_folder(tmp_path, monkeypatch):
    root = tmp_path / "input"
    root.mkdir()
    monkeypatch.chdir(root)
    monkeypatch.setattr(guided, "interactive_streams", lambda: True)
    monkeypatch.setattr(guided, "owns_console", lambda: True)
    monkeypatch.setattr(
        guided, "report_directories", lambda: ((root, "inside"), (tmp_path, "outside"))
    )
    inputs(monkeypatch, ["", "", ""])
    assert main([]) == 0
    assert not list(root.glob("*.html"))
    assert len(list(tmp_path.glob("secretscan-report-*.html"))) == 1


@pytest.mark.parametrize("failure", [OSError("private detail"), None, False])
def test_browser_failure(guided_tree, monkeypatch, capsys, failure):
    inputs(monkeypatch, ["y", ""])
    browser = (
        Mock(side_effect=failure)
        if isinstance(failure, OSError)
        else Mock(return_value=failure)
    )
    monkeypatch.setattr(guided.webbrowser, "open", browser)
    assert main([str(guided_tree)]) == 1
    output = capsys.readouterr().out
    assert "Open the saved HTML report manually" in output
    assert "private detail" not in output


@pytest.mark.parametrize(
    "response", ["missing", "file", EOFError(), KeyboardInterrupt()]
)
def test_guided_input_error(guided_tree, tmp_path, monkeypatch, capsys, response):
    (tmp_path / "file").touch()
    prompts = inputs(monkeypatch, [response, ""])
    assert main([]) == 2
    assert prompts[-1] == "Press Enter to exit..."
    output = capsys.readouterr().out
    assert "Traceback" not in output
    assert not list(tmp_path.glob("*.html"))


@pytest.mark.parametrize("failure", [OSError, RuntimeError, TypeError])
def test_guided_errors_pause(guided_tree, monkeypatch, capsys, failure):
    prompts = inputs(monkeypatch, [""])
    monkeypatch.setattr(guided, "scan", Mock(side_effect=failure("private detail")))
    assert main([str(guided_tree)]) == 2
    assert prompts == ["Press Enter to exit..."]
    assert "private detail" not in capsys.readouterr().out


def test_guided_root_symlink(guided_tree, monkeypatch):
    prompts = inputs(monkeypatch, [""])
    monkeypatch.setattr(Path, "is_symlink", lambda _: True)
    assert main([str(guided_tree)]) == 2
    assert prompts == ["Press Enter to exit..."]


def test_pause_eof(guided_tree, monkeypatch, capsys):
    inputs(monkeypatch, ["", EOFError()])
    assert main([str(guided_tree)]) == 1
    assert "Closing secretscan" in capsys.readouterr().out


def test_never_prompt_without_tty(guided_tree, monkeypatch, capsys):
    monkeypatch.setattr(guided, "interactive_streams", lambda: False)
    prompt = Mock(side_effect=AssertionError("unexpected prompt"))
    monkeypatch.setattr("builtins.input", prompt)
    assert guided.run_guided() == 2
    assert main([str(guided_tree)]) == 2
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    assert "scan PATH" in capsys.readouterr().err
    prompt.assert_not_called()


def test_report_collisions(guided_tree, tmp_path, monkeypatch, capsys):
    class Clock:
        @staticmethod
        def now():
            return datetime(2026, 10, 17, 12, 34, 56)

    monkeypatch.setattr(guided, "datetime", Clock)
    existing = tmp_path / "secretscan-report-20261017-123456.html"
    existing.write_text("keep existing report", encoding="utf-8")
    prompts = inputs(monkeypatch, [""])
    assert main([str(guided_tree)]) == 2
    assert existing.read_text() == "keep existing report"
    assert prompts == ["Press Enter to exit..."]
    assert "outside the scan tree" in capsys.readouterr().out


def test_report_fallbacks(guided_tree, tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    not_directory = tmp_path / "file"
    not_directory.touch()
    monkeypatch.setattr(
        guided,
        "report_directories",
        lambda: (
            (missing, "missing"),
            (not_directory, "file"),
            (guided_tree, "inside"),
            (tmp_path, "outside"),
        ),
    )
    report, label = guided.save_report(guided_tree, "safe content")
    assert label == "outside"
    assert report.parent == tmp_path
    monkeypatch.setattr(
        guided, "report_directories", lambda: ((guided_tree, "inside"),)
    )
    with pytest.raises(ScanError, match="outside the scan tree"):
        guided.save_report(guided_tree, "safe content")


def test_default_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guided.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    assert [path for path, label in guided.report_directories()] == [
        tmp_path,
        tmp_path / "temp",
        tmp_path / "home" / "Documents",
    ]


def test_default_locations_are_lazy(guided_tree, tmp_path, monkeypatch):
    monkeypatch.setattr(guided, "report_directories", report_directories)
    temp = Mock(side_effect=OSError("private detail"))
    monkeypatch.setattr(guided.tempfile, "gettempdir", temp)
    report, label = guided.save_report(guided_tree, "safe content")
    assert report.parent == tmp_path
    temp.assert_not_called()
    monkeypatch.setattr(Path, "cwd", Mock(side_effect=OSError("private detail")))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert list(report_directories()) == [
        (tmp_path / "Documents", "Documents directory")
    ]


def test_report_unwritable_fallback(guided_tree, tmp_path, monkeypatch):
    from secretscan import cli

    first = tmp_path / "unwritable"
    first.mkdir()
    monkeypatch.setattr(
        guided, "report_directories", lambda: ((first, "first"), (tmp_path, "fallback"))
    )
    real_write = cli.write

    def write(path, content, force):
        if path.parent == first:
            raise ScanError("cannot write output file")
        real_write(path, content, force)

    monkeypatch.setattr(cli, "write", write)
    report, label = guided.save_report(guided_tree, "safe content")
    assert report.parent == tmp_path and label == "fallback"


def test_terminal_usage_without_prompts(guided_tree, monkeypatch, capsys):
    monkeypatch.setattr(guided, "owns_console", lambda: False)
    prompt = Mock(side_effect=AssertionError("unexpected prompt"))
    monkeypatch.setattr("builtins.input", prompt)
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    assert main([str(guided_tree)]) == 2
    assert "scan PATH" in capsys.readouterr().err
    prompt.assert_not_called()


def test_cli_commands_never_guide(guided_tree, monkeypatch, capsys):
    prompt = Mock(side_effect=AssertionError("unexpected prompt"))
    monkeypatch.setattr("builtins.input", prompt)
    assert main(["rules"]) == 0
    capsys.readouterr()
    with pytest.raises(SystemExit) as version:
        main(["--version"])
    assert version.value.code == 0
    assert main(["scan", str(guided_tree), "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert data["findings"][0]["rule_id"] == "aws-access-key"
    prompt.assert_not_called()
