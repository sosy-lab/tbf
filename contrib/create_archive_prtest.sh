#!/bin/bash
set -eao pipefail
IFS=$'\t\n'

DIRNAME="$(dirname "$(readlink -f "$0")")/.."
VERSION=$(git describe --always --dirty)
TMPDIR=$(mktemp -d)
pushd "$TMPDIR" > /dev/null
ln -s "$DIRNAME" prtest
find prtest/tbf/ -name '*.py' -exec sed -i "s/\(__VERSION__\s*=\s*\).*/\1\"$VERSION\"/" '{}' +
zip --exclude="*/lib/py/benchexec/*" --exclude="*/lib/py/Benchexec*" --exclude="*/lib/py/bin/*" --exclude="*/.idea/*" --exclude="*/tbf/tools/afl/*" --exclude="*/tbf/tools/cpatiger/*" --exclude="*/tbf/tools/crest/*" --exclude="*/tbf/tools/fshell/*" --exclude="*/tbf/tools/klee/*" --exclude="*/__pycache__/*" --exclude="*/test/*" -r prtest.zip prtest/{bin/tbf,tbf,lib,LICENSE.txt}
popd
mv "$TMPDIR/prtest.zip" ./
echo "Wrote prtest.zip, version $VERSION"
