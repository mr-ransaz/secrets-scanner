# Changelog

## Unreleased — 0.1.0

- Added Windows console-owned guided startup for double-click and single-folder
  drag-and-drop, masked summaries, outside-tree HTML reports, browser consent
  and an exit pause. Terminals, redirected streams and normal CLI commands keep
  CLI behavior. Console API failures safely fall back to the CLI.
- Added simulated guided-mode and console-API regression tests and redirected
  startup checks to the executable verifier and live smoke test.

- Initial defensive scanner with bounded rule patterns, masked findings,
  fingerprint baselines, safe traversal, text and JSON output.
- Added bounded offline Git history, SARIF 2.1.0, self-contained escaped HTML,
  masking of secret-like path labels and subprocess smoke verification.
- Added Windows single-file executable packaging, executable/wheel verifiers,
  local release checksums, read-only cross-platform CI and optional release CI.
- Protected output hard links and redacted detected values in metadata;
  documented thresholds, security design, local evidence and remaining checks.
