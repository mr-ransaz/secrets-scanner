"""Generate SHA256SUMS for exactly the locally built release artifacts."""

import hashlib
from pathlib import Path

from secretscan import __version__


def main() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist"
    names = [
        "secretscan.exe",
        f"secrets_scanner-{__version__}-py3-none-any.whl",
        f"secrets_scanner-{__version__}.tar.gz",
    ]
    records = []
    for name in names:
        with (dist / name).open("rb") as stream:
            records.append(
                f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {name}"
            )
    (dist / "SHA256SUMS").write_text("\n".join(records) + "\n", encoding="ascii")
    print("checksums: 3 artifacts written to dist/SHA256SUMS")


if __name__ == "__main__":
    main()
