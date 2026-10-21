# AnyPkg v1.0.0.2 — Universal Native Linux Package Installer & Cross-Format Exporter

> **Install any Linux package format natively onto your distro (`apt`, `dnf`/`zypper`, or `pacman`), OR convert & export between formats (`.deb` ⇄ `.rpm` ⇄ `.AppImage` ⇄ `.pkg.tar.zst` ⇄ `.apk` ⇄ `.xbps` ⇄ `.txz` ⇄ `.tar.zst`).**  
> *Zero `snapd` daemon. Zero `flatpak` runtime bloat. 100% Native packages.*

---

## Dual Paper-Folder Tab Widescreen UI (`v1.0.0.2`)

Designed for **`1360x766` laptop screens** (and scaling cleanly to larger desktop monitors) with **zero outer page scrolling** and a built-in **🌙 Dark / ☀️ Light Mode** switcher:

1. **Folder Tab 1: `📥 Native System Installer`**
   - Automatically detects your host Linux distribution base (**Debian/Ubuntu/Mint**, **Fedora/RHEL/openSUSE**, or **Arch/Manjaro/EndeavourOS**).
   - Converts any dropped/opened package into your system's **100% native package format**, resolves dependencies (`apt`, `dnf`/`zypper`, `pacman` + `yay`/`paru`), and installs it in one click.
2. **Folder Tab 2: `📤 Package Converter / Exporter`**
   - Shares the exact same 2-column widescreen outfit as the Installer tab, dedicated exclusively to **exporting packages from any format to another format** without installing them on your host:
     - **`.deb` ➔ `.rpm`**, **`.deb` ➔ `.AppImage`**, **`.deb` ➔ `.pkg.tar.zst`**
     - **`.rpm` ➔ `.deb`**, **`.rpm` ➔ `.AppImage`**, **`.rpm` ➔ `.pkg.tar.zst`**
     - **`.AppImage` / `.snap` / `.tar.*` ➔ `.deb`, `.rpm`, `.pkg.tar.zst`, `.apk`, `.xbps`, `.txz`**
   - Includes a **2x4 Target Export Format Selector Grid**, **Output Folder Picker**, **Translated Target Dependency Checklist**, and **Live Exporter Processing Tracker**.

---

## Supported Input & Export Formats

| Format | Input (Read/Extract) | Export (Build Output) | Native Host Install |
| :--- | :---: | :---: | :---: |
| **Debian / Ubuntu (`.deb`)** | ✅ | ✅ | ✅ (`apt-get`) |
| **Fedora / RHEL / openSUSE (`.rpm`)** | ✅ | ✅ | ✅ (`dnf` / `zypper`) |
| **Arch Linux (`.pkg.tar.zst`)** | ✅ | ✅ | ✅ (`pacman` + `yay`/`paru`) |
| **Portable AppImage (`.AppImage`)** | ✅ | ✅ *(FUSE-less & SquashFS)* | ✅ *(Converted to native pkg)* |
| **Alpine Linux (`.apk`)** | ✅ | ✅ | ✅ *(Converted to native pkg)* |
| **Void Linux (`.xbps`)** | ✅ | ✅ | ✅ *(Converted to native pkg)* |
| **Slackware (`.txz` / `.tgz`)** | ✅ | ✅ | ✅ *(Converted to native pkg)* |
| **Solus (`.eopkg`)** | ✅ | — | ✅ *(Converted to native pkg)* |
| **Ubuntu Snap (`.snap`)** | ✅ *(No `snapd`!)* | — | ✅ *(Converted to native pkg)* |
| **Binary Tarball (`.tar.zst` / `.gz` / `.xz`)** | ✅ | ✅ (`.tar.zst`) | ✅ *(Converted to native pkg)* |

---

## Installation (Arch, Ubuntu/Mint/Debian, Fedora, openSUSE)

```bash
git clone https://github.com/YOUR_USERNAME/anypkg.git
cd anypkg
chmod +x install.sh
./install.sh
```

- On **Arch-based distros**, `./install.sh` asks which AUR helper you use (`yay`, `paru`, or `none`) — and if you choose `none`, offers to automatically build and install `yay` for you.

## Uninstallation

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## License

MIT License — see [LICENSE](LICENSE).
