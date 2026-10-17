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

## Stage 3

- Last implementation checkpoint before this stage: fbd906e.
- PyInstaller 6.22.3 with contrib hooks 2026.8 built the Windows x64 console
  executable using Python 3.14.0 and packaging/secretscan.spec. Final executable
  size: 9,507,836 bytes. UPX is disabled; bytecode optimization level is 1.
- Chosen layout: one file. This locally verified build provides exactly one
  executable artifact and needs no installed Python. It extracts its bundled
  runtime on startup, which adds startup cost and requires a writable temp
  directory. Build and verification scripts set project-local temp/cache paths,
  restore environment variables and remove their own scratch directories.
- Final executable verification output (exit 0):
  `smoke: text/json/sarif/html, exits 0/1/2, baseline, masking: PASS`
  `exe verification: PASS; version, rules, text/JSON/SARIF/HTML, exits, baseline, masking`
- Executable README examples returned 0 for version/rules, 1 for the synthetic
  text/HTML scan, and 0 for an additional high-severity repository history scan.
- Wheel and sdist build succeeded, including a wheel built from the sdist.
  Disposable venv wheel verification passed: no-index/no-deps installation,
  console version/rules/scans and full smoke from a different working directory,
  plus pip check. The directory is inside ignored .work to honor project-only
  writes; it is not the repository root. Temporary venvs are removed in finally.
- New output protection rejects hard-linked destinations even with force;
  an actual project-local hard-link regression test passed outside the restricted
  app sandbox. The restricted sandbox denied creating that link. Symlink
  privilege was unavailable even in the filesystem-capable run, so Windows
  loop/outside-link tests use deterministic mocks; historical link tree entries
  are tested with real Git metadata. Unreadable-file tests also use mocks.
- All detected values are also removed from path/root metadata before output,
  including generic credentials embedded in otherwise unrelated filenames.
  Raw match values exist only in transient scan memory, never result objects,
  serialized artifacts or logs. SARIF declares Unicode code-point columns.
- Final module/executable pytest runs: 46 passed each. Combined coverage 98.78%,
  branch measurement enabled: 359/363 statements and 128/130 branches (98.46%).
  Ruff check/format, diff check and live smoke passed. Placeholder matches are
  only the documented AGENTS.md exceptions. README bootstrap was re-executed
  successfully with project-local temp/cache paths; editable install and pip
  check passed. The documented synthetic sample and its exit codes were verified.
- CI uses read-only contents permissions, Ubuntu/Windows Python 3.14, pinned
  action majors, lint/format/both pytest entries/smoke/self-scan/package checks;
  executable checks run only on Windows. Optional v* release requires CI,
  checks package/tag agreement, rebuilds/verifies assets, creates checksums and
  uploads with GitHub CLI. Only publish gets contents: write. No PyPI upload.
- Action-major references and PyInstaller behavior checked against primary docs:
  https://github.com/actions/checkout, https://github.com/actions/setup-python,
  https://github.com/actions/upload-artifact,
  https://pyinstaller.org/en/stable/usage.html.
- SARIF structure follows the OASIS 2.1.0 description, with no schema download:
  https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html.
- Not verified: hosted CI, Linux execution, GitHub artifact/release/SARIF upload,
  push protection, SmartScreen/reputation behavior, code signing and manual
  browser rendering/filter interaction. The executable is unsigned. Docker is
  out of scope. No push, tag, remote repository creation or release was performed.

## Final checkpoint

- Last implementation commit: 1530b84. Final documentation checkpoint records
  verified results; application code is unchanged after that commit.
- Final full-tree self-scan: 31 files, zero findings, exit 0 (coverage.json is
  generated/ignored by Git but included in the scanner's file count).
- Final wheel/sdist rebuild and disposable wheel verification passed with the
  final application code. SHA256SUMS contains exactly the exe, wheel and sdist;
  all three digests were independently recomputed with hashlib.sha256 and matched.
  No generated dist artifacts are tracked. A final docs-only rebuild refreshes
  the package metadata and source archive; checksums are regenerated afterward.
- Demo input and masked reports remain under ignored .work/demo intentionally
  for owner inspection. Smoke, executable and wheel verifiers cleaned their
  per-run scratch directories. All local gates passed; manual checks remain
  exactly those listed above and in STATE.md.
