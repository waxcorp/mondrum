class Instrument {
  fun void receive(int signals[]) {}
}

class Controller extends Instrument {
  int _controller_shred_id;
  Instrument _instruments[];

  fun void controller_main_loop() {
    (spork ~ control_loop()).id() => _controller_shred_id;
    me.yield();
  }

  fun void control_loop() {
    while (1) {
      control_signal() @=> int sig[];
      for (0 => int x; x < _instruments.cap(); x++) {
        sig => _instruments[x].receive;
      }
    }
  }

  fun int[] control_signal() {}
}

class KbController extends Controller {
  // TODO(josh): see about http://smelt.cs.princeton.edu/code/keyboard/kb.ck
  int _sig;
  KBHit _kb_hit;

  fun int[] control_signal() {
    _kb_hit => now;

    int sig[256];
    0 => int i;
    while (_kb_hit.more()) {
      _kb_hit.getchar() => sig[i];
      i++;
    }

    return sig;
  }
}

class MonDrumDBObject extends Controller {
  MonDrum @ _mondrum;
  MonDrumProject @ _prj;
  string _path;

  fun void init(string path, MonDrum mondrum) {
    path => _path;
    mondrum @=> _mondrum;

    init_helper();
  }

  fun void init_helper() {}

  fun void load(string path) {
    // _mondrum.db.load_mondrum_object(this, path, _toString());
  }
}

class MonDrumProgram extends MonDrumDBObject {
  Gain _gain_l, _gain_r;
  MonDrumSample _samples[256];
  0.5 => gain;

  fun void init_helper() {
    for (0 => int i; i < _samples.cap(); i++) { this @=> _samples[i]._pgm; }
  }

  fun float gain(float g) { return g => _gain_l.gain => _gain_r.gain; }
  fun float gain() { return _gain_l.gain(); }
}

class MonDrumSequenceTrack extends MonDrumDBObject {
  Gain _gain_l, _gain_r;
  MonDrumProgram @ _pgm;
}

class MonDrumSample extends MonDrumDBObject {
  MonDrumProgram @ _pgm;
  LiSa @ _lisa_l, _lisa_r;
  Gain @ _out_l, _out_r;
  int _shred_id;

  fun void init_helper() {
    LiSa l @=> _lisa_l;
    LiSa r @=> _lisa_r;
    _pgm._gain_l @=> _out_l;
    _pgm._gain_r @=> _out_r;
    0.5 => gain;
  }

  fun void load_file(string path, SndBuf buf_l, SndBuf buf_r) {
    path => _path;

    <<< this.toString(), "loading", _path >>>;

    _path + "_l.wav" => buf_l.read;
    _path + "_r.wav" => buf_r.read;

    copy_from_sndbuf_to_lisa(buf_l, _lisa_l);
    copy_from_sndbuf_to_lisa(buf_r, _lisa_r);

    <<< this.toString(), "done loading", _path >>>;
  }

  fun void copy_from_sndbuf_to_lisa(SndBuf b, LiSa l) {
    b.samples()::samp => l.duration;
    for (0 => int i; i < b.samples(); i++) {
      l.valueAt(b.valueAt(i), i::samp);
    }
  }

  fun void play(dur pos) {
    (spork ~ play_shred(pos)).id() => _shred_id;
    me.yield();
  }

  fun void play_shred(dur pos) {
    stop(me.id()); // in case we're currently playing

    <<< "starting at pos", pos >>>;

    connect();
    pos => _lisa_l.playPos => _lisa_r.playPos;
    true => _lisa_l.play => _lisa_r.play;
    _lisa_l.duration() - pos => now;
    disconnect();
  }

  fun void connect() {
    disconnect();
    _lisa_l => _out_l;
    _lisa_r => _out_r;
  }

  fun void disconnect() {
    false => _lisa_l.play => _lisa_r.play;
    _lisa_l =< _out_l;
    _lisa_r =< _out_r;
  }

  fun void stop(int not_this_id) { if (not_this_id != _shred_id) stop(); }
  fun void stop() {
    disconnect();
    Machine.remove(_shred_id);
  }

  // UGen/LiSa-compatible functions

  fun float gain() { return _lisa_l.gain(); }
  fun float gain(float g) {
    return g => _lisa_l.gain => _lisa_r.gain;
  }

  fun float rate() { return _lisa_l.rate(); }
  fun float rate(float r) {
    return r => _lisa_l.rate => _lisa_r.rate;
  }

  fun dur duration() { return _lisa_l.duration(); }
}

class MonDrumSequenceEvent extends Event {
  float loop_percent;
  int id;
}

