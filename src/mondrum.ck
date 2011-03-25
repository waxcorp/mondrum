public class Monome {
  OscSend xmit;
  int model;
  string xmit_prefix;
  OscRecv recv;
  MonomeButton buttons[][];

  fun void init(string xmit_host, string xmit_prefix, int xmit_port,
    int recv_port, int model) {
    model => this.model;
    xmit_prefix => this.xmit_prefix;
    this.xmit.setHost(xmit_host, xmit_port);
    recv_port => this.recv.port;
    this.recv.listen();

    if (model == 64) setup_buttons(8, 8);
  }

  fun void setup_buttons(int x, int y) {
    MonomeButton buttons[x][y];
    for (0 => int a; a < x; a++) {
      for (0 => int b; b < y; b++) {
        new MonomeButton @=> buttons[a][b];
        buttons[a][b].init(a, b, this, 50::ms);
      }
    }
    buttons @=> this.buttons;
  }
}

class MonomeButton {
  16 => int brightness_levels;
  1 => int level;
  int x;
  int y;
  Monome m;

  fun void init(int x, int y, Monome m, dur init_glow_duration) {
    x => this.x;
    y => this.y;
    m @=> this.m;
    glow(init_glow_duration, 1);
  }

  fun void start_xmit_xy(string msg) {
    this.m.xmit.startMsg(msg);
    this.x => this.m.xmit.addInt;
    this.y => this.m.xmit.addInt;
  }

  fun void set_level(int level) {
    if (level > this.brightness_levels) {
      this.brightness_levels - (level % this.brightness_levels) => level;
      if (level == 0) 1 +=> level;
    }
    start_xmit_xy(m.xmit_prefix + "/grid/led/level/set, i i i");
    (Std.abs(level) - 1) => this.m.xmit.addInt => this.level;
  }

  fun void glow(dur ramp_dur, int iterations) {
    // TODO(josh): figure out how to do "and" < -1 for infinite glow
    for (iterations => int i; i > 0; i--) {
      for (1 => int x; x < (2*(this.brightness_levels)); x++) {
        (x $ float) / 100 => float ratio;
        ramp_dur * (1 / this.brightness_levels $ float) => now;
        set_level(x);
      }
    }
  }
}

// Buttons won't run in their own shreds.  Currently it just glows
// each button in succession when initialized.  Eg:
//   Monome m;
//   m.init("localhost", "/monome", 14457, 8000, 64);
