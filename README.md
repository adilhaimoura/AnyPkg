# AnyPkg v1.1.0 — Universal Native Linux Package Installer & Cross-Format Exporter

> **Install any Linux package format natively onto your distro (`apt`, `dnf`/`zypper`, or `pacman`), OR convert & export between formats (`.deb` ⇄ `.rpm` ⇄ `.AppImage` ⇄ `.pkg.tar.zst` ⇄ `.apk` ⇄ `.xbps` ⇄ `.txz` ⇄ `.tar.zst`).**  
> *Zero `snapd` daemon. Zero `flatpak` runtime bloat. 100% Native packages.*

---

## Dual Paper-Folder Tab Widescreen UI (`v1.1.0`)

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
   - **Bulk export (new in v1.1.0):** select **multiple files** in the file picker, **drag & drop several files at once**, or press **Open Folder…** to queue every supported package in a folder (top level only, no subfolders) — one click exports the whole queue into the chosen output folder, with per-file `[i/N]` progress and a success/failure summary. The Installer tab (Tab 1) stays single-file.

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

## Headless CLI (`v1.1.0`)

After `./install.sh`, AnyPkg is on your `PATH` as `anypkg`. Run it **without arguments** to open the GUI, or use the CLI on servers, scripts and CI (works **without GTK** — no display needed):

```bash
anypkg --version                        # print version
anypkg --help                           # top-level help with examples
anypkg convert --help                   # convert subcommand help

# single file
anypkg convert ./app.deb --to rpm -o ./out

# bulk: a whole folder, one source type at a time (top level only, no subfolders)
anypkg convert ./downloads --to native --pattern '*.deb' -o ./out

# bulk: several explicit files, or a glob (quote it so anypkg expands it)
anypkg convert a.deb b.rpm c.AppImage --to appimage
anypkg convert '*.pkg.tar.zst' --to deb -o ./converted
```

- Each `SOURCE` may be a package **file**, a **folder** (scanned top level only), or a **glob pattern**.
- `--to` accepts `deb`, `rpm`, `arch`, `appimage`, `apk`, `xbps`, `slackware`, `tarball`, or **`native`** (= your host distro's package format, auto-detected).
- `--pattern '*.deb'` restricts folder/glob inputs to one source type; a folder with **mixed** formats is rejected with a hint unless you pass `--pattern` — one source type per run, one target format per run.
- By default the ELF shared-library scan maps dependencies into the exported package (same shared engine as the GUI Exporter tab); pass `--no-map-deps` to skip it.
- Exit codes: `0` = everything converted, `1` = some files failed (a per-file summary is printed), `2` = bad input/usage. Output filename collisions get a `-2`, `-3`, … suffix instead of overwriting.

## Installation (Arch, Ubuntu/Mint/Debian, Fedora, openSUSE)

```bash
git clone https://github.com/adilhaimoura/anypkg.git
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

## Credits

- **[@Coding-01](https://github.com/Coding-01)** — the original `convert` CLI subcommand in their fork inspired the headless CLI and bulk conversion added in **v1.1.0** (`anypkg convert …`, multi-file / folder / multi-drop export in the GUI). Thank you!
- **adilhaimoura** — original AnyPkg: GUI dashboard, native installer and cross-format exporter.

## License

MIT License — see [LICENSE](LICENSE).
