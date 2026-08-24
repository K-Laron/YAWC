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
pill {
  background: #0f172a;
  color: white;
  border-radius: 9999px;
  padding: 10px 20px;
  font-size: 14pt;
  font-weight: 600;
  border: 1px solid #334155;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
.recording { background: #dc2626; }
.transcribing { background: #1e293b; }
.polished { background: #059669; }
"""

class PillWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="YAWC Pill")
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 40)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        self.set_decorated(False)
        self.set_resizable(False)
        # pill content — actual UI: icon + text in rounded pill
        self.label = Gtk.Label(label="○ YAWC")
        self.label.add_css_class("pill")
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        box.append(self.spinner)
        box.append(self.label)
        self.set_child(box)
        self.present()
        GLib.timeout_add(100, self.poll)

    def poll(self):
        if STATE.exists():
            try:
                data=json.loads(STATE.read_text())
                icons={"idle":"○","recording":"● REC","transcribing":"◐","polished":"✓","error":"✕"}
                state=data.get('state','idle')
                self.label.set_label(f"{icons.get(state,state)} {data.get('text','')[:40]}")
                # actual UI: color per state + spinner
                self.label.remove_css_class("recording"); self.label.remove_css_class("transcribing"); self.label.remove_css_class("polished")
                if state=="recording": self.label.add_css_class("recording"); self.spinner.set_visible(True); self.spinner.start()
                elif state=="transcribing": self.label.add_css_class("transcribing"); self.spinner.set_visible(True); self.spinner.start()
                elif state=="polished": self.label.add_css_class("polished"); self.spinner.set_visible(False); self.spinner.stop()
                else: self.spinner.set_visible(False); self.spinner.stop()
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
