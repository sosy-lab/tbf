#!/bin/bash

PROG=$1
COUNT=0
if [[ -z $PROG ]]; then
  &>2 echo "Usage: run.sh PROG"
fi

while true; do
  $PROG
  mv 'vector.test' "vector${COUNT}.test"
  (( COUNT += 1 ))
done
