"""Install a wheel without dependencies into a disposable project-local venv."""

import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from smoke_test import run_checks


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    parent = project / ".work" / "wheel-check"
    parent.mkdir(parents=True, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(prefix="run-", dir=parent)
    old = {key: os.environ.get(key) for key in ("TEMP", "TMP", "TMPDIR")}
    try:
        work = Path(scratch.name)
        temp = work / "tmp"
        temp.mkdir()
        os.environ.update({key: str(temp) for key in old})
        wheels = list((project / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("expected one wheel")
        target = work / "venv"
        venv.EnvBuilder(with_pip=True).create(target)
        binary = target / ("Scripts" if os.name == "nt" else "bin")
        python = binary / ("python.exe" if os.name == "nt" else "python")
        console = binary / ("secretscan.exe" if os.name == "nt" else "secretscan")
        install = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(wheels[0]),
            ],
            cwd=work,
            capture_output=True,
            check=False,
        )
        if install.returncode:
            raise RuntimeError("wheel installation failed")
        outside = work / "outside"
        outside.mkdir()
        run_checks([str(console)], outside)
        check = subprocess.run(
            [str(python), "-m", "pip", "check"],
            cwd=outside,
            capture_output=True,
            check=False,
        )
        if check.returncode:
            raise RuntimeError("wheel dependency check failed")
        print(
            "wheel: isolated no-deps install, console outside repo root, "
            "version/rules/scan, full smoke, pip check: PASS"
        )
        return 0
    except OSError, RuntimeError, subprocess.SubprocessError:
        print("wheel: FAIL (no raw process output displayed)", file=sys.stderr)
        return 1
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        scratch.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
