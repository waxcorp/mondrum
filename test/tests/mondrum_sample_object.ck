"/Users/josh/tmp/foo.aif" => string path;
if (me.args() > 0) { me.arg(0) => path; }

for (0 => int i; i < 8; i++) {
  .2 => mondrum.prj.pgms[0].samples[i].gain.gain;
  path => mondrum.prj.pgms[0].samples[i].path;
  <<< "playing" >>>;
  mondrum.prj.pgms[0].samples[i].play();
  300::ms => now;
}

// wait for the last sample to play out
mondrum.prj.pgms[0].samples[0].buf_l.samples()::samp => now;
