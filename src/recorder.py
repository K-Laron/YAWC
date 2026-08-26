#!/usr/bin/env python3
# ponytail: Recorder — the ONE hold->release capture state machine per 03/08.
# Owns: mode file, arecord lifecycle, ALL pill states (sole writer — open item 4),
# polished->idle tail. Entry points choose name + on-release callback.
# Distinct `name` per entry = distinct /tmp files, so entries can't clobber.
import pathlib, subprocess, time

import src.pill as pill


class Recorder:
    def __init__(self, name: str, on_release):
        """on_release(wav_path) -> result text (None = no usable audio)."""
        self.mode = pathlib.Path(f"/tmp/yawc-{name}.hold")
        self.wav = pathlib.Path(f"/tmp/yawc-{name}.wav")
        self.on_release = on_release
        self.proc: subprocess.Popen | None = None

    def begin(self):
        # One hold at a time: RIGHTALT fires on multiple evdev nodes — second node no-op
        if self.proc is not None and self.proc.poll() is None:
            return
        self.mode.touch()
        pill.recording(1)
        self.proc = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", str(self.wav)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def release(self):
        """Hold ended: flush capture, run pipeline, render outcome tail.
        No-op when a sibling node already released (multi-node RIGHTALT)."""
        if self.proc is None:
            return None
        self.proc.terminate()  # SIGTERM lets arecord flush the wav on exit
        try:
            self.proc.wait(timeout=0.15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc = None
        self.mode.unlink(missing_ok=True)
        result = None
        if self.wav.exists() and self.wav.stat().st_size > 44:
            pill.transcribing()
            result = self.on_release(str(self.wav))
        self.wav.unlink(missing_ok=True)
        pill.polished(result if result else "no audio")
        time.sleep(2)  # ponytail: outcome flash; shorten if it feels laggy
        pill.idle()
        return result

    def toggle(self):
        """Spawn-per-press entries: one process per key press."""
        if self.mode.exists():
            self.release()
        else:
            self.begin()
