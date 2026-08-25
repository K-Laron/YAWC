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
