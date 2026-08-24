#!/usr/bin/env python3
# ponytail: pill overlay — GTK4 layer-shell on any app (niri OVERLAY, top 20)
# Writes via src/pill.py /tmp/yawc-pill.state, this overlay renders it above any app
import gi, pathlib, json, os
# LD_PRELOAD workaround for gtk4-layer-shell link order per warning
if "LD_PRELOAD" not in os.environ or "gtk4-layer-shell" not in os.environ["LD_PRELOAD"]:
    os.environ["LD_PRELOAD"] = "/usr/lib/libgtk4-layer-shell.so:" + os.environ.get("LD_PRELOAD","")

gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gtk4LayerShell, GLib

STATE = pathlib.Path("/tmp/yawc-pill.state")
CSS = b"""
window { background: transparent; }
pill { background: #0f172a; color: white; border-radius: 9999px; padding: 8px 16px; }
"""

class PillWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="YAWC Pill")
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 20)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        self.set_decorated(False)
        self.set_resizable(False)
        # pill content
        self.label = Gtk.Label(label="○ idle")
        self.label.add_css_class("pill")
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_halign(Gtk.Align.CENTER)
        box.append(self.label)
        self.set_child(box)
        self.present()
        GLib.timeout_add(100, self.poll)

    def poll(self):
        if STATE.exists():
            try:
                data=json.loads(STATE.read_text())
                icons={"idle":"○","recording":"● REC","transcribing":"◐","polished":"✓","error":"✕"}
                self.label.set_label(f"{icons.get(data['state'],data['state'])} {data.get('text','')[:40]}")
                self.set_visible(True)
            except: pass
        else:
            self.set_visible(False)
        return True

def main():
    app=Gtk.Application(application_id="com.yawc.Pill")
    def on_activate(a):
        w=PillWindow()
        a.add_window(w)
    app.connect("activate", on_activate)
    app.run(None)

if __name__=="__main__": main()
