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
/* class selectors: bare 'pill'/'wave' would match node names, not these classes */
.pill {
  background: rgba(12,12,14,0.88);
  color: #e8e8ea;
  border-radius: 9999px;
  padding: 9px 16px;
  font-size: 12px;
  border: 1px solid rgba(255,255,255,0.06);
  box-shadow: 0 4px 16px rgba(0,0,0,0.5);
}
.wave { background: white; border-radius: 2px; min-width: 3px; }
.timer { font-family: monospace; font-size: 10px; color: #77777f; }
.dim { color: #9a9aa2; font-size: 11px; }
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
        # pill content — small Wispr-like wave + dim label + timer (no mic)
        self.wave_bars = []
        self.wave_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        for _ in range(6):
            bar = Gtk.Box(); bar.add_css_class("wave"); bar.set_size_request(3, 8)
            self.wave_bars.append(bar)
            self.wave_box.append(bar)
        self.wave_box.set_visible(False)
        self.label = Gtk.Label(label="Listening")
        self.label.add_css_class("pill")
        self.label.add_css_class("dim")
        self.timer = Gtk.Label(label="00:00")
        self.timer.add_css_class("timer")
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # pill container — UX: wave + text + timer + spinner (no mic)
        pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pill_box.set_halign(Gtk.Align.CENTER)
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
        # ponytail: synthetic sine wave — real mic amplitude if fake reads wrong
        if self.wave_box.get_visible():
            import math
            self.tick += 1
            for i, bar in enumerate(self.wave_bars):
                h = 10 + 7 * math.sin(self.tick / 2.0 + i * 0.9)
                bar.set_size_request(3, max(4, int(h)))
        return True

    def update_timer(self):
        # UX: timer counts during recording like Wispr
        if self.wave_box.get_visible() and self.start_time:
            import time
            elapsed = int(time.time() - self.start_time)
            self.timer.set_label(f"{elapsed//60}:{elapsed%60:02d}")
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
                    self.label.set_label("Listening")
                    self.wave_box.set_visible(True); self.spinner.set_visible(False); self.spinner.stop()
                elif state=="transcribing":
                    self.start_time = 0
                    self.label.set_label("Transcribing")
                    self.wave_box.set_visible(False); self.spinner.set_visible(True); self.spinner.start()
                elif state=="polished":
                    self.start_time = 0
                    # UI only — hide transcript text, just show Done
                    self.label.set_label("✓ Done")
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
