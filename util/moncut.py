import OSC
import scalpel.gtkui
import threading
import time
import sys

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


class MonomeCutInterface:
  def __init__(self, xmit_host='127.0.0.1', xmit_port=8000, recv_port=9000,
               model=64):
    self.xmit_host = xmit_host
    self.xmit_port = xmit_port
    self.recv_port = recv_port
    self.model = model
    self.page_button_coords, self.block_audio_selection = self.setup_model()
    self.page_id = 0
    self.start_osc_server()
    self.osc_client = OSC.OSCClient()
    self.osc_client.connect((xmit_host, xmit_port))
    self.selected_button_coords = ()
    self.set_page()
    self.blink = False
    self.blink_thread = threading.Thread(target=self.blink_loop)
    self.blink_thread.start()
    self.selection_one = None
    self.selection_two = None

  def set_page(self, page_id=None):
    if self.selected_button_coords:
      print 'WARN: cannot change pages while selection is active'
      return None

    if page_id:
      self.page_id = page_id

    for coord in self.page_button_coords:
      self.set_level(coord, 0)

    self.set_level(self.page_button_coords[self.page_id], 15)

  def coord_to_pad_id(self, coord):
    index_on_page = self.playable_button_coords.index(coord)

    return (self.page_id * self.playable_button_coords) + index_on_page

  def start_osc_server(self):
    s = OSC.ThreadingOSCServer(('127.0.0.1', self.recv_port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/grid/key', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/grid/key':
      state, coord = data[0], tuple(data[1])

      if state is 1:
        if coord in self.playable_button_coords:
          if self.selected_button_coords:
            if coord in self.selected_button_coords:
              self.play_coord(data)
            else:
              print 'not in selection:', data

          else:
            if self.selection_one is None:
              self.selected_button_coords = self.selection_one = coord
              self.blink = True

            else:
              if self.selection_two is None:
                if self.selection_two is self.selection_one:
                  return None

                self.selection_two = coord
                self.selected_button_coords = self.coords_in_block(
                  *list(self.selection_one) + list(self.selection_two)
                )

              else:
                if self.blink is True:
                  if self.selection_two == coord:
                    self.blink = False
                    self.set_up_block_audio_selection()

                else:
                  self.play_button(data)

        elif coord in self.page_button_coords:
          self.set_page(self.page_id_coords.index(coord))

        else:
          print 'unknown button:', data

  def set_up_block_audio_selection(self):
    pass

  def play_button(self, data):
    self.selection.get()

  def coords_in_block(self, ax, ay, bx, by):
    buttons = []
    for y in range(sorted((ay, by))[0], sorted((ay, by))[1] + 1):
      for x in range(sorted((ax, bx))[0], sorted((ax, bx))[1] + 1):
        buttons.append((x, y))

    return tuple(sorted(buttons, key=lambda x: x[1], reverse=True))

  def setup_model(self):
    if self.model == 64:
      self.x_size = 8
      self.y_size = 8
      self.playable_button_coords = self.coords_in_block(0, 7, 7, 3)
      pbc = self.coords_in_block(0, 2, 7, 2)
      return (pbc, dict(map(lambda x: (x, {}), pbc)))

  def blink_loop(self):
    while not time.sleep(0.05):
      while self.blink:
        print 'blinking'
        for coord in self.selected_button_coords:
          self.set_level(coord, 15)
        time.sleep(0.5)
        for coord in self.selected_button_coords:
          self.set_level(coord, 0)
        time.sleep(0.5)

  def set_level(self, coords, level):
    msg = OSC.OSCMessage('/monome/grid/led/level/set')
    msg.append(coords[0])
    msg.append(coords[1])
    msg.append(level)
    self.osc_client.send(msg)

  def show_block(self, ax, ay, bx, by):
    block_buttons = self.coords_in_block(ax, ay, bx, by)

    for y in sorted(range(self.y_size), reverse=True):
      for x in sorted(range(self.x_size)):
        if (x, y) in block_buttons:
          sys.stdout.write('1 ')
          time.sleep(0.2)
        else:
          sys.stdout.write('0 ')
      print

  def load_sound(self, filename, ocs_control):
    self.filename = filename
    self.osc_control = osc_control
    self.sound = scalpel.gtkui.app.edit.Sound(filename)
    self.player = scalpel.gtkui.app.player.Player(self.sound)
    self.graph = scalpel.gtkui.app.graphmodel.Graph(self.sound)
    self.curs = scalpel.gtkui.app.cursor.Cursor(self.graph, self.player)
    self.sel = scalpel.gtkui.app.selection.Selection(self.graph, self.curs)

    self.con = scalpel.gtkui.app.control.Controller(
      self.sound, self.player, self.graph, self.sel
    )

    scalpel.gtkui.app.new_sound_loaded(
      self.con, self.graph, self.sel, self.curs
    )

    self.osc_control.update(
      self.sound, self.player, self.graph, self.curs, self.sel, self.con
    )


if __name__ == '__main__':
  filename = '/Users/josh/tmp/5_gongs.wav'

  osc_control = OSCControl(None, None, None, None, None, None)
  monome_cut_interface = MonomeCutInterface()
  monome_cut_interface.load_sound(filename, osc_control)

  scalpel.gtkui.main_loop()
