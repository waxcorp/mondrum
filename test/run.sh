#!/bin/bash

[ "$*" ] && tests="$*" || tests=test/tests/*.ck

for test in $tests; do
  tmp=$(mktemp -t mondrum-test)
  echo 'ProduceMonDrum p; p.produce() @=> MonDrum @ mondrum;' >> $tmp
  cat $test >> $tmp

  echo INFO: running test $test from $tmp
  cat -n $tmp | sed -e 's/^/INFO: /'
  echo
  chuck src/mondrum.ck test/lib/test-setup.ck $tmp
  echo -e "INFO: test $test complete\n"

  rm $tmp
done
