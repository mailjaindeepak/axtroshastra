#!/bin/bash
# Runs inside quay.io/pypa/manylinux_2_28_aarch64 to build an offline wheelhouse:
# all deps arrive as prebuilt aarch64/cp312 wheels; only pyswisseph compiles, and
# it is repaired with auditwheel to a portable manylinux wheel.
set -euo pipefail
P=/opt/python/cp312-cp312/bin

echo ">> ensuring a linkable libsqlite3 (pyswisseph links -lsqlite3)"
mkdir -p /tmp/sqlink
# Prefer a static lib or unversioned .so; else fall back to a versioned .so.*
SQ="$(find /opt/_internal /usr/local /usr/lib64 /usr/lib -name 'libsqlite3.a' 2>/dev/null | head -1 || true)"
[ -z "$SQ" ] && SQ="$(find /opt/_internal /usr/local /usr/lib64 /usr/lib -name 'libsqlite3.so' 2>/dev/null | head -1 || true)"
[ -z "$SQ" ] && SQ="$(find /opt/_internal /usr/local /usr/lib64 /usr/lib -name 'libsqlite3.so.*' 2>/dev/null | head -1 || true)"
if [ -n "$SQ" ]; then
  # Create an UNVERSIONED symlink so -lsqlite3 resolves.
  ln -sf "$SQ" /tmp/sqlink/libsqlite3.so
  export LDFLAGS="-L/tmp/sqlink ${LDFLAGS:-}"
  export LD_LIBRARY_PATH="$(dirname "$SQ"):/tmp/sqlink:${LD_LIBRARY_PATH:-}"
  echo "   using $SQ  (symlinked to /tmp/sqlink/libsqlite3.so)"
else
  echo "   no libsqlite3 found; bounded yum fallback"
  timeout 240 yum install -y sqlite-devel >/dev/null 2>&1 || true
fi

echo ">> upgrading pip/auditwheel"
"$P/pip" install --upgrade pip auditwheel >/dev/null

rm -rf /tmp/raw && mkdir -p /tmp/raw
rm -rf /io/packages && mkdir -p /io/packages

echo ">> building/collecting wheels for cp312 aarch64"
"$P/pip" wheel -r /io/requirements.build.txt -w /tmp/raw

echo ">> normalizing (repair source-built wheels to manylinux)"
for w in /tmp/raw/*.whl; do
  base=$(basename "$w")
  case "$base" in
    *manylinux*|*none-any*|*abi3*) cp "$w" /io/packages/ ;;
    *linux_aarch64*)               auditwheel repair "$w" -w /io/packages/ || cp "$w" /io/packages/ ;;
    *)                             cp "$w" /io/packages/ ;;
  esac
done

echo "=== wheelhouse contents ==="
ls -1 /io/packages
echo "WHEELHOUSE_OK count=$(ls -1 /io/packages/*.whl | wc -l)"
