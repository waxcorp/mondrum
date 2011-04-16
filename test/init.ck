MonDrum mondrum;
mondrum.init("localhost", "/monome", 14457, 8000, 64, "/mondrum", "localhost",
             14030, 14130, "");

<<< "OK" >>>;

for (0 => int i; i < 8; i++) {
  2 => mondrum.prj.pgms[0].samples[i].gain.gain;
  me.arg(0) => mondrum.prj.pgms[0].samples[i].path;
  250::ms => now;
  mondrum.prj.pgms[0].samples[i].play();
}

while (1::second => now);
