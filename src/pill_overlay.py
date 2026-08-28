#!/usr/bin/env python3
# ponytail: pill overlay — GTK4 layer-shell on any app (niri OVERLAY, top 20)
# Writes via src/pill.py /tmp/yawc-pill.state, this overlay renders it above any app
import gi, os, sys, time, pathlib
# LD_PRELOAD workaround for gtk4-layer-shell link order per warning
if "LD_PRELOAD" not in os.environ or "gtk4-layer-shell" not in os.environ["LD_PRELOAD"]:
    os.environ["LD_PRELOAD"] = "/usr/lib/libgtk4-layer-shell.so:" + os.environ.get("LD_PRELOAD","")

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from src import pill as pill_state

gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gtk4LayerShell, GLib

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
        # pill content — Wispr-like wave: 7 bars, some long some short, not uniform
        self.wave_bars = []
        self.wave_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.wave_box.set_valign(Gtk.Align.CENTER)
        for _ in range(7):
            bar = Gtk.Box(); bar.add_css_class("wave"); bar.set_size_request(3, 10)
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
        GLib.timeout_add(50, self.poll)
        GLib.timeout_add(33, self.animate_wave)
        GLib.timeout_add(200, self.update_timer)

    def _mic_level(self):
        # ponytail: read live wav tail for real amplitude; fallback to None -> synthetic
        try:
            import pathlib, struct, math
            # evdev is the hot path; check any yawc wav if evdev missing (toggle/cmd)
            cands = sorted(pathlib.Path("/tmp").glob("yawc-*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
            p = cands[0] if cands else None
            if not p or not p.exists() or p.stat().st_size <= 48:
                return None
            size = p.stat().st_size
            with open(p, "rb") as f:
                f.seek(max(44, size - 4096))
                data = f.read()
            n = len(data) // 2
            if n < 64:
                return None
            samples = struct.unpack(f"<{n}h", data[: n * 2])
            rms = math.sqrt(sum(s * s for s in samples) / n) / 32768.0
            return min(1.0, rms * 5.0)  # boost quiet mics; ponytail: tune 5.0 if wave feels flat/loud
        except Exception:
            return None

    def animate_wave(self):
        if self.wave_box.get_visible():
            import math
            self.tick += 1
            level = self._mic_level()
            if level is None:
                level = 0.35
            for i, bar in enumerate(self.wave_bars):
                # phase spread so adjacent bars are out of sync -> some long, some short
                phase = self.tick * 0.55 + i * 0.95
                h = 6 + level * 12 + 8 * math.sin(phase) * (0.5 + level * 0.7)
                # second harmonic staggers neighbors so not all peak together
                h += 3 * math.sin(phase * 1.6 + i * 0.8) * (0.4 + level * 0.5)
                bar.set_size_request(3, max(5, int(h)))
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
        # dumb renderer: intents come from pill.ui_for (pure, tested in tests/)
        ui = pill_state.ui_for(pill_state.parse())
        self.set_visible(ui["visible"])
        if not ui["visible"]:
            self.start_time = 0
            self.timer.set_visible(False)
            return True
        self.label.set_label(ui["label"])
        self.wave_box.set_visible(ui["wave"])
        self.spinner.set_visible(ui["spinner"])
        if ui["spinner"]:
            self.spinner.start()
        else:
            self.spinner.stop()
        if ui["timer"] and not self.start_time:
            self.start_time = time.time()
        elif not ui["timer"]:
            self.start_time = 0
            self.timer.set_visible(False)
        return True

def main():
    app=Gtk.Application(application_id="com.yawc.Pill")
    def on_activate(a):
        w=PillWindow()
        a.add_window(w)
    app.connect("activate", on_activate)
    app.run(None)

if __name__=="__main__": main()
