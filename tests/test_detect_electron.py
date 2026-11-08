#!/usr/bin/env python3
"""Unit tests for bundled-Electron detection (tests the functions in anypkg.py).

Run from the repo root:  python3 tests/test_detect_electron.py
Headless-safe: no GTK, no bsdtar needed (builds a synthetic stage dir).
"""
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import anypkg  # noqa: E402


def build_fake_electron_stage(root: Path, version: str = "43.1.2") -> tuple[Path, Path]:
    """Create a fake extracted package stage that looks like an Electron app."""
    bundle = root / "opt" / "freebuff"
    (bundle / "resources").mkdir(parents=True)
    (bundle / "resources" / "app.asar").write_bytes(b"ASAR-fake-payload")
    (bundle / "resources" / "default_app.asar").write_bytes(b"ASAR-default")
    # the runtime binary must be > 20MB to be considered (real electron ~100-300MB)
    fake_bin = bundle / "freebuff"
    buf = bytearray(21 * 1024 * 1024)
    buf[0:4] = b"\x7fELF"
    tag = f"Electron/{version} Chrome/138.0.7204.0".encode()
    buf[1024 * 1024 : 1024 * 1024 + len(tag)] = tag
    fake_bin.write_bytes(bytes(buf))
    (bundle / "chrome-sandbox").write_bytes(b"\x7fELF setuid sandbox")
    (bundle / "libEGL.so").write_bytes(b"fake libEGL")
    (bundle / "icudtl.dat").write_bytes(b"fake icu")
    return bundle, fake_bin


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td)
        bundle, binp = build_fake_electron_stage(stage)
        info = anypkg.find_electron_bundle(stage)
        assert info is not None, "electron bundle not detected"
        assert info["version"] == "43.1.2", info["version"]
        assert info["major"] == 43
        assert info["chrome"] == "138.0.7204.0", info["chrome"]
        assert info["binary"] == binp
        assert info["bundle_root"] == bundle
        assert info["sha256"] == hashlib.sha256(binp.read_bytes()).hexdigest()
        assert info["runtime_mb"] > 20, info["runtime_mb"]
        print(f"PASS  detect bundle: v{info['version']} major={info['major']} "
              f"runtime={info['runtime_mb']:.1f}MB sha={info['sha256'][:12]}…")

        # verdict string works headless (no electron43 installed here)
        v = anypkg.electron_verdict(info)
        assert "electron43" in v
        print(f"PASS  verdict headless: {v}")

        # system_electron_info must not crash and returns a dict
        si = anypkg.system_electron_info(43)
        assert isinstance(si, dict) and "package" in si
        print(f"PASS  system_electron_info(43) -> {si}")

    # no-electron stage -> None
    with tempfile.TemporaryDirectory() as td:
        s2 = Path(td)
        (s2 / "usr" / "bin").mkdir(parents=True)
        (s2 / "usr" / "bin" / "plainapp").write_bytes(b"#!/bin/sh\necho hi\n")
        assert anypkg.find_electron_bundle(s2) is None
        print("PASS  plain package -> no electron detected")

    # small ELF next to app.asar must NOT count as electron runtime
    with tempfile.TemporaryDirectory() as td:
        s3 = Path(td)
        b = s3 / "opt" / "x"
        (b / "resources").mkdir(parents=True)
        (b / "resources" / "app.asar").write_bytes(b"asar")
        (b / "helper").write_bytes(b"\x7fELF" + b"Electron/44.0.0" + b"\x00" * 100)
        assert anypkg.find_electron_bundle(s3) is None
        print("PASS  tiny helper binary ignored (<20MB)")

    # convert_one_package logs the detection line (stubbed extract/build)
    def fake_extract(src, stage_dir, work_dir, log_fn):
        build_fake_electron_stage(stage_dir)
        return ({"Package": "freebuff", "Version": "2.0", "Description": "x"}, [])

    def fake_build(fmt, stage_dir, n, v, d, deps, out_dir, log_fn):
        out = Path(out_dir) / f"{n}-{v}-1.deb"
        out.write_bytes(b"pkg")
        return out

    anypkg.extract_any_to_stage = fake_extract
    anypkg.build_package_for_format = fake_build
    anypkg.scan_elf_needed_sonames = lambda s, l: []
    logs = []
    with tempfile.TemporaryDirectory() as outdir:
        res = anypkg.convert_one_package(Path("/tmp/freebuff.deb"), "deb", Path(outdir), logs.append)
    assert res is not None
    elec_lines = [m for m in logs if "Bundled Electron" in m]
    assert elec_lines and "43.1.2" in elec_lines[0], logs
    assert any("Electron check" in m for m in logs), logs
    print("PASS  convert log shows: " + elec_lines[0][:90] + "…")

    print("ALL ELECTRON-DETECTION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
