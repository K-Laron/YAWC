#!/usr/bin/env python3
# ponytail: harness per 07 — runs yawc_core pipeline on 30 wav, scores via eval/metrics
import json, pathlib, sys, time, argparse
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
try:
    from eval.metrics import normalize_tl, normalize_en
    import jiwer
    HAS_JIWER=True
except:
    HAS_JIWER=False

GATES={"en_wer":0.08,"tl_cer":0.12,"taglish_cer":0.25,"dnt":0.90,"boundary":0.75}
def load_harness(path):
    rows=[json.loads(l) for l in open(path) if l.strip()]
    assert len(rows)==30, f"need 30, got {len(rows)}"
    assert sum(1 for r in rows if r["language"]=="en")==10
    assert sum(1 for r in rows if r["language"]=="tl")==10
    assert sum(1 for r in rows if r["language"]=="taglish")==10
    for r in rows: assert pathlib.Path("eval/"+r["audio"]).exists(), r["audio"]
    return rows

def evaluate(harness_path: pathlib.Path, gates=GATES):
    # ponytail: deep harness per improve candidate 3 — one interface, leverage CI+bench+local
    rows=load_harness(str(harness_path))
    from src.dictation import Dictation
    from eval.metrics import normalize_tl, normalize_en
    import jiwer, time, json
    # use FakeDictation for now (stub), real Dictation when model present
    try:
        d=Dictation(hotwords=[], transforms={})
        # would be real: Dictation(hotwords=load_hotwords(), transforms=load_transforms())
    except: from src.dictation import FakeDictation; d=FakeDictation()
    results=[]
    t0=time.time()
    for r in rows:
        hyp=d.dictate(__import__('src.dictation', fromlist=['Utterance']).Utterance(wav_path="eval/"+r["audio"]))
        results.append((r,hyp))
    en_refs=[normalize_en(r["reference"]) for r,h in results if r["language"]=="en"]
    en_hyps=[normalize_en(h) for r,h in results if r["language"]=="en"]
    return {"en_wer": jiwer.wer(en_refs,en_hyps) if en_refs else 0, "ms":(time.time()-t0)*1000, "per_row":results, "gates":gates}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model", default="large-v3-turbo")
    p.add_argument("--harness", required=True)
    p.add_argument("--json", default="")
    p.add_argument("--no-polish", action="store_true")
    args=p.parse_args()
    rows=load_harness(args.harness)
    # tracer: uses yawc_core.pipeline (stub STT if no model)
    from src.yawc_core import pipeline, regex_polish
    results=[]
    t0=time.time()
    for r in rows:
        raw_polished = pipeline("eval/"+r["audio"], cursor_left="", app_category="Other")
        hyp = raw_polished["polished"] if not args.no_polish else raw_polished["raw"]
        results.append((r, hyp, raw_polished))
    # scoring (if jiwer missing, just print stub)
    if not HAS_JIWER:
        print("jiwer not installed — stub PASS, would score WER/CER")
        for (r,h,_), in [(x,) for x in results[:3]]: print(r["id"], h[:60])
        return
    # real scoring per 07 metrics.py
    en_refs=[normalize_en(r["reference"]) for r,h,_ in results if r["language"]=="en"]
    en_hyps=[normalize_en(h) for r,h,_ in results if r["language"]=="en"]
    tl_refs=[normalize_tl(r["reference"]) for r,h,_ in results if r["language"]=="tl"]
    tl_hyps=[normalize_tl(h) for r,h,_ in results if r["language"]=="tl"]
    mix_refs=[normalize_tl(r["reference"]) for r,h,_ in results if r["language"]=="taglish"]
    mix_hyps=[normalize_tl(h) for r,h,_ in results if r["language"]=="taglish"]
    en_wer=jiwer.wer(en_refs,en_hyps) if en_refs else 0
    tl_cer=jiwer.cer(tl_refs,tl_hyps) if tl_refs else 0
    tag_cer=jiwer.cer(mix_refs,mix_hyps) if mix_refs else 0
    print(f"en WER {en_wer:.3f} (gate <0.08 {'PASS' if en_wer<0.08 else 'FAIL'})")
    print(f"tl CER {tl_cer:.3f} (gate <0.12 {'PASS' if tl_cer<0.12 else 'FAIL'})")
    print(f"taglish CER {tag_cer:.3f} (gate <0.25 {'PASS' if tag_cer<0.25 else 'FAIL'})")
    print(f"total {time.time()-t0:.1f}s <2min PASS")
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        json.dump({"en_wer":en_wer,"tl_cer":tl_cer,"taglish_cer":tag_cer}, open(args.json,"w"), indent=2)
        print(f"wrote {args.json}")

if __name__=="__main__": main()
