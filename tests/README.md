# tests — AnyPkg local test ground

- `run_cli_tests.sh` — fast pre-push smoke tests (no GTK, no bsdtar needed).
  Run from the repo root before every push:

      bash tests/run_cli_tests.sh

- `trial/` — scratch folder for manual testing (downloaded packages, shims,
  fixtures). Git-ignored except its own README, so it is never pushed.

Flow: test locally -> commit on the arena branch -> push branch -> open PR ->
merge only after review. If anything breaks on main later, revert the PR (one
click) — release tags (v1.1.0, v1.1.1, ...) stay downloadable forever.
