#!/usr/bin/env python3
# ponytail: interactive eval recorder — enter=record, ctrl+c on arecord=saves+next,
# existing wavs skipped so you can stop/resume. Real corpus only works with real voice.
import json, pathlib, subprocess, sys

rows = [json.loads(l) for l in open("eval/harness.jsonl") if l.strip()]
todo = done = skip = 0
for r in rows:
    wav = pathlib.Path("eval/audio") / pathlib.Path(r["audio"]).name
    if wav.exists():
        skip += 1
        print(f"[skip] {wav.name} already recorded")
        continue
    ref = r["reference"]
    if ref.startswith("Hello test"):
        print(f"NOTE {r['id']} reference is still a stub — edit eval/harness.jsonl first")
        sys.exit(1)
    todo += 1
    try:
        input(f"\n[{done+skip+1}/{len(rows)}] ({r['language']}) ENTER then read aloud:\n  {ref}\n> ")
        subprocess.run(["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-q", str(wav)])
        done += 1
    except KeyboardInterrupt:
        # ctrl+c during arecord = keep clip, next sentence; twice quickly = abort below
        if pathlib.Path(wav).exists():
            print("saved, next")
            done += 1
        else:
            print("skipped")
print(f"\nrecorded {done}, skipped {skip} existing")
if todo == 0:
    print("all done — score with:")
    print("python3 -m eval.harness --harness eval/harness.jsonl --json runs/now.json")