class MonDrumSequence extends MonDrumDBObject {
  MonDrumSequenceTrack _tracks[128];
  MonDrumSequenceTrack @ _track;
  MonDrumSequenceEvent _tick_events[];

  [1, 1, 1, 1] @=> int _loc[];
  2 => int _bars;
  4 => int _beats;
  96 => int _ticks;
  96 => int _semi_ticks;

  88 => int _bpm;
  1 => int _cur_tick;
  true => int _use_master_bpm;

  fun void init_helper() {
    MonDrumSequenceEvent tix[(_bars * _beats * _ticks)] @=> _tick_events;
    for (0 => int i; i < _tracks.cap(); i++) {
      _tracks[i].init("", _mondrum);
      _mondrum._prj._pgms[0] @=> _tracks[i]._pgm;
    }
    _tracks[0] @=> _mondrum._prj._seq._track;
  }

  fun int loc_to_tick(int l[]) {
    return (((l[0]-1) * _beats) + (l[1]-1)) * _ticks + (l[2]-1) + 1;
  }

  fun int[] tick_to_loc(int t) {
    t--;
    1 + (t / (_beats * _ticks)) => int bar;
    1 + ((t / _ticks) % _beats) => int beat;
    1 + (t % _ticks) => int semi_beat;

    return [bar, beat, semi_beat, 1];
  }

  fun int get_bpm() {
    if (_use_master_bpm) {
      return _mondrum._prj._bpm;
    } else {
      return _bpm;
    }
  }

  fun dur tick_dur() {
    60::second / get_bpm() => dur beat_dur;
    _bars * _beats => int beats_in_loop;
    beat_dur * beats_in_loop => dur loop_dur;

    return loop_dur / _tick_events.cap();
  }

  fun void set_loc(int t) {
    t => _cur_tick;
    tick_to_loc(t) @=> _loc;
  }

  fun void set_loc(int l[]) {
    l @=> _loc;
    loc_to_tick(l) => _cur_tick;
  }

  fun void tick() { tick(_loc); }
  fun void tick(int l[]) {
    set_loc(l);

    if (_cur_tick > _tick_events.cap()) {
      set_loc(1);
    } else {
      if (l[2] == 1) <<< l[0], l[1], l[2] >>>;
      _tick_events[(_cur_tick - 1)].broadcast();
      tick_dur() => now;
      set_loc(_cur_tick + 1);
    }
  }

  fun void receive(int data[]) {}
}

class MonDrumProject {
  MonDrum @ _mondrum;
  MonDrumSequence _seqs[128];
  MonDrumProgram _pgms[128];
  _seqs[0] @=> MonDrumSequence _seq;
  88 => int _bpm;
  string _path;

  fun void init(string path, MonDrum mondrum) {
    path => _path;
    mondrum @=> _mondrum;

    for (0 => int i; i < _pgms.cap(); i++) _pgms[i].init("", mondrum);
    for (0 => int i; i < _seqs.cap(); i++) _seqs[i].init("", mondrum);

    load(path);
  }

  fun void load(string path) {
    _mondrum._db.load_mondrum_project(this, path);
  }
}

public class MonDrum extends Controller {
  Monome _monome;
  MonDrumDB _db;
  MonDrumSequenceController _seqctl;
  MonDrumProject _prj;

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
    _monome.init(monome_xmit_host, monome_xmit_prefix, monome_xmit_port,
                     monome_recv_port, monome_model);
    _db.init(_monome, mondrum_db_xmit_prefix, mondrum_db_xmit_host,
                 mondrum_db_xmit_port, mondrum_db_recv_port);
    _prj.init(prj_path, this);
    _seqctl.init(this);
  }
}

class Monome {
  OscSend _xmit;
  int _model;
  string _xmit_prefix;
  OscRecv _recv;
  MonomeButton _buttons[][];

  fun void init(string xmit_host, string xmit_prefix, int xmit_port,
                int recv_port, int model) {
    model => _model;
    xmit_prefix => _xmit_prefix;
    _xmit.setHost(xmit_host, xmit_port);
    recv_port => _recv.port;
    _recv.listen();
    set_all_buttons(0);

    if (model == 64) setup_buttons(8, 8);
  }

  fun void set_all_buttons(int state) {
    _xmit.startMsg(_xmit_prefix + "/grid/led/all i");
    _xmit.addInt(state);
  }

