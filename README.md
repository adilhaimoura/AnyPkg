# AnyPkg — Universal Native Linux Package Converter & Installer

> **Convert and install `.deb`, `.rpm`, `.pkg.tar.zst`, `.AppImage`, `.apk`, `.xbps`, `.txz`, `.eopkg`, `.snap`, and `.tar.*` into your Linux distribution's 100% native package format in one click.**  
> *Zero `snapd` daemon. Zero `flatpak` runtime bloat. 100% Native packages managed by `apt`, `dnf`/`zypper`, or `pacman`.*

---

## Why AnyPkg?

Most desktop Linux users run one of **3 major distribution bases**:
1. **Debian / Ubuntu / Linux Mint / Pop!_OS** (`.deb` via `apt`)
2. **Fedora / Nobara / RHEL / openSUSE** (`.rpm` via `dnf` / `zypper`)
3. **Arch Linux / Manjaro / EndeavourOS / CachyOS** (`.pkg.tar.zst` via `pacman` + `yay` / `paru`)

When a developer only distributes a program as a `.deb`, `.rpm`, `.AppImage`, or `.snap`, users on other distros are stuck. **AnyPkg** detects which system you are running on setup and converts **any of 10 Linux packaging formats** directly into your system's **native package format**, resolves all required dependencies automatically, and installs it natively in one click.

```text
  [ ANY INPUT FORMAT ]                [ UNIVERSAL STAGE ]              [ HOST NATIVE FORMAT ]
 .deb / .rpm / .pkg.tar.zst  ───►  1. Extract Payload          ───►  • Debian/Mint/Ubuntu ──► .deb  (installed via apt)
 .AppImage / .snap / .apk          2. Scan ELF Binaries (.so)        • Fedora/openSUSE    ──► .rpm  (installed via dnf/zypper)
 .xbps / .txz / .eopkg / .tar.*    3. Normalize Paths (/usr)         • Arch/Manjaro       ──► .zst  (installed via pacman + yay/paru)
```

---

## Key Features

- **Automatic Host Base Detection**: Detects whether you are on **Debian/Ubuntu/Mint**, **Fedora/RHEL/openSUSE**, or **Arch/Manjaro** and automatically targets your native package manager.
- **Widescreen Single-Screen Dashboard (`1310x710`)**: Designed to fit `1360x768` laptop screens with **zero outer page scrolling** while scaling cleanly on desktop monitors. Every section (Package Info, Options, Action Buttons, Resolved Dependencies, and Live Processing Log) is visible at a glance.
- **ELF Shared-Library Dependency Engine**: Scans all ELF binaries and `.so` libraries inside the package (`readelf -d`) and maps required `DT_NEEDED` libraries to your distro's native package names using:
  - **Arch**: `pacman -Qoq` + `pkgfile` + `debtap` + AUR resolution (`yay` / `paru`)
  - **Debian / Ubuntu / Mint**: `dpkg -S` + `apt-file`
  - **Fedora / openSUSE**: `rpm -qf` + native 64-bit SONAME resolution (`rpmbuild`)
- **Zero-Bloat Native `.AppImage` & `.snap` Conversion**: Unpacks `.AppImage` and `.snap` SquashFS archives directly into `/opt/<appname>`, creates `/usr/bin/<appname>` launchers and `/usr/share/applications/<appname>.desktop` entries, and packs them into native `.deb`, `.rpm`, or `.pkg.tar.zst` packages — **without** installing `snapd` or `flatpak`.
- **Cross-Distro "Convert Only" Mode**: Use the top-right **Target Output** dropdown to build a `.pkg.tar.zst`, `.deb`, or `.rpm` from any source package without installing.

---

## Supported Input Formats (10 Formats)

| Input Format | Origin | Converted To |
| :--- | :--- | :--- |
| **`.deb`** | Debian, Ubuntu, Linux Mint | Native `.pkg.tar.zst`, `.rpm`, or installed directly via `apt` |
| **`.rpm`** | Fedora, RHEL, openSUSE | Native `.pkg.tar.zst`, `.deb`, or installed directly via `dnf`/`zypper` |
| **`.pkg.tar.zst` / `.xz`** | Arch Linux, Manjaro | Native `.deb`, `.rpm`, or installed directly via `pacman` + `yay`/`paru` |
| **`.AppImage`** | Portable Linux Binary | Unpacked into `/opt/<app>` + `.desktop` -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.snap`** | Ubuntu Snap Archive | Unsquashed (no `snapd`!) into `/opt/<app>` + `.desktop` -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.apk`** | Alpine / Chimera Linux | Normalized & mapped -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.xbps`** | Void Linux | Normalized & mapped -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.txz` / `.tgz` / `.tlz`** | Slackware Linux | Normalized & mapped -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.eopkg`** | Solus Linux | Normalized & mapped -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |
| **`.tar.gz` / `.xz` / `.zst` / `.bz2`** | Prebuilt Binary Tarballs | Wrapped into `/opt/<app>` + `/usr/bin/<app>` -> Native `.deb`, `.rpm`, or `.pkg.tar.zst` |

---

## Installation (Arch, Ubuntu/Mint/Debian, Fedora, openSUSE)

```bash
git clone https://github.com/YOUR_USERNAME/anypkg.git
cd anypkg
chmod +x install.sh
./install.sh
```

- On **Arch-based distros**, `./install.sh` will ask which AUR helper you use (`yay`, `paru`, or `none`) — and if you select `none` (or don't have one installed yet), it will offer to automatically build and install `yay` for you.
- On **Debian/Ubuntu/Mint** and **Fedora/openSUSE**, `./install.sh` automatically installs all required native packaging and GTK4 dependencies and registers double-click file associations.

---

## Uninstallation

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## License

MIT License — see [LICENSE](LICENSE).
