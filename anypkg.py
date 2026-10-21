#!/usr/bin/env python3
"""
AnyPkg v1.0.0.2 — Universal Native Linux Package Installer & Cross-Format Exporter
Features a dual Paper-Folder Tab Widescreen Dashboard (1310x710 for 1360x766 laptops):
  • Tab 1: [📥 Native System Installer] — One-click native install into your host distro
           (Debian/Ubuntu/Mint .deb, Fedora/openSUSE .rpm, or Arch/Manjaro .pkg.tar.zst)
  • Tab 2: [📤 Package Converter / Exporter] — Convert & export between Linux package formats
           (.deb ⇄ .rpm ⇄ .AppImage ⇄ .pkg.tar.zst ⇄ .apk ⇄ .xbps ⇄ .txz ⇄ .tar.zst)
"""

import json
import os
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk, Pango

try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw

    HAS_ADW = True
except (ValueError, ImportError):
    HAS_ADW = False


APP_ID = "org.anypkg.installer"
APP_VERSION = "1.0.0.2"
APP_TITLE = f"AnyPkg v{APP_VERSION} — Universal Linux Package Installer & Exporter"
CONFIG_DIR = Path.home() / ".config" / "anypkg"
CONFIG_FILE = CONFIG_DIR / "settings.json"
SYS_CONFIG_FILE = Path("/etc/anypkg.conf")
ROOT_HELPER = "/usr/local/bin/anypkg-root-helper"

DEFAULT_SETTINGS = {
    "dark_mode": True,
    "wipeout_versions": True,
    "auto_fix_missing_deps": True,
    "install_aur_deps": True,
    "keep_converted_pkg": True,
    "auto_start_on_open": False,
    "pseudo_64bit": False,
    "aur_helper": "yay",
    "export_format": "rpm",
    "export_map_deps": True,
    "export_strip_versions": True,
    "export_bundle_desktop": True,
}

# Cross-distro common package name mappings -> (arch_name, deb_name, rpm_name)
CROSS_DISTRO_MAP = {
    "glibc": ("glibc", "libc6", "glibc"),
    "libc6": ("glibc", "libc6", "glibc"),
    "gcc-libs": ("gcc-libs", "libstdc++6", "libstdc++"),
    "libstdc++": ("gcc-libs", "libstdc++6", "libstdc++"),
    "libstdc++6": ("gcc-libs", "libstdc++6", "libstdc++"),
    "zlib": ("zlib", "zlib1g", "zlib"),
    "zlib1g": ("zlib", "zlib1g", "zlib"),
    "openssl": ("openssl", "libssl3", "openssl-libs"),
    "openssl-libs": ("openssl", "libssl3", "openssl-libs"),
    "libssl3": ("openssl", "libssl3", "openssl-libs"),
    "dbus": ("dbus", "libdbus-1-3", "dbus-libs"),
    "dbus-libs": ("dbus", "libdbus-1-3", "dbus-libs"),
    "alsa-lib": ("alsa-lib", "libasound2", "alsa-lib"),
    "libasound2": ("alsa-lib", "libasound2", "alsa-lib"),
    "at-spi2-core": ("at-spi2-core", "libatspi2.0-0", "at-spi2-core"),
    "atk": ("at-spi2-core", "libatk1.0-0", "atk"),
    "libcups": ("libcups", "libcups2", "cups-libs"),
    "cups-libs": ("libcups", "libcups2", "cups-libs"),
    "libcups2": ("libcups", "libcups2", "cups-libs"),
    "gtk3": ("gtk3", "libgtk-3-0", "gtk3"),
    "libgtk-3-0": ("gtk3", "libgtk-3-0", "gtk3"),
    "gtk4": ("gtk4", "libgtk-4-1", "gtk4"),
    "libgtk-4-1": ("gtk4", "libgtk-4-1", "gtk4"),
    "libnotify": ("libnotify", "libnotify4", "libnotify"),
    "libx11": ("libx11", "libx11-6", "libX11"),
    "libX11": ("libx11", "libx11-6", "libX11"),
    "libxcomposite": ("libxcomposite", "libxcomposite1", "libXcomposite"),
    "libXcomposite": ("libxcomposite", "libxcomposite1", "libXcomposite"),
    "libxcursor": ("libxcursor", "libxcursor1", "libXcursor"),
    "libXcursor": ("libxcursor", "libxcursor1", "libXcursor"),
    "libxdamage": ("libxdamage", "libxdamage1", "libXdamage"),
    "libXdamage": ("libxdamage", "libxdamage1", "libXdamage"),
    "libxext": ("libxext", "libxext6", "libXext"),
    "libXext": ("libxext", "libxext6", "libXext"),
    "libxfixes": ("libxfixes", "libxfixes3", "libXfixes"),
    "libXfixes": ("libxfixes", "libxfixes3", "libXfixes"),
    "libxi": ("libxi", "libxi6", "libXi"),
    "libXi": ("libxi", "libxi6", "libXi"),
    "libxrandr": ("libxrandr", "libxrandr2", "libXrandr"),
    "libXrandr": ("libxrandr", "libxrandr2", "libXrandr"),
    "libxrender": ("libxrender", "libxrender1", "libXrender"),
    "libXrender": ("libxrender", "libxrender1", "libXrender"),
    "libxss": ("libxss", "libxss1", "libXScrnSaver"),
    "libXScrnSaver": ("libxss", "libxss1", "libXScrnSaver"),
    "libxtst": ("libxtst", "libxtst6", "libXtst"),
    "libXtst": ("libxtst", "libxtst6", "libXtst"),
    "libxcb": ("libxcb", "libxcb1", "libxcb"),
    "libxkbcommon": ("libxkbcommon", "libxkbcommon0", "libxkbcommon"),
    "libdrm": ("libdrm", "libdrm2", "libdrm"),
    "mesa": ("mesa", "libgbm1", "mesa-libgbm"),
    "mesa-libgbm": ("mesa", "libgbm1", "mesa-libgbm"),
    "libgbm1": ("mesa", "libgbm1", "mesa-libgbm"),
    "nspr": ("nspr", "libnspr4", "nspr"),
    "nss": ("nss", "libnss3", "nss"),
    "pango": ("pango", "libpango-1.0-0", "pango"),
    "cairo": ("cairo", "libcairo2", "cairo"),
    "gdk-pixbuf2": ("gdk-pixbuf2", "libgdk-pixbuf-2.0-0", "gdk-pixbuf2"),
    "expat": ("expat", "libexpat1", "expat"),
    "curl": ("curl", "libcurl4", "libcurl"),
    "libcurl": ("curl", "libcurl4", "libcurl"),
    "fuse2": ("fuse2", "libfuse2", "fuse-libs"),
    "fuse-libs": ("fuse2", "libfuse2", "fuse-libs"),
    "xdg-utils": ("xdg-utils", "xdg-utils", "xdg-utils"),
}

BASE_GLIBC_SONAMES = {
    "libc.so.6",
    "libm.so.6",
    "libdl.so.2",
    "libpthread.so.0",
    "librt.so.1",
    "libresolv.so.2",
    "libutil.so.1",
    "ld-linux-x86-64.so.2",
    "ld-linux.so.2",
    "libgcc_s.so.1",
    "libstdc++.so.6",
}

EXPORT_FORMATS = [
    ("deb", "📦  Debian / Ubuntu (.deb)", ".deb"),
    ("rpm", "🎩  Fedora / RHEL / openSUSE (.rpm)", ".rpm"),
    ("arch", "🏔️  Arch Linux (.pkg.tar.zst)", ".pkg.tar.zst"),
    ("appimage", "🚀  Portable AppImage (.AppImage)", ".AppImage"),
    ("apk", "🌲  Alpine Linux (.apk)", ".apk"),
    ("xbps", "🌌  Void Linux (.xbps)", ".xbps"),
    ("slackware", "💿  Slackware (.txz)", ".txz"),
    ("tarball", "📁  Standalone Binary Tarball (.tar.zst)", ".tar.zst"),
]


