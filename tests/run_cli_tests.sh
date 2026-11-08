#!/usr/bin/env bash
# AnyPkg pre-push smoke tests. Headless-safe: needs only python3 (no GTK, no bsdtar).
# Usage: bash tests/run_cli_tests.sh   (from anywhere; it cds to the repo root)
set -u
cd "$(dirname "$0")/.."
PY=python3
fail=0
ok()   { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }
check_eq() { if [[ "$2" == "$3" ]]; then ok "$1"; else bad "$1 (expected [$2] got [$3])"; fi; }
check_contains() { if grep -qF -- "$3" <<<"$2"; then ok "$1"; else bad "$1 (missing [$3])"; fi; }

# 0) compiles
$PY -m py_compile anypkg.py && ok "py_compile anypkg.py" || bad "py_compile anypkg.py"
rm -rf __pycache__

VER=$($PY anypkg.py --version 2>&1); check_eq "--version exit/output" "AnyPkg v$($PY -c 'import re;print(re.search(r"APP_VERSION = \"(.*?)\"", open("anypkg.py").read()).group(1))')" "$VER"

out=$($PY anypkg.py -h 2>&1); rc=$?
check_eq "top-level -h exit" "0" "$rc"
check_contains "top-level -h lists convert" "$out" "convert"
check_contains "top-level -h lists install" "$out" "install"
check_contains "top-level -h shows format legend" "$out" "target formats"

out=$($PY anypkg.py convert -h 2>&1); rc=$?
check_eq "convert -h exit" "0" "$rc"
check_contains "convert -h documents destination inference" "$out" "destination filename"
check_contains "convert -h documents --gui" "$out" "--gui"

out=$($PY anypkg.py install -h 2>&1); rc=$?
check_eq "install -h exit" "0" "$rc"
check_contains "install -h documents --keep" "$out" "--keep"

# error paths
$PY anypkg.py convert /nonexistent.deb --to rpm >/dev/null 2>&1; check_eq "missing source exit" "2" "$?"
$PY anypkg.py convert /nonexistent.deb >/dev/null 2>&1; check_eq "single arg without --to/dest exit" "2" "$?"
out=$($PY anypkg.py convert /nonexistent.deb 2>&1); check_contains "no-target error prints legend" "$out" "target formats"
$PY anypkg.py convert x.deb --to bogus >/dev/null 2>&1; check_eq "invalid --to exit" "2" "$?"

# fixtures
FX=$(mktemp -d)
mkdir -p "$FX/sub"
echo x > "$FX/a-1.0_amd64.deb"; echo x > "$FX/b-2.0_amd64.deb"; echo x > "$FX/c-1.0.x86_64.rpm"; echo x > "$FX/sub/hidden.deb"; echo x > "$FX/notes.txt"
$PY anypkg.py convert "$FX" --to deb -o "$FX/out" >/dev/null 2>&1; check_eq "mixed folder without --pattern refused" "2" "$?"
out=$($PY anypkg.py convert "$FX" --to deb --pattern '*.deb' -o "$FX/out" 2>&1)
check_contains "folder+pattern finds top-level debs only" "$out" "bulk convert: 2 file(s)"
if grep -q "hidden.deb" <<<"$out"; then bad "subdir file must not be picked up"; else ok "no recursion into subfolders"; fi
out=$($PY anypkg.py convert "$FX/a-1.0_amd64.deb" "telegram.pkg.tar.zst" -o "$FX/out" 2>&1)
check_contains "destination filename inference" "$out" "Destination 'telegram.pkg.tar.zst' -> target format: arch"
out=$($PY anypkg.py convert "$FX/a-1.0_amd64.deb" "$FX/c-1.0.x86_64.rpm" --to rpm -o "$FX/out" 2>&1)
check_contains "explicit multi-file bulk header" "$out" "bulk convert: 2 file(s) -> .rpm"
rm -rf "$FX"

echo
if [[ $fail -eq 0 ]]; then echo "ALL SMOKE TESTS PASSED"; else echo "SOME TESTS FAILED"; exit 1; fi
