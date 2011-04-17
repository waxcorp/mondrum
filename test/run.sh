#!/bin/bash

for test in test/tests/*.ck; do
  tmp=$(mktemp -t mondrum-test)
  echo 'ProduceMonDrum p; p.produce() @=> MonDrum @ mondrum;' >> $tmp
  cat $test >> $tmp

  echo INFO: running test $test from $tmp
  chuck src/mondrum.ck test/lib/test-setup.ck $tmp
  echo -e "INFO: test $test complete\n"
done
