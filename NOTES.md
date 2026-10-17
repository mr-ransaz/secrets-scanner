# Build and verification notes

## Bootstrap

- Initial commit: a40faa3; clean main branch; STATE.md absent as expected.
- Windows Python 3.14.0 verified at
  `C:\Users\mstit\AppData\Local\Programs\Python\Python314\python.exe`.
  `py -3.14` failed to find Python. Used the verified executable to create .venv.
- Initial ensurepip failed because the default temporary directory was outside
  the workspace. Retried venv ensurepip with TEMP/TMP set to `.work/tmp`;
  installation succeeded. All subsequent Python tools use the project venv.
- Direct dev pins from PyPI metadata: pytest 9.1.1, pytest-cov 7.1.0,
  ruff 0.17.1, build 1.6.1, PyInstaller 6.22.3. Build backend setuptools 84.0.0.
  These versions permit Python 3.14; actual installation and execution below
  establish local compatibility. Runtime has no dependencies. Test, lint,
  coverage and packaging tools belong only in dev; setuptools is build-only.
- Sources: https://pypi.org/project/pytest/,
  https://pypi.org/project/pytest-cov/, https://pypi.org/project/ruff/,
  https://pypi.org/project/build/, https://pypi.org/project/pyinstaller/,
  https://pypi.org/project/setuptools/ (metadata checked 2026-10-17).
- Docker is explicitly out of scope for version 0.1.0.

## Stage 1

- Editable dev install succeeded on Python 3.14.0; pip check reported no broken
  requirements. Test scratch directories are created explicitly under .work
  because the sandbox cannot create pytest's default numbered temp directory.
- 36 tests passed; combined statement/branch coverage 97.89%, branch measurement
  enabled and the 90% gate enforced. Both pytest entry points are required.
- Symlink/outside-link/loop and unreadable-file behavior are initially tested
  with deterministic mocks, independent of Windows link privileges.
- All links and junctions are skipped; UTF-8 replacement decoding, bounded file
  reads, constant public errors and masked-only Finding objects protect output.
- Stage 1 implements text/JSON and fingerprint-only baselines. Reports/history
  and executable packaging remain for subsequent stages.
- Both pytest entry points passed (36 each), Ruff check/format and diff checks
  passed. Placeholder scan matches only the documented AGENTS.md examples.
- Self-scan initially found the public entropy test fixture; that single line
  now carries the tool's inline suppression. No whole module is excluded from
  the tracked-file test. Final Stage 1 self-scan: 16 files, zero findings.
