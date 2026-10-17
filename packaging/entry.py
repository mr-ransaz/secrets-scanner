"""PyInstaller entry point; importing scanned files is never required."""

from secretscan.cli import main

raise SystemExit(main())
