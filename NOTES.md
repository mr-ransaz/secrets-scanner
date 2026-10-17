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

## Stage 2

- Last implementation checkpoint: 83f2646.
- Git 2.55.0.windows.5 exercised against isolated temporary repositories with
  deterministic authors/dates, no global config changes. Tests cover removed
  secrets, line numbers, depth limits, subtree/file scope, merged branches,
  symlink tree entries, binary/oversize revisions and missing Git/repository.
- Git uses fixed argument lists, no shell; inherited Git overrides are removed
  (except ceiling directories), external diff/text conversion and fsmonitor
  are disabled, protocol access denied and lazy fetch disabled. Each read has
  a 30-second timeout and 8 MiB cap; cap/failure returns exit 2.
- Added SARIF 2.1.0 required-field tests and HTML escaping tests for hostile
  names/content, masked secret-like path labels, UTC metadata and local filter.
  SARIF is structurally tested only, not schema-validated or hosted-uploaded.
- Expanded generic assignment handling to unquoted literals, with regression
  coverage. No source module is excluded from repository scanning.
- Local module pytest: 44 passed; combined statement/branch coverage 98.73%.
- Live smoke output: `smoke: text/json/sarif/html, exits 0/1/2, baseline, masking: PASS`
  (exit 0). No raw subprocess output is printed on smoke failure.
- Final Stage 2 gates: Ruff check/format, both pytest entries (44 each), diff
  check passed; placeholder matches only documented AGENTS.md exceptions.
  Repository self-scan: 20 files, zero findings, exit 0.
