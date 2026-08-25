#!/usr/bin/env python3
# ponytail: niri-bind entry — Right Alt hold via spawn-per-press, Recorder owns the rest
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from src.recorder import Recorder
from src.dictation import dictate_and_paste

if __name__ == "__main__":
    Recorder("toggle", on_release=dictate_and_paste).toggle()
