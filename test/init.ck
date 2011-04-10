MonDrum mondrum;
mondrum.init("localhost", "/monome", 14457, 8000, 64, "/mondrum", "localhost",
             14030, 14130, 79, 1);

mondrum.sequencer.play();
1::second => now;
mondrum.sequencer.stop();
1::second => now;
mondrum.sequencer.playpause();
1::second => now;
mondrum.sequencer.stop();
1::second => now;
mondrum.sequencer.stop();

<<< "got here" >>>;

while (1::second => now);
