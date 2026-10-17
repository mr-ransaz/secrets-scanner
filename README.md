# secrets-scanner 0.1.0

Educational, defensive offline scanner by MR Ransaz. Runtime uses Python 3.14
and the standard library only. Development is in progress; local verification
is recorded in NOTES.md and STATE.md.

`secretscan scan PATH` returns 0 for clean input, 1 for findings and 2 for errors.
`secretscan rules` lists the transparent rules. Outputs contain masked previews
and SHA-256 fingerprints. A line containing `secretscan:ignore` is skipped;
other lines in the file are still scanned.

`--git-history` additionally scans added lines in commits reachable from HEAD
(default `--max-commits 200`). Git must be installed and the target must be in a
repository with HEAD. Merges are compared with their first parent. Git reads
are offline with external diff/text conversion disabled, 30-second timeouts
and an 8 MiB output cap per command. Binary/oversize revisions are skipped.

`--format json|sarif` selects machine output; `--output FILE` saves it.
SARIF 2.1.0 is **structurally tested only**, without downloading a schema.
`--report FILE.html` creates a self-contained dark HTML report with escaped
values and a local text filter. All outputs mask secret-like filenames too.
Output files inside the scan tree require `--allow-in-tree`; replacing an
existing regular file additionally requires `--force`.
