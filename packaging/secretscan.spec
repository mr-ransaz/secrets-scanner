# Build with the project's venv; SPECPATH is provided by PyInstaller.
from pathlib import Path

project = Path(SPECPATH).parent
analysis = Analysis(
    [str(project / "packaging" / "entry.py")],
    pathex=[str(project / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
archive = PYZ(analysis.pure)
exe = EXE(
    archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="secretscan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
