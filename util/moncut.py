import OSC
import scalpel.gtkui
import threading

class OSCControl:
  def __init__(self, sound, player, graph, curs, sel, con, port=8000):
    self.update(sound, player, graph, curs, sel, con)
    self.start_osc_server(port)

  def update(self, sound, player, graph, curs, sel, con):
    self._sound = sound
    self._player = player
    self._graph = graph
    self._curs = curs
    self._selection = sel
    self._controller = con

  def start_osc_server(self, port):
    s = OSC.ThreadingOSCServer(('localhost', port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/grid/key', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()

  def osc_dispatch(self, pattern, tags, data, client_address):
    print pattern, tags, data, client_address

def load_sound(filename, ocs_control):
  sound = scalpel.gtkui.app.edit.Sound(filename)
  player = scalpel.gtkui.app.player.Player(sound)
  graph = scalpel.gtkui.app.graphmodel.Graph(sound)
  curs = scalpel.gtkui.app.cursor.Cursor(graph, player)
  sel = scalpel.gtkui.app.selection.Selection(graph, curs)
  con = scalpel.gtkui.app.control.Controller(sound, player, graph, sel)
  osc_control.update(sound, player, graph, curs, sel, con)
  scalpel.gtkui.app.new_sound_loaded(con, graph, sel, curs)

if __name__ == '__main__':
  filename = '/Users/josh/tmp/5_gongs.wav'

  osc_control = OSCControl(None, None, None, None, None, None)
  load_sound(filename, osc_control)

  scalpel.gtkui.main_loop()
