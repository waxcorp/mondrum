"/Users/josh/tmp/bigfile2_39690000_52920000" => string path;

mondrum._prj._pgms[0]._samples[0].init(path, mondrum);

<<< "start" >>>;
mondrum._prj._pgms[0]._samples[0].play(44100*60*4);
5::second => now;
mondrum._prj._pgms[0]._samples[0].play((44100*60*4.5) $ int);
5::second => now;
mondrum._prj._pgms[0]._samples[0].stop();

// wait a little while longer to make sure cpu has drained
5::second => now;
