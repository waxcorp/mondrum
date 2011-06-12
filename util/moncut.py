import OSC
import scalpel.gtkui
import threading
import time

class OSCControl:
  def __init__(self, sound, player, graph, curs, sel, con, port=8000):
    self.start_osc_server(port)
    self._state = 0

  def update(self, sound, player, graph, curs, sel, con):
    self._sound = sound
    self._player = player
    self._graph = graph
    self._curs = curs
    self._selection = sel
    self._controller = con
    self._graph.zoom_out_full()
    self._selection.select_all()
    self._start, self._end = self._selection.get()
    t = threading.Thread(target=self.update_selection_loop)
    t.start()

  def start_osc_server(self, port):
    s = OSC.ThreadingOSCServer(('localhost', port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/enc/key', self.osc_dispatch)
    s.addMsgHandler('/monome/enc/delta', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()

  def update_selection_loop(self):
    while not time.sleep(.05):
      self._selection.set(self._start, self._end)

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/enc/delta':
      if self._state == 1:
        self._graph.zoom_on(
          self._selection.pixels()[data[0]],
          (100 - data[1]) / 100.
        )

      elif self._state == 0:
        start, end = self._selection.get()
        v_start, v_end = self._graph.view()
        v_width = v_end - v_start
        mod_ratio = (v_width / 800.)

        if data[1] > 0:
          mod = int(abs(data[1]) * mod_ratio)
        else:
          mod = -int(abs(data[1]) * mod_ratio)

        if data[0] == 0:
          start += mod
          if start < 0:
            start = 0
          self._start = start

        elif data[0] == 1:
          end += mod
          if end > self._graph.numframes():
            end = self._graph.numframes()

          self._end = end

    elif pattern == '/monome/enc/key':
      self._state = data[1]

def load_sound(filename, ocs_control):
  sound = scalpel.gtkui.app.edit.Sound(filename)
  player = scalpel.gtkui.app.player.Player(sound)
  graph = scalpel.gtkui.app.graphmodel.Graph(sound)
  curs = scalpel.gtkui.app.cursor.Cursor(graph, player)
  sel = scalpel.gtkui.app.selection.Selection(graph, curs)
  con = scalpel.gtkui.app.control.Controller(sound, player, graph, sel)

  scalpel.gtkui.app.new_sound_loaded(con, graph, sel, curs)
  osc_control.update(sound, player, graph, curs, sel, con)

if __name__ == '__main__':
  filename = '/Users/josh/tmp/5_gongs.wav'

  osc_control = OSCControl(None, None, None, None, None, None)
  load_sound(filename, osc_control)

  scalpel.gtkui.main_loop()
