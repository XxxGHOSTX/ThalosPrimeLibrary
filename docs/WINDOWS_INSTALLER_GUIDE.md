# Thalos Prime Windows Installer (3 Steps)

## 1) Download and extract
- Download the release ZIP and extract it.
- Open the extracted folder.

## 2) Run installer
- Double-click `Setup.exe`.
- Keep defaults for easiest install:
  - Start Menu shortcut: enabled
  - Desktop shortcut: enabled (prompted during install)

## 3) Launch
- Start Thalos Prime from Desktop or Start Menu.
- On first launch, setup is automatic:
  - Per-user config is created in AppData
  - Runtime data folder is created
  - Backend starts
  - Matrix UI opens in browser

---

## Troubleshooting

### App does not open UI
- Wait up to 20 seconds after first launch.
- Confirm no firewall prompt is blocking localhost access.
- Open `http://127.0.0.1:8000/` manually in browser.

### Port conflict
- Open Settings tab in UI and change Runtime Port.
- Save settings and relaunch from shortcut.

### Reinstall/Repair
- Re-run `Setup.exe` and select repair/reinstall path.
- Uninstall removes program files and shortcuts; user settings remain in AppData.

---

## Installer artifacts
- `Setup.exe` — consumer installer
- `ThalosPrime.msi` — enterprise MSI
- `SHA256SUMS.txt` — signed checksum list for release artifacts
