import OSC
import gobject
import gtk
import scalpel.gtkui
import sys
import threading
import time

gtk.gdk.threads_init()


class OSCControl:
  def __init__(self, sound, player, graph, curs, sel, con, recv_port=8001):
    self.start_osc_server(recv_port)
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
  def __init__(self, xmit_host='127.0.0.1', xmit_port=17448, recv_port=8000,
               model=64):
    self.xmit_host = xmit_host
    self.xmit_port = xmit_port
    self.recv_port = recv_port
    self.model = model
    self.page_button_coords, self.block_audio_selection = self.setup_model()
    self.page_id = 0
    self.start_osc_server()
    self.set_level_all(0)
    self.selected_button_coords = ()
    self.set_page()
    self.blink = threading.Event()
    self.blink_on = threading.Event()
    self.blink_thread = threading.Thread(target=self.blink_loop)
    self.blink_thread.start()
    self.selection_one = None
    self.selection_two = None

  def start_osc_server(self):
    s = OSC.ThreadingOSCServer(('127.0.0.1', self.recv_port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/grid/key', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()
    self.osc_client = s.client

  def set_page(self, page_id=None):
    if self.selected_button_coords:
      print 'WARN: cannot change pages while selection is active'
      return None

    if page_id is not None:
      self.page_id = page_id

    for coord in self.page_button_coords:
      self.set_level(coord, 0)

    self.set_level(self.page_button_coords[self.page_id], 15)

  def coord_to_pad_id(self, coord):
    index_on_page = self.playable_button_coords.index(coord)

    return (self.page_id * self.playable_button_coords) + index_on_page

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/grid/key':
      coord, state = tuple(data[:2]), data[2]

      if state is 1:
        if coord in self.playable_button_coords:
          if self.selected_button_coords:
            if coord in self.selected_button_coords:
              self.play_coord(data)
            else:
              print 'not in selection:', data

          if self.selection_one is None:
            return self._start_selection(coord)

          else:
            if self.selection_two is None:
              return self._complete_or_clear_selection(coord)

            else:
              if self.blink.is_set():
                if coord == self.selection_two:
                  self.blink.clear()
                  self.set_levels(self.selected_button_coords, 15)
                  self._set_up_block_audio_selection()

              else:
                if coord == self.selection_two:
                  self.blink.set()
                  self.blink_on.clear()
                  self.set_levels(self.selected_button_coords, 0)
                else:
                  self.selection_two = coord
                  self.selected_button_coords = self.coords_in_block(
                    *list(self.selection_one) + list(self.selection_two)
                  )

                print 'would play button'
                #self.play_button(data)

        elif coord in self.page_button_coords:
          self.set_page(self.page_button_coords.index(coord))

        else:
          print 'unknown button:', data

  def _start_selection(self, coord):
    print 'starting selection'
    self.selection_one = coord
    self.selected_button_coords = (coord,)
    self.blink.set()

  def _complete_or_clear_selection(self, coord):
    if coord == self.selection_one:
      self._clear_selection()
    else:
      print 'select block'
      self.selection_two = coord
      self.selected_button_coords = self.coords_in_block(
        *list(self.selection_one) + list(self.selection_two)
      )
      self.set_levels(self.selected_button_coords, 15)

  def _clear_selection(self):
    print 'clearing selection'
    self.selection_one, self.selection_two = None, None
    self.selected_button_coords = ()
    self.blink.clear()

  def play_coord(self, data):
    print 'would play data', data

  def _set_up_block_audio_selection(self):
    print 'would set up block audio selection'

  def play_button(self, data):
    print self.sel.get()

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
      pbc = reversed(list(self.coords_in_block(0, 2, 7, 2)))
      return (tuple(pbc), dict(map(lambda x: (x, {}), pbc)))

  def blink_loop(self):
    self.blink_on.set()
    while True:
      self.blink.wait()
      print 'blinking', time.time()

      if self.blink_on.is_set():
        self.set_levels(self.selected_button_coords, 15)

      for x in range(500):
        if self.blink_on.is_set():
          time.sleep(0.001)
        else:
          break

      if self.blink.is_set():
        self.blink_on.set()
        self.set_levels(self.selected_button_coords, 0)

      for x in range(500):
        if self.blink.is_set():
          time.sleep(0.001)
        else:
          break

  def set_level_all(self, level):
    msg = OSC.OSCMessage('/monome/grid/led/all')
    msg.append(level)
    self.osc_client.sendto(msg, (self.xmit_host, self.xmit_port))

  def set_levels(self, coords, level):
    for coord in coords:
       self.set_level(coord, level)

  def set_level(self, coord, level):
    msg = OSC.OSCMessage('/monome/grid/led/set')
    msg += list(coord) + [level]
    self.osc_client.sendto(msg, (self.xmit_host, self.xmit_port))

  def load_sound(self, filename, osc_control):
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


class MockMonome(gtk.Window):
  def __init__(self, height=8, width=8, recv_port=9500, xmit_port=9000):
    self.height = height
    self.width = width
    self.recv_port = recv_port
    self.xmit_port = xmit_port
    self.buttons = {}

    self.start_osc_server()
    self.setup_gtk_window()

  def setup_gtk_window(self):
    # Create the toplevel window
    gtk.Window.__init__(self)

    self.set_title(self.__class__.__name__)
    self.set_border_width(10)

    main_vbox = gtk.VBox()
    self.add(main_vbox)

    frame_horiz = gtk.Frame(str(self.recv_port))
    main_vbox.pack_start(frame_horiz, padding=10)

    vbox = gtk.VBox()
    vbox.set_border_width(10)
    frame_horiz.add(vbox)

    for y in sorted(range(self.height), reverse=True):
      vbox.pack_start(self.create_button_row(y), padding=0)

    self.show_all()

  def create_button_row(self, y):
    frame = gtk.Frame(None)
    bbox = gtk.HButtonBox()
    bbox.set_border_width(5)
    bbox.set_layout(gtk.BUTTONBOX_SPREAD)
    bbox.set_spacing(0)
    frame.add(bbox)
    print 'adding', bbox

    for x in range(self.width):
      button = self.buttons[(x, y)] = gtk.Button(label='0')
      button.set_name('%d_%d' % (x, y))
      button.connect('pressed', self.pressed)
      button.connect('released', self.released)
      bbox.add(button)

    return frame

  def pressed(self, button):
    dat = [ int(x) for x in button.name.split('_') ] + [1]
    msg = OSC.OSCMessage('/monome/grid/key') + dat
    self.osc_client.sendto(msg, ('127.0.0.1', self.xmit_port))

  def released(self, button):
    dat = [ int(x) for x in button.name.split('_') ] + [0]
    msg = OSC.OSCMessage('/monome/grid/key') + dat
    self.osc_client.sendto(msg, ('127.0.0.1', self.xmit_port))

  def start_osc_server(self):
    s = OSC.ThreadingOSCServer(('127.0.0.1', self.recv_port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/grid/led/set', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()
    self.osc_client = s.client

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/grid/led/set':
      gobject.idle_add(self.set_led, *data)

  def set_led(self, x, y, level):
    self.buttons[(x, y)].set_label(str(level))


if __name__ == '__main__':
  filename = '/Users/josh/tmp/5_gongs.wav'

  #mock_monome = MockMonome(recv_port=17448, xmit_port=8000)

  # to set up the remote device port create an OSCClient as c and do:
  # c.sendto(OSC.OSCMessage('/sys/port') + 8001,  ('127.0.0.1', 17441))

  osc_control = OSCControl(None, None, None, None, None, None)
  monome_cut_interface = MonomeCutInterface()
  monome_cut_interface.load_sound(filename, osc_control)

  scalpel.gtkui.main_loop()
