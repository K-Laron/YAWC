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
  background: rgba(15,23,42,0.92);
  color: white;
  border-radius: 9999px;
  padding: 12px 24px;
  font-size: 13pt;
  font-weight: 600;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 8px 24px rgba(0,0,0,0.6), 0 2px 8px rgba(0,0,0,0.4);
}
.recording { background: rgba(220,38,38,0.95); }
.transcribing { background: rgba(30,41,59,0.95); }
.polished { background: rgba(5,150,105,0.95); }
wave { background: white; border-radius: 2px; min-width: 3px; }
timer { font-family: monospace; font-size: 10pt; opacity: 0.9; }
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
        # pill content — Wispr-like: mic + waveform + text + timer (UX)
        self.icon = Gtk.Label(label="🎤")
        self.wave1 = Gtk.Box(); self.wave1.add_css_class("wave"); self.wave1.set_size_request(3, 8)
        self.wave2 = Gtk.Box(); self.wave2.add_css_class("wave"); self.wave2.set_size_request(3, 14)
        self.wave3 = Gtk.Box(); self.wave3.add_css_class("wave"); self.wave3.set_size_request(3, 10)
        self.wave_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.wave_box.append(self.wave1); self.wave_box.append(self.wave2); self.wave_box.append(self.wave3)
        self.wave_box.set_visible(False)
        self.label = Gtk.Label(label="Listening…")
        self.label.add_css_class("pill")
        self.timer = Gtk.Label(label="00:00")
        self.timer.add_css_class("timer")
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # pill container — UX: icon + wave + text + timer + spinner
        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pill_box.set_halign(Gtk.Align.CENTER)
        pill_box.append(self.icon)
        pill_box.append(self.wave_box)
        pill_box.append(self.label)
        pill_box.append(self.timer)
        pill_box.append(self.spinner)
        self.label_box = pill_box
        self.label_box.add_css_class("pill")
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer.set_halign(Gtk.Align.CENTER)
        outer.append(self.label_box)
        self.set_child(outer)
        self.present()
        self.tick = 0
        self.start_time = 0
        GLib.timeout_add(100, self.poll)
        GLib.timeout_add(150, self.animate_wave)
        GLib.timeout_add(200, self.update_timer)

    def animate_wave(self):
        if self.wave_box.get_visible():
            import random
            self.wave1.set_size_request(3, random.randint(6, 14))
            self.wave2.set_size_request(3, random.randint(10, 18))
            self.wave3.set_size_request(3, random.randint(6, 12))
            self.tick += 1
        return True

    def update_timer(self):
        # UX: timer counts during recording like Wispr
        if self.wave_box.get_visible() and self.start_time:
            import time
            elapsed = int(time.time() - self.start_time)
            self.timer.set_label(f"{elapsed//60:02d}:{elapsed%60:02d}")
            self.timer.set_visible(True)
        else:
            self.timer.set_visible(False)
        return True

    def poll(self):
        if STATE.exists():
            try:
                data=json.loads(STATE.read_text())
                state=data.get('state','idle')
                text=data.get('text','')[:50]
                if state=="recording":
                    if not self.start_time:
                        import time; self.start_time = time.time()
                    self.label.set_label("Listening…  release Right Alt to paste")
                    self.label_box.remove_css_class("transcribing"); self.label_box.remove_css_class("polished"); self.label_box.add_css_class("recording")
                    self.wave_box.set_visible(True); self.spinner.set_visible(False); self.spinner.stop()
                elif state=="transcribing":
                    self.start_time = 0
                    self.label.set_label("Transcribing…")
                    self.label_box.remove_css_class("recording"); self.label_box.remove_css_class("polished"); self.label_box.add_css_class("transcribing")
                    self.wave_box.set_visible(False); self.spinner.set_visible(True); self.spinner.start()
                elif state=="polished":
                    self.start_time = 0
                    self.label.set_label(text if text else "✓ Done")
                    self.label_box.remove_css_class("recording"); self.label_box.remove_css_class("transcribing"); self.label_box.add_css_class("polished")
                    self.wave_box.set_visible(False); self.spinner.set_visible(False); self.spinner.stop()
                else:
                    self.label.set_label(text)
                    self.wave_box.set_visible(False); self.spinner.set_visible(False)
                self.set_visible(True)
            except: pass
        else:
            self.start_time = 0
            self.timer.set_visible(False)
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
