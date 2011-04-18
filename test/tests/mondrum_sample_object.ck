"/Users/josh/tmp/foo.aif" => string path;
if (me.args() > 0) { me.arg(0) => path; }

32 => int samples;

for (0 => int i; i < samples; i++) {
  <<< "loading", i >>>;
  spork ~ mondrum._prj._pgms[0]._samples[i].init(path, mondrum);
}

me.yield();
(mondrum._prj._pgms[0]._samples[0]._buf_l.samples()/4)::samp => now;
//2::second => now;

for (0 => int i; i < samples; i++) {
  <<< "playing", i >>>;
  mondrum._prj._pgms[0]._samples[i].play();
  50::ms => now;
}

// wait for the last sample to play out
mondrum._prj._pgms[0]._samples[0]._buf_l.samples()::samp => now;

// wait a little while longer to make sure cpu has drained
5::second => now;