  fun void set_level(string t, int x, int y, int l) {
    if (t == "set") {
      _buttons[x][y].set_level(l);
    } else {
      _xmit.startMsg(_xmit_prefix + "/grid/led/level/" + t + " iii");
      _xmit.addInt(x);
      _xmit.addInt(y);
      _xmit.addInt(l);
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
    buttons @=> _buttons;
  }
}

class MonomeButton {
  int _brightness_levels[15];
  0 => int _level;
  int _x;
  int _y;
  Monome _m;
  OscEvent _key;
  string _attrs[];

  fun void init(int y, int x, Monome m) {
    x => _x;
    y => _y;
    m @=> _m;
    _m._recv.event(_m._xmit_prefix + "/grid/key iii") @=> _key;
    spork ~ key_event_manager();
  }

  fun void key_event_manager() {
    while (true) {
      _key => now;
      until (_key.nextMsg() == 0) {
        _key.getInt() => int x_pos;
        _key.getInt() => int y_pos;
        _key.getInt() => int s;
        if (x_pos != _x || y_pos != _y) break;

        if (s == 0) 0 => _level;
        if (s == 1) 15 => _level;
        set_level(_level);
      }
    }
  }

  fun void start_xmit_xy(string msg) {
    _m._xmit.startMsg(msg);
    _x => _m._xmit.addInt;
    _y => _m._xmit.addInt;
  }

  fun void set_level(int level) {
    if (level > _brightness_levels.cap()) {
      _brightness_levels.cap() - 
        (level % _brightness_levels.cap()) => level;
      if (level == 0) 1 +=> level;
    }
    start_xmit_xy(_m._xmit_prefix + "/grid/led/level/set, iii");
    Std.abs(level) => _m._xmit.addInt => _level;
  }

  fun void glow(dur ramp_dur, int iters, dur pause) {
    pause => now;
    // TODO(josh): figure out how to do "and" < -1 for infinite glow
    for (0 => int i; i < iters; i++) {
      for (1 => int x; x < (2*(_brightness_levels.cap())); x++) {
        (x $ float) / 100 => float ratio;
        ramp_dur * (1 / _brightness_levels.cap() $ float) => now;
        set_level(x);
      }
    }
  }
}

class MonDrumDB {
  Monome _monome;
  "/mondrum_db/" => string _xmit_prefix;
  string _xmit_host;
  int _xmit_port;
  OscSend _xmit;
  OscRecv _recv;

  fun void init(Monome monome, string xmit_prefix, string xmit_host,
                int xmit_port, int recv_port) {
    monome @=> _monome;
    xmit_prefix => _xmit_prefix;
    _xmit.setHost(xmit_host, xmit_port);
    recv_port => _recv.port;
    _recv.listen();
  }

  fun void load_mondrum_project(MonDrumProject mondrum_project, string prj) {
    // do things
  }

  fun MonDrumSequence load_mondrum_sequence(string prj, int seq_id) {
    // do things
  }
}

class MonDrumSequenceController extends KbController {
  MonDrum @ _mondrum;
  int _main_loop_shred_id;
  Event _start_event;
  Event _stop_event;
  Event _playpause_event;
  "stopped" => string _state;

  fun void init(MonDrum mondrum) {
    mondrum @=> _mondrum;

    Instrument instruments_placeholder[1] @=> _instruments;
    this @=> _instruments[0];

    spork ~ playstart_loop();
    controller_main_loop();
    me.yield();
  }

  fun void playpause() {
    if (_state == "paused") {
      "playing" => _state;
    } else if (_state == "playing") {
      "paused" => _state;
    } else if (_state == "stopped") {
      _start_event.broadcast();
      "playing" => _state;
    }

    _playpause_event.broadcast();
  }

  fun void playstart_loop() {
    while (1) {
      _start_event => now;
      "playing" => _state;
      (spork ~ main_loop()).id() => _main_loop_shred_id;

      _stop_event => now;
      Machine.remove(_main_loop_shred_id);
    }
  }

  fun void main_loop() {
    _mondrum._prj._seq.tick([1, 1, 1, 1]);
    while (1) {
      if (_state == "paused") _playpause_event => now;
      _mondrum._prj._seq.tick();
    }
  }

  // like MPC we pause if we're currently playing and stop/reset if not.
  fun void stop() {
    if (_state == "playing") {
      playpause();
    } else {
      _stop_event.broadcast();
      "stopped" => _state;
    }
  }

  fun void play() { if (_state != "playing") playpause(); }

  fun void playstart() {
    stop();
    stop();
    me.yield();
    _start_event.broadcast();
  }

  fun void receive(int signals[]) {
    if (signals[0] == 112) {
      playstart();
    } else if (signals[0] == 111) {
      play();
    } else if (signals[0] == 105) {
      stop();
    }
  }
}
