"""Prepare an ignored synthetic folder for README and manual executable checks."""

from pathlib import Path


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    directory = project / ".work" / "demo" / "input"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "sample.txt"
    content = "AKIA" + "7ZQ2" * 4 + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise SystemExit(
                "demo: existing sample differs; choose a clean demo directory"
            )
    else:
        path.write_text(content, encoding="utf-8")
    print("demo: prepared .work/demo/input/sample.txt (public synthetic fixture)")


if __name__ == "__main__":
    main()
