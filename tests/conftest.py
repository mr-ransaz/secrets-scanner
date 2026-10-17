"""Create the test scratch parent even in a fresh checkout."""

import os
from pathlib import Path


def pytest_configure(config):
    parent = Path(__file__).resolve().parents[1] / ".work" / "pytest"
    parent.mkdir(parents=True, exist_ok=True)
    os.environ["PYTEST_DEBUG_TEMPROOT"] = str(parent)
