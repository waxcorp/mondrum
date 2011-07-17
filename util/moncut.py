import OSC
import gobject
import gtk
import itertools
import os
import scalpel.gtkui
import sys
import threading
import time

gtk.gdk.threads_init()


class GTKSound:
  def __init__(self, recv_port=8001):
    self.start_osc_server(recv_port)
    self._state = 0

  def load_file(self, filename):
    self.filename = os.path.realpath(filename)
    self.sound = scalpel.gtkui.app.edit.Sound(filename)
    self.player = scalpel.gtkui.app.player.Player(self.sound)
    self.graph = scalpel.gtkui.app.graphmodel.Graph(self.sound)
    self.cursor = scalpel.gtkui.app.cursor.Cursor(self.graph, self.player)
    self.selection = scalpel.gtkui.app.selection.Selection(
      self.graph, self.cursor
    )
    self.controller = scalpel.gtkui.app.control.Controller(
      self.sound, self.player, self.graph, self.selection
    )
    scalpel.gtkui.app.new_sound_loaded(
      self.controller, self.graph, self.selection, self.cursor
    )

    self.graph.zoom_out_full()
    self.selection.select_all()
    self._start, self._end = self.selection.get()

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
      try:
        self.selection.set(self._start, self._end)
      except:
        pass

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/enc/delta':
      if self._state == 1:
        self.graph.zoom_on(
          self.selection.pixels()[data[0]],
          (100 - data[1]) / 100.
        )

      elif self._state == 0:
        start, end = self.selection.get()
        v_start, v_end = self.graph.view()
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
          if end > self.graph.numframes():
            end = self.graph.numframes()

          self._end = end

    elif pattern == '/monome/enc/key':
      self._state = data[1]


