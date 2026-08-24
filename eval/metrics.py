# ponytail: metrics stub per 07 — jiwer WER/CER, normalize_tl hyphen tolerant
import re, unicodedata
def normalize_tl(t): 
    t=unicodedata.normalize("NFC",t).lower()
    t=re.sub(r"[\u2010-\u2015\-]"," ",t)
    t=re.sub(r"[^\w\s']","",t)
    return re.sub(r"\s+"," ",t).strip()
def normalize_en(t):
    t=unicodedata.normalize("NFC",t).lower()
    return re.sub(r"\s+"," ",re.sub(r"[^\w\s']","",t)).strip()
