#!/bin/bash

[ "$*" ] && tests="$*" || tests=test/tests/*.ck

for file in $tests; do
  tmp=$(mktemp -t mondrum-test)
  echo 'ProduceMonDrum p; p.produce() @=> MonDrum @ mondrum;' >> $tmp
  cat $file >> $tmp

  echo INFO: running test $test from $tmp
  cat -n $tmp | sed -e 's/^/INFO: /'
  echo
  sudo nice -n -19 chuck src/mondrum.ck test/lib/test-setup.ck $tmp
  echo -e "INFO: test $test complete\n"

  rm $tmp
done
