# secrets-scanner 0.1.0

An educational, defensive portfolio project by **MR Ransaz**, licensed MIT 2026.
It scans local files and Git history for likely hardcoded secrets and emits
masked text, JSON, SARIF or a self-contained HTML report. Runtime dependencies:
Python **3.14** and its standard library; system Git is needed only for history.

Repository: [mr-ransaz/secrets-scanner](https://github.com/mr-ransaz/secrets-scanner).
Distribution: `secrets-scanner`; import package and command: `secretscan`.
Local Windows checks are recorded in [NOTES.md](NOTES.md). Hosted CI has **not**
been executed or verified. No artifacts have been published.

## PowerShell quick start

Run from the repository root with an installed Python 3.14 executable available
as `python`. Verify its version before creating the environment. These temporary
and cache paths keep bootstrap writes inside the project. The `py -3.14`
launcher failed on the development machine; the verified executable from
`Get-Command python` worked (details in NOTES.md).

```powershell
New-Item -ItemType Directory -Force .work\tmp | Out-Null
$env:TEMP = (Resolve-Path .work\tmp).Path
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.work\pip-cache'
& (Get-Command python).Source --version
& (Get-Command python).Source -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m secretscan --version
.\.venv\Scripts\python.exe -m secretscan rules
.\.venv\Scripts\python.exe -m secretscan scan .
```

The console command `secretscan` is installed in the venv's Scripts directory.
Using `python -m secretscan` explicitly selects the intended environment.
The clean-repository scan returns 0; finding a likely secret returns **1**, which
is an intentional result, not a crash.

## Prepared synthetic example

The helper writes only public synthetic input to the ignored `.work/demo/input`
folder. It is idempotent for its own sample and refuses different existing data.

```powershell
.\.venv\Scripts\python.exe scripts\demo.py
.\.venv\Scripts\python.exe -m secretscan scan .work\demo\input --no-color
```

Verified text output (exit **1**):

```text
secretscan 0.1.0: 1 files scanned, 1 findings
sample.txt:1:1 high aws-access-key AK****Q2 [34b04bfb20df]
```

Save JSON, HTML and a baseline outside the input folder (exit 1), then use that
baseline to suppress the known finding (exit 0):

```powershell
.\.venv\Scripts\python.exe -m secretscan scan .work\demo\input --format json --output .work\demo\results.json --report .work\demo\report.html --write-baseline .work\demo\baseline.json
.\.venv\Scripts\python.exe -m secretscan scan .work\demo\input --baseline .work\demo\baseline.json
.\.venv\Scripts\python.exe -m secretscan scan .work\demo\input --format sarif --output .work\demo\results.sarif
```

Existing outputs require `--force` on subsequent runs. To write inside a scanned
directory, also supply `--allow-in-tree`; supplying both explicitly permits
replacement of a scanned regular file, so choose destinations deliberately.
The target file itself, symlink/junction destinations, hard-linked existing
files and conflicting output destinations are refused.

## Commands and options

| Command | Behavior |
| --- | --- |
| `secretscan scan PATH` | Scan one file or a directory recursively |
| `secretscan scan PATH --git-history` | Also inspect added lines in reachable commits |
| `secretscan rules` | List rule ID, severity and description |
| `secretscan --version` | Print the installed version |

All options below belong to `scan`.

| Option | Default / meaning |
| --- | --- |
| `--format text\|json\|sarif` | `text`; JSON/SARIF may go to stdout |
| `--output FILE` | Save JSON/SARIF; rejected with text format |
| `--report FILE.html` | Additionally save a single HTML report |
| `--min-severity low\|medium\|high` | `low`; filter findings and exit status |
| `--exclude GLOB` | Repeatable, case-insensitive patterns against relative paths or components |
| `--baseline FILE` | Suppress matching full fingerprints |
| `--write-baseline FILE` | Write fingerprint-only JSON; merge an input baseline if supplied |
| `--max-file-size BYTES` | `1048576` (1 MiB); must be positive |
| `--git-history` | Read history through system Git; no shell invocation |
| `--max-commits N` | `200`; positive cap on commits reachable from HEAD |
| `--no-color` | Accepted for automation; text is always color-free in 0.1.0 |
| `--allow-in-tree` | Explicitly allow output in the scanned directory |
| `--force` | Explicitly allow replacing an existing regular output file |
| `--help` | Show usage |

Default exclusions include `.git`, `.venv`, `node_modules`, `__pycache__`,
`dist`, `build`, `.work`, pytest/Ruff caches, egg metadata and common binary
extensions (images, PDF, archives, executables, media and databases).
The full list is in `src/secretscan/scanner.py`. Globs are fnmatch patterns;
they are not Git ignore rules, and there is no negation/re-include syntax.

| Exit code | Meaning |
| --- | --- |
| 0 | No unsuppressed findings at the selected minimum severity |
| 1 | One or more unsuppressed findings at that severity or above |
| 2 | Usage/runtime error, invalid baseline, unavailable Git/repository, or refused output |

Skipped files are counted by reason. Exit 0 with skipped files does not establish
that every file was inspected. Errors omit raw OS/Git exception text and raw
invalid arguments to avoid leaking sensitive paths or values.

## Detection rules

Patterns are compiled and bounded; these formats are intentionally transparent
and incomplete. A format match does not prove a credential is real or active.

| Rule ID | Severity | Shape or heuristic |
| --- | --- | --- |
| `aws-access-key` | high | AKIA/ASIA followed by 16 uppercase letters/digits |
| `github-token` | high | Classic gh[pousr] prefix plus 36 alphanumerics; fine-grained github_pat prefix plus 22–255 characters |
| `slack-token` | high | xox[baprs] prefix, dash, 10–180 alphanumerics/dashes |
| `google-api-key` | high | AIza prefix plus 35 URL-safe characters |
| `stripe-live-key` | high | Stripe live secret prefix plus 24–128 alphanumerics |
| `jwt` | medium | Three base64url-like segments; header begins eyJ; not decoded or verified |
| `private-key` | high | Generic, RSA, EC, DSA, OpenSSH or encrypted private-key PEM header |
| `credential-assignment` | medium | Case-insensitive password/secret/token/api_key literal assignment; heuristic below |
| `basic-auth-url` | high | HTTP(S) URL containing bounded username:password before @ |
| `high-entropy` | low | Mixed-case/digit token, 24–128 characters, entropy at least 4.5 bits/character |

Shannon entropy is `H = -sum(p * log2(p))`, with character frequencies `p`;
empty input has entropy 0. Generic assignments accept quoted or whitespace-free
unquoted literals up to 512 characters, at least 12 characters long, and either
entropy at least **3.0** bits/character or length at least **24**. Space between
the name, separator and literal is capped at 16 characters per gap.
The low-severity heuristic examines contiguous ASCII letters, digits and
`_+/=-`, requires lowercase, uppercase and a digit, and uses **4.5** bits/character.
Boundary values are tested. Multiple rules may flag the same value separately.

Placeholder filtering ignores the documented default-password word, the words
example/password/secret/token, and values starting with example, your_, `${VAR}`
style syntax or `<...>` syntax (case-insensitive). It does not infer whether a
string is a runtime variable or a live credential. Random IDs, code expressions,
sample data and public JWTs can cause false positives. Short, low-entropy,
unsupported, split, encoded or obfuscated secrets can be missed.

## Masking, fingerprints and suppression

Finding objects contain rule ID, severity, relative path, line, 1-based Unicode
column span (end exclusive), masked preview, fingerprint and optional commit ID.
Previews keep at most two leading and two trailing characters, separated by
four asterisks; short values become only asterisks. Secret-like portions of path
and root labels are masked as well. Text escapes terminal control characters.
Reports never include source lines or absolute root/home paths.

Fingerprint input is UTF-8 `rule_id + NUL + relative_path + NUL + secret_value`,
hashed with SHA-256. Saved JSON/SARIF/baselines contain the full 64 hex characters;
text and HTML display 12. The hash has no reversible encoding of the secret,
but unkeyed hashes of guessable values can be guessed offline. Treat reports
and baselines as sensitive metadata. Renaming a file changes its fingerprint;
line moves and different commits do not. Baselines suppress matching rules and
paths across commits. Minimum severity applies before baseline creation.

Any line containing the exact marker `secretscan:ignore` is skipped. Other lines
in that file remain subject to scanning; there is no whole-file comment ignore.
The repository's single public entropy-fixture line uses this mechanism. Tests
scan all tracked files with no module-level exclusion.

## Git history and file safety

History is additional to the working-tree scan. It considers at most 200 commits
reachable from HEAD by default; merges are compared with their first parent,
and branch commits are included when reachable within the cap. The same value
may appear as several historical findings. Deleted secrets can be found in
their earlier added lines. Paths outside a requested subtree/file are ignored.
Empty repositories without HEAD return 2; shallow checkouts limit visible history.

Git uses fixed subprocess argument lists, no shell, no external diff/textconv,
no fsmonitor, no global/system config, no lazy object fetch and no allowed Git
network protocols. Reads have a **30-second timeout** and **8 MiB output cap**
per command (blob reads also obey the selected file-size bound). A cap or Git
failure aborts with 2. Binary, excluded, oversize and non-regular historical
entries are counted as skipped. Git must already have the necessary objects.

The scanner reads files without executing/importing them. It skips NUL-containing
binary files, oversize files, unreadable entries, all symlinks/junctions and
special files; skipping links prevents loops and outside-root traversal. Text
uses UTF-8 with replacement decoding. Working-tree scans are not atomic
snapshots; run against a stable tree. Exclusions and limits reduce coverage.
No scanner code opens sockets or makes network requests; a regression test
replaces socket constructors with failing functions. Build/install tools need
network access to obtain dependencies, separately from scanning.

## HTML and SARIF

HTML is one local dark-themed file with inline CSS and minimal inline filter JS,
summary cards, and rows grouped by relative file. All dynamic text is escaped
with `html.escape`; filtering uses `textContent`. No CDN, external scripts,
fonts or assets are loaded. Metadata includes version, UTC time, root name and
history status. With history enabled, files-scanned includes file revisions.

SARIF 2.1.0 includes rule metadata, relative URI locations, Unicode code-point
columns, severity levels and `partialFingerprints`. It is **structurally tested
only**, without external schema downloads or a verified GitHub SARIF upload.

## Windows executable and packaging

```powershell
.\scripts\build_exe.ps1
.\scripts\verify_exe.ps1
.\dist\secretscan.exe --version
.\dist\secretscan.exe rules
.\dist\secretscan.exe scan .work\demo\input --no-color
.\dist\secretscan.exe scan .work\demo\input --report .work\demo\exe-report.html
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe scripts\verify_wheel.py
.\.venv\Scripts\python.exe scripts\checksums.py
```

The Windows x64 single-file build bundles Python. It needs no separate Python
installation to run, but extracts its runtime into a temporary directory on
startup. PyInstaller is dev-only. The build and verifier manage project-local
temporary directories and remove them in `finally`. The executable is **unsigned**;
Windows SmartScreen or endpoint software may warn or block it. These reputation
checks have not been tested. Do not bypass organizational security policy.

`dist/` holds the `.exe`, wheel, sdist and `SHA256SUMS` locally and is ignored by
Git. The wheel checker creates an isolated venv, installs only the wheel with
`--no-index --no-deps`, runs its console command outside the repository root,
executes the full smoke suite and cleans up. Python in that disposable venv is
used only for this packaging verification. Build sizes and versions are in NOTES.

## Tests and CI

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\pytest.exe -q
git diff --check
.\.venv\Scripts\python.exe scripts\smoke_test.py
.\.venv\Scripts\python.exe -m secretscan scan . --min-severity high
```

`pyproject.toml` enforces at least 90% combined statement/branch coverage on
application code. Packaging scripts are outside that coverage target. Tests use
project-local scratch directories, synthetic provider values assembled at runtime,
and isolated Git repositories with deterministic identity and no global changes.
Where Windows denies symlink privilege, deterministic filesystem mocks exercise
the link policy; unreadable files are mocked. Hard-link overwrite prevention is
tested against an actual project-local hard link. Restricted app sandboxes may
need permission for that test; ordinary filesystem-capable runs passed locally.

The live smoke script checks text/JSON/SARIF/HTML, exits 0/1/2, baseline round trip
and absence of full synthetic values in every output. It cleans temporary data
in `finally`. Verification details are recorded in NOTES.md and STATE.md.

`.github/workflows/ci.yml` has read-only contents permission and Python 3.14 on
Ubuntu and Windows. It runs dependency checks, lint, format, both pytest entry
points, smoke, self-scan, package builds and isolated wheel checks. Windows also
builds/verifies the executable and checksums. Actions use fixed major versions.
For a consuming job with the installed package, a scan step is:

```yaml
- name: Scan checkout
  run: .venv/bin/python -m secretscan scan . --min-severity high
```

This returns 1 if findings should fail the job. Configure exclusions and review
baselines deliberately. Hosted execution, Linux behavior and artifact uploads
remain unverified until the owner runs CI.

The optional release workflow responds to `v*` tags, requires successful CI,
checks the tag matches the package version, rebuilds/verifies all assets and
uploads them with GitHub CLI. Only its publish job has `contents: write`.
It does not publish to PyPI. No tag, push or release command is a local gate;
the owner must review CI and push protection before any release.

## Project layout

```text
src/secretscan/       CLI, rules, safe traversal, history, serializers
tests/               Synthetic regression and tracked-file self-scan tests
scripts/             Smoke, demo, executable and wheel verification, checksums
packaging/           PyInstaller entry and spec
.github/workflows/   Read-only CI and optional tag-triggered release
README.md            Usage and limitations
NOTES.md             Actual local evidence and build choices
STATE.md             Concise current checkpoint
CHANGELOG.md         Version history
```

## Known limitations and responsible use

This tool does not verify that a secret is live, decode/verify JWTs, decrypt
anything, inspect encoded or obfuscated secrets, or cover every provider format.
Heuristics have false positives and false negatives. The configured file/history
limits and skipped entries leave gaps; Git history is limited to reachable,
locally available commits. Baselines and inline ignores can hide real problems.
Concurrent filesystem replacement is outside its snapshot guarantees. Output
files are individually written, not a transaction across several destinations.

It is not a replacement for GitHub secret scanning or gitleaks, and no parity
with those tools is claimed. Use it only on files and repositories you own or
are authorized to inspect. A suspected leaked credential should be reviewed
and revoked/rotated through its provider, then removed from relevant storage
and history under an authorized remediation process.
