"/Users/josh/tmp/bigfile2_39690000_52920000" => string path;

SndBuf buf_l, buf_r;
mondrum._prj._pgms[0]._samples[0].init(path, mondrum);
mondrum._prj._pgms[0]._samples[0].load_file(path, buf_l, buf_r);

mondrum._prj._pgms[0]._gain_l => dac.chan(0);
mondrum._prj._pgms[0]._gain_r => dac.chan(1);

<<< "start" >>>;
mondrum._prj._pgms[0]._samples[0].play(5::second);
5::second => now;
mondrum._prj._pgms[0]._samples[0].play(30::second);
5::second => now;
mondrum._prj._pgms[0]._samples[0].stop();

// wait a little while longer to make sure cpu has drained
5::second => now;
