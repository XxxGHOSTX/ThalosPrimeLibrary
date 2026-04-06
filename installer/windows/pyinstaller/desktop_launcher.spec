# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
UI_STATIC = PROJECT_ROOT / "thalos_prime" / "ui" / "static"
UI_TEMPLATES = PROJECT_ROOT / "thalos_prime" / "ui" / "templates"

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "thalos_prime" / "desktop_launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(UI_STATIC), "thalos_prime/ui/static"),
        (str(UI_TEMPLATES), "thalos_prime/ui/templates"),
        (str(PROJECT_ROOT / ".env.example"), "."),
    ],
    hiddenimports=[
        "uvicorn",
        "fastapi",
        "thalos_prime.api.server",
        "thalos_prime.api.routes.settings",
        "thalos_prime.user_settings",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ThalosPrimeLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ThalosPrime",
)
