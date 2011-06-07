import OSC
import threading

# Scalpel sound editor (http://scalpelsound.online.fr)
# Copyright 2009 (C) Pierre Duquesne <stackp@online.fr>
# Licensed under the Revised BSD License.

from scalpel import constants

# pygtk gets program name from sys.argv[0]. This name appears in
# taskbars when windows are grouped together.
import sys
sys.argv[0] = constants.__appname__

from scalpel import app
from scalpel import control
from scalpel.gtkwaveform import GraphView, GraphScrollbar
from scalpel.gtkfiledialog import OpenFileDialog, SaveFileDialog, \
                                                        SaveSelectionFileDialog
import copy
import os.path
import urllib
import gobject
import gtk
gtk.gdk.threads_init()

def main_loop():
    gtk.main()

class EditorWindow(gtk.Window):
  def __init__(self, notebook):
    gtk.Window.__init__(self)

    self.notebook = notebook
    self.notebook.root_window = self
    self.notebook.connect('filename-changed', self._on_filename_changed)

    self.vbox = gtk.VBox()
    self.vbox.pack_start(self.notebook, expand=True, fill=True)
    self.add(self.vbox)

    # keyboard shortcuts
    kval = gtk.gdk.keyval_from_name
    self.handlers = {
      'space': self.toggle_play,
      'ISO_Level3_Shift': self.play,
      '<Shift>Home': self.select_till_start,
      '<Shift>End': self.select_till_end
    }
    self.connect('key_press_event', self.on_key_press_event)

    self.resize(700, 500)
    self.show_all()

  def on_new_sound_loaded(self, controller, graph, sel, curs):
    page = EditorPage(controller, graph, sel, curs)
    self.notebook.add_page(page)

  def _on_filename_changed(self, notebook, filename):
    self._filename_update(filename)

  def _filename_update(self, filename):
    self._update_title(filename)

  def _update_title(self, filename=None):
    title = constants.__appname__
    if filename:
      title = os.path.basename(filename) + ' - ' + title
    self.set_title(title)

  # -- GTK Callbacks
  def __getattr__(self, name):
    """Redirect callbacks.

    The gtk widget passed to the callback (first argument) will
    not be passed to the invoked method.

    """
    if name in ['play', 'toggle_play', 'stop', 'goto_start',
      'goto_end', 'select_all', 'zoom_in', 'zoom_out', 'zoom_fit',
      'select_till_start', 'select_till_end']:
      method = getattr(self.notebook, name)

      def forward(*args):
        method(*args[1:])

      return forward
    else:
      raise AttributeError(name)

  def on_key_press_event(self, widget, event):
    key = gtk.gdk.keyval_name(event.keyval)
    if event.state is gtk.gdk.SHIFT_MASK:
      key = '<Shift>' + key
    if key in self.handlers:
      handler = self.handlers[key]
      handler()


class EditorNotebook(gtk.Notebook):
  __gsignals__ = {
    'filename-changed': (
      gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)
    ),
    'error': (
      gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (gobject.TYPE_PYOBJECT,gobject.TYPE_PYOBJECT)
    ),
  }

  def __init__(self):
    gtk.Notebook.__init__(self)
    self.root_window = None
    self.set_scrollable(True)
    self.set_show_border(False)
    self.popup_enable()
    self.connect('switch-page', self.on_page_switch)
    self.connect('page-added', self.hide_show_tabs)
    self.connect('page-removed', self.hide_show_tabs)

  def on_page_switch(self, notebook, _, numpage):
    page = self.get_nth_page(numpage)
    self.emit("filename-changed", page.filename())

  def on_filename_changed(self, widget, filename):
    current_page = self.get_nth_page(self.get_current_page())
    if widget is current_page:
      self.emit('filename-changed', filename)

  def on_error(self, widget, title, text):
    self.emit('error', title, text)

  def hide_show_tabs(self, *args):
    if self.get_n_pages() <= 1:
      self.set_property('show-tabs', False)
    else:
      self.set_property('show-tabs', True)

  def add_page(self, page):
    page.show_all()
    i = self.append_page_menu(page, tab_label=page.tab,
                  menu_label=page.menu_title)
    self.set_tab_reorderable(page, True)
    self.set_current_page(i)
    page.connect('filename-changed', self.on_filename_changed)
    page.connect('must-close', self.close_page_by_id)
    page.connect('error', self.on_error)
    self.emit('filename-changed', page.filename())

  def is_empty(self):
    return self.get_n_pages() == 0

  def close_page_by_id(self, widget):
    for numpage in range(self.get_n_pages()):
      page = self.get_nth_page(numpage)
      if page is widget:
        return self.close_page(numpage)

  def close_page(self, numpage=None):
    if numpage is None:
      numpage = self.get_current_page()
    try:
      self._close_page(numpage, force=False)
    except control.FileNotSaved:
      proceed = self._show_dialog_close()
      if not proceed:
        return False
      else:
        self._close_page(numpage, force=True)
    return True

  def _close_page(self, numpage, force=False):
    page = self.get_nth_page(numpage)
    page.close(force)
    self.remove_page(numpage)
    page.destroy()
    return True

  def _show_dialog_close(self):
    dialog = gtk.MessageDialog(parent=self.root_window,
                   type=gtk.MESSAGE_WARNING)
    name = self.filename() or 'sound'
    name = os.path.basename(name)
    name = name.replace('&', '&amp;')
    dialog.set_markup('<b>Save %s before closing?</b>' % name)
    dialog.add_button('Close _without saving', gtk.RESPONSE_NO)
    dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    dialog.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)
    dialog.set_default_response(gtk.RESPONSE_CANCEL)
    response = dialog.run()
    dialog.destroy()
    proceed = False
    if response == gtk.RESPONSE_NO:
      proceed = True
    elif response == gtk.RESPONSE_YES:
      self.save()
      proceed = True
    return proceed

  def __getattr__(self, name):
    if name in ['play', 'toggle_play', 'stop', 'goto_start', 'goto_end',
      'select_all', 'zoom_in', 'zoom_out', 'zoom_fit', 'select_till_start',
      'select_till_end', 'save_selection_as', 'filename']:

      def forward(*args):
        page = self.get_nth_page(self.get_current_page())
        method = getattr(page, name)
        return method(*args)

      return forward
    else:
      raise AttributeError(name)


