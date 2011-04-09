MonDrum md;
md.init("localhost", "/monome", 14457, 8000, 64, "/mondrum", "localhost",
         14030, 14130, 79, 1);

md.s.control_start.broadcast();
4::second => now;
md.s.control_stop.broadcast();
2::second => now;
md.s.control_start.broadcast();

2::second => now;
md.s.pause_play();
1::second => now;
md.s.pause_play();

while (1::second => now);
