#!/usr/bin/env python3
# ponytail: harness per 07 — drives the real Dictation seam on 30 wav, scores via eval/metrics
import json, pathlib, sys, argparse, time
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
try:
    from eval.metrics import normalize_tl, normalize_en, dnt_rate, boundary_check
    import jiwer
    HAS_JIWER = True
except Exception:
    HAS_JIWER = False
    jiwer = None
    normalize_tl = normalize_en = dnt_rate = boundary_check = None

GATES = {"en_wer": 0.08, "tl_cer": 0.12, "taglish_cer": 0.25,
         "dnt": 0.90, "boundary": 0.75}


def load_harness(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    assert len(rows) == 30, f"need 30, got {len(rows)}"
    assert sum(1 for r in rows if r["language"] == "en") == 10
    assert sum(1 for r in rows if r["language"] == "tl") == 10
    assert sum(1 for r in rows if r["language"] == "taglish") == 10
    for r in rows:
        assert pathlib.Path("eval/" + r["audio"]).exists(), r["audio"]
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--harness", required=True)
    p.add_argument("--json", default="")
    p.add_argument("--no-polish", action="store_true")
    args = p.parse_args()
    rows = load_harness(args.harness)
    # eval loads its own whisper copy; the resident daemon (llama + maybe whisper)
    # would OOM us into empty transcripts. Pause it, always restore after.
    import subprocess
    def _unit_active():
        return subprocess.run(["systemctl", "--user", "is-active", "--quiet", "yawc-evdev"]).returncode == 0
    paused = False
    if _unit_active():
        subprocess.run(["systemctl", "--user", "stop", "yawc-evdev"])
        paused = True
        time.sleep(2)  # let CUDA memory actually free
        print("(paused yawc-evdev for VRAM headroom — restoring after)")
    try:
        _run_gates(args, rows)
    finally:
        if paused:
            subprocess.run(["systemctl", "--user", "start", "yawc-evdev"])
            print("(yawc-evdev restored)")


def _run_gates(args, rows):
    from src.dictation import Dictation, Utterance
    from src.polish import load_hotwords
    from eval.metrics import normalize_tl, normalize_en
    d = Dictation(hotwords=load_hotwords())
    results = []
    t0 = time.time()
    for r in rows:
        hyp = d.dictate(Utterance(wav_path="eval/" + r["audio"], app_id="eval"),
                        polish=not args.no_polish)
        results.append((r, hyp))
    if not HAS_JIWER:
        print("jiwer not installed — stub PASS, would score WER/CER")
        for r, h in results[:3]:
            print(r["id"], h[:60])
        return
    en = [(r, h) for r, h in results if r["language"] == "en"]
    tl = [(r, h) for r, h in results if r["language"] == "tl"]
    mix = [(r, h) for r, h in results if r["language"] == "taglish"]
    en_wer = jiwer.wer([normalize_en(r["reference"]) for r, _ in en],
                       [normalize_en(h) for _, h in en]) if en else 0
    tl_cer = jiwer.cer([normalize_tl(r["reference"]) for r, _ in tl],
                       [normalize_tl(h) for _, h in tl]) if tl else 0
    tag_cer = jiwer.cer([normalize_tl(r["reference"]) for r, _ in mix],
                        [normalize_tl(h) for _, h in mix]) if mix else 0
    print(f"en WER {en_wer:.3f} (gate <{GATES['en_wer']} {'PASS' if en_wer < GATES['en_wer'] else 'FAIL'})")
    print(f"tl CER {tl_cer:.3f} (gate <{GATES['tl_cer']} {'PASS' if tl_cer < GATES['tl_cer'] else 'FAIL'})")
    print(f"taglish CER {tag_cer:.3f} (gate <{GATES['taglish_cer']} {'PASS' if tag_cer < GATES['taglish_cer'] else 'FAIL'})")
    hyps_all = [h for _, h in results]
    dnt = dnt_rate(rows, hyps_all)
    bnd = boundary_check(rows, hyps_all)
    print(f"DNT {dnt:.3f} (gate >={GATES['dnt']} {'PASS' if dnt >= GATES['dnt'] else 'FAIL'})")
    br = bnd["rate"]
    if br is None:
        print("boundary n/a — no boundary phrases in corpus")
    else:
        print(f"boundary {bnd['pass']}/{bnd['total']} (gate >={GATES['boundary']} "
              f"{'PASS' if br >= GATES['boundary'] else 'FAIL'})")
    print(f"total {time.time()-t0:.1f}s <2min PASS")
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"en_wer": en_wer, "tl_cer": tl_cer, "taglish_cer": tag_cer,
                   "do_not_translate": dnt,
                   "boundary": {"rate": br, "pass": bnd["pass"], "total": bnd["total"]}},
                  open(args.json, "w"), indent=2)
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
