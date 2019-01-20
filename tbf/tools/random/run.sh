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

exit_message() {
    echo "Created tests: $COUNT"
}

trap exit_message SIGINT SIGTERM SIGKILL

LINES_COVERED=0
while true; do
  touch 'vector.test'
  "$PROG" || true
  if [[ -e ${PROG}.gcno ]]; then
      LINES_COVERED_NEW=$(gcov ${PROG}.c | egrep '^Lines' | cut -d":" -f 2 | cut -d"%" -f 1)
      echo "Looking at gcov"
  else
      LINES_COVERED_NEW=$(( $LINES_COVERED + 1))
  fi
  if (( $(echo "$LINES_COVERED_NEW > $LINES_COVERED" | bc -l) )); then
      mv 'vector.test' "vector${COUNT}.test"
      (( COUNT += 1 ))
  fi
  LINES_COVERED=$LINES_COVERED_NEW
done
