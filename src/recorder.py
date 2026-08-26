#!/usr/bin/env python3
# ponytail: Recorder — the ONE hold->release capture state machine per 03/08.
# Owns: mode file, arecord lifecycle, VRAM policy (release_llm at hold-start),
# pill states, polished->idle tail. Entry points choose name + on-release callback.
# Distinct `name` per entry = distinct /tmp files, so toggle and evdev can't clobber.
import pathlib, subprocess, time

import src.pill as pill
from src import polish


class Recorder:
    def __init__(self, name: str, on_release):
        """on_release(wav_path) -> pill text (or None for 'no audio')."""
        self.mode = pathlib.Path(f"/tmp/yawc-{name}.hold")
        self.wav = pathlib.Path(f"/tmp/yawc-{name}.wav")
        self.on_release = on_release

    def start(self):
        # LLM lifecycle lives in polish (port-health truth); daemons preload at startup
        self.mode.touch()
        self.mode.touch()
        pill.recording(1)
        subprocess.Popen(["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", str(self.wav)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        """Release: returns on_release result text, or None if no usable audio."""
        subprocess.run(["pkill", "-f", f"arecord.*{self.wav}"], stderr=subprocess.DEVNULL)
        time.sleep(0.2)
        self.mode.unlink(missing_ok=True)
        usable = self.wav.exists() and self.wav.stat().st_size > 44
        result = self.on_release(str(self.wav)) if usable else None
        self.wav.unlink(missing_ok=True)
        return result

    def finish(self, result):
        # pill tail: show outcome 2s, then hide
        pill.polished(result if result else "no audio")
        time.sleep(2)
        pill.idle()

    def toggle(self):
        """Spawn-per-press entries: one process per key press."""
        if self.mode.exists():
            self.finish(self.stop())
        else:
            self.start()
