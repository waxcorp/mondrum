class Instrument {
  fun void receive(int signals[]) {
  }
}

class Controller extends Instrument {
  int controller_shred_id;
  Instrument instruments[];

  fun void controller_main_loop() {
    (spork ~ this.control_loop()).id() => this.controller_shred_id;
    me.yield();
  }

  fun void control_loop() {
    while (1) {
      this.control_signal() @=> int sig[];
      for (0 => int x; x < this.instruments.cap(); x++) {
        sig => this.instruments[x].receive;
      }
    }
  }

  fun int[] control_signal() {
  }
}

class KbController extends Controller {
  // TODO(josh): see about http://smelt.cs.princeton.edu/code/keyboard/kb.ck
  int sig;
  KBHit kb_hit;

  fun int[] control_signal() {
    this.kb_hit => now;

    int sig[256];
    0 => int i;
    while (kb_hit.more()) {
      this.kb_hit.getchar() => sig[i];
      i++;
    }

    return sig;
  }
}

class MonDrumProject {
  MonDrumSequence seqs[32];
  MonDrumProgram pgms[64];
  seqs[0] @=> MonDrumSequence seq;
  88 => int bpm;

  fun void init(string prj_path) {
    for (0 => int i; i < this.seqs.cap(); i++) this.seqs[i].init(this);
    for (0 => int i; i < this.pgms.cap(); i++) this.pgms[i].init(this);

    if (prj_path != "") {
      // this.mondrum.db.load_mondrum_project(this, prj_path);
    }
  }

  fun void load(string prj_path) {
    // stub
  }
}

class MonDrumProgram {
  MonDrumProject @ prj;

  fun void init(MonDrumProject prj) {
    prj @=> this.prj;
  }
}

class MonDrumSequenceEvent extends Event {
  float loop_percent;
  int id;
}

class MonDrumSequence extends Instrument {
  MonDrum @ mondrum;
  MonDrumProject @ prj;
  MonDrumSequenceTrack tracks[64];
  MonDrumSequenceEvent ticks[];

  [1, 1, 1, 1] @=> int loc[];
  2 => int bars;
  4 => int beats;
  16 => int semi_beats;
  128 => int micro_beats;

  int bpm;
  1 => int cur_tick;
  true => int use_master_bpm;

  fun void init(MonDrumProject prj) {
    MonDrumSequenceEvent tix[(bars * beats * semi_beats)] @=> this.ticks;
    prj @=> this.prj;
  }

  fun int loc_to_tick(int l[]) {
    (((l[0]-1) * this.beats) + (l[1]-1)) * this.semi_beats +
     (l[2]-1) + 1 => int t;

    return t;
  }

  fun int[] tick_to_loc(int t) {
    t--;
    1 + (t / (this.beats * this.semi_beats)) => int bar;
    1 + ((t / this.semi_beats) % this.beats) => int beat;
    1 + (t % this.semi_beats) => int semi_beat;

    return [bar, beat, semi_beat, 1];
  }

  fun int get_bpm() {
    if (use_master_bpm) {
      return this.prj.bpm;
    } else {
      return this.bpm;
    }
  }

  fun dur tick_dur() {
    60::second / get_bpm() => dur beat_dur;
    this.bars * this.beats => int beats_in_loop;
    beat_dur * beats_in_loop => dur loop_dur;

    return loop_dur / this.ticks.cap();
  }

  fun void set_loc(int t) {
    t => this.cur_tick;
    tick_to_loc(t) @=> this.loc;
  }

  fun void set_loc(int l[]) {
    l @=> this.loc;
    loc_to_tick(l) => this.cur_tick;
  }

  fun void tick() { tick(this.loc); }
  fun void tick(int l[]) {
    set_loc(l);
    <<< "tick", this.cur_tick, "loc", l[0], l[1], l[2] >>>;

    if (this.cur_tick > this.ticks.cap()) {
    } else {
      this.ticks[(this.cur_tick - 1)].broadcast();
      tick_dur() => now;
      set_loc(this.cur_tick + 1);
    }
  }

