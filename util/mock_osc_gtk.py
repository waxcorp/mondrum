import OSC
import gtk
import pygtk
import sys

pygtk.require('2.0')


def create_bbox(width, title=None, spacing=0, layout=gtk.BUTTONBOX_SPREAD):
  frame = gtk.Frame(title)
  bbox = gtk.HButtonBox()
  bbox.set_border_width(5)
  bbox.set_layout(layout)
  bbox.set_spacing(spacing)
  frame.add(bbox)

  for x in range(width):
    bbox.add(gtk.Button(label='0'))

  return frame


class MockMonome(gtk.Window):
  def __init__(self, height, width, recv_port, parent=None):
    # Create the toplevel window
    gtk.Window.__init__(self)

    try:
      self.set_screen(parent.get_screen())
    except AttributeError:
      self.connect('destroy', lambda *w: gtk.main_quit())

    self.set_title(self.__class__.__name__)
    self.set_border_width(10)

    main_vbox = gtk.VBox()
    self.add(main_vbox)

    frame_horiz = gtk.Frame(str(recv_port))
    main_vbox.pack_start(frame_horiz, padding=10)

    vbox = gtk.VBox()
    vbox.set_border_width(10)
    frame_horiz.add(vbox)

    for y in range(height):
      vbox.pack_start(create_bbox(width), padding=0)

    self.show_all()


def main():
  recv_port, height, width = [ int(x) for x in sys.argv[1:] ]
  MockMonome(recv_port, 8, 8)
  gtk.main()


if __name__ == '__main__':
  main()
