# secrets-scanner 0.1.0

Educational, defensive offline scanner by MR Ransaz. Runtime uses Python 3.14
and the standard library only. Development is in progress; local verification
is recorded in NOTES.md and STATE.md.

`secretscan scan PATH` returns 0 for clean input, 1 for findings and 2 for errors.
`secretscan rules` lists the transparent rules. Outputs contain masked previews
and SHA-256 fingerprints. A line containing `secretscan:ignore` is skipped;
other lines in the file are still scanned.