# ---------------------------------------------------------------------------
# Host Distro & Settings Detection
# ---------------------------------------------------------------------------
def detect_host_distro() -> dict:
    pretty_name = "Linux"
    os_id = ""
    id_like = ""
    try:
        os_rel = Path("/etc/os-release")
        if os_rel.exists():
            for line in os_rel.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("PRETTY_NAME="):
                    pretty_name = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("ID="):
                    os_id = line.split("=", 1)[1].strip().strip('"').lower()
                elif line.startswith("ID_LIKE="):
                    id_like = line.split("=", 1)[1].strip().strip('"').lower()
    except Exception:
        pass

    combined = f"{os_id} {id_like}"
    if shutil.which("pacman") or "arch" in combined:
        return {
            "base": "arch",
            "pretty": pretty_name,
            "ext": ".pkg.tar.zst",
            "pkg_mgr": "pacman",
            "label": f"{pretty_name} (Arch Base • Native .pkg.tar.zst)",
        }
    if shutil.which("apt-get") or any(k in combined for k in ("debian", "ubuntu", "mint")):
        return {
            "base": "deb",
            "pretty": pretty_name,
            "ext": ".deb",
            "pkg_mgr": "apt",
            "label": f"{pretty_name} (Debian/Ubuntu Base • Native .deb)",
        }
    if shutil.which("dnf") or shutil.which("zypper") or any(
        k in combined for k in ("fedora", "rhel", "suse", "centos")
    ):
        mgr = "zypper" if shutil.which("zypper") and not shutil.which("dnf") else "dnf"
        return {
            "base": "rpm",
            "pretty": pretty_name,
            "ext": ".rpm",
            "pkg_mgr": mgr,
            "label": f"{pretty_name} (RPM Base • Native .rpm via {mgr})",
        }
    return {
        "base": "arch",
        "pretty": pretty_name,
        "ext": ".pkg.tar.zst",
        "pkg_mgr": "pacman",
        "label": f"{pretty_name} (Arch Base • Native .pkg.tar.zst)",
    }


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        if SYS_CONFIG_FILE.exists():
            sys_data = json.loads(SYS_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(sys_data, dict):
                settings.update(sys_data)
    except Exception:
        pass
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update(data)
    except Exception:
        pass
    return settings


def save_settings(settings: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Built-in Graphical SUDO_ASKPASS mode
# ---------------------------------------------------------------------------
def run_askpass_dialog(prompt_text: str) -> int:
    if HAS_ADW:
        Adw.init()
    result = {"password": None}

    app = Gtk.Application(application_id="org.anypkg.askpass")

    def on_activate(application):
        win = Gtk.ApplicationWindow(application=application)
        win.set_title("Authentication Required (sudo)")
        win.set_default_size(420, 180)
        win.set_resizable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        win.set_child(box)

        lbl = Gtk.Label(label=prompt_text or "Enter your sudo password to continue:")
        lbl.set_wrap(True)
        lbl.set_xalign(0)
        box.append(lbl)

        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        entry.set_hexpand(True)
        box.append(entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        box.append(btn_box)

        cancel_btn = Gtk.Button(label="Cancel")
        ok_btn = Gtk.Button(label="Authenticate")
        ok_btn.add_css_class("suggested-action")
        btn_box.append(cancel_btn)
        btn_box.append(ok_btn)

        def submit(*_args):
            result["password"] = entry.get_text()
            win.close()

        def cancel(*_args):
            result["password"] = None
            win.close()

        ok_btn.connect("clicked", submit)
        entry.connect("activate", submit)
        cancel_btn.connect("clicked", cancel)
        win.present()

    app.connect("activate", on_activate)
    app.run([])

    if result["password"] is not None:
        sys.stdout.write(result["password"] + "\n")
        sys.stdout.flush()
        return 0
    return 1


# ---------------------------------------------------------------------------
# Package Format Detection & Metadata Inspection
# ---------------------------------------------------------------------------
def detect_package_format(path: Path) -> str:
    name_lower = path.name.lower()
    if (
        name_lower.endswith(".pkg.tar.zst")
        or name_lower.endswith(".pkg.tar.xz")
        or name_lower.endswith(".pkg.tar.gz")
    ):
        return "arch"
    if name_lower.endswith(".deb") or name_lower.endswith(".udeb"):
        return "deb"
    if name_lower.endswith(".rpm"):
        return "rpm"
    if name_lower.endswith(".appimage"):
        return "appimage"
    if name_lower.endswith(".apk"):
        return "apk"
    if name_lower.endswith(".xbps"):
        return "xbps"
    if name_lower.endswith(".txz") or name_lower.endswith(".tgz") or name_lower.endswith(".tlz"):
        return "slackware"
    if name_lower.endswith(".eopkg"):
        return "eopkg"
    if name_lower.endswith(".snap"):
        return "snap"
    if any(
        name_lower.endswith(ext)
        for ext in (".tar.gz", ".tar.xz", ".tar.zst", ".tar.bz2")
    ):
        return "tarball"
    return "unknown"


FORMAT_LABELS = {
    "deb": "Debian / Ubuntu (.deb)",
    "rpm": "Fedora / RHEL / openSUSE (.rpm)",
    "appimage": "Portable AppImage (.AppImage)",
    "apk": "Alpine Linux (.apk)",
    "xbps": "Void Linux (.xbps)",
    "slackware": "Slackware (.txz / .tgz)",
    "eopkg": "Solus (.eopkg)",
    "snap": "Snap Archive (.snap)",
    "tarball": "Binary Tarball (.tar.*)",
    "arch": "Arch Linux (.pkg.tar.*)",
    "unknown": "Unknown Format",
}


def sanitize_pkgname(raw_name: str) -> str:
    name = raw_name.strip().lower()
    name = re.sub(r"_(amd64|x86_64|i386|i686|arm64|aarch64|all|any)$", "", name)
    name = re.sub(r"[^a-z0-9@._+-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "converted-pkg"


def sanitize_pkgver(raw_ver: str) -> str:
    ver = raw_ver.strip()
    if ":" in ver:
        ver = ver.split(":", 1)[1]
    ver = ver.replace("-", ".").replace("_", ".").replace("~", ".")
    ver = re.sub(r"[^a-zA-Z0-9.]", "", ver).strip(".")
    if not ver or not ver[0].isdigit():
        ver = "1.0." + ver if ver else "1.0.0"
    return ver


def strip_version_constraint(dep_str: str) -> str:
    return re.split(r"[<>=:(]", dep_str.strip(), maxsplit=1)[0].strip()


def parse_rpm_header_python(rpm_path: Path) -> dict:
    info = {}
    try:
        with rpm_path.open("rb") as f:
            lead = f.read(96)
            if len(lead) < 96 or lead[:4] != b"\xed\xab\xee\xdb":
                return info

            def read_hdr():
                magic = f.read(8)
                if len(magic) < 8 or magic[:3] != b"\x8e\xad\xe8":
                    return None, None
                nindex, hsize = struct.unpack(">II", f.read(8))
                index_data = f.read(16 * nindex)
                store = f.read(hsize)
                return (nindex, index_data), store

            sig_idx, _sig_store = read_hdr()
            if sig_idx is None:
                return info
            pos = f.tell()
            pad = (8 - (pos % 8)) % 8
            if pad:
                f.read(pad)

            hdr_idx, store = read_hdr()
            if hdr_idx is None:
                return info
            nindex, index_data = hdr_idx

            def get_cstr(offset: int) -> str:
                end = store.find(b"\x00", offset)
                if end == -1:
                    return ""
                return store[offset:end].decode("utf-8", errors="replace")

            def get_str_array(offset: int, count: int) -> list[str]:
                out = []
                cur = offset
                for _ in range(count):
                    end = store.find(b"\x00", cur)
                    if end == -1:
                        break
                    out.append(store[cur:end].decode("utf-8", errors="replace"))
                    cur = end + 1
                return out

            for i in range(nindex):
                tag, dtype, offset, count = struct.unpack(
                    ">IIII", index_data[i * 16 : (i + 1) * 16]
                )
                if tag == 1000 and dtype == 6:
                    info["Name"] = get_cstr(offset)
                elif tag == 1001 and dtype == 6:
                    info["Version"] = get_cstr(offset)
                elif tag == 1004 and dtype in (6, 9):
                    info["Summary"] = get_cstr(offset)
                elif tag == 1005 and dtype in (6, 9):
                    info["Description"] = get_cstr(offset)
                elif tag == 1009 and dtype == 4:
                    sz = struct.unpack(">I", store[offset : offset + 4])[0]
                    info["Size"] = f"{sz // 1024} KB"
                elif tag == 1015 and dtype == 6:
                    info["Packager"] = get_cstr(offset)
                elif tag == 1022 and dtype == 6:
                    info["Arch"] = get_cstr(offset)
                elif tag == 1049 and dtype == 8:
                    reqs = [
                        r
                        for r in get_str_array(offset, count)
                        if not r.startswith("rpmlib(") and not r.startswith("config(")
                    ]
                    info["Requires"] = ", ".join(reqs)
    except Exception:
        pass
    return info


def parse_snap_yaml_text(yaml_text: str) -> dict:
    info = {"name": "", "version": "", "summary": "", "commands": []}
    for line in yaml_text.splitlines():
        s = line.strip()
        if line.startswith("name:"):
            info["name"] = line.split(":", 1)[1].strip().strip("'\"")
        elif line.startswith("version:"):
            info["version"] = line.split(":", 1)[1].strip().strip("'\"")
        elif line.startswith("summary:"):
            info["summary"] = line.split(":", 1)[1].strip().strip("'\"")
        elif s.startswith("command:"):
            cmd = s.split(":", 1)[1].strip().strip("'\"")
            if cmd:
                info["commands"].append(cmd)
    return info


def parse_package_metadata(pkg_path: Path) -> dict:
    fmt = detect_package_format(pkg_path)
    meta = {
        "Format": FORMAT_LABELS.get(fmt, fmt),
        "Package": sanitize_pkgname(pkg_path.stem.split(".tar")[0].split(".pkg")[0]),
        "Version": "1.0.0",
        "Architecture": "x86_64",
        "Installed-Size": f"{pkg_path.stat().st_size // 1024} KB (archive)",
        "Maintainer": "Unknown",
        "Depends": "Auto-detected via ELF shared libraries & package metadata",
        "Description": f"Ready to process {pkg_path.name}.",
    }

    if fmt == "deb":
        try:
            with tempfile.TemporaryDirectory(prefix="anypkg-meta-") as tmpdir:
                proc = subprocess.run(
                    ["bsdtar", "-tf", str(pkg_path)], capture_output=True, text=True, check=False
                )
                control_member = next(
                    (l.strip() for l in proc.stdout.splitlines() if l.strip().startswith("control.tar")),
                    None,
                )
                if control_member:
                    subprocess.run(
                        ["bsdtar", "-xf", str(pkg_path), "-C", tmpdir, control_member],
                        capture_output=True,
                        check=True,
                    )
                    control_tar = Path(tmpdir) / control_member
                    ctrl_proc = subprocess.run(
                        ["bsdtar", "-xOf", str(control_tar), "./control"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if ctrl_proc.returncode != 0:
                        ctrl_proc = subprocess.run(
                            ["bsdtar", "-xOf", str(control_tar), "control"],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                    if ctrl_proc.stdout:
                        current_key = None
                        desc_lines = []
                        for line in ctrl_proc.stdout.splitlines():
                            if line.startswith((" ", "\t")):
                                if current_key == "Description":
                                    desc_lines.append(line.strip())
                                elif current_key and current_key in meta:
                                    meta[current_key] += " " + line.strip()
                                continue
                            if ":" in line:
                                k, v = line.split(":", 1)
                                k, v = k.strip(), v.strip()
                                current_key = k
                                if k == "Description":
                                    desc_lines = [v] if v else []
                                elif k in meta:
                                    meta[k] = v
                        if desc_lines:
                            meta["Description"] = " ".join(desc_lines)
        except Exception as exc:
            meta["Description"] = f"Could not inspect .deb metadata: {exc}"

    elif fmt == "rpm":
        rpm_info = parse_rpm_header_python(pkg_path)
        if rpm_info:
            meta["Package"] = rpm_info.get("Name", meta["Package"])
            meta["Version"] = rpm_info.get("Version", meta["Version"])
            meta["Architecture"] = rpm_info.get("Arch", meta["Architecture"])
            meta["Installed-Size"] = rpm_info.get("Size", meta["Installed-Size"])
            meta["Maintainer"] = rpm_info.get("Packager", meta["Maintainer"])
            meta["Depends"] = rpm_info.get("Requires", meta["Depends"])
            meta["Description"] = (
                rpm_info.get("Description") or rpm_info.get("Summary") or meta["Description"]
            )

    elif fmt in ("apk", "arch"):
        proc = subprocess.run(
            ["bsdtar", "-xOf", str(pkg_path), ".PKGINFO"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            deps = []
            for line in proc.stdout.splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = [x.strip() for x in line.split("=", 1)]
                    if k == "pkgname":
                        meta["Package"] = v
                    elif k == "pkgver":
                        meta["Version"] = v
                    elif k == "arch":
                        meta["Architecture"] = v
                    elif k == "size":
                        meta["Installed-Size"] = f"{int(v) // 1024} KB" if v.isdigit() else v
                    elif k == "packager":
                        meta["Maintainer"] = v
                    elif k == "pkgdesc":
                        meta["Description"] = v
                    elif k == "depend":
                        deps.append(v)
            if deps:
                meta["Depends"] = ", ".join(deps)

    elif fmt == "xbps":
        proc = subprocess.run(
            ["bsdtar", "-xOf", str(pkg_path), "./props.plist"],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["bsdtar", "-xOf", str(pkg_path), "props.plist"],
                capture_output=True,
                check=False,
            )
        if proc.returncode == 0 and proc.stdout:
            try:
                pl = plistlib.loads(proc.stdout)
                meta["Package"] = pl.get("pkgname", meta["Package"])
                meta["Version"] = sanitize_pkgver(pl.get("version", meta["Version"]))
                meta["Architecture"] = pl.get("architecture", meta["Architecture"])
                meta["Maintainer"] = pl.get("maintainer", meta["Maintainer"])
                meta["Description"] = pl.get("short_desc", meta["Description"])
                if "run_depends" in pl:
                    meta["Depends"] = ", ".join(pl["run_depends"])
            except Exception:
                pass

    elif fmt == "eopkg":
        proc = subprocess.run(
            ["bsdtar", "-xOf", str(pkg_path), "metadata.xml"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            try:
                root = ET.fromstring(proc.stdout)
                pkg_el = root.find("Package")
                if pkg_el is not None:
                    meta["Package"] = pkg_el.findtext("Name", meta["Package"])
                    meta["Description"] = pkg_el.findtext("Summary", meta["Description"])
                    meta["Architecture"] = pkg_el.findtext("Architecture", meta["Architecture"])
                    hist = pkg_el.find("History/Update")
                    if hist is not None:
                        meta["Version"] = hist.findtext("Version", meta["Version"])
                    deps = [
                        d.text.strip()
                        for d in pkg_el.findall("RuntimeDependencies/Dependency")
                        if d.text
                    ]
                    if deps:
                        meta["Depends"] = ", ".join(deps)
            except Exception:
                pass

    elif fmt in ("appimage", "snap"):
        m = re.match(r"^([a-zA-Z0-9._-]+?)[-_](\d+[.\d]*)", pkg_path.stem)
        if m:
            meta["Package"] = sanitize_pkgname(m.group(1))
            meta["Version"] = sanitize_pkgver(m.group(2))

    return meta


# ---------------------------------------------------------------------------
# Universal Extraction & ELF Dependency Resolver
# ---------------------------------------------------------------------------
def extract_any_to_stage(
    input_path: Path, stage_dir: Path, work_dir: Path, log_fn
) -> tuple[dict, list[str]]:
    fmt = detect_package_format(input_path)
    meta = parse_package_metadata(input_path)
    pkgname = sanitize_pkgname(meta.get("Package", input_path.stem))
    extra_deps = []
    if meta.get("Depends") and not meta["Depends"].startswith("Auto-detected"):
        extra_deps = [d.strip() for d in meta["Depends"].split(",") if d.strip()]

    if fmt == "deb":
        log_fn("==> Extracting .deb data payload…")
        deb_tmp = work_dir / "deb_tmp"
        deb_tmp.mkdir(parents=True, exist_ok=True)
        subprocess.run(["bsdtar", "-xf", str(input_path), "-C", str(deb_tmp)], check=True)
        data_tar = next(deb_tmp.glob("data.tar*"), None)
        if not data_tar:
            raise RuntimeError("Could not find data.tar.* inside .deb archive")
        subprocess.run(["bsdtar", "-xpf", str(data_tar), "-C", str(stage_dir)], check=True)

    elif fmt in ("rpm", "apk", "xbps", "slackware", "arch"):
        log_fn(f"==> Extracting {FORMAT_LABELS.get(fmt, fmt)} payload with bsdtar…")
        subprocess.run(["bsdtar", "-xpf", str(input_path), "-C", str(stage_dir)], check=True)

    elif fmt == "eopkg":
        log_fn("==> Extracting Solus (.eopkg) container and install.tar.xz payload…")
        eopkg_tmp = work_dir / "eopkg_tmp"
        eopkg_tmp.mkdir(parents=True, exist_ok=True)
        subprocess.run(["bsdtar", "-xf", str(input_path), "-C", str(eopkg_tmp)], check=True)
        install_tar = next(eopkg_tmp.glob("install.tar*"), None)
        if not install_tar:
            raise RuntimeError("Missing install.tar.* inside .eopkg")
        subprocess.run(["bsdtar", "-xpf", str(install_tar), "-C", str(stage_dir)], check=True)

    elif fmt == "appimage":
        log_fn("==> Extracting AppImage payload…")
        app_extract_dir = work_dir / "appimage_extract"
        app_extract_dir.mkdir(parents=True, exist_ok=True)
        tmp_appimage = app_extract_dir / input_path.name
        shutil.copy2(input_path, tmp_appimage)
        tmp_appimage.chmod(
            tmp_appimage.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )

        subprocess.run(
            [str(tmp_appimage), "--appimage-extract"],
            cwd=str(app_extract_dir),
            capture_output=True,
            check=False,
        )
        squash_root = app_extract_dir / "squashfs-root"
        if not squash_root.exists() and shutil.which("unsquashfs"):
            subprocess.run(
                ["unsquashfs", "-d", str(squash_root), str(tmp_appimage)],
                capture_output=True,
                check=False,
            )

        opt_dest = stage_dir / "opt" / pkgname
        usr_bin = stage_dir / "usr" / "bin"
        usr_apps = stage_dir / "usr" / "share" / "applications"
        usr_icons = stage_dir / "usr" / "share" / "pixmaps"
        opt_dest.mkdir(parents=True, exist_ok=True)
        usr_bin.mkdir(parents=True, exist_ok=True)
        usr_apps.mkdir(parents=True, exist_ok=True)
        usr_icons.mkdir(parents=True, exist_ok=True)

        if squash_root.exists():
            shutil.copytree(squash_root, opt_dest, symlinks=True, dirs_exist_ok=True)
            os.symlink(f"/opt/{pkgname}/AppRun", usr_bin / pkgname)
            for dfile in squash_root.glob("*.desktop"):
                content = dfile.read_text(encoding="utf-8", errors="replace")
                content = re.sub(
                    r"^Exec=.*$", f"Exec=/usr/bin/{pkgname} %U", content, flags=re.MULTILINE
                )
                (usr_apps / f"{pkgname}.desktop").write_text(content, encoding="utf-8")
                break
            for icon in list(squash_root.glob("*.png")) + list(squash_root.glob("*.svg")):
                if not icon.is_symlink():
                    shutil.copy2(icon, usr_icons / icon.name)
        else:
            target_bin = opt_dest / f"{pkgname}.AppImage"
            shutil.copy2(tmp_appimage, target_bin)
            os.symlink(f"/opt/{pkgname}/{pkgname}.AppImage", usr_bin / pkgname)
            extra_deps.extend(["fuse2", "zlib"])

    elif fmt == "snap":
        if not shutil.which("unsquashfs"):
            raise RuntimeError("'squashfs-tools' (unsquashfs) is required to extract .snap archives.")
        log_fn("==> Unsquashing .snap archive into native /opt layout (no snapd used)…")
        snap_root = work_dir / "snap_root"
        subprocess.run(
            ["unsquashfs", "-d", str(snap_root), str(input_path)],
            capture_output=True,
            check=True,
        )
        snap_yaml = snap_root / "meta" / "snap.yaml"
        snap_cmd = None
        if snap_yaml.exists():
            yinfo = parse_snap_yaml_text(snap_yaml.read_text(encoding="utf-8", errors="replace"))
            if yinfo["name"]:
                pkgname = sanitize_pkgname(yinfo["name"])
                meta["Package"] = pkgname
            if yinfo["version"]:
                meta["Version"] = sanitize_pkgver(yinfo["version"])
            if yinfo["summary"]:
                meta["Description"] = yinfo["summary"]
            if yinfo["commands"]:
                snap_cmd = yinfo["commands"][0].split()[0]

        opt_dest = stage_dir / "opt" / pkgname
        usr_bin = stage_dir / "usr" / "bin"
        usr_apps = stage_dir / "usr" / "share" / "applications"
        opt_dest.parent.mkdir(parents=True, exist_ok=True)
        usr_bin.mkdir(parents=True, exist_ok=True)
        usr_apps.mkdir(parents=True, exist_ok=True)

        shutil.move(str(snap_root), str(opt_dest))

        launcher = usr_bin / pkgname
        exec_rel = snap_cmd or f"usr/bin/{pkgname}"
        launcher.write_text(
            f"""#!/usr/bin/env bash
export SNAP="/opt/{pkgname}"
export LD_LIBRARY_PATH="/opt/{pkgname}/usr/lib:/opt/{pkgname}/usr/lib/x86_64-linux-gnu:/opt/{pkgname}/lib:/opt/{pkgname}/lib/x86_64-linux-gnu:${{LD_LIBRARY_PATH:-}}"
exec "/opt/{pkgname}/{exec_rel}" "$@"
""",
            encoding="utf-8",
        )
        launcher.chmod(0o755)

        gui_dir = opt_dest / "meta" / "gui"
        if gui_dir.exists():
            for dfile in gui_dir.glob("*.desktop"):
                content = dfile.read_text(encoding="utf-8", errors="replace")
                content = content.replace("${SNAP}", f"/opt/{pkgname}")
                content = re.sub(
                    r"^Exec=.*$", f"Exec=/usr/bin/{pkgname} %U", content, flags=re.MULTILINE
                )
                (usr_apps / f"{pkgname}.desktop").write_text(content, encoding="utf-8")

    elif fmt == "tarball":
        log_fn("==> Extracting binary tarball archive…")
        raw_extract = work_dir / "tar_extract"
        raw_extract.mkdir(parents=True, exist_ok=True)
        subprocess.run(["bsdtar", "-xpf", str(input_path), "-C", str(raw_extract)], check=True)
        top_entries = [p.name for p in raw_extract.iterdir()]
        if any(d in top_entries for d in ("usr", "opt", "etc", "bin", "lib")):
            shutil.copytree(raw_extract, stage_dir, symlinks=True, dirs_exist_ok=True)
        else:
            src_root = raw_extract
            if len(top_entries) == 1 and (raw_extract / top_entries[0]).is_dir():
                src_root = raw_extract / top_entries[0]
            opt_dest = stage_dir / "opt" / pkgname
            opt_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_root, opt_dest, symlinks=True, dirs_exist_ok=True)

            usr_bin = stage_dir / "usr" / "bin"
            usr_bin.mkdir(parents=True, exist_ok=True)
            for candidate in opt_dest.iterdir():
                if (
                    candidate.is_file()
                    and os.access(candidate, os.X_OK)
                    and not candidate.name.endswith(".so")
                ):
                    os.symlink(f"/opt/{pkgname}/{candidate.name}", usr_bin / pkgname)
                    break

    for foreign in (
        ".PKGINFO",
        ".MTREE",
        ".SIGN",
        ".INSTALL",
        ".CHANGELOG",
        "props.plist",
        "files.plist",
        "install",
        "metadata.xml",
        "files.xml",
        "DEBIAN",
    ):
        fp = stage_dir / foreign
        if fp.is_dir() and foreign in ("install", "DEBIAN"):
            shutil.rmtree(fp, ignore_errors=True)
        elif fp.exists() or fp.is_symlink():
            fp.unlink(missing_ok=True)
    for sign_file in stage_dir.glob(".SIGN*"):
        sign_file.unlink(missing_ok=True)

    return meta, extra_deps


def scan_elf_needed_sonames(stage_dir: Path, log_fn) -> list[str]:
    elf_files = []
    bundled_sonames = set()

    for root, _dirs, files in os.walk(stage_dir):
        for fname in files:
            fpath = Path(root) / fname
            if ".so" in fname:
                bundled_sonames.add(fname)
            if fpath.is_symlink() or not fpath.is_file():
                continue
            try:
                with fpath.open("rb") as f:
                    if f.read(4) == b"\x7fELF":
                        elf_files.append(fpath)
            except Exception:
                pass

    needed_sonames = set()
    if elf_files and shutil.which("readelf"):
        log_fn(
            f"==> Scanning {len(elf_files)} ELF binary/library file(s) for shared library dependencies…"
        )
        for i in range(0, len(elf_files), 100):
            chunk = [str(p) for p in elf_files[i : i + 100]]
            proc = subprocess.run(
                ["readelf", "-d", *chunk], capture_output=True, text=True, check=False
            )
            for line in proc.stdout.splitlines():
                if "(NEEDED)" in line and "Shared library:" in line:
                    m = re.search(r"\[([^\]]+)\]", line)
                    if m:
                        soname = m.group(1).strip()
                        if soname not in bundled_sonames and soname not in BASE_GLIBC_SONAMES:
                            needed_sonames.add(soname)
    return sorted(needed_sonames)


def resolve_dependencies_for_target(
    target_base: str, needed_sonames: list[str], extra_raw_deps: list[str]
) -> list[str]:
    if target_base in ("appimage", "tarball", "slackware"):
        return []

    resolved = set()
    tuple_idx = 0 if target_base in ("arch", "apk", "xbps") else (1 if target_base == "deb" else 2)

    for soname in needed_sonames:
        if target_base == "arch":
            lib_p = Path("/usr/lib") / soname
            if lib_p.exists() and shutil.which("pacman"):
                proc = subprocess.run(
                    ["pacman", "-Qoq", str(lib_p)], capture_output=True, text=True, check=False
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    pkg = proc.stdout.strip().splitlines()[0].strip()
                    if pkg != "glibc":
                        resolved.add(pkg)
                    continue
            if shutil.which("pkgfile"):
                pf = subprocess.run(
                    ["pkgfile", "-r", f"^/usr/lib/{re.escape(soname)}$"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if pf.returncode == 0 and pf.stdout.strip():
                    pkg = pf.stdout.strip().splitlines()[0].strip().split("/")[-1]
                    if pkg != "glibc":
                        resolved.add(pkg)
                    continue

        elif target_base == "deb":
            if shutil.which("dpkg"):
                dp = subprocess.run(
                    ["dpkg", "-S", soname], capture_output=True, text=True, check=False
                )
                if dp.returncode == 0 and dp.stdout.strip():
                    first_pkg = dp.stdout.splitlines()[0].split(":", 1)[0].strip()
                    if first_pkg and first_pkg != "libc6":
                        resolved.add(first_pkg)
                        continue
            if shutil.which("apt-file"):
                af = subprocess.run(
                    ["apt-file", "-l", "search", "-x", f"/{re.escape(soname)}$"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if af.returncode == 0 and af.stdout.strip():
                    first_pkg = af.stdout.strip().splitlines()[0].strip()
                    if first_pkg and first_pkg != "libc6":
                        resolved.add(first_pkg)
                        continue

        elif target_base == "rpm":
            lib64_p = Path("/usr/lib64") / soname
            if lib64_p.exists() and shutil.which("rpm"):
                rp = subprocess.run(
                    ["rpm", "-qf", "--qf", "%{NAME}\n", str(lib64_p)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if rp.returncode == 0 and rp.stdout.strip():
                    pkg = rp.stdout.strip().splitlines()[0].strip()
                    if pkg != "glibc":
                        resolved.add(pkg)
                    continue
            resolved.add(f"{soname}()(64bit)")

        elif target_base == "apk":
            resolved.add(f"so:{soname}")

    for raw_dep in extra_raw_deps:
        base = strip_version_constraint(raw_dep)
        if not base or base.startswith("/") or "rpmlib(" in base or base.startswith("so:"):
            continue
        if base in CROSS_DISTRO_MAP:
            mapped = CROSS_DISTRO_MAP[base][tuple_idx]
            if mapped not in ("glibc", "libc6"):
                resolved.add(mapped)
        elif base.lower() in CROSS_DISTRO_MAP:
            mapped = CROSS_DISTRO_MAP[base.lower()][tuple_idx]
            if mapped not in ("glibc", "libc6"):
                resolved.add(mapped)

    return sorted(resolved)


def normalize_usrmerge(stage_dir: Path, log_fn):
    merges = [
        (stage_dir / "bin", stage_dir / "usr" / "bin"),
        (stage_dir / "sbin", stage_dir / "usr" / "bin"),
        (stage_dir / "usr" / "sbin", stage_dir / "usr" / "bin"),
        (stage_dir / "lib", stage_dir / "usr" / "lib"),
        (stage_dir / "lib64", stage_dir / "usr" / "lib"),
        (stage_dir / "usr" / "lib64", stage_dir / "usr" / "lib"),
    ]
    for src_dir, dst_dir in merges:
        if src_dir.is_symlink():
            src_dir.unlink()
            continue
        if src_dir.exists() and src_dir.is_dir():
            log_fn(
                f"==> Normalizing filesystem hierarchy: /{src_dir.relative_to(stage_dir)} -> /{dst_dir.relative_to(stage_dir)}"
            )
            dst_dir.mkdir(parents=True, exist_ok=True)
            for item in list(src_dir.iterdir()):
                target = dst_dir / item.name
                if (
                    target.exists()
                    and target.is_dir()
                    and item.is_dir()
                    and not item.is_symlink()
                ):
                    shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)
                    shutil.rmtree(item)
                else:
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    shutil.move(str(item), str(target))
            shutil.rmtree(src_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Package Exporters / Builders for All Target Formats
# (.pkg.tar.zst, .deb, .rpm, .AppImage, .apk, .xbps, .txz, .tar.zst)
# ---------------------------------------------------------------------------
def calc_dir_size_bytes(stage_dir: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(stage_dir):
        for fn in files:
            fp = Path(root) / fn
            if not fp.is_symlink() and fp.is_file():
                total += fp.stat().st_size
    return total


def build_arch_pkg_from_stage(
    stage_dir: Path,
    pkgname: str,
    pkgver: str,
    pkgdesc: str,
    depends: list[str],
    output_dir: Path,
    log_fn,
) -> Path | None:
    normalize_usrmerge(stage_dir, log_fn)
    total_size = calc_dir_size_bytes(stage_dir)
    clean_name = sanitize_pkgname(pkgname)
    clean_ver = f"{sanitize_pkgver(pkgver)}-1"
    clean_desc = " ".join(pkgdesc.splitlines()).strip() or f"Converted package {clean_name}"

    pkginfo_lines = [
        "# Generated by AnyPkg Universal Converter",
        f"pkgname = {clean_name}",
        f"pkgbase = {clean_name}",
        f"pkgver = {clean_ver}",
        f"pkgdesc = {clean_desc[:200]}",
        "url = https://github.com/anypkg/anypkg",
        f"builddate = {int(time.time())}",
        "packager = AnyPkg Universal Converter <anypkg@local>",
        f"size = {total_size}",
        "arch = x86_64",
        "license = custom",
    ]
    for dep in depends:
        pkginfo_lines.append(f"depend = {dep}")

    (stage_dir / ".PKGINFO").write_text("\n".join(pkginfo_lines) + "\n", encoding="utf-8")
    out_pkg = output_dir / f"{clean_name}-{clean_ver}-x86_64.pkg.tar.zst"
    pack_script = f"""
    set -e
    cd "{stage_dir}"
    top_items=(".PKGINFO")
    for item in *; do
        if [[ -e "$item" ]]; then
            top_items+=("$item")
        fi
    done
    LANG=C bsdtar -czf .MTREE --format=mtree \\
        --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' \\
        "${{top_items[@]}}"
    final_items=(".PKGINFO" ".MTREE")
    for item in *; do
        if [[ -e "$item" ]]; then
            final_items+=("$item")
        fi
    done
    LANG=C bsdtar -cf - "${{final_items[@]}}" | zstd -q -T0 -f -o "{out_pkg}"
    """
    log_fn(f"==> Packing Arch package: {out_pkg.name}")
    proc = subprocess.run(
        ["fakeroot", "bash", "-c", pack_script], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0 or not out_pkg.exists():
        log_fn(f"Error building .pkg.tar.zst: {proc.stderr}")
        return None
    return out_pkg


def build_deb_pkg_from_stage(
    stage_dir: Path,
    pkgname: str,
    pkgver: str,
    pkgdesc: str,
    depends: list[str],
    output_dir: Path,
    log_fn,
) -> Path | None:
    normalize_usrmerge(stage_dir, log_fn)
    size_kb = max(1, calc_dir_size_bytes(stage_dir) // 1024)
    clean_name = re.sub(r"[^a-z0-9+.-]", "-", sanitize_pkgname(pkgname)).strip("-")
    clean_ver = sanitize_pkgver(pkgver) + "-1"
    clean_desc = " ".join(pkgdesc.splitlines()).strip() or f"Converted package {clean_name}"

    debian_dir = stage_dir / "DEBIAN"
    debian_dir.mkdir(parents=True, exist_ok=True)
    control_lines = [
        f"Package: {clean_name}",
        f"Version: {clean_ver}",
        "Section: misc",
        "Priority: optional",
        "Architecture: amd64",
        f"Installed-Size: {size_kb}",
        "Maintainer: AnyPkg Universal Converter <anypkg@local>",
    ]
    if depends:
        control_lines.append(f"Depends: {', '.join(depends)}")
    control_lines.append(f"Description: {clean_desc[:240]}")

    (debian_dir / "control").write_text("\n".join(control_lines) + "\n", encoding="utf-8")
    out_deb = output_dir / f"{clean_name}_{clean_ver}_amd64.deb"

    log_fn(f"==> Packing Debian/Ubuntu package: {out_deb.name}")
    if shutil.which("dpkg-deb"):
        cmd = ["fakeroot", "dpkg-deb", "-Zxz", "--build", str(stage_dir), str(out_deb)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and out_deb.exists():
            return out_deb

    fallback_script = f"""
    set -e
    tmp_deb="$(mktemp -d)"
    echo "2.0" > "$tmp_deb/debian-binary"
    (cd "{debian_dir}" && LANG=C bsdtar -czf "$tmp_deb/control.tar.gz" .)
    rm -rf "{debian_dir}"
    (cd "{stage_dir}" && LANG=C bsdtar -cJf "$tmp_deb/data.tar.xz" .)
    ar rcs "{out_deb}" "$tmp_deb/debian-binary" "$tmp_deb/control.tar.gz" "$tmp_deb/data.tar.xz"
    rm -rf "$tmp_deb"
    """
    proc = subprocess.run(
        ["fakeroot", "bash", "-c", fallback_script], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0 or not out_deb.exists():
        log_fn(f"Error building .deb: {proc.stderr}")
        return None
    return out_deb


def build_rpm_pkg_from_stage(
    stage_dir: Path,
    pkgname: str,
    pkgver: str,
    pkgdesc: str,
    depends: list[str],
    output_dir: Path,
    log_fn,
) -> Path | None:
    if not shutil.which("rpmbuild"):
        log_fn("Error: 'rpmbuild' (package: rpm-build / rpm-tools) is required to export .rpm files.")
        return None

    clean_name = sanitize_pkgname(pkgname)
    clean_ver = sanitize_pkgver(pkgver)
    clean_desc = " ".join(pkgdesc.splitlines()).strip() or f"Converted package {clean_name}"

    rpm_top = output_dir / "rpmbuild"
    for sub in ("BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS", "BUILDROOT"):
        (rpm_top / sub).mkdir(parents=True, exist_ok=True)

    file_entries = []
    for root, _dirs, files in os.walk(stage_dir):
        for fn in files:
            fp = Path(root) / fn
            rel = "/" + str(fp.relative_to(stage_dir))
            file_entries.append(f'"{rel}"')

    req_lines = "\n".join(f"Requires: {d}" for d in depends if d)
    spec_path = rpm_top / "SPECS" / f"{clean_name}.spec"
    spec_content = f"""Name:           {clean_name}
Version:        {clean_ver}
Release:        1
Summary:        {clean_desc[:120]}
License:        Custom
BuildArch:      x86_64
AutoReqProv:    no
{req_lines}

%description
{clean_desc}

%install
cp -a "{stage_dir}/." "%{{buildroot}}/"

%files
%defattr(-,root,root,-)
{chr(10).join(file_entries)}
"""
    spec_path.write_text(spec_content, encoding="utf-8")
    log_fn(f"==> Building RPM package with rpmbuild: {clean_name}-{clean_ver}-1.x86_64.rpm")
    proc = subprocess.run(
        [
            "rpmbuild",
            "-bb",
            "--define",
            f"_topdir {rpm_top}",
            "--define",
            "_binary_payload w2.xzdio",
            str(spec_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    built_rpms = list((rpm_top / "RPMS").rglob("*.rpm"))
    if proc.returncode != 0 or not built_rpms:
        log_fn(f"rpmbuild error: {proc.stderr or proc.stdout}")
        return None

    out_rpm = output_dir / built_rpms[0].name
    shutil.copy2(built_rpms[0], out_rpm)
    return out_rpm


def build_appimage_from_stage(
    stage_dir: Path,
    pkgname: str,
    pkgver: str,
    pkgdesc: str,
    output_dir: Path,
    log_fn,
) -> Path | None:
    """
    Build a portable, self-contained .AppImage from `stage_dir` (e.g. .deb -> .AppImage, .rpm -> .AppImage).
    Creates `AppRun`, root `.desktop` & icon, packs SquashFS via `mksquashfs` (or `appimagetool`),
    and attaches a universal FUSE/unsquashfs self-executing AppImage header.
    """
    normalize_usrmerge(stage_dir, log_fn)
    clean_name = sanitize_pkgname(pkgname)
    clean_ver = sanitize_pkgver(pkgver)

    # Locate main executable inside stage_dir
    main_exec_rel = None
    usr_bin = stage_dir / "usr" / "bin"
    if usr_bin.exists():
        exact = usr_bin / clean_name
        if exact.exists():
            main_exec_rel = f"usr/bin/{clean_name}"
        else:
            for item in sorted(usr_bin.iterdir()):
                if item.is_file() or item.is_symlink():
                    main_exec_rel = f"usr/bin/{item.name}"
                    break
    if not main_exec_rel and (stage_dir / "opt").exists():
        for root, _dirs, files in os.walk(stage_dir / "opt"):
            for fn in files:
                fp = Path(root) / fn
                if os.access(fp, os.X_OK) and not fn.endswith(".so"):
                    main_exec_rel = str(fp.relative_to(stage_dir))
                    break
            if main_exec_rel:
                break

    if not main_exec_rel:
        main_exec_rel = f"usr/bin/{clean_name}"

    # Create AppRun at root of stage_dir
    apprun = stage_dir / "AppRun"
    apprun_content = f"""#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
export APPDIR="$HERE"
export PATH="$HERE/usr/bin:$HERE/bin:$HERE/usr/local/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$HERE/usr/lib/x86_64-linux-gnu:$HERE/usr/lib64:$HERE/lib:$HERE/lib64:${{LD_LIBRARY_PATH:-}}"
export XDG_DATA_DIRS="$HERE/usr/share:${{XDG_DATA_DIRS:-/usr/local/share:/usr/share}}"
export GSETTINGS_SCHEMA_DIR="$HERE/usr/share/glib-2.0/schemas:${{GSETTINGS_SCHEMA_DIR:-}}"
exec "$HERE/{main_exec_rel}" "$@"
"""
    apprun.write_text(apprun_content, encoding="utf-8")
    apprun.chmod(0o755)

    # Ensure root .desktop file exists inside AppDir
    desktop_files = list((stage_dir / "usr" / "share" / "applications").glob("*.desktop")) if (stage_dir / "usr" / "share" / "applications").exists() else []
    if desktop_files:
        shutil.copy2(desktop_files[0], stage_dir / f"{clean_name}.desktop")
    else:
        (stage_dir / f"{clean_name}.desktop").write_text(
            f"""[Desktop Entry]
Type=Application
Name={clean_name}
Comment={pkgdesc[:120]}
Exec={clean_name}
Icon={clean_name}
Categories=Utility;
""",
            encoding="utf-8",
        )

    out_appimage = output_dir / f"{clean_name}-{clean_ver}-x86_64.AppImage"
    log_fn(f"==> Building portable AppImage: {out_appimage.name}")

    if shutil.which("appimagetool"):
        env = os.environ.copy()
        env["ARCH"] = "x86_64"
        proc = subprocess.run(
            ["appimagetool", str(stage_dir), str(out_appimage)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and out_appimage.exists():
            out_appimage.chmod(0o755)
            return out_appimage

    if not shutil.which("mksquashfs"):
        log_fn("Error: 'squashfs-tools' (mksquashfs) is required to build .AppImage packages.")
        return None

    sqfs_file = output_dir / "payload.sqfs"
    proc = subprocess.run(
        ["mksquashfs", str(stage_dir), str(sqfs_file), "-root-owned", "-noappend"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not sqfs_file.exists():
        log_fn(f"mksquashfs error: {proc.stderr}")
        return None

    # Prepend self-contained AppImage launcher header (supports --appimage-extract and FUSE-less execution)
    stub_header = b"""#!/usr/bin/env bash
set -e
SELF="$(readlink -f "$0")"
OFFSET=$(awk '/^__SQUASHFS_BELOW__/ {print NR + 1; exit 0; }' "$SELF")
if [[ "${1:-}" == "--appimage-extract" ]]; then
    rm -rf squashfs-root
    tail -n +$OFFSET "$SELF" > /tmp/anypkg-extract-$$.sqfs
    unsquashfs -d squashfs-root /tmp/anypkg-extract-$$.sqfs >/dev/null
    rm -f /tmp/anypkg-extract-$$.sqfs
    echo "Extracted to squashfs-root"
    exit 0
fi
RUN_DIR="/tmp/.appimage-${USER:-0}-$(basename "$SELF")-$(stat -c %Y "$SELF")"
if [[ ! -x "$RUN_DIR/AppRun" ]]; then
    rm -rf "$RUN_DIR"
    mkdir -p "$RUN_DIR"
    tail -n +$OFFSET "$SELF" > "$RUN_DIR/image.sqfs"
    unsquashfs -f -d "$RUN_DIR" "$RUN_DIR/image.sqfs" >/dev/null 2>&1
    rm -f "$RUN_DIR/image.sqfs"
fi
exec "$RUN_DIR/AppRun" "$@"
__SQUASHFS_BELOW__
"""
    with out_appimage.open("wb") as out_f:
        out_f.write(stub_header)
        with sqfs_file.open("rb") as sq_f:
            shutil.copyfileobj(sq_f, out_f)
    sqfs_file.unlink(missing_ok=True)
    out_appimage.chmod(0o755)
    return out_appimage


def build_apk_or_xbps_or_txz_or_tarball(
    export_fmt: str,
    stage_dir: Path,
    pkgname: str,
    pkgver: str,
    pkgdesc: str,
    depends: list[str],
    output_dir: Path,
    log_fn,
) -> Path | None:
    normalize_usrmerge(stage_dir, log_fn)
    clean_name = sanitize_pkgname(pkgname)
    clean_ver = sanitize_pkgver(pkgver)
    total_size = calc_dir_size_bytes(stage_dir)

    if export_fmt == "apk":
        pkginfo = [
            f"pkgname = {clean_name}",
            f"pkgver = {clean_ver}-r0",
            f"pkgdesc = {' '.join(pkgdesc.splitlines())[:160]}",
            "url = https://github.com/anypkg/anypkg",
            f"builddate = {int(time.time())}",
            "packager = AnyPkg Universal Exporter",
            f"size = {total_size}",
            "arch = x86_64",
            "license = custom",
        ]
        for d in depends:
            pkginfo.append(f"depend = {d}")
        (stage_dir / ".PKGINFO").write_text("\n".join(pkginfo) + "\n", encoding="utf-8")
        out_file = output_dir / f"{clean_name}-{clean_ver}-r0.apk"
        log_fn(f"==> Exporting Alpine (.apk) package: {out_file.name}")
        proc = subprocess.run(
            ["fakeroot", "bsdtar", "-czf", str(out_file), "-C", str(stage_dir), "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return out_file if proc.returncode == 0 and out_file.exists() else None

    if export_fmt == "xbps":
        plist_data = {
            "arch": "x86_64",
            "pkgname": clean_name,
            "version": f"{clean_ver}_1",
            "pkgver": f"{clean_name}-{clean_ver}_1",
            "short_desc": " ".join(pkgdesc.splitlines())[:140] or clean_name,
            "maintainer": "AnyPkg <anypkg@local>",
            "license": "custom",
            "installed_size": total_size,
            "run_depends": depends,
        }
        (stage_dir / "props.plist").write_bytes(plistlib.dumps(plist_data))
        out_file = output_dir / f"{clean_name}-{clean_ver}_1.x86_64.xbps"
        log_fn(f"==> Exporting Void Linux (.xbps) package: {out_file.name}")
        proc = subprocess.run(
            ["fakeroot", "bsdtar", "--zstd", "-cf", str(out_file), "-C", str(stage_dir), "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return out_file if proc.returncode == 0 and out_file.exists() else None

    if export_fmt == "slackware":
        inst_dir = stage_dir / "install"
        inst_dir.mkdir(parents=True, exist_ok=True)
        short_d = " ".join(pkgdesc.splitlines())[:70] or clean_name
        slack_lines = [f"{clean_name}: {clean_name} ({short_d})"] + [f"{clean_name}:" for _ in range(10)]
        (inst_dir / "slack-desc").write_text("\n".join(slack_lines) + "\n", encoding="utf-8")
        out_file = output_dir / f"{clean_name}-{clean_ver}-x86_64-1.txz"
        log_fn(f"==> Exporting Slackware (.txz) package: {out_file.name}")
        proc = subprocess.run(
            ["fakeroot", "bsdtar", "-cJf", str(out_file), "-C", str(stage_dir), "."],
            capture_output=True,
            text=True,
            check=False,
        )
        return out_file if proc.returncode == 0 and out_file.exists() else None

    # Standalone Binary Tarball (.tar.zst)
    out_file = output_dir / f"{clean_name}-{clean_ver}-x86_64.tar.zst"
    log_fn(f"==> Exporting standalone binary archive: {out_file.name}")
    proc = subprocess.run(
        ["fakeroot", "bsdtar", "--zstd", "-cf", str(out_file), "-C", str(stage_dir), "."],
        capture_output=True,
        text=True,
        check=False,
    )
    return out_file if proc.returncode == 0 and out_file.exists() else None


# ---------------------------------------------------------------------------
# Dependency Inspection & Classification Across All 3 Bases
# ---------------------------------------------------------------------------
def read_package_deps(pkg_path: Path) -> list[str]:
    fmt = detect_package_format(pkg_path)
    if fmt == "arch":
        proc = subprocess.run(
            ["bsdtar", "-xOf", str(pkg_path), ".PKGINFO"],
            capture_output=True,
            text=True,
            check=False,
        )
        return [
            l.strip()[len("depend = ") :].strip()
            for l in proc.stdout.splitlines()
            if l.strip().startswith("depend = ")
        ]
    meta = parse_package_metadata(pkg_path)
    raw = meta.get("Depends", "")
    if not raw or raw.startswith("Auto-detected"):
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]


def classify_dependencies(deps: list[str], target_base: str, aur_helper: str) -> list[dict]:
    if not deps:
        return []

    results = []
    if target_base == "arch" and shutil.which("pacman"):
        proc = subprocess.run(
            ["pacman", "-T", *deps], capture_output=True, text=True, check=False
        )
        unsatisfied_raw = set(l.strip() for l in proc.stdout.splitlines() if l.strip())
        unsatisfied_names = {strip_version_constraint(d) for d in unsatisfied_raw}
        helper_cmd = aur_helper if aur_helper in ("yay", "paru") and shutil.which(aur_helper) else None

        for dep in deps:
            base = strip_version_constraint(dep)
            if dep not in unsatisfied_raw and base not in unsatisfied_names:
                results.append({"raw": dep, "name": base, "status": "installed"})
                continue
            sync = subprocess.run(
                ["pacman", "-Sp", "--print-format", "%n", base],
                capture_output=True,
                text=True,
                check=False,
            )
            if sync.returncode == 0 and sync.stdout.strip():
                results.append({"raw": dep, "name": base, "status": "official"})
                continue
            if helper_cmd:
                aur = subprocess.run(
                    [helper_cmd, "-Si", base], capture_output=True, text=True, check=False
                )
                if aur.returncode == 0 and "Repository" in aur.stdout:
                    results.append({"raw": dep, "name": base, "status": "aur"})
                    continue
            results.append({"raw": dep, "name": base, "status": "missing"})
        return results

    if target_base == "deb" and shutil.which("dpkg-query"):
        for dep in deps:
            base = strip_version_constraint(dep).split("|")[0].strip()
            st = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", base],
                capture_output=True,
                text=True,
                check=False,
            )
            if st.returncode == 0 and "install ok installed" in st.stdout:
                results.append({"raw": dep, "name": base, "status": "installed"})
                continue
            ac = subprocess.run(
                ["apt-cache", "show", base], capture_output=True, text=True, check=False
            )
            if ac.returncode == 0 and "Package:" in ac.stdout:
                results.append({"raw": dep, "name": base, "status": "official"})
            else:
                results.append({"raw": dep, "name": base, "status": "missing"})
        return results

    if target_base == "rpm" and shutil.which("rpm"):
        for dep in deps:
            base = strip_version_constraint(dep)
            rq = subprocess.run(
                ["rpm", "-q", "--whatprovides", base],
                capture_output=True,
                text=True,
                check=False,
            )
            if rq.returncode == 0:
                results.append({"raw": dep, "name": base, "status": "installed"})
            else:
                results.append({"raw": dep, "name": base, "status": "official"})
        return results

    return [{"raw": d, "name": strip_version_constraint(d), "status": "official"} for d in deps]


def repack_package_without_deps(
    pkg_path: Path, deps_to_remove: set[str], log_fn
) -> bool:
    if not deps_to_remove:
        return True

    fmt = detect_package_format(pkg_path)
    log_fn(
        f"==> Stripping {len(deps_to_remove)} unresolvable dependency entry(s): {', '.join(sorted(deps_to_remove))}"
    )

    if fmt == "arch":
        with tempfile.TemporaryDirectory(prefix="anypkg-repack-") as tmpdir:
            tmp_path = Path(tmpdir)
            pkg_info_proc = subprocess.run(
                ["bsdtar", "-xOf", str(pkg_path), ".PKGINFO"],
                capture_output=True,
                text=True,
                check=False,
            )
            if pkg_info_proc.returncode != 0:
                return False

            new_lines = []
            for line in pkg_info_proc.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("depend = "):
                    dep_val = stripped[len("depend = ") :].strip()
                    base_val = strip_version_constraint(dep_val)
                    if dep_val in deps_to_remove or base_val in deps_to_remove:
                        continue
                new_lines.append(line)

            new_pkginfo = tmp_path / ".PKGINFO"
            new_pkginfo.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

            repack_script = f"""
            set -e
            mkdir -p "{tmp_path}/extract"
            cd "{tmp_path}/extract"
            bsdtar -xpf "{pkg_path}"
            cp "{new_pkginfo}" .PKGINFO
            rm -f .MTREE
            all_files=(".PKGINFO")
            if [[ -f .INSTALL ]]; then all_files+=(".INSTALL"); fi
            if [[ -f .CHANGELOG ]]; then all_files+=(".CHANGELOG"); fi
            for item in *; do
                if [[ -e "$item" ]]; then
                    all_files+=("$item")
                fi
            done
            LANG=C bsdtar -czf .MTREE --format=mtree \\
                --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' \\
                "${{all_files[@]}}"
            final_files=(".PKGINFO" ".MTREE")
            if [[ -f .INSTALL ]]; then final_files+=(".INSTALL"); fi
            if [[ -f .CHANGELOG ]]; then final_files+=(".CHANGELOG"); fi
            for item in *; do
                if [[ -e "$item" ]]; then
                    final_files+=("$item")
                fi
            done
            LANG=C bsdtar -cf - "${{final_files[@]}}" | zstd -q -T0 -f -o "{pkg_path}"
            """
            proc = subprocess.run(
                ["fakeroot", "bash", "-c", repack_script],
                capture_output=True,
                text=True,
                check=False,
            )
            return proc.returncode == 0

    if fmt == "deb" and shutil.which("dpkg-deb"):
        with tempfile.TemporaryDirectory(prefix="anypkg-deb-repack-") as tmpdir:
            ext_dir = Path(tmpdir) / "pkg"
            subprocess.run(["fakeroot", "dpkg-deb", "-R", str(pkg_path), str(ext_dir)], check=True)
            ctrl_file = ext_dir / "DEBIAN" / "control"
            if ctrl_file.exists():
                lines = ctrl_file.read_text(encoding="utf-8").splitlines()
                out_lines = []
                for line in lines:
                    if line.startswith("Depends:"):
                        raw_deps = [d.strip() for d in line.split(":", 1)[1].split(",") if d.strip()]
                        kept = [
                            d
                            for d in raw_deps
                            if d not in deps_to_remove
                            and strip_version_constraint(d) not in deps_to_remove
                        ]
                        if kept:
                            out_lines.append(f"Depends: {', '.join(kept)}")
                    else:
                        out_lines.append(line)
                ctrl_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
            subprocess.run(
                ["fakeroot", "dpkg-deb", "-Zxz", "--build", str(ext_dir), str(pkg_path)],
                check=True,
            )
            return True

    return True


def is_debtap_initialized() -> bool:
    cache_dir = Path("/var/cache/debtap")
    return cache_dir.exists() and len(list(cache_dir.glob("*"))) > 0


# ---------------------------------------------------------------------------
# Main Widescreen Window with Paper-Folder Tabs (v1.0.0.2)
# ---------------------------------------------------------------------------
class AnyPkgWindow(Gtk.ApplicationWindow):
    def __init__(
        self, app: Gtk.Application, initial_pkg: Path | None = None, auto_run: bool = False
    ):
        super().__init__(application=app)
        self.set_title(APP_TITLE)
        # Fits 1360x766 laptop screens with zero outer page scrolling
        self.set_default_size(1310, 715)

        self.host_info = detect_host_distro()
        self.settings = load_settings()

        # Shared / Tab 1 (Native Installer) state
        self.current_pkg: Path | None = None
        self.converted_pkg: Path | None = None
        self.is_busy = False
        self.dep_checkbuttons: dict[str, Gtk.CheckButton] = {}

        # Tab 2 (Universal Converter / Exporter) state
        self.export_src_pkg: Path | None = None
        self.export_out_dir: Path = Path.home()
        self.last_exported_file: Path | None = None
        self.export_dep_checks: dict[str, Gtk.CheckButton] = {}
        self.export_format_radios: dict[str, Gtk.CheckButton] = {}

        self._apply_css()
        self._build_ui()
        self._apply_theme()

        if initial_pkg and initial_pkg.exists():
            self.load_package_both_tabs(initial_pkg)
            if auto_run or self.settings.get("auto_start_on_open", False):
                GLib.timeout_add(350, self._trigger_auto_convert)

    def _trigger_auto_convert(self):
        if self.current_pkg and not self.is_busy:
            self.on_convert_and_install_clicked(None)
        return False

    def _apply_theme(self):
        is_dark = bool(self.settings.get("dark_mode", True))
        if HAS_ADW:
            try:
                style_mgr = Adw.StyleManager.get_default()
                style_mgr.set_color_scheme(
                    Adw.ColorScheme.FORCE_DARK if is_dark else Adw.ColorScheme.FORCE_LIGHT
                )
            except Exception:
                pass
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            try:
                gtk_settings.set_property("gtk-application-prefer-dark-theme", is_dark)
            except Exception:
                pass

        if is_dark:
            self.remove_css_class("theme-light")
            self.add_css_class("theme-dark")
            if hasattr(self, "theme_btn"):
                self.theme_btn.set_label("☀️ Light")
                self.theme_btn.set_tooltip_text("Switch to Light Mode")
        else:
            self.remove_css_class("theme-dark")
            self.add_css_class("theme-light")
            if hasattr(self, "theme_btn"):
                self.theme_btn.set_label("🌙 Dark")
                self.theme_btn.set_tooltip_text("Switch to Dark Mode")

    def on_toggle_theme_clicked(self, _btn):
        self.settings["dark_mode"] = not bool(self.settings.get("dark_mode", True))
        save_settings(self.settings)
        self._apply_theme()

    def _apply_css(self):
        css = b"""
        window.theme-dark {
            background-color: #18181f;
            color: #f0f0f5;
        }
        window.theme-light {
            background-color: #eef0f5;
            color: #1c1c21;
        }
        /* Paper Folder Notebook Tab Styling */
        window.theme-dark notebook.folder-tabs > header {
            background-color: #121218;
            border-bottom: 2px solid #3584e4;
            padding: 6px 12px 0px 12px;
        }
        window.theme-light notebook.folder-tabs > header {
            background-color: #dfe3ec;
            border-bottom: 2px solid #1c71d8;
            padding: 6px 12px 0px 12px;
        }
        notebook.folder-tabs > header > tabs > tab {
            border-radius: 10px 10px 0px 0px;
            padding: 8px 22px;
            margin-right: 6px;
            font-weight: bold;
            font-size: 13.5px;
            border: 1px solid rgba(128, 128, 140, 0.25);
            border-bottom: none;
        }
        window.theme-dark notebook.folder-tabs > header > tabs > tab {
            background-color: #22222c;
            color: #a0a4b8;
        }
        window.theme-dark notebook.folder-tabs > header > tabs > tab:checked {
            background-color: #2b2b38;
            color: #ffffff;
            border-top: 3px solid #3584e4;
        }
        window.theme-light notebook.folder-tabs > header > tabs > tab {
            background-color: #cfd5e2;
            color: #4a5060;
        }
        window.theme-light notebook.folder-tabs > header > tabs > tab:checked {
            background-color: #ffffff;
            color: #1c71d8;
            border-top: 3px solid #1c71d8;
        }
        window.theme-dark .card-panel {
            background-color: #24242e;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 10px;
            padding: 10px 14px;
        }
        window.theme-light .card-panel {
            background-color: #ffffff;
            border: 1px solid rgba(0, 0, 0, 0.11);
            border-radius: 10px;
            padding: 10px 14px;
        }
        window.theme-dark .log-view,
        window.theme-dark .log-view text {
            background-color: #131318;
            color: #d8dee9;
            font-family: Monospace;
            font-size: 11.5px;
        }
        window.theme-light .log-view,
        window.theme-light .log-view text {
            background-color: #f7f9fc;
            color: #1e2430;
            font-family: Monospace;
            font-size: 11.5px;
        }
        .section-heading {
            font-weight: bold;
            font-size: 12.5px;
            opacity: 0.85;
        }
        .badge-installed {
            background-color: #26a269;
            color: #ffffff;
            border-radius: 5px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: bold;
        }
        .badge-official {
            background-color: #1c71d8;
            color: #ffffff;
            border-radius: 5px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: bold;
        }
        .badge-aur {
            background-color: #e66100;
            color: #ffffff;
            border-radius: 5px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: bold;
        }
        .badge-missing {
            background-color: #c01c28;
            color: #ffffff;
            border-radius: 5px;
            padding: 1px 7px;
            font-size: 11px;
            font-weight: bold;
        }
        .host-strip {
            background-color: alpha(#1c71d8, 0.15);
            border: 1px solid alpha(#1c71d8, 0.40);
            border-radius: 8px;
            padding: 5px 12px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        open_btn = Gtk.Button(label="Open Package…")
        open_btn.set_icon_name("document-open-symbolic")
        open_btn.connect("clicked", self.on_open_clicked)
        header.pack_start(open_btn)

        ver_badge = Gtk.Label(label=f"v{APP_VERSION}")
        ver_badge.add_css_class("dim-label")
        header.pack_start(ver_badge)

        # Dark / Light Mode Switcher Button
        self.theme_btn = Gtk.Button(label="☀️ Light")
        self.theme_btn.connect("clicked", self.on_toggle_theme_clicked)
        header.pack_end(self.theme_btn)

        update_db_btn = Gtk.Button(label="Update DB")
        update_db_btn.set_tooltip_text("Refresh package & library mapping databases")
        update_db_btn.connect("clicked", self.on_update_db_clicked)
        header.pack_end(update_db_btn)
        self.update_db_btn = update_db_btn

        # Drag-and-drop on entire window
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk_DragAction_COPY())
        drop_target.connect("drop", self.on_file_dropped)

        # Paper Folder Notebook (Switches between Tab 1: Native Installer & Tab 2: Package Exporter)
        self.notebook = Gtk.Notebook()
        self.notebook.add_css_class("folder-tabs")
        self.notebook.set_vexpand(True)
        self.notebook.set_hexpand(True)
        self.notebook.add_controller(drop_target)
        self.set_child(self.notebook)

        # Build Tab 1 & Tab 2 with matching widescreen dashboard layout
        tab1_widget = self._build_installer_tab()
        tab1_label = Gtk.Label(label="📥   Native System Installer")
        self.notebook.append_page(tab1_widget, tab1_label)

        tab2_widget = self._build_exporter_tab()
        tab2_label = Gtk.Label(label="📤   Package Converter / Exporter")
        self.notebook.append_page(tab2_widget, tab2_label)

    # =======================================================================
    # TAB 1: NATIVE SYSTEM INSTALLER (Widescreen 2-Column Dashboard)
    # =======================================================================
    def _build_installer_tab(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_margin_top(8)
        page.set_margin_bottom(10)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_vexpand(True)
        page.set_hexpand(True)

        # Host Strip
        host_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        host_strip.add_css_class("host-strip")
        aur_cfg = self.settings.get("aur_helper", "yay")
        extra_info = f" • AUR Helper: {aur_cfg}" if self.host_info["base"] == "arch" else ""
        host_lbl = Gtk.Label(xalign=0)
        host_lbl.set_hexpand(True)
        host_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        host_lbl.set_markup(
            f"🖥 <b>Detected Host:</b> {GLib.markup_escape_text(self.host_info['label'])}{extra_info}   |   <b>100% Native Mode</b> (Zero Snapd / Zero Flatpak)"
        )
        host_strip.append(host_lbl)
        page.append(host_strip)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        columns.set_vexpand(True)
        columns.set_hexpand(True)
        columns.set_homogeneous(True)
        page.append(columns)

        # --- LEFT COLUMN (Tab 1) ---
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_vexpand(True)
        left_col.set_hexpand(True)
        columns.append(left_col)

        pkg_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pkg_card.add_css_class("card-panel")
        left_col.append(pkg_card)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pkg_card.append(top_row)

        pkg_icon = Gtk.Image.new_from_icon_name("package-x-generic")
        pkg_icon.set_pixel_size(38)
        top_row.append(pkg_icon)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_col.set_hexpand(True)
        top_row.append(title_col)

        self.pkg_title_lbl = Gtk.Label(xalign=0)
        self.pkg_title_lbl.set_markup(
            "<b>Drop any Linux package here (.deb, .rpm, .pkg.tar.zst, .AppImage, .snap…)</b>"
        )
        self.pkg_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_col.append(self.pkg_title_lbl)

        self.pkg_sub_lbl = Gtk.Label(
            label="Or click 'Browse…' / double-click any package file in your file manager.",
            xalign=0,
        )
        self.pkg_sub_lbl.add_css_class("dim-label")
        self.pkg_sub_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        title_col.append(self.pkg_sub_lbl)

        browse_btn = Gtk.Button(label="Browse…")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.connect("clicked", self.on_open_clicked)
        top_row.append(browse_btn)

        self.meta_grid = Gtk.Grid(column_spacing=12, row_spacing=3)
        pkg_card.append(self.meta_grid)

        self.meta_labels = {}
        fields = [
            ("Format", "Source Format:"),
            ("Version", "Version / Arch:"),
            ("Installed-Size", "Archive Size:"),
            ("Maintainer", "Maintainer:"),
            ("Description", "Summary:"),
        ]
        for row_idx, (key, title) in enumerate(fields):
            k_lbl = Gtk.Label(label=title, xalign=0, yalign=0)
            k_lbl.add_css_class("dim-label")
            v_lbl = Gtk.Label(label="—", xalign=0, yalign=0)
            v_lbl.set_hexpand(True)
            v_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            v_lbl.set_lines(1)
            self.meta_grid.attach(k_lbl, 0, row_idx, 1, 1)
            self.meta_grid.attach(v_lbl, 1, row_idx, 1, 1)
            self.meta_labels[key] = v_lbl

        # Options Card (Tab 1)
        opts_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        opts_card.add_css_class("card-panel")
        opts_card.set_vexpand(True)
        left_col.append(opts_card)

        opts_hdr = Gtk.Label(label="NATIVE INSTALLER OPTIONS", xalign=0)
        opts_hdr.add_css_class("section-heading")
        opts_card.append(opts_hdr)

        self._add_compact_toggle(
            opts_card,
            "wipeout_versions",
            "Strip foreign version constraints (--wipeout)",
            "Prevents Debian/Fedora epoch syntax from blocking native installation.",
        )
        self._add_compact_toggle(
            opts_card,
            "auto_fix_missing_deps",
            "Auto-remove unresolvable foreign dependencies",
            "Strips virtual foreign package names that do not exist in your distro's repos.",
        )
        self._add_compact_toggle(
            opts_card,
            "install_aur_deps",
            "Auto-resolve extra / AUR dependencies (yay / paru)",
            "On Arch, installs missing AUR dependencies automatically before pacman -U.",
        )
        self._add_compact_toggle(
            opts_card,
            "keep_converted_pkg",
            f"Keep converted native ({self.host_info['ext']}) file next to source",
            "Saves a copy of the generated native package in the same folder.",
        )
        self._add_compact_toggle(
            opts_card,
            "auto_start_on_open",
            "Instant 1-Click Auto-Install when opening from File Manager",
            "Double-clicking any package file starts conversion & installation immediately.",
        )

        # Action Bar (Tab 1)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        left_col.append(action_box)

        self.convert_install_btn = Gtk.Button(
            label=f"⚡ One-Click Convert & Install Natively ({self.host_info['pkg_mgr']})"
        )
        self.convert_install_btn.add_css_class("suggested-action")
        self.convert_install_btn.set_hexpand(True)
        self.convert_install_btn.set_size_request(-1, 42)
        self.convert_install_btn.set_sensitive(False)
        self.convert_install_btn.connect("clicked", self.on_convert_and_install_clicked)
        action_box.append(self.convert_install_btn)

        send_to_exporter_btn = Gtk.Button(label="Switch to Exporter Tab ➔")
        send_to_exporter_btn.set_size_request(-1, 42)
        send_to_exporter_btn.connect("clicked", lambda _b: self.notebook.set_current_page(1))
        action_box.append(send_to_exporter_btn)

        # --- RIGHT COLUMN (Tab 1) ---
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_col.set_vexpand(True)
        right_col.set_hexpand(True)
        columns.append(right_col)

        deps_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        deps_card.add_css_class("card-panel")
        deps_card.set_vexpand(True)
        right_col.append(deps_card)

        deps_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        deps_card.append(deps_top)

        self.deps_hdr_lbl = Gtk.Label(label="RESOLVED NATIVE DEPENDENCIES", xalign=0)
        self.deps_hdr_lbl.add_css_class("section-heading")
        self.deps_hdr_lbl.set_hexpand(True)
        deps_top.append(self.deps_hdr_lbl)

        self.reinstall_custom_btn = Gtk.Button(label="Repackage & Install Checked")
        self.reinstall_custom_btn.set_sensitive(False)
        self.reinstall_custom_btn.connect("clicked", self.on_reinstall_selected_deps_clicked)
        deps_top.append(self.reinstall_custom_btn)

        deps_scroll = Gtk.ScrolledWindow()
        deps_scroll.set_vexpand(True)
        deps_scroll.set_min_content_height(130)
        deps_card.append(deps_scroll)

        self.deps_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        deps_scroll.set_child(self.deps_list_box)

        placeholder_dep = Gtk.Label(
            label="Load and convert a package to inspect or toggle its resolved native dependencies.",
            xalign=0,
        )
        placeholder_dep.add_css_class("dim-label")
        self.deps_list_box.append(placeholder_dep)

        tracker_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tracker_card.add_css_class("card-panel")
        tracker_card.set_vexpand(True)
        right_col.append(tracker_card)

        tracker_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tracker_card.append(tracker_top)

        tracker_hdr = Gtk.Label(label="INSTALLER PROCESSING TRACKER & LIVE LOG", xalign=0)
        tracker_hdr.add_css_class("section-heading")
        tracker_top.append(tracker_hdr)

        self.step_label = Gtk.Label(label="Ready.", xalign=1)
        self.step_label.set_hexpand(True)
        self.step_label.set_ellipsize(Pango.EllipsizeMode.END)
        tracker_top.append(self.step_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        tracker_card.append(self.progress_bar)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        log_scroll.set_min_content_height(160)
        tracker_card.append(log_scroll)

        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("log-view")
        log_scroll.set_child(self.log_view)
        self.log_buffer = self.log_view.get_buffer()

        return page

    # =======================================================================
    # TAB 2: UNIVERSAL PACKAGE CONVERTER / EXPORTER (Same Outfit & Parts!)
    # =======================================================================
    def _build_exporter_tab(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_margin_top(8)
        page.set_margin_bottom(10)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_vexpand(True)
        page.set_hexpand(True)

        # Exporter Strip
        exp_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        exp_strip.add_css_class("host-strip")
        exp_lbl = Gtk.Label(xalign=0)
        exp_lbl.set_hexpand(True)
        exp_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        exp_lbl.set_markup(
            "📦 <b>Cross-Distro Package Exporter:</b> Convert between <tt>.deb</tt>, <tt>.rpm</tt>, <tt>.AppImage</tt>, <tt>.pkg.tar.zst</tt>, <tt>.apk</tt>, <tt>.xbps</tt>, <tt>.txz</tt>, and <tt>.tar.zst</tt> without installing on your host."
        )
        exp_strip.append(exp_lbl)
        page.append(exp_strip)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        columns.set_vexpand(True)
        columns.set_hexpand(True)
        columns.set_homogeneous(True)
        page.append(columns)

        # --- LEFT COLUMN (Tab 2: Source Package + Target Format Grid + Export Options + Action Bar) ---
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_col.set_vexpand(True)
        left_col.set_hexpand(True)
        columns.append(left_col)

        # 1. Source Package Card (Tab 2)
        src_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        src_card.add_css_class("card-panel")
        left_col.append(src_card)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        src_card.append(top_row)

        pkg_icon = Gtk.Image.new_from_icon_name("package-x-generic")
        pkg_icon.set_pixel_size(38)
        top_row.append(pkg_icon)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_col.set_hexpand(True)
        top_row.append(title_col)

        self.exp_title_lbl = Gtk.Label(xalign=0)
        self.exp_title_lbl.set_markup(
            "<b>Drop source package to export (.deb, .rpm, .pkg.tar.zst, .AppImage, .snap…)</b>"
        )
        self.exp_title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_col.append(self.exp_title_lbl)

        self.exp_sub_lbl = Gtk.Label(
            label="Select any source package, pick your target export format below, and click Export.",
            xalign=0,
        )
        self.exp_sub_lbl.add_css_class("dim-label")
        self.exp_sub_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        title_col.append(self.exp_sub_lbl)

        browse_btn = Gtk.Button(label="Browse…")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.connect("clicked", self.on_open_clicked)
        top_row.append(browse_btn)

        self.exp_meta_grid = Gtk.Grid(column_spacing=12, row_spacing=3)
        src_card.append(self.exp_meta_grid)

        self.exp_meta_labels = {}
        fields = [
            ("Format", "Source Format:"),
            ("Version", "Version / Arch:"),
            ("Installed-Size", "Archive Size:"),
            ("Description", "Summary:"),
        ]
        for row_idx, (key, title) in enumerate(fields):
            k_lbl = Gtk.Label(label=title, xalign=0, yalign=0)
            k_lbl.add_css_class("dim-label")
            v_lbl = Gtk.Label(label="—", xalign=0, yalign=0)
            v_lbl.set_hexpand(True)
            v_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            v_lbl.set_lines(1)
            self.exp_meta_grid.attach(k_lbl, 0, row_idx, 1, 1)
            self.exp_meta_grid.attach(v_lbl, 1, row_idx, 1, 1)
            self.exp_meta_labels[key] = v_lbl

        # 2. Target Format & Destination Card (Tab 2)
        target_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        target_card.add_css_class("card-panel")
        target_card.set_vexpand(True)
        left_col.append(target_card)

        tgt_hdr = Gtk.Label(label="SELECT TARGET EXPORT FORMAT (e.g. .deb ➔ .rpm, .deb ➔ .AppImage)", xalign=0)
        tgt_hdr.add_css_class("section-heading")
        target_card.append(tgt_hdr)

        # 2x4 Grid of Target Format Radio Buttons
        fmt_grid = Gtk.Grid(column_spacing=14, row_spacing=4)
        fmt_grid.set_Column_homogeneous(True) if hasattr(fmt_grid, "set_Column_homogeneous") else fmt_grid.set_column_homogeneous(True)
        target_card.append(fmt_grid)

        saved_fmt = self.settings.get("export_format", "rpm")
        first_radio: Gtk.CheckButton | None = None

        for idx, (fmt_key, fmt_label, _ext) in enumerate(EXPORT_FORMATS):
            chk = Gtk.CheckButton(label=fmt_label)
            if first_radio is None:
                first_radio = chk
            else:
                chk.set_group(first_radio)
            if fmt_key == saved_fmt:
                chk.set_active(True)

            def on_toggled(btn, key=fmt_key):
                if btn.get_active():
                    self.settings["export_format"] = key
                    save_settings(self.settings)
                    self._preview_export_dependencies()

            chk.connect("toggled", on_toggled)
            self.export_format_radios[fmt_key] = chk
            fmt_grid.attach(chk, idx % 2, idx // 2, 1, 1)

        # Output Directory Row
        dir_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dir_row.set_margin_top(4)
        target_card.append(dir_row)

        dir_lbl = Gtk.Label(label="Output Folder:", xalign=0)
        dir_lbl.add_css_class("dim-label")
        dir_row.append(dir_lbl)

        self.exp_dir_entry = Gtk.Label(label=str(self.export_out_dir), xalign=0)
        self.exp_dir_entry.set_hexpand(True)
        self.exp_dir_entry.set_ellipsize(Pango.EllipsizeMode.START)
        dir_row.append(self.exp_dir_entry)

        choose_dir_btn = Gtk.Button(label="Change Folder…")
        choose_dir_btn.connect("clicked", self.on_choose_export_dir_clicked)
        dir_row.append(choose_dir_btn)

        # Compact Exporter Switches
        self._add_compact_toggle(
            target_card,
            "export_map_deps",
            "Auto-translate ELF shared library dependencies to target distro",
            "Maps DT_NEEDED .so libraries into native .rpm / .deb / .pkg.tar.zst dependencies.",
        )
        self._add_compact_toggle(
            target_card,
            "export_bundle_desktop",
            "Generate AppRun & .desktop launcher for AppImage / Tarball exports",
            "Ensures exported .AppImage files run self-contained on any Linux desktop.",
        )

        # 3. Action Bar (Tab 2)
        exp_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        left_col.append(exp_action_box)

        self.export_now_btn = Gtk.Button(label="🚀 Convert & Export Package Now")
        self.export_now_btn.add_css_class("suggested-action")
        self.export_now_btn.set_hexpand(True)
        self.export_now_btn.set_size_request(-1, 42)
        self.export_now_btn.set_sensitive(False)
        self.export_now_btn.connect("clicked", self.on_export_now_clicked)
        exp_action_box.append(self.export_now_btn)

        self.open_exp_folder_btn = Gtk.Button(label="📂 Open Output Folder")
        self.open_exp_folder_btn.set_size_request(-1, 42)
        self.open_exp_folder_btn.connect("clicked", self.on_open_export_folder_clicked)
        exp_action_box.append(self.open_exp_folder_btn)

        # --- RIGHT COLUMN (Tab 2: Target Dependencies + Export Processing Tracker) ---
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_col.set_vexpand(True)
        right_col.set_hexpand(True)
        columns.append(right_col)

        exp_deps_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        exp_deps_card.add_css_class("card-panel")
        exp_deps_card.set_vexpand(True)
        right_col.append(exp_deps_card)

        exp_deps_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        exp_deps_card.append(exp_deps_top)

        self.exp_deps_hdr_lbl = Gtk.Label(
            label="TRANSLATED TARGET DEPENDENCIES (CHECK / UNCHECK BEFORE EXPORT)", xalign=0
        )
        self.exp_deps_hdr_lbl.add_css_class("section-heading")
        self.exp_deps_hdr_lbl.set_hexpand(True)
        exp_deps_top.append(self.exp_deps_hdr_lbl)

        exp_deps_scroll = Gtk.ScrolledWindow()
        exp_deps_scroll.set_vexpand(True)
        exp_deps_scroll.set_min_content_height(130)
        exp_deps_card.append(exp_deps_scroll)

        self.exp_deps_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        exp_deps_scroll.set_child(self.exp_deps_list_box)

        exp_placeholder = Gtk.Label(
            label="Load a package to preview & customize the dependencies that will be written into the exported package.",
            xalign=0,
        )
        exp_placeholder.add_css_class("dim-label")
        self.exp_deps_list_box.append(exp_placeholder)

        # Bottom-Right Card (Tab 2): Export Processing Tracker & Log
        exp_tracker_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        exp_tracker_card.add_css_class("card-panel")
        exp_tracker_card.set_vexpand(True)
        right_col.append(exp_tracker_card)

        exp_tracker_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        exp_tracker_card.append(exp_tracker_top)

        exp_tracker_hdr = Gtk.Label(label="EXPORTER PROCESSING TRACKER & LIVE LOG", xalign=0)
        exp_tracker_hdr.add_css_class("section-heading")
        exp_tracker_top.append(exp_tracker_hdr)

        self.exp_step_label = Gtk.Label(label="Ready to export.", xalign=1)
        self.exp_step_label.set_hexpand(True)
        self.exp_step_label.set_ellipsize(Pango.EllipsizeMode.END)
        exp_tracker_top.append(self.exp_step_label)

        self.exp_progress_bar = Gtk.ProgressBar()
        self.exp_progress_bar.set_show_text(True)
        exp_tracker_card.append(self.exp_progress_bar)

        exp_log_scroll = Gtk.ScrolledWindow()
        exp_log_scroll.set_vexpand(True)
        exp_log_scroll.set_min_content_height(160)
        exp_tracker_card.append(exp_log_scroll)

        self.exp_log_view = Gtk.TextView()
        self.exp_log_view.set_editable(False)
        self.exp_log_view.set_cursor_visible(False)
        self.exp_log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.exp_log_view.add_css_class("log-view")
        exp_log_scroll.set_child(self.exp_log_view)
        self.exp_log_buffer = self.exp_log_view.get_buffer()

        return page

    def _add_compact_toggle(self, parent: Gtk.Box, key: str, title: str, subtitle: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_col.set_hexpand(True)

        t_lbl = Gtk.Label(label=title, xalign=0)
        s_lbl = Gtk.Label(label=subtitle, xalign=0)
        s_lbl.add_css_class("dim-label")
        s_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        text_col.append(t_lbl)
        text_col.append(s_lbl)

        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        sw.set_active(bool(self.settings.get(key, False)))

        def on_notify(switch, _param):
            self.settings[key] = switch.get_active()
            save_settings(self.settings)

        sw.connect("notify::active", on_notify)
        row.append(text_col)
        row.append(sw)
        parent.append(row)

    # -----------------------------------------------------------------------
    # Thread-safe UI updaters for Both Tabs
    # -----------------------------------------------------------------------
    def append_log(self, text: str, exporter: bool = False):
        def _do():
            buf = self.exp_log_buffer if exporter else self.log_buffer
            view = self.exp_log_view if exporter else self.log_view
            end_iter = buf.get_end_iter()
            buf.insert(end_iter, text.rstrip("\n") + "\n")
            mark = buf.create_mark(None, buf.get_end_iter(), False)
            view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
            return False

        GLib.idle_add(_do)

    def set_progress(self, fraction: float, status_text: str, exporter: bool = False):
        def _do():
            pbar = self.exp_progress_bar if exporter else self.progress_bar
            slbl = self.exp_step_label if exporter else self.step_label
            pbar.set_fraction(max(0.0, min(1.0, fraction)))
            pbar.set_text(f"{int(fraction * 100)}%")
            slbl.set_markup(f"<b>{GLib.markup_escape_text(status_text)}</b>")
            return False

        GLib.idle_add(_do)

    def set_busy(self, busy: bool):
        def _do():
            self.is_busy = busy
            has_file = self.current_pkg is not None
            self.convert_install_btn.set_sensitive(has_file and not busy)
            self.export_now_btn.set_sensitive((self.export_src_pkg is not None) and not busy)
            self.update_db_btn.set_sensitive(not busy)
            return False

        GLib.idle_add(_do)

    def populate_deps_ui(self, classified_deps: list[dict]):
        def _do():
            child = self.deps_list_box.get_first_child()
            while child is not None:
                next_child = child.get_next_sibling()
                self.deps_list_box.remove(child)
                child = next_child

            self.dep_checkbuttons.clear()
            if not classified_deps:
                lbl = Gtk.Label(label="No external runtime dependencies required.", xalign=0)
                lbl.add_css_class("dim-label")
                self.deps_list_box.append(lbl)
                self.deps_hdr_lbl.set_text("RESOLVED NATIVE DEPENDENCIES (0)")
                self.reinstall_custom_btn.set_sensitive(False)
                return False

            for item in classified_deps:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                chk = Gtk.CheckButton(label=item["raw"])
                is_active = not (
                    item["status"] == "missing"
                    and self.settings.get("auto_fix_missing_deps", True)
                )
                chk.set_active(is_active)
                chk.set_hexpand(True)
                self.dep_checkbuttons[item["raw"]] = chk

                badge = Gtk.Label()
                if item["status"] == "installed":
                    badge.set_text("Installed")
                    badge.add_css_class("badge-installed")
                elif item["status"] == "official":
                    badge.set_text("Official Repo")
                    badge.add_css_class("badge-official")
                elif item["status"] == "aur":
                    badge.set_text("AUR")
                    badge.add_css_class("badge-aur")
                else:
                    badge.set_text("Unmapped")
                    badge.add_css_class("badge-missing")

                row.append(chk)
                row.append(badge)
                self.deps_list_box.append(row)

            self.deps_hdr_lbl.set_text(
                f"RESOLVED NATIVE DEPENDENCIES ({len(classified_deps)})"
            )
            self.reinstall_custom_btn.set_sensitive(self.converted_pkg is not None)
            return False

        GLib.idle_add(_do)

    # -----------------------------------------------------------------------
    # File Loading & Export Directory Picker
    # -----------------------------------------------------------------------
    def on_file_dropped(self, _target, value, _x, _y) -> bool:
        if isinstance(value, Gio.File):
            path_str = value.get_path()
            if path_str:
                p = Path(path_str)
                if p.exists() and detect_package_format(p) != "unknown":
                    self.load_package_both_tabs(p)
                    return True
        return False

    def on_open_clicked(self, _btn):
        patterns = [
            "*.deb",
            "*.rpm",
            "*.AppImage",
            "*.appimage",
            "*.apk",
            "*.xbps",
            "*.txz",
            "*.tgz",
            "*.tlz",
            "*.eopkg",
            "*.snap",
            "*.tar.gz",
            "*.tar.xz",
            "*.tar.zst",
            "*.tar.bz2",
            "*.pkg.tar.zst",
            "*.pkg.tar.xz",
        ]
        if hasattr(Gtk, "FileDialog"):
            dialog = Gtk.FileDialog()
            dialog.set_title("Select Linux Package")
            pkg_filter = Gtk.FileFilter()
            pkg_filter.set_name(
                "All Supported Linux Packages (.deb, .rpm, .pkg.tar.zst, .AppImage, .apk, .xbps, .txz, .eopkg, .snap, .tar.*)"
            )
            for pat in patterns:
                pkg_filter.add_pattern(pat)
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(pkg_filter)
            dialog.set_filters(filters)

            def on_open_finish(dlg, res):
                try:
                    gfile = dlg.open_finish(res)
                    if gfile and gfile.get_path():
                        self.load_package_both_tabs(Path(gfile.get_path()))
                except Exception:
                    pass

            dialog.open(self, None, on_open_finish)
        else:
            native = Gtk.FileChooserNative.new(
                "Select Linux Package",
                self,
                Gtk.FileChooserAction.OPEN,
                "_Open",
                "_Cancel",
            )
            pkg_filter = Gtk.FileFilter()
            pkg_filter.set_name("All Supported Linux Packages")
            for pat in patterns:
                pkg_filter.add_pattern(pat)
            native.add_filter(pkg_filter)

            def on_resp(dlg, response):
                if response == Gtk.ResponseType.ACCEPT:
                    gfile = dlg.get_file()
                    if gfile and gfile.get_path():
                        self.load_package_both_tabs(Path(gfile.get_path()))

            native.connect("response", on_resp)
            native.show()

    def on_choose_export_dir_clicked(self, _btn):
        if hasattr(Gtk, "FileDialog"):
            dialog = Gtk.FileDialog()
            dialog.set_title("Select Export Output Folder")

            def on_folder_finish(dlg, res):
                try:
                    gfile = dlg.select_folder_finish(res)
                    if gfile and gfile.get_path():
                        self.export_out_dir = Path(gfile.get_path())
                        self.exp_dir_entry.set_text(str(self.export_out_dir))
                except Exception:
                    pass

            dialog.select_folder(self, None, on_folder_finish)

    def on_open_export_folder_clicked(self, _btn):
        if self.export_out_dir.exists():
            subprocess.Popen(["xdg-open", str(self.export_out_dir)])

    def load_package_both_tabs(self, pkg_path: Path):
        resolved = pkg_path.resolve()
        self.current_pkg = resolved
        self.export_src_pkg = resolved
        self.export_out_dir = resolved.parent
        self.exp_dir_entry.set_text(str(self.export_out_dir))
        self.converted_pkg = None

        fmt = detect_package_format(resolved)
        meta = parse_package_metadata(resolved)

        pkg_name = GLib.markup_escape_text(meta.get("Package", resolved.stem))
        pkg_ver = GLib.markup_escape_text(meta.get("Version", ""))
        markup_title = f"<big><b>{pkg_name}</b></big>  <tt>{pkg_ver}</tt>"

        # Update Tab 1 labels
        self.pkg_title_lbl.set_markup(markup_title)
        self.pkg_sub_lbl.set_text(str(resolved))
        self.meta_labels["Format"].set_text(meta.get("Format", "-"))
        self.meta_labels["Version"].set_text(
            f"{meta.get('Version', '-')} ({meta.get('Architecture', 'x86_64')})"
        )
        self.meta_labels["Installed-Size"].set_text(meta.get("Installed-Size", "-"))
        self.meta_labels["Maintainer"].set_text(meta.get("Maintainer", "-"))
        self.meta_labels["Description"].set_text(
            " ".join(meta.get("Description", "-").splitlines())
        )

        # Update Tab 2 labels
        self.exp_title_lbl.set_markup(markup_title)
        self.exp_sub_lbl.set_text(str(resolved))
        self.exp_meta_labels["Format"].set_text(meta.get("Format", "-"))
        self.exp_meta_labels["Version"].set_text(
            f"{meta.get('Version', '-')} ({meta.get('Architecture', 'x86_64')})"
        )
        self.exp_meta_labels["Installed-Size"].set_text(meta.get("Installed-Size", "-"))
        self.exp_meta_labels["Description"].set_text(
            " ".join(meta.get("Description", "-").splitlines())
        )

        self.convert_install_btn.set_sensitive(not self.is_busy)
        self.export_now_btn.set_sensitive(not self.is_busy)

        self.set_progress(0.0, f"Loaded {resolved.name} — Ready.", exporter=False)
        self.set_progress(0.0, f"Loaded {resolved.name} — Ready to export.", exporter=True)
        self.append_log(f"Loaded {FORMAT_LABELS.get(fmt, fmt)}: {resolved}", exporter=False)
        self.append_log(f"Loaded source package ({fmt}): {resolved}", exporter=True)

        self._preview_export_dependencies()

    def _preview_export_dependencies(self):
        if not self.export_src_pkg:
            return
        meta = parse_package_metadata(self.export_src_pkg)
        raw_str = meta.get("Depends", "")
        raw_list = (
            [d.strip() for d in raw_str.split(",") if d.strip()]
            if raw_str and not raw_str.startswith("Auto-detected")
            else []
        )
        target_fmt = self.settings.get("export_format", "rpm")
        mapped = resolve_dependencies_for_target(target_fmt, [], raw_list)

        child = self.exp_deps_list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.exp_deps_list_box.remove(child)
            child = nxt

        self.export_dep_checks.clear()
        if not mapped:
            lbl = Gtk.Label(
                label=(
                    "Self-contained bundle (no external package manager dependencies)."
                    if target_fmt in ("appimage", "tarball", "slackware")
                    else "ELF shared libraries (.so) will be scanned and mapped automatically during export."
                ),
                xalign=0,
            )
            lbl.add_css_class("dim-label")
            self.exp_deps_list_box.append(lbl)
            self.exp_deps_hdr_lbl.set_text(f"TRANSLATED '{target_fmt.upper()}' DEPENDENCIES (AUTO ELF SCAN)")
            return

        for dep in mapped:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            chk = Gtk.CheckButton(label=dep)
            chk.set_active(True)
            chk.set_hexpand(True)
            self.export_dep_checks[dep] = chk

            badge = Gtk.Label(label=f"Target: {target_fmt}")
            badge.add_css_class("badge-official")
            row.append(chk)
            row.append(badge)
            self.exp_deps_list_box.append(row)

        self.exp_deps_hdr_lbl.set_text(
            f"TRANSLATED '{target_fmt.upper()}' DEPENDENCIES ({len(mapped)} PREVIEWED + ELF SCAN)"
        )

    # -----------------------------------------------------------------------
    # Subprocess & Root Execution
    # -----------------------------------------------------------------------
    def _run_streaming_cmd(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict | None = None,
        exporter: bool = False,
    ) -> int:
        self.append_log(f"$ {' '.join(cmd)}", exporter=exporter)
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line)
            self.append_log(clean, exporter=exporter)
        proc.wait()
        return proc.returncode

    def _get_askpass_env(self) -> dict:
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(Path(__file__).resolve())
        return env

    def _run_root_action(self, action: str, arg: str | None = None) -> int:
        if Path(ROOT_HELPER).exists():
            cmd = ["pkexec", ROOT_HELPER, action]
            if arg:
                cmd.append(arg)
            return self._run_streaming_cmd(cmd)

        base = self.host_info["base"]
        if action == "update-db":
            if base == "arch":
                cmd = ["pkexec", "bash", "-c", "pkgfile -u || true; debtap -u || true"]
            elif base == "deb":
                cmd = ["pkexec", "bash", "-c", "apt-get update && (apt-file update || true)"]
            else:
                cmd = ["pkexec", "bash", "-c", "dnf makecache || zypper refresh || true"]
        elif action == "install-pkg" and arg:
            if base == "arch":
                cmd = ["pkexec", "pacman", "-U", "--noconfirm", "--needed", arg]
            elif base == "deb":
                cmd = ["pkexec", "apt-get", "install", "-y", "--allow-downgrades", arg]
            elif self.host_info["pkg_mgr"] == "zypper":
                cmd = ["pkexec", "zypper", "--non-interactive", "install", "--allow-unsigned-rpm", arg]
            else:
                cmd = ["pkexec", "dnf", "install", "-y", arg]
        else:
            return 1
        return self._run_streaming_cmd(cmd)

    # -----------------------------------------------------------------------
    # Tab 1: Native System Installer Pipeline
    # -----------------------------------------------------------------------
    def on_update_db_clicked(self, _btn):
        if self.is_busy:
            return
        self.set_busy(True)

        def worker():
            try:
                self.set_progress(0.2, "Updating package & library databases (requires root)…")
                rc = self._run_root_action("update-db")
                if rc == 0:
                    self.set_progress(1.0, "Databases updated successfully!")
                else:
                    self.set_progress(0.0, f"Database update exited with code {rc}.")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def on_convert_and_install_clicked(self, _btn):
        if not self.current_pkg or self.is_busy:
            return
        self.set_busy(True)

        def worker():
            try:
                pkg_file = self.current_pkg
                assert pkg_file is not None
                src_fmt = detect_package_format(pkg_file)
                target_base = self.host_info["base"]

                if src_fmt == target_base:
                    self.append_log(
                        f"==> Package {pkg_file.name} is already in native '{target_base}' format."
                    )
                    self.converted_pkg = pkg_file
                else:
                    with tempfile.TemporaryDirectory(prefix="anypkg-work-") as tmpdir:
                        work_dir = Path(tmpdir)
                        generated_pkg: Path | None = None

                        if src_fmt == "deb" and target_base == "arch" and shutil.which("debtap"):
                            if not is_debtap_initialized():
                                self.set_progress(0.2, "Initializing debtap & pkgfile databases…")
                                self._run_root_action("update-db")

                            if is_debtap_initialized():
                                self.set_progress(0.35, f"Converting {pkg_file.name} via debtap…")
                                safe_deb = work_dir / "input_package.deb"
                                shutil.copy2(pkg_file, safe_deb)
                                flags = ["-Q"]
                                if self.settings.get("wipeout_versions", True):
                                    flags.append("-w")
                                rc = self._run_streaming_cmd(
                                    ["debtap", *flags, safe_deb.name], cwd=work_dir
                                )
                                cands = list(work_dir.glob("*.pkg.tar.*"))
                                if rc == 0 and cands:
                                    generated_pkg = cands[0]

                        if generated_pkg is None:
                            self.set_progress(
                                0.35,
                                f"Morphing {pkg_file.name} ({src_fmt}) -> native '{target_base}' package…",
                            )
                            stage_dir = work_dir / "stage"
                            stage_dir.mkdir(parents=True, exist_ok=True)
                            meta, extra_deps = extract_any_to_stage(
                                pkg_file, stage_dir, work_dir, self.append_log
                            )
                            needed_sonames = scan_elf_needed_sonames(stage_dir, self.append_log)
                            resolved_deps = resolve_dependencies_for_target(
                                target_base, needed_sonames, extra_deps
                            )
                            self.append_log(
                                f"==> Resolved {target_base} dependencies: {', '.join(resolved_deps) if resolved_deps else 'none'}"
                            )

                            pkgname = meta.get("Package", pkg_file.stem)
                            pkgver = meta.get("Version", "1.0.0")
                            pkgdesc = meta.get("Description", f"Converted from {pkg_file.name}")

                            if target_base == "arch":
                                generated_pkg = build_arch_pkg_from_stage(
                                    stage_dir,
                                    pkgname,
                                    pkgver,
                                    pkgdesc,
                                    resolved_deps,
                                    work_dir,
                                    self.append_log,
                                )
                            elif target_base == "deb":
                                generated_pkg = build_deb_pkg_from_stage(
                                    stage_dir,
                                    pkgname,
                                    pkgver,
                                    pkgdesc,
                                    resolved_deps,
                                    work_dir,
                                    self.append_log,
                                )
                            elif target_base == "rpm":
                                generated_pkg = build_rpm_pkg_from_stage(
                                    stage_dir,
                                    pkgname,
                                    pkgver,
                                    pkgdesc,
                                    resolved_deps,
                                    work_dir,
                                    self.append_log,
                                )

                        if not generated_pkg or not generated_pkg.exists():
                            self.set_progress(0.0, "Package conversion failed. See log.")
                            return

                        if self.settings.get("keep_converted_pkg", True):
                            dest_pkg = pkg_file.parent / generated_pkg.name
                        else:
                            dest_pkg = Path(tempfile.gettempdir()) / generated_pkg.name

                        shutil.copy2(generated_pkg, dest_pkg)
                        self.converted_pkg = dest_pkg
                        self.append_log(f"==> Saved native package: {dest_pkg}")

                assert self.converted_pkg is not None

                self.set_progress(0.65, "Checking native repository dependencies…")
                raw_deps = read_package_deps(self.converted_pkg)
                aur_helper = self.settings.get("aur_helper", "yay")
                classified = classify_dependencies(raw_deps, target_base, aur_helper)
                self.populate_deps_ui(classified)

                missing_deps = {d["raw"] for d in classified if d["status"] == "missing"}
                aur_deps = [d["name"] for d in classified if d["status"] == "aur"]

                if missing_deps and self.settings.get("auto_fix_missing_deps", True):
                    self.set_progress(
                        0.72,
                        f"Stripping {len(missing_deps)} unresolvable foreign dependency(s)…",
                    )
                    repack_package_without_deps(
                        self.converted_pkg, missing_deps, self.append_log
                    )

                if (
                    target_base == "arch"
                    and aur_deps
                    and self.settings.get("install_aur_deps", True)
                    and aur_helper in ("yay", "paru")
                    and shutil.which(aur_helper)
                ):
                    self.set_progress(
                        0.80,
                        f"Installing {len(aur_deps)} AUR dependency(s) via {aur_helper}…",
                    )
                    self._run_streaming_cmd(
                        [
                            aur_helper,
                            "-S",
                            "--needed",
                            "--noconfirm",
                            "--sudoflags",
                            "-A",
                            *aur_deps,
                        ],
                        env=self._get_askpass_env(),
                    )

                self.set_progress(
                    0.90,
                    f"Installing {self.converted_pkg.name} natively via {self.host_info['pkg_mgr']}…",
                )
                rc = self._run_root_action("install-pkg", str(self.converted_pkg))
                if rc == 0:
                    self.set_progress(
                        1.0,
                        f"✓ Installed {self.converted_pkg.name} natively!",
                    )
                else:
                    self.set_progress(
                        0.0,
                        "Installation failed. Uncheck broken deps above and click 'Repackage & Install Checked'.",
                    )
            except Exception as exc:
                self.append_log(f"Error: {exc}")
                self.set_progress(0.0, f"Error: {exc}")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def on_reinstall_selected_deps_clicked(self, _btn):
        if not self.converted_pkg or not self.converted_pkg.exists() or self.is_busy:
            return

        unchecked = {
            dep for dep, chk in self.dep_checkbuttons.items() if not chk.get_active()
        }
        self.set_busy(True)

        def worker():
            try:
                assert self.converted_pkg is not None
                self.set_progress(0.4, "Repackaging with checked dependencies only…")
                repack_package_without_deps(self.converted_pkg, unchecked, self.append_log)
                self.set_progress(0.8, f"Installing {self.converted_pkg.name}…")
                rc = self._run_root_action("install-pkg", str(self.converted_pkg))
                if rc == 0:
                    self.set_progress(
                        1.0, f"✓ Installed {self.converted_pkg.name} natively!"
                    )
                else:
                    self.set_progress(0.0, "Installation failed. Check log for details.")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # Tab 2: Universal Package Converter / Exporter Pipeline
    # -----------------------------------------------------------------------
    def on_export_now_clicked(self, _btn):
        if not self.export_src_pkg or self.is_busy:
            return
        self.set_busy(True)

        def exp_log(msg: str):
            self.append_log(msg, exporter=True)

        def worker():
            try:
                src_file = self.export_src_pkg
                assert src_file is not None
                src_fmt = detect_package_format(src_file)
                target_fmt = self.settings.get("export_format", "rpm")

                self.set_progress(
                    0.15,
                    f"Extracting {src_file.name} ({src_fmt}) for '{target_fmt}' export…",
                    exporter=True,
                )

                with tempfile.TemporaryDirectory(prefix="anypkg-export-") as tmpdir:
                    work_dir = Path(tmpdir)
                    stage_dir = work_dir / "stage"
                    stage_dir.mkdir(parents=True, exist_ok=True)

                    meta, extra_deps = extract_any_to_stage(
                        src_file, stage_dir, work_dir, exp_log
                    )

                    # Respect unchecked dependencies in the Exporter preview panel
                    unchecked = {
                        dep
                        for dep, chk in self.export_dep_checks.items()
                        if not chk.get_active()
                    }

                    resolved_deps = []
                    if self.settings.get("export_map_deps", True) and target_fmt not in (
                        "appimage",
                        "tarball",
                        "slackware",
                    ):
                        self.set_progress(
                            0.45,
                            f"Scanning ELF binaries & mapping '{target_fmt}' dependencies…",
                            exporter=True,
                        )
                        needed_sonames = scan_elf_needed_sonames(stage_dir, exp_log)
                        resolved_deps = [
                            d
                            for d in resolve_dependencies_for_target(
                                target_fmt, needed_sonames, extra_deps
                            )
                            if d not in unchecked
                        ]
                        exp_log(
                            f"==> Mapped '{target_fmt}' dependencies: {', '.join(resolved_deps) if resolved_deps else 'none'}"
                        )

                    # Populate Tab 2 dependency list with final resolved dependencies
                    def _update_exp_deps():
                        child = self.exp_deps_list_box.get_first_child()
                        while child is not None:
                            nxt = child.get_next_sibling()
                            self.exp_deps_list_box.remove(child)
                            child = nxt
                        self.export_dep_checks.clear()
                        for d in resolved_deps:
                            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                            chk = Gtk.CheckButton(label=d)
                            chk.set_active(True)
                            chk.set_hexpand(True)
                            self.export_dep_checks[d] = chk
                            badge = Gtk.Label(label=f"Exported ({target_fmt})")
                            badge.add_css_class("badge-installed")
                            row.append(chk)
                            row.append(badge)
                            self.exp_deps_list_box.append(row)
                        self.exp_deps_hdr_lbl.set_text(
                            f"TRANSLATED '{target_fmt.upper()}' DEPENDENCIES ({len(resolved_deps)})"
                        )
                        return False

                    GLib.idle_add(_update_exp_deps)

                    pkgname = meta.get("Package", src_file.stem)
                    pkgver = meta.get("Version", "1.0.0")
                    pkgdesc = meta.get("Description", f"Exported from {src_file.name}")

                    self.set_progress(
                        0.70,
                        f"Building target '{target_fmt}' package…",
                        exporter=True,
                    )

                    built_file: Path | None = None
                    if target_fmt == "deb":
                        built_file = build_deb_pkg_from_stage(
                            stage_dir, pkgname, pkgver, pkgdesc, resolved_deps, work_dir, exp_log
                        )
                    elif target_fmt == "rpm":
                        built_file = build_rpm_pkg_from_stage(
                            stage_dir, pkgname, pkgver, pkgdesc, resolved_deps, work_dir, exp_log
                        )
                    elif target_fmt == "arch":
                        built_file = build_arch_pkg_from_stage(
                            stage_dir, pkgname, pkgver, pkgdesc, resolved_deps, work_dir, exp_log
                        )
                    elif target_fmt == "appimage":
                        built_file = build_appimage_from_stage(
                            stage_dir, pkgname, pkgver, pkgdesc, work_dir, exp_log
                        )
                    else:
                        built_file = build_apk_or_xbps_or_txz_or_tarball(
                            target_fmt,
                            stage_dir,
                            pkgname,
                            pkgver,
                            pkgdesc,
                            resolved_deps,
                            work_dir,
                            exp_log,
                        )

                    if not built_file or not built_file.exists():
                        self.set_progress(
                            0.0,
                            f"Export to '{target_fmt}' failed. Check log below.",
                            exporter=True,
                        )
                        return

                    self.export_out_dir.mkdir(parents=True, exist_ok=True)
                    final_dest = self.export_out_dir / built_file.name
                    shutil.copy2(built_file, final_dest)
                    self.last_exported_file = final_dest
                    exp_log(f"==> ✓ Successfully exported package to: {final_dest}")
                    self.set_progress(
                        1.0,
                        f"✓ Exported: {final_dest.name}",
                        exporter=True,
                    )
            except Exception as exc:
                exp_log(f"Export error: {exc}")
                self.set_progress(0.0, f"Export error: {exc}", exporter=True)
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()


def Gdk_DragAction_COPY():
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk

    return Gdk.DragAction.COPY


class AnyPkgApp(Gtk.Application):
    def __init__(self, initial_pkg: Path | None = None, auto_run: bool = False):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.initial_pkg = initial_pkg
        self.auto_run = auto_run
        self.win: AnyPkgWindow | None = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        if HAS_ADW:
            Adw.init()

    def do_activate(self):
        if not self.win:
            self.win = AnyPkgWindow(
                self, initial_pkg=self.initial_pkg, auto_run=self.auto_run
            )
        self.win.present()

    def do_open(self, files, _n_files, _hint):
        pkg_path = None
        for gfile in files:
            if gfile.get_path():
                pkg_path = Path(gfile.get_path())
                break
        if not self.win:
            self.win = AnyPkgWindow(
                self, initial_pkg=pkg_path, auto_run=self.auto_run
            )
        elif pkg_path:
            self.win.load_package_both_tabs(pkg_path)
            if self.auto_run:
                self.win.on_convert_and_install_clicked(None)
        self.win.present()


def main():
    if len(sys.argv) >= 2 and (
        sys.argv[1] == "--askpass"
        or "password" in sys.argv[1].lower()
        or "[sudo]" in sys.argv[1].lower()
    ):
        prompt = (
            sys.argv[2]
            if (sys.argv[1] == "--askpass" and len(sys.argv) > 2)
            else sys.argv[1]
        )
        sys.exit(run_askpass_dialog(prompt))

    auto_run = False
    pkg_arg: Path | None = None

    for arg in sys.argv[1:]:
        if arg in ("-a", "--auto"):
            auto_run = True
        elif not arg.startswith("-"):
            p = Path(arg)
            if p.exists():
                pkg_arg = p

    app = AnyPkgApp(initial_pkg=pkg_arg, auto_run=auto_run)
    sys.exit(app.run([]))


if __name__ == "__main__":
    main()