class MonomeCutInterface:
  def __init__(self, xmit_host='127.0.0.1', xmit_port=17448, recv_port=8000,
               model=64):
    self.xmit_host = xmit_host
    self.xmit_port = xmit_port
    self.recv_port = recv_port
    self.recorded_selections = {}
    self.current_selection = {}
    self.current_selection['coord_one'] = None
    self.current_selection['coord_two'] = None
    self.current_selection['coords'] = ()
    self.model = model
    self.setup_model()
    self.page_id = 0
    self.start_osc_server()
    self.set_level_all(0)
    self.blink = threading.Event()
    self.blink_on = threading.Event()
    self.blink_thread = threading.Thread(target=self.blink_loop)
    self.blink_thread.start()
    self.control_panel_map = {
      (7, 0): self._clear_selection,
      (7, 1): self._record_selection,
    }
    self.gtk_sound = GTKSound()
    self.set_page()

  def start_osc_server(self):
    s = OSC.ThreadingOSCServer(('127.0.0.1', self.recv_port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/grid/key', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()
    self.osc_client = s.client

  def set_page(self, page_id=None):
    if self.current_selection['coords']:
      print 'WARN: cannot change pages while selection is active'
      return None

    if page_id is not None:
      self.page_id = page_id

    self.set_levels(self.page_button_coords, 0)
    self.set_level(self.page_button_coords[self.page_id], 15)
    self._clear_selection()

  def osc_dispatch(self, pattern, tags, data, client_address):
    if pattern == '/monome/grid/key':
      coord, state = tuple(data[:2]), data[2]

      if state is 1:
        if coord in self.playable_button_coords:
          if coord in self.current_selection['coords']:
            self.play_coord(data)
          elif coord in self.current_selection['coords']:
            self._update_selection_with_recorded_block(coord)
          else:
            print 'not in selection:', data

          if self.current_selection['coord_one'] is None:
            return self._start_selection(coord)

          else:
            if self.current_selection['coord_two'] is None:
              return self._stage_selection(coord)

            else:
              if self.blink.is_set():
                if coord == self.current_selection['coord_two']:
                  self._update_selection(coord)
                elif coord == self.current_selection['coord_one']:
                  self._clear_selection()
                else:
                  self._stage_selection(coord)

              else:
                print 'would play button'

        elif coord in self.page_button_coords:
          self.set_page(self.page_button_coords.index(coord))

        else:
          if coord in self.control_panel_map:
            self.control_panel_map[coord]()
          else:
            print 'unknown button:', data

  def _start_selection(self, coord):
    print 'starting selection'
    self.current_selection['coord_one'] = coord
    self.current_selection['coords'] = (coord,)
    self.blink.set()

  def _stage_selection(self, coord):
    print 'staging current selection'
    self.set_levels(self.current_selection['coords'], 0)
    self.current_selection['coord_two'] = coord
    self.current_selection['coords'] = self.coords_in_block(
      *list(self.current_selection['coord_one']) + \
       list(self.current_selection['coord_two'])
    )
    self.set_levels(self.current_selection['coords'], 15)

  def _clear_selection(self):
    print 'clearing selection'
    self.current_selection['coord_one'] = None
    self.current_selection['coord_two'] = None
    self.blink.clear()

    self.set_levels(self.playable_button_coords, 0)
    for block in self.recorded_selections[self.page_id]:
      block_coord_list = list(itertools.chain(*block))
      self.set_levels(self.coords_in_block(*block_coord_list), 5)

    self.current_selection['coords'] = ()

  def _update_selection(self, coord):
    print 'updating current selection'
    self.current_selection.update({
      'graph': {'selection': self.gtk_sound.selection.get()},
      'latest_coord': self.current_selection['coords'][0],
    })
    self.blink.clear()
    self.set_levels(self.current_selection['coords'], 5)

  def _update_selection_with_recorded_block(self, coord):
    self.current_selection = {
    }

  def _record_selection(self):
    print 'recording selection'

    block_coords = (
      self.current_selection['coords'][0:1][0],
      self.current_selection['coords'][-1:][0],
    )

    self.recorded_selections[self.page_id].update({
      block_coords: {
        'filename': self.gtk_sound.filename,
        'frames': self.current_selection['graph']['selection'],
        'coords': {},
      },
    })

    for coord in self.current_selection['coords']:
      i = self.current_selection['coords'].index(coord)
      self.recorded_selections[self.page_id][block_coords]['coords'][coord] = {
        'frames': self._selection_slice_frames(i)
      }

    self._clear_selection()
    import pprint
    pprint.pprint(dict(self.recorded_selections))

  def _selection_slice_frames(self, index):
    frames = self.current_selection['graph']['selection']
    len_frames = frames[1] - frames[0]
    slice_size = len_frames / len(self.current_selection['coords'])

    slice_start = (slice_size * index) + frames[0]
    slice_end = frames[1]

    return slice_start, slice_end

  def play_coord(self, data):
    print 'would play data', data

  def play_button(self, data):
    print self.gsel.get()

  def coords_in_block(self, ax, ay, bx, by):
    buttons = []
    for y in range(sorted((ay, by))[0], sorted((ay, by))[1] + 1):
      for x in range(sorted((ax, bx))[0], sorted((ax, bx))[1] + 1):
        buttons.append((x, y))

    return tuple(sorted(buttons, key=lambda x: (x[1], x[0]), reverse=True))

  def setup_model(self):
    if self.model == 64:
      self.x_size = 8
      self.y_size = 8
      self.playable_button_coords = self.coords_in_block(0, 7, 7, 3)
      self.page_button_coords = self.coords_in_block(0, 2, 7, 2)

    for x in range(len(self.page_button_coords)):
      self.recorded_selections[x] = {}

  def blink_loop(self):
    self.blink_on.set()
    while True:
      self.blink.wait()

      if self.blink_on.is_set():
        self.set_levels(self.current_selection['coords'], 15)

      for x in range(500):
        if self.blink_on.is_set():
          time.sleep(0.001)
        else:
          break

      if self.blink.is_set():
        self.blink_on.set()
        self.set_levels(self.current_selection['coords'], 0)

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

  monome_cut_interface = MonomeCutInterface()
  monome_cut_interface.gtk_sound.load_file(filename)

  scalpel.gtkui.main_loop()
