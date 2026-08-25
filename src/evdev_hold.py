#!/usr/bin/env python3
# ponytail: resident evdev entry — Right Alt hold, Recorder owns capture lifecycle.
# Resident loop = STT model stays hot across utterances (08) — this is the fast path.
import asyncio, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import evdev

from src.recorder import Recorder
from src.dictation import dictate_and_paste

# 100/108 = KEY_RIGHTALT aliases on some keyboards; "Keyboard"/"Rapoo" filters
# this machine's devices (map: optimized for this machine only)
KEYS = [evdev.ecodes.KEY_RIGHTALT, 100, 108]


def get_kb_devices():
    devs = []
    for p in evdev.list_devices():
        dev = evdev.InputDevice(p)
        keys = dev.capabilities().get(evdev.ecodes.EV_KEY, [])
        if any(k in keys for k in KEYS):
            if "Rapoo" in dev.name or "Keyboard" in dev.name:
                devs.append(dev)
    return devs


async def handle_device(dev: evdev.InputDevice, rec: Recorder):
    print(f"grabbing {dev.path} {dev.name}", flush=True)
    holding = False
    async for event in dev.async_read_loop():
        if event.type != evdev.ecodes.EV_KEY or event.code not in KEYS:
            continue
        if event.value == 1 and not holding:
            holding = True
            print("HOLD start", dev.path, flush=True)
            rec.start()
        elif event.value == 0 and holding:
            holding = False
            print("HOLD release", dev.path, flush=True)
            result = await asyncio.to_thread(rec.stop)  # STT+LLM off the evdev loop
            await asyncio.to_thread(rec.finish, result)


async def main():
    rec = Recorder("evdev", on_release=dictate_and_paste)
    devs = get_kb_devices()
    if not devs:
        print("no kb with RIGHTALT (input group? Rapoo filter?)", flush=True)
        return
    print(f"found {len(devs)} kb devices", flush=True)
    for d in devs:
        print(f"  {d.path} {d.name}", flush=True)
    await asyncio.gather(*(handle_device(d, rec) for d in devs))


if __name__ == "__main__":
    asyncio.run(main())
