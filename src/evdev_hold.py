#!/usr/bin/env python3
# ponytail: resident evdev entry — Right Alt hold, Recorder owns capture lifecycle
# AND all pill rendering. Supervisor: USB receivers re-enumerate (device churn kills
# read streams silently); rescan every 5s, respawn handlers, never exit on death.
import asyncio, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import evdev

from src.recorder import Recorder
from src.dictation import dictate_and_paste
from src import polish

# 100/108 = KEY_RIGHTALT aliases on some keyboards; "Keyboard"/"Rapoo" filters
# this machine's devices (map: optimized for this machine only)
KEYS = [evdev.ecodes.KEY_RIGHTALT, 100, 108]


def get_kb_devices():
    devs = []
    for p in evdev.list_devices():
        try:
            dev = evdev.InputDevice(p)
            keys = dev.capabilities().get(evdev.ecodes.EV_KEY, [])
            if any(k in keys for k in KEYS):
                if "Rapoo" in dev.name or "Keyboard" in dev.name:
                    devs.append(dev)
        except OSError:
            continue  # node vanished mid-scan (churn) — skip
    return devs


async def handle_device(dev: evdev.InputDevice, rec: Recorder):
    print(f"grabbing {dev.path} {dev.name}", flush=True)
    holding = False
    try:
        async for event in dev.async_read_loop():
            if event.type != evdev.ecodes.EV_KEY or event.code not in KEYS:
                continue
            if event.value == 1 and not holding:
                holding = True
                print("HOLD start", dev.path, flush=True)
                rec.begin()
            elif event.value == 0 and holding:
                holding = False
                print("HOLD release", dev.path, flush=True)
                await asyncio.to_thread(rec.release)  # pipeline + pill tail off the loop
    except Exception as e:
        print(f"stream ended {dev.path}: {e!r}", flush=True)
    if holding:
        # ponytail: died mid-hold (unplug) — truncated audio still runs the full
        # pipeline; gate on min wav duration here if that ever pastes junk
        await asyncio.to_thread(rec.release)
    print(f"handler exit {dev.path}", flush=True)


async def main():
    # preload LLM once — weights load while the daemon idles, polish is warm forever
    await asyncio.to_thread(polish.preload_llm)
    rec = Recorder("evdev", on_release=dictate_and_paste)
    tasks: dict[str, asyncio.Task] = {}
    while True:
        for dev in get_kb_devices():
            if dev.path not in tasks or tasks[dev.path].done():
                tasks[dev.path] = asyncio.create_task(handle_device(dev, rec))
        tasks = {p: t for p, t in tasks.items() if not t.done()}
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
