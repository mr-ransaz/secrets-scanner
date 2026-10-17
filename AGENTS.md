# Working agreement

## Session-start protocol
1. Read this file and STATE.md before editing anything.
2. Run `git status --short`; stop if the tree is dirty. Never overwrite or
   discard existing changes.
3. Run `git log -1 --oneline`; confirm branch and Python version.
4. Inspect the relevant code, tests and docs before changing anything.
5. If STATE.md mentions a release tag, resolve it with
   `git rev-list -n 1 <tag>` (never use `^{commit}` in PowerShell).

## Rules
- Python 3.14 only. Run every Python tool through
  `.\.venv\Scripts\python.exe` (pip, ruff, pytest, project CLI/server).
  Never use global Python or global tool launchers. Git uses `git`.
- Dependencies follow the Project profile below. Every dependency change
  must be explained in NOTES.md. Dev-only tools go in the `dev` extra.
- Never log, store, print or commit real passwords, tokens, keys, .env
  files or databases. Use only public synthetic values in tests and docs.
  Never put raw exceptions or secret values into logs or responses.
- Inspect before editing; make the smallest complete fix; add meaningful
  regression tests. Never skip tests or suppress failures to pass a gate.
- README claims and captured outputs must be verified by execution.
  Clearly separate local/mocked checks from unverified external services
  (Docker, hosted CI, live network). Never claim an unrun check passed.
- No placeholders in committed files (YOUR_USERNAME, Your Name, TODO,
  changeme). Use the real values from the Project profile.
- Small Conventional Commits (feat:, fix:, test:, docs:, ci:, chore:) with
  explicit paths. Do not push, rewrite history, reset unrelated changes,
  or touch anything outside the project folder.
- Tags: follow the Project profile. Never move or delete an existing tag.
- No subagents unless the user explicitly asks.

## Gate checklist (run in this order)
1. `.\.venv\Scripts\python.exe -m ruff check .`
2. `.\.venv\Scripts\python.exe -m ruff format --check .`
3. `.\.venv\Scripts\python.exe -m pytest -q` (coverage minimum from profile)
4. `.\.venv\Scripts\pytest.exe -q`
5. `git diff --check`
6. Placeholder scan:
   `git grep -n -i -E "YOUR_USERNAME|Your Name|TODO|FIXME|changeme"`
   must be empty (except documented placeholders in .env.example).
7. Docker build only if docker exists; otherwise list as manual check.
8. Verify every runnable README example and its output/exit code.

## End of task
- Update README, NOTES.md and CHANGELOG with supported claims only.
- Update STATE.md last (max 60 lines): real gate results, last
  implementation commit, remaining unverified work.
- Commit the checkpoint, confirm a clean tree, then STOP. Print:
  `git log --oneline`, `git status`, test count and coverage, anything
  not verified, and MANUAL CHECKS.

## Project profile
- Name: secrets-scanner
- GitHub repository: mr-ransaz/secrets-scanner
- Distribution / Python package / command: secrets-scanner / secretscan / secretscan
- Author / license: MR Ransaz / MIT 2026
- Version: 0.1.0
- Purpose: a defensive CLI and Windows executable that scans folders and
  Git repositories for likely hardcoded secrets, with masked output,
  JSON/SARIF-style machine output and a self-contained HTML report.
- Stack: Python 3.14, runtime dependencies stdlib-only. Dev tools: pytest,
  pytest-cov, ruff, build, PyInstaller (dev/build extra only).
- Layout: src/secretscan/, tests/, scripts/, packaging/. README.md,
  NOTES.md, STATE.md, CHANGELOG.md and AGENTS.md in the repository root.
- Coverage minimum: 90% with branch coverage on application code.
- Security invariants: never print, log, store or serialize a complete
  detected secret; masked previews only; reports must not contain full
  values. Findings carry rule id, file, line, severity, masked preview and
  a non-reversible fingerprint. Scanner never makes network requests and
  never modifies scanned files. Treat scanned files as untrusted input:
  size limits, binary detection, symlink safety, no execution.
- Test fixtures: never commit complete realistic secrets or provider
  tokens. Assemble synthetic secrets at runtime in tests from fragments,
  or use documented non-secret examples only. This is required so GitHub
  push protection does not block pushes.
- Report safety: HTML report is one local file, no external assets, all
  values escaped, no scripts that load remote resources.
- Tag policy: create no tags. Never push or create a GitHub repository.
- Placeholder scan exception: literal forbidden-pattern examples in
  AGENTS.md and rule names in documentation are not defects.
- Initial bootstrap exception: if STATE.md or commit history does not
  exist, record that and initialize them. The initial untracked AGENTS.md
  may be inspected and committed; stop for other unexplained changes.
- Docker is out of scope for 0.1.0. Skip it explicitly.