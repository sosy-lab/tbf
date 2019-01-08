#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

PROG="$1"
COUNT=0
if [[ -z "$PROG" ]]; then
  >&2 echo "Usage: run.sh PROG"
  exit
fi
if [[ ! -x "$PROG" ]]; then
  >&2 echo "Given file not executable"
  exit
fi

if ! command -v "$PROG"; then
    PROG="./${PROG}"
fi

while true; do
  touch 'vector.test'
  "$PROG"
  mv 'vector.test' "vector${COUNT}.test"
  (( COUNT += 1 ))
done