class EditorPage(gtk.VBox):
  __gsignals__ = {
    'filename-changed': (
      gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)
    ),
    'must-close': (
      gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()
    ),
    'error': (
      gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)
    ),
  }

  def __init__(self, controller, graph, selection, cursor):
    gtk.VBox.__init__(self)
    self.ctrl = controller

    # Close button
    image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
    button = gtk.Button()
    button.set_relief(gtk.RELIEF_NONE)
    button.set_focus_on_click(False)
    button.set_image(image)
    style = gtk.RcStyle()
    style.xthickness = 0
    style.ythickness = 0
    button.modify_style(style)
    button.connect('clicked', self.must_close)

    # Tab title
    self.title = gtk.Label()
    self.tab = gtk.HBox()
    self.tab.modify_style(style)
    self.tab.pack_start(self.title, True, True)
    self.tab.pack_end(button, False, False)
    self.tab.show_all()

    # Popup menu page title
    self.menu_title = gtk.Label()

    self.waveform = GraphView(graph, selection, cursor)
    self.scrollbar = GraphScrollbar(graph)
    self.statusbar = gtk.Statusbar()
    self.pack_start(self.waveform, expand=True, fill=True)
    self.pack_start(self.scrollbar, expand=False, fill=False)
    self.pack_end(self.statusbar, expand=False, fill=False)
    self.waveform.connect('selection-changed',
                        self.on_selection_changed)
    self.ctrl.filename_changed.connect(self._update_filename)
    self.ctrl.error.connect(self.emit_error)
    self._update_filename()

  def must_close(self, *args):
    self.emit('must-close')

  def close(self, force=False):
    self.ctrl.close(force)

  def emit_error(self, title, text):
    self.emit('error', title, text)

  def _update_filename(self):
    filename = self.ctrl.filename() or None
    if filename:
      name = os.path.basename(filename)
    else:
      name = 'Unsaved'

    self.title.set_text(name)
    self.menu_title.set_text(name)
    self.emit('filename-changed', filename)

  def __getattr__(self, name):
    if name in ['play', 'toggle_play', 'stop', 'goto_start', 'goto_end',
      'select_all', 'zoom_in', 'zoom_out', 'zoom_fit', 'select_till_start',
      'select_till_end', 'filename', 'on_selection_changed']:

      method = getattr(self.ctrl, name)
      def forward(*args):
        return method(*args)

      return forward
    else:
      raise AttributeError(name)


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
    self._waveform = None
    self._event = gtk.gdk.Event(gtk.gdk.BUTTON_PRESS)

    self._graph.zoom_out_full()
    self._selection.select_all()
    self._state = 0

  def start_osc_server(self, port):
    s = OSC.ThreadingOSCServer(('localhost', port))
    s.addDefaultHandlers()
    s.addMsgHandler('/monome/enc/delta', self.osc_dispatch)
    s.addMsgHandler('/monome/enc/key', self.osc_dispatch)
    t = threading.Thread(target=s.serve_forever)
    t.start()

  def osc_dispatch(self, pattern, tags, data, client_address):
    start, end = self._selection.pixels()
    #print start, end

    if pattern == '/monome/enc/delta':
      if self._state == 1:
        self._graph.zoom_on(self._selection.pixels()[data[0]],
          (100 - data[1]) / 100.)
      elif self._state == 0:
        if data[0] == 0:
          start += data[1]
          if start < 0:
            start = 0

          self._event.x = float(start)
          self._event.y = float(1)

        elif data[0] == 1:
          end += data[1]
          if self._graph.pxltofrm(end) > self._graph.numframes():
            end = self._graph.frmtopxl(self._graph.numframes())

          self._event.x = float(end)
          self._event.y = float(0)

        self._waveform.emit('motion_notify_event', self._event)

    elif pattern == '/monome/enc/key':
      self._state = data[1]


class ArcSelection(object):
  def __init__(self, widget, selection):
    self.widget = widget
    self._selection = selection
    widget.connect("motion_notify_event", self.motion_notify)

  def motion_notify(self, widget, event):
    if event.y > 0:
      self._selection.move_start_to_pixel(event.x)
    else: 
      self._selection.move_end_to_pixel(event.x)


def load_sound(filename, ocs_control):
  sound = app.edit.Sound(filename)
  player = app.player.Player(sound)
  graph = app.graphmodel.Graph(sound)
  curs = app.cursor.Cursor(graph, player)
  sel = app.selection.Selection(graph, curs)
  con = app.control.Controller(sound, player, graph, sel)

  osc_control.update(sound, player, graph, curs, sel, con)
  app.new_sound_loaded(con, graph, sel, curs)

if __name__ == '__main__':
  filename = '/Users/josh/tmp/bigfile9.wav'

  notebook = EditorNotebook()
  win = EditorWindow(notebook)
  app.new_sound_loaded.connect(win.on_new_sound_loaded)

  osc_control = OSCControl(None, None, None, None, None, None)
  load_sound(filename, osc_control)
  waveform = notebook.get_nth_page(0).waveform
  osc_control._waveform = waveform
  #waveform.disconnect(27)
  ArcSelection(waveform, osc_control._selection)

  print win
  main_loop()
