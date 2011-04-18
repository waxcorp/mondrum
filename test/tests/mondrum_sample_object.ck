"/Users/josh/tmp/foo.aif" => string path;
if (me.args() > 0) { me.arg(0) => path; }

64 => int samples;

for (0 => int i; i < samples; i++) {
  <<< "loading", i >>>;
  spork ~ mondrum.prj.pgms[0].samples[i].init(path, mondrum);
}

me.yield();
(mondrum.prj.pgms[0].samples[0].buf_l.samples()/4)::samp => now;

for (0 => int i; i < samples; i++) {
  <<< "playing", i >>>;
  mondrum.prj.pgms[0].samples[i].play();
  100::ms => now;
}

// wait for the last sample to play out
mondrum.prj.pgms[0].samples[0].buf_l.samples()::samp => now;

// wait a little while longer to make sure cpu has drained
5::second => now;
