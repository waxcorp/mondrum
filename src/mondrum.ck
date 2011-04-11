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

class SequencerEvent extends Event {
  float loop_percent;
  int id;
}

class MonDrumSequence {
  fun void init(int foo) {
    <<< foo >>>;
  }
}

class MonDrumProgram {
  fun void init(int foo) {
    <<< foo >>>;
  }
}

public class MonDrum extends Instrument {
  Monome monome;
  SampleEngine sample_engine;
  Sequencer sequencer;

  fun void init(string monome_xmit_host,
                string monome_xmit_prefix,
                int monome_xmit_port,
                int monome_recv_port,
                int monome_model,
                string sampeng_xmit_prefix,
                string sampeng_xmit_host,
                int sampeng_xmit_port,
                int sampeng_recv_port,
                int sequencer_bpm,
                int sequencer_bars) {
    this.monome.init(monome_xmit_host, monome_xmit_prefix, monome_xmit_port,
                     monome_recv_port, monome_model);
    this.sample_engine.init(this.monome, sampeng_xmit_prefix, sampeng_xmit_host,
                            sampeng_xmit_port, sampeng_recv_port);
    this.sequencer.init(sequencer_bpm, sequencer_bars);
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

class SampleEngine {
  Monome m;
  string xmit_prefix;
  string xmit_host;
  int xmit_port;
  OscSend xmit;
  OscRecv recv;

  fun void init(Monome m, string xmit_prefix, string xmit_host, int xmit_port,
                int recv_port) {
    m @=> this.m;
    xmit_prefix => this.xmit_prefix;
    this.xmit.setHost(xmit_host, xmit_port);
    recv_port => this.recv.port;
    this.recv.listen();
  }

  fun void read_matrix() {
    this.m.buttons[0][0].set_level(15);
  }
}

class Sequencer extends KbController {
  float bpm;
  int bars;
  4 => int beats_per_bar;
  SequencerEvent sequencer_events[];
  100 => int events_per_bar;
  int main_loop_shred_id;
  Event control_start_event;
  Event control_stop_event;
  time event_start_time;
  dur loop_dur;
  dur step_dur;
  Event playpause_event;
  "stopped" => string state;

  fun void init(float bpm, int bars) {
    (events_per_bar * bars) => int total_events;
    SequencerEvent seq_evs[total_events];

    for (0 => int i; i < total_events; i++) {
      (i $ float) / (total_events $ float) => seq_evs[i].loop_percent;
      i => seq_evs[i].id;
    }

    seq_evs @=> this.sequencer_events;
    bpm => this.bpm;
    bars => this.bars;

    calc_durs();
    spork ~ playstart_loop();

    Instrument instruments_placeholder[1] @=> this.instruments;
    this @=> this.instruments[0];
    controller_main_loop();

    me.yield();
  }

  fun void playpause() {
    if (this.state == "paused") {
      "playing" => this.state;
    } else if (this.state == "playing") {
      "paused" => this.state;
    } else if (this.state == "stopped") {
      this.control_start_event.broadcast();
      "playing" => this.state;
    }

    playpause_event.broadcast();
  }

  fun void calc_durs() {
    60::second / this.bpm => dur beat_dur;
    this.bars * this.beats_per_bar => int beats_in_loop;
    beat_dur * beats_in_loop => this.loop_dur;
    loop_dur / this.sequencer_events.cap() => this.step_dur;
  }

  fun void playstart_loop() {
    while (1) {
      this.control_start_event => now;

      (spork ~ main_loop()).id() => this.main_loop_shred_id;

      this.control_stop_event => now;
      Machine.remove(this.main_loop_shred_id);
    }
  }

  fun void main_loop() {
    while (1) {
      for (0 => int i; i < this.sequencer_events.cap(); i++) {
        if (this.state == "paused")  playpause_event => now;
        this.sequencer_events[i].broadcast();
        if ((i % 5) == 0) <<< i >>>;
        this.step_dur => now;
      }
    }
  }

  // like MPC we pause if we're currently playing and stop/reset if not.
  fun void stop() {
    <<< "stop" >>>;
    if (this.state == "playing") {
      this.playpause();
    } else {
      this.control_stop_event.broadcast();
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
    this.control_start_event.broadcast();
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
