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
    this.set_all_buttons(0);

    if (model == 64) setup_buttons(8, 8);
  }

  fun void set_all_buttons(int state) {
    this.xmit.startMsg(this.xmit_prefix + "/grid/led/all i");
    this.xmit.addInt(state);
  }

  fun void set_level(string t, int x, int y, int l) {
    if (t == "set") {
      this.buttons[x][y].set_level(l);
    } else {
      this.xmit.startMsg(this.xmit_prefix + "/grid/led/level/" + t + " iii");
      this.xmit.addInt(x);
      this.xmit.addInt(y);
      this.xmit.addInt(l);
    }
  }

  fun void setup_buttons(int x, int y) {
    MonomeButton buttons[x][y];
    for (0 => int a; a < x; a++) {
      for (0 => int b; b < y; b++) {
        new MonomeButton @=> buttons[a][b];
        buttons[a][b].init(a, b, this);
        //spork ~ buttons[a][b].glow((a*b*50::ms/5), 3, (3*a+b*b)*250::ms);
      }
    }
    me.yield();
    buttons @=> this.buttons;
  }
}

class MonomeButton {
  int brightness_levels[15];
  0 => int level;
  int x;
  int y;
  Monome m;
  OscEvent key;

  fun void init(int x, int y, Monome m) {
    x => this.x;
    y => this.y;
    m @=> this.m;
    this.m.recv.event(this.m.xmit_prefix + "/grid/key iii") @=> this.key;
    spork ~ this.key_event_manager();
  }

  fun void key_event_manager() {
    while (true) {
      this.key => now;
      until (this.key.nextMsg() == 0) {
        this.key.getInt() => int x_pos;
        this.key.getInt() => int y_pos;
        this.key.getInt() => int s;
        if (this.x != x_pos) break;
        if (this.y != y_pos) break;

        if (s == 0) 0 => this.level;
        if (s == 1) 15 => this.level;
        this.set_level(level);
      }
    }
  }

  fun void start_xmit_xy(string msg) {
    this.m.xmit.startMsg(msg);
    this.x => this.m.xmit.addInt;
    this.y => this.m.xmit.addInt;
  }

  fun void set_level(int level) {
    if (level > this.brightness_levels.cap()) {
      this.brightness_levels.cap() - 
        (level % this.brightness_levels.cap()) => level;
      if (level == 0) 1 +=> level;
    }
    start_xmit_xy(m.xmit_prefix + "/grid/led/level/set, iii");
    Std.abs(level) => this.m.xmit.addInt => this.level;
  }

  fun void glow(dur ramp_dur, int iters, dur pause) {
    pause => now;
    // TODO(josh): figure out how to do "and" < -1 for infinite glow
    for (0 => int i; i < iters; i++) {
      for (1 => int x; x < (2*(this.brightness_levels.cap())); x++) {
        (x $ float) / 100 => float ratio;
        ramp_dur * (1 / this.brightness_levels.cap() $ float) => now;
        set_level(x);
      }
    }
  }
}
