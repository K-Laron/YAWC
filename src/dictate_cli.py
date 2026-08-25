#!/usr/bin/env python3
# ponytail: argv-safe CLI for yawc-daemon dictate — wav path never spliced into source
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from src.dictation import Dictation, Utterance
from src import polish, injection

wav = sys.argv[1] if len(sys.argv) > 1 else "/tmp/live.wav"
d = Dictation(hotwords=polish.load_hotwords())
out = d.dictate(Utterance(wav_path=wav))
print(out)
if out:
    injection.inject(out, restore=True)
