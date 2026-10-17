# Project state

- Version: 0.1.0; branch: main; no release tags created.
- Last implementation commit: 04db134 (Windows guided startup).
- Stages 1–3 implemented: safe scanner, bounded history, masked reports,
  baselines/ignores, Windows executable, packaging verifiers and workflows.
- Python 3.14.0; editable dev install succeeded; pip check passed.
- Windows guided startup added; normal CLI/redirected invocations retain CLI mode.
- Local tests: 93 passed each entry; branch coverage enabled; combined 99.10%.
- Statements: 496/500; branches: 162/164 (98.78%); guided module 100%.
- Ruff check/format, both pytest entry points and diff checks passed.
- Placeholder matches: AGENTS.md documented exceptions only.
- Live smoke: text/JSON/SARIF/HTML, exits 0/1/2, baseline, masking PASS, exit 0.
- Final self-scan: 33 files, zero findings, exit 0.
- PyInstaller 6.22.3 / hooks 2026.8; exe: 9,648,309 bytes; exe verification PASS.
- Redirected exe no-args/folder/missing: exit 2, no prompts PASS.
- Guided flow/API ownership tested with mocks and simulated input; no rule changes.
- Native Windows console/parent query probe ran; Explorer behavior still manual.
- Refreshed wheel/sdist and isolated wheel console smoke/pip check PASS.
- README bootstrap, synthetic output/exit codes and executable examples verified.
- Local artifacts/checksums refreshed; dist ignored; no dependencies changed.
- All gates rerun after implementation commit and passed; pip check passed.
- Manual: exe against .work/demo/input; open .work/demo/exe-report.html,
  inspect masking/filter; owner creates empty remote, pushes, observes CI and
  push protection, then decides on release. No push/tag/release performed here.
- Windows links/unreadable behavior partly mocked; hard links tested on disk.
- Manual guided: Explorer double-click and drag folder; quoted path/Enter default,
  masked output, outside-tree HTML, browser No/Yes, error and final Enter pauses.
- Docker is out of scope. Hosted CI and external release remain unverified.
