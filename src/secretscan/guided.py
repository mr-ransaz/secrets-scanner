"""Opt-in Windows console guidance; redirected and terminal runs stay CLI-only."""

import ctypes
import os
import sys
import tempfile
import webbrowser
from collections.abc import Iterator
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from secretscan import __version__
from secretscan.reports import html_report
from secretscan.scanner import ScanError, scan


def interactive_streams() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except AttributeError, OSError, ValueError, RuntimeError:
        return False


def console_processes() -> set[int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel.GetConsoleProcessList
    function.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    function.restype = wintypes.DWORD
    processes = (wintypes.DWORD * 64)()
    count = function(processes, len(processes))
    return set(processes[:count]) if 0 < count <= len(processes) else set()


def parent_is_same_executable() -> bool:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # Limited query access is sufficient; the parent is never modified.
    handle = kernel.OpenProcess(0x1000, False, os.getppid())
    if not handle:
        return False
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        if not kernel.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(length)
        ):
            return False
        return Path(buffer.value).resolve() == Path(sys.executable).resolve()
    finally:
        kernel.CloseHandle(handle)


def owns_console() -> bool:
    if sys.platform != "win32":
        return False
    try:
        processes = console_processes()
        if processes == {os.getpid()}:
            return True
        # A one-file PyInstaller console also contains its waiting bootloader.
        return bool(
            getattr(sys, "frozen", False)
            and processes == {os.getpid(), os.getppid()}
            and parent_is_same_executable()
        )
    except Exception:
        # Console detection is optional; API failures must preserve CLI behavior.
        return False


def directory_argument(value: str) -> Path:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return Path(value) if value else Path.cwd()


def bare_directory(arguments: list[str]) -> bool:
    if (
        len(arguments) != 1
        or not arguments[0].strip()
        or arguments[0] in {"scan", "rules"}
    ):
        return False
    if arguments[0].startswith("-"):
        return False
    try:
        return directory_argument(arguments[0]).is_dir()
    except OSError, ValueError:
        return False


def guided_mode(arguments: list[str]) -> bool:
    return bool(
        (not arguments or bare_directory(arguments))
        and interactive_streams()
        and owns_console()
    )


def report_directories() -> Iterator[tuple[Path, str]]:
    for directory, label in (
        (Path.cwd, "current working directory"),
        (lambda: Path(tempfile.gettempdir()), "temporary directory"),
        (lambda: Path.home() / "Documents", "Documents directory"),
    ):
        try:
            yield directory(), label
        except OSError, RuntimeError:
            continue


def save_report(root: Path, content: str) -> tuple[Path, str]:
    from secretscan.cli import validate_destinations, write

    name = datetime.now().strftime("secretscan-report-%Y%m%d-%H%M%S.html")
    for directory, label in report_directories():
        try:
            directory = directory.resolve(strict=True)
            if not directory.is_dir() or directory.is_relative_to(root):
                continue
            destination = directory / name
            validate_destinations([destination], root, False, False)
            write(destination, content, False)
            return destination, label
        except OSError, ScanError:
            # Try the next outside-tree location without exposing OS/path details.
            continue
    raise ScanError("cannot create a new HTML report outside the scan tree")


def run_guided(argument: str | None = None) -> int:
    from secretscan.cli import text_output

    if not interactive_streams():
        return 2
    try:
        print(f"secretscan {__version__} - guided mode")
        print("Read-only scan, offline, masked output; saves one HTML report.")
        raw = (
            input("Folder path (Enter = current folder): ")
            if argument is None
            else argument
        )
        root = directory_argument(raw)
        if not root.is_dir():
            raise ScanError("folder must exist and be a directory")
        if root.is_symlink() or root.is_junction():
            raise ScanError("scan root must not be a symlink or junction")
        root = root.resolve()
        result = scan(root)
        print(text_output(result), end="")
        report, location = save_report(root, html_report(result))
        print(f"HTML report saved in {location}: {report.name}")
        if (
            input("Open HTML report in your default browser? (y/N): ").strip().lower()
            == "y"
        ):
            try:
                opened = webbrowser.open(report.as_uri(), new=2)
            except OSError, webbrowser.Error:
                opened = False
            if not opened:
                print(
                    "Could not open the browser. Open the saved HTML report manually."
                )
        return int(bool(result.findings))
    except EOFError, KeyboardInterrupt:
        print("Guided scan cancelled.")
        return 2
    except ScanError as error:
        print(f"secretscan: error: {error}")
        return 2
    except Exception:
        print("secretscan: error: guided scan or report failed")
        return 2
    finally:
        if interactive_streams():
            try:
                input("Press Enter to exit...")
            except EOFError, KeyboardInterrupt, OSError, ValueError, RuntimeError:
                print("Closing secretscan.")
