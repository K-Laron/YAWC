# ponytail: metrics stub per 07 — jiwer WER/CER, normalize_tl hyphen tolerant
import re, unicodedata
def normalize_tl(t): 
    t=unicodedata.normalize("NFC",t).lower()
    t=re.sub(r"[\u2010-\u2015\-]"," ",t)
    t=re.sub(r"[^\w\s']","",t)
    return re.sub(r"\s+"," ",t).strip()
def normalize_en(t):
    t=unicodedata.normalize("NFC",t).lower()
    t=re.sub(r"[^\w\s']","",t)
    # digits/number words, contractions, compound spellings: same token for WER
    eq={"zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5",
        "six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
        "i'm":"i am","i've":"i have","i'll":"i will","let's":"let us",
        "don't":"do not","can't":"cannot","won't":"will not",
        "it's":"it is","that's":"that is","we're":"we are",
        "you're":"you are","they're":"they are","isn't":"is not",
        "backup":"back up","checkout":"check out"}
    t=" ".join(eq.get(w,w) for w in t.split())
    return re.sub(r"\s+"," ",t).strip()

# 07 gates: do-not-translate (TL->EN hallucination) + kamag-anak/hanggang-ngayon boundary
TAGALOG_STOP = {"ako","ikaw","siya","kami","tayo","kayo","sila","nasa","sa","ng",
                "ang","mga","na","ay","hindi","huwag","po","opo","yung","kung",
                "kamag","anak","hanggang","ngayon","kapatid","kasama","punta"}
BOUNDARY_PHRASES = ["kamag anak", "hanggang ngayon"]

def dnt_rate(rows, hyps):
    """Pass rate: tl/taglish refs with >=2 Tagalog stop words keep >=1 in hyp.
    Zero Tagalog tokens left = translation hallucination. Gate >=0.90."""
    flags = checked = 0
    for r, h in zip(rows, hyps):
        if r["language"] not in ("tl", "taglish"):
            continue
        checked += 1
        ref = normalize_tl(r["reference"]).split()
        hyp_w = normalize_tl(h).split()
        if sum(w in TAGALOG_STOP for w in ref) >= 2:
            if not any(w in TAGALOG_STOP for w in hyp_w):
                flags += 1
    return 1 - flags / max(1, checked)

def boundary_check(rows, hyps):
    """Rate of boundary phrases surviving normalization in hyp when present in
    reference. Gate >=0.75 per research/07."""
    checks = []
    for r, h in zip(rows, hyps):
        nr, nh = normalize_tl(r["reference"]), normalize_tl(h)
        for p in BOUNDARY_PHRASES:
            if p in nr:
                checks.append((r["id"], p, p in nh))
    return {"pass": sum(1 for _, _, ok in checks if ok),
            "total": len(checks),
            "rate": (sum(1 for *_, ok in checks if ok) / len(checks)) if checks else None,
            "details": checks}
