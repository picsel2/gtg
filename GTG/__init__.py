import gi


def gi_version_requires():
    gi.require_version('Gdk', '4.0')
    gi.require_version('Gtk', '4.0')
    gi.require_version('GtkSource', '5')
