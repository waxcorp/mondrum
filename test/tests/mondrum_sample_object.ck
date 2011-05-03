"/Users/josh/tmp/5_gongs" => string path;
if (me.args() > 0) { me.arg(0) => path; }

64 => int samples;
SndBuf buf_l, buf_r;

for (0 => int i; i < samples; i++) {
  <<< "loading", i >>>;
  mondrum._prj._pgms[0]._samples[i].init(path, mondrum);
  mondrum._prj._pgms[0]._samples[i].load_file(path, buf_l, buf_r);
}

mondrum._prj._pgms[0]._gain_l => dac.chan(0);
mondrum._prj._pgms[0]._gain_r => dac.chan(1);

for (0 => int i; i < samples; i++) {
  <<< "playing", i >>>;
  mondrum._prj._pgms[0]._samples[i].play(0);
  200::ms => now;
}

// wait for the last sample to play out
mondrum._prj._pgms[0]._samples[0].duration() => now;

// wait a little while longer to make sure cpu has drained
5::second => now;
