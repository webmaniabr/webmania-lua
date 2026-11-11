#!/bin/sh
# Builds this Lua SDK over the pinned C SDK binary archive and runs the optional
# homologation example with the same Lua 5.4 interpreter. Configuration comes only
# from the environment; see README, "Teste em homologação". Without WEBMANIA_LIVE=1
# it exits 77 before any network. WEBMANIA_C_ARCHIVE is the C SDK binary archive; its
# content is verified against dependency-lock.json before anything is extracted (see c_archive.py).
#
# WEBMANIA_EXAMPLE_WORK (optional, default TMPDIR or /tmp) is only the place where a
# new private scratch directory is created. That private directory is the only path
# this script removes, when it exits: nothing that already existed is deleted.
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
if [ "${WEBMANIA_LIVE:-}" != "1" ]; then
  printf '%s\n' '{"result":"blocked"}'
  exit 77
fi
blocked() {
  printf '{"result":"blocked","reason":"%s"}\n' "$1"
  exit 77
}
# inside PATH DIR: PATH is DIR or lies below it.
inside() {
  case "$1/" in
    "${2%/}"/*) return 0 ;;
  esac
  return 1
}
# resolve PATH: the physical path of PATH, which need not exist yet. Its deepest existing
# ancestor is resolved and the missing components are appended, so the overlap checks run
# before anything is created. A missing "." or ".." component, one that exists but is not a
# directory, and an existing part that cannot be entered are refused.
resolve() {
  r_path="$1"
  r_rest=""
  case "$r_path" in /*) ;; *) r_path="$(pwd -P)/$r_path" ;; esac
  while [ ! -d "$r_path" ]; do
    r_name="$(basename "$r_path")"
    case "$r_name" in . | ..) return 1 ;; esac
    if [ -e "$r_path" ] || [ -L "$r_path" ]; then return 1; fi
    r_rest="/$r_name$r_rest"
    r_path="$(dirname "$r_path")"
  done
  # Checked explicitly: resolve runs on the left of ||, where errexit does not apply.
  r_base="$(cd "$r_path" && pwd -P)" || return 1
  [ -n "$r_base" ] || return 1
  if [ "$r_base" = / ] && [ -n "$r_rest" ]; then r_base=""; fi
  printf '%s%s\n' "$r_base" "$r_rest"
}
ARCHIVE="${WEBMANIA_C_ARCHIVE:-/deps/c/webmania-c-binary.tar.gz}"
LUA_DIR="${WEBMANIA_LUA_DIR:-/opt/lua-5.4.9}"
# The archive digest changes with any documentation file inside it, so its content is checked instead:
# c_archive.py accepts only plain directories and regular files whose manifest (every file but the inert
# README) and pinned files match dependency-lock.json, and extracts only what it verified. Anything else blocks.
CHECK="$ROOT/examples/homologacao/c_archive.py"
python3 -I "$CHECK" verify "$ROOT/dependency-lock.json" "$ARCHIVE" || blocked "C archive differs from the lock"
if [ -n "${WEBMANIA_EXAMPLE_WORK:-}" ]; then
  # Checked on the resolved path before it is created: a refused path leaves nothing behind.
  BASE="$(resolve "$WEBMANIA_EXAMPLE_WORK")" || blocked "work directory is not a directory path"
  inside "$ROOT" "$BASE" && blocked "work directory overlaps the checkout"
else
  BASE="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
fi
# The private copy below would copy itself: the scratch directory must be outside the checkout.
inside "$BASE" "$ROOT" && blocked "work directory overlaps the checkout"
mkdir -p "$BASE"
WORK="$(mktemp -d "$BASE/webmania-lua-example.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir "$WORK/c-prefix"
python3 -I "$CHECK" extract "$ROOT/dependency-lock.json" "$ARCHIVE" "$WORK/c-prefix" || blocked "C archive differs from the lock"
# Build from a private copy: the checkout may be read-only. The example itself runs from the
# caller's directory, so relative payload and ledger paths keep their meaning.
cp -R "$ROOT" "$WORK/src"
(cd "$WORK/src" && luarocks --lua-version=5.4 --lua-dir="$LUA_DIR" --tree="$WORK/rocks" make webmania-0.1.0alpha5-1.rockspec \
  WEBMANIA_DIR="$WORK/c-prefix" LUA_DIR="$LUA_DIR" LUA_BINDIR="$LUA_DIR/bin" LUA_INCDIR="$LUA_DIR/include" \
  LUA_LIBDIR="$LUA_DIR/lib" --deps-mode=none >/dev/null)
# Not exec: the private directory is removed when the example ends.
status=0
LUA_PATH="$WORK/rocks/share/lua/5.4/?.lua;;" LUA_CPATH="$WORK/rocks/lib/lua/5.4/?.so" \
WEBMANIA_WORKER_PATH="$WORK/c-prefix/libexec/webmania-native-worker" "$LUA_DIR/bin/lua" "$ROOT/examples/homologacao/main.lua" || status=$?
exit "$status"
