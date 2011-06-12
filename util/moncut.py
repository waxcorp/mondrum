import OSC
import scalpel.gtkui
import threading

class OSCControl:
  def __init__(self, sound, player, graph, curs, sel, con, port=8000):
    self.start_osc_server(port)

  def update(self, sound, player, graph, curs, sel, con):
    self._sound = sound
    self._player = player
    self._graph = graph
    self._curs = curs
    self._selection = sel
    self._controller = con
    self._graph.zoom_out_full()
    self._selection.select_all()
    self._state = 0

  def start_osc_server(self, port):
    s = OSC.ThreadingOSCServer(('localhost', port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/enc/key', self.osc_dispatch)
    s.addMsgHandler('/monome/enc/delta', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/enc/delta':
      if self._state == 1:
        self._graph.zoom_on(
          self._selection.pixels()[data[0]],
          (100 - data[1]) / 100.
        )

      elif self._state == 0:
        start, end = self._selection.pixels()

        if data[0] == 0:
          start += data[1]
          if start < 0:
            start = 0
          self._selection.move_start_to_pixel(start)

        elif data[0] == 1:
          end += data[1]
          if self._graph.pxltofrm(end) > self._graph.numframes():
            end = self._graph.frmtopxl(self._graph.numframes())

          self._selection.move_end_to_pixel(end)

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
