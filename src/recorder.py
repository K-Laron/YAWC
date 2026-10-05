#!/usr/bin/env python3
# ponytail: Recorder deep module — single owner of arecord + hold state file.
# Owns: mode file, arecord lifecycle, ALL pill states (sole writer — open item 4),
# polished->idle tail. Entry points choose name + on-release callback.
# Distinct `name` per entry = distinct /tmp files, so entries can't clobber.
import pathlib, subprocess, threading, time

import src.pill as pill


class Recorder:
    def __init__(self, name: str, on_release):
        self.mode = pathlib.Path(f"/tmp/yawc-{name}.hold")
        self.wav = pathlib.Path(f"/tmp/yawc-{name}.wav")
        self.on_release = on_release
        self.proc: subprocess.Popen | None = None
        self._gen = 0  # increments each begin; tail only idles if no newer hold
        self._lock = threading.Lock()
        self._busy = False  # True while release/transcription/cleanup is in flight

    def begin(self):
        with self._lock:
            # Reject if busy cleaning up previous utterance or already recording
            if self._busy:
                return
            if self.proc is not None and self.proc.poll() is None:
                return
            self._gen += 1
            self.mode.touch()
            pill.recording(1)
            self.proc = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", str(self.wav)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def release(self):
        """Hold ended: flush capture, run pipeline, render outcome tail.
        Atomic test-and-set ensures multi-node evdev releases cannot duplicate pipeline."""
        with self._lock:
            if self._busy or self.proc is None:
                return None
            self._busy = True
            proc = self.proc
            self.proc = None
            gen = self._gen
            self.mode.unlink(missing_ok=True)

        proc.terminate()  # SIGTERM lets arecord flush the wav on exit
        try:
            proc.wait(timeout=0.15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        result = None
        try:
            if self.wav.exists() and self.wav.stat().st_size > 44:
                pill.transcribing()
                result = self.on_release(str(self.wav))
        except Exception as e:
            print(f"[recorder] on_release failed: {e!r}", flush=True)
            result = None
        finally:
            try:
                self.wav.unlink(missing_ok=True)
            except Exception:
                pass
            pill.polished(result if result else "no audio")

            with self._lock:
                self._busy = False

            def _idle_tail():
                time.sleep(2)  # outcome flash duration
                with self._lock:
                    if self._gen == gen and self.proc is None and not self._busy:
                        pill.idle()

            threading.Thread(target=_idle_tail, daemon=True).start()

        return result

    def toggle(self):
        # 07 toggle mode: first call begins, second releases
        if self.proc is not None and self.proc.poll() is None:
            return self.release()
        self.begin()
        return None
