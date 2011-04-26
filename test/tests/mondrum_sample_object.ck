"/Users/josh/tmp/5_gongs_0_926123" => string path;
if (me.args() > 0) { me.arg(0) => path; }

64 => int samples;

for (0 => int i; i < samples; i++) {
  <<< "loading", i >>>;
  spork ~ mondrum._prj._pgms[0]._samples[i].init(path, mondrum);
}

me.yield();
(mondrum._prj._pgms[0]._samples[0]._buf_l.samples()/2)::samp => now;

for (0 => int i; i < samples; i++) {
  <<< "playing", i >>>;
  mondrum._prj._pgms[0]._samples[i].play(0);
  100::ms => now;
}

// wait for the last sample to play out
mondrum._prj._pgms[0]._samples[0]._buf_l.samples()::samp => now;

// wait a little while longer to make sure cpu has drained
5::second => now;