  fun void receive(int data[]) {
    
  }
}

class MonDrumSequenceTrack {
  100 => int volume;

  fun void init(int foo) {
    <<< foo >>>;
  }
}

public class MonDrum extends Instrument {
  Monome monome;
  MonDrumDB db;
  MonDrumSequenceController seqctl;

  fun void init(string monome_xmit_host,
                string monome_xmit_prefix,
                int monome_xmit_port,
                int monome_recv_port,
                int monome_model,
                string mondrum_db_xmit_prefix,
                string mondrum_db_xmit_host,
                int mondrum_db_xmit_port,
                int mondrum_db_recv_port,
                string prj_path) {
    this.monome.init(monome_xmit_host, monome_xmit_prefix, monome_xmit_port,
                     monome_recv_port, monome_model);
    this.db.init(this.monome, mondrum_db_xmit_prefix, mondrum_db_xmit_host,
                 mondrum_db_xmit_port, mondrum_db_recv_port);
    this.seqctl.init(prj_path);
  }
}

class Monome {
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
        spork ~ buttons[a][b].glow((a*b*50::ms/5), 3, (3*a+b*b)*250::ms);
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
  string attrs[];

  fun void init(int y, int x, Monome m) {
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

class MonDrumDB {
  Monome monome;
  "/mondrum_db/" => string xmit_prefix;
  string xmit_host;
  int xmit_port;
  OscSend xmit;
  OscRecv recv;

  fun void init(Monome monome, string xmit_prefix, string xmit_host,
                int xmit_port, int recv_port) {
    monome @=> this.monome;
    xmit_prefix => this.xmit_prefix;
    this.xmit.setHost(xmit_host, xmit_port);
    recv_port => this.recv.port;
    this.recv.listen();
  }

  fun void load_mondrum_project(MonDrumProject mondrum_project, string prj) {
    
  }

  fun MonDrumSequence load_mondrum_sequence(string prj, int seq_id) {
    // do things
  }
}

class MonDrumSequenceController extends KbController {
  MonDrumProject prj;
  int main_loop_shred_id;
  Event start_event;
  Event stop_event;
  Event playpause_event;
  "stopped" => string state;

  fun void init(string prj_path) {
    this.prj.init(prj_path);

    Instrument instruments_placeholder[1] @=> this.instruments;
    this @=> this.instruments[0];

    spork ~ playstart_loop();
    controller_main_loop();
    me.yield();
  }

  fun void playpause() {
    if (this.state == "paused") {
      "playing" => this.state;
    } else if (this.state == "playing") {
      "paused" => this.state;
    } else if (this.state == "stopped") {
      this.start_event.broadcast();
      "playing" => this.state;
    }

    playpause_event.broadcast();
  }

  fun void playstart_loop() {
    while (1) {
      this.start_event => now;
      "playing" => this.state;
      (spork ~ main_loop()).id() => this.main_loop_shred_id;

      this.stop_event => now;
      Machine.remove(this.main_loop_shred_id);
    }
  }

  fun void main_loop() {
    this.prj.seq.tick([1, 1, 1, 1]);
    while (1) {
      if (this.state == "paused") playpause_event => now;
      this.prj.seq.tick();
    }
  }

  // like MPC we pause if we're currently playing and stop/reset if not.
  fun void stop() {
    <<< "stop" >>>;
    if (this.state == "playing") {
      this.playpause();
    } else {
      this.stop_event.broadcast();
      "stopped" => this.state;
    }
  }

  fun void play() {
    <<< "play" >>>;
    if (this.state != "playing") this.playpause();
  }

  fun void playstart() {
    <<< "playstart" >>>;
    this.stop();
    this.stop();
    me.yield();
    this.start_event.broadcast();
  }

  fun void receive(int signals[]) {
    if (signals[0] == 112) {
      this.playstart();
    } else if (signals[0] == 111) {
      this.play();
    } else if (signals[0] == 105) {
      this.stop();
    }
  }
}
