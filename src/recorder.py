#!/usr/bin/env python3
# ponytail: Recorder deep module — single owner of arecord + hold state file.
# Owns: mode file, arecord lifecycle, ALL pill states (sole writer — open item 4),
# polished->idle tail. Entry points choose name + on-release callback.
# Distinct `name` per entry = distinct /tmp files, so entries can't clobber.
import contextlib, fcntl, os, pathlib, signal, subprocess, threading, time

import src.pill as pill


def _proc_token(pid: int) -> str | None:
    try:
        comm = pathlib.Path(f"/proc/{pid}/comm").read_text().strip()
        if "arecord" not in comm:
            return None
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
        rparen = stat.rfind(")")
        if rparen == -1:
            return None
        fields = stat[rparen + 1:].split()
        return f"{comm}:{fields[19]}"
    except Exception:
        return None


class Recorder:
    def __init__(self, name: str, on_release):
        self.mode = pathlib.Path(f"/tmp/yawc-{name}.hold")
        self.wav = pathlib.Path(f"/tmp/yawc-{name}.wav")
        self.pid_file = pathlib.Path(f"/tmp/yawc-{name}.pid")
        self.lock_file = pathlib.Path(f"/tmp/yawc-{name}.lock")
        self.busy_file = pathlib.Path(f"/tmp/yawc-{name}.busy")
        self.on_release = on_release
        self.proc: subprocess.Popen | None = None
        self._gen = 0  # increments each begin; tail only idles if no newer hold
        self._lock = threading.Lock()
        self._busy = False  # True while release/transcription/cleanup is in flight

    @contextlib.contextmanager
    def _flock(self):
        with open(self.lock_file, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _read_pid_token(self) -> tuple[int, str] | None:
        try:
            if not self.pid_file.exists():
                return None
            content = self.pid_file.read_text().strip()
            parts = content.split(":", 1)
            pid = int(parts[0])
            token = parts[1] if len(parts) > 1 else None
            curr_token = _proc_token(pid)
            if curr_token and (token is None or curr_token == token):
                return pid, curr_token
            self.pid_file.unlink(missing_ok=True)
            return None
        except Exception:
            self.pid_file.unlink(missing_ok=True)
            return None

    def begin(self):
        with self._lock, self._flock():
            # Reject if busy cleaning up previous utterance or already recording
            if self._busy or self.busy_file.exists():
                return
            if self.proc is not None and self.proc.poll() is None:
                return
            active = self._read_pid_token()
            if active is not None:
                return  # already recording in another process

            self._gen += 1
            self.mode.touch()
            pill.recording(1)
            self.proc = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", str(self.wav)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            token = _proc_token(self.proc.pid)
            try:
                self.pid_file.write_text(f"{self.proc.pid}:{token or ''}")
            except Exception:
                pass

    def release(self):
        """Hold ended: flush capture, run pipeline, render outcome tail.
        Captures state and marks busy under lock, then releases locks before
        stopping process or invoking on_release to avoid blocking caller event loops."""
        with self._lock, self._flock():
            if self._busy or self.busy_file.exists():
                return None
            proc = self.proc
            pid = None
            if proc is None:
                active = self._read_pid_token()
                if active is not None:
                    pid, _ = active

            if proc is None and pid is None:
                return None

            self._busy = True
            try:
                self.busy_file.touch()
            except Exception:
                pass
            self.proc = None
            gen = self._gen

        # Locks are now released; begin() or event loops can query state without blocking
        if proc is not None:
            proc.terminate()  # SIGTERM lets arecord flush the wav on exit
            try:
                proc.wait(timeout=0.15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        elif pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(15):
                    time.sleep(0.01)
                    os.kill(pid, 0)
            except OSError:
                pass  # process exited
            else:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

        result = None
        try:
            if self.wav.exists() and self.wav.stat().st_size > 44:
                pill.transcribing()
                result = self.on_release(str(self.wav))
        except Exception as e:
            print(f"[recorder] on_release failed: {e!r}", flush=True)
            result = None
        finally:
            self.pid_file.unlink(missing_ok=True)
            self.mode.unlink(missing_ok=True)
            self.busy_file.unlink(missing_ok=True)
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
                    if self._gen == gen and self.proc is None and not self._busy and not self.busy_file.exists():
                        pill.idle()

            threading.Thread(target=_idle_tail, daemon=True).start()

        return result

    def toggle(self):
        # 07 toggle mode: first call begins, second releases (cross-process aware)
        with self._flock():
            is_active = (self.proc is not None and self.proc.poll() is None) or (self._read_pid_token() is not None) or self.mode.exists() or self.busy_file.exists()
        if is_active:
            return self.release()
        self.begin()
        return None
