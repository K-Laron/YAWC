# 06 — Personal Dictionary, Snippets, Hotwords

> Ticket: [wayfinder/issues/06-personal-dictionary-hotwords.md](../wayfinder/issues/06-personal-dictionary-hotwords.md)
> Decision: **JSON files + hotwords/initial_prompt injection, no DB**

## Storage

```
~/.config/yawc/dictionary.json   # hotwords
~/.config/yawc/snippets.json     # cue → expand
```

**dictionary.json schema:**
```json
[
  {"term":"Priya","hint":"Priya","lang":"en","scope":"global","weight":1.0},
  {"term":"kamag-anak","hint":"kamag anak","lang":"tl","scope":"global"},
  {"term":"hanggang ngayon","hint":"hanggang ngayon","lang":"tl","scope":"global"}
]
```
**snippets.json:**
```json
{"add disclaimer":"This message is confidential and intended only for the recipient.","brb":"Be right back — saglit lang."}
```

No SQLite — ponytail: JSON, grep-able, git-syncable. Import via `yawc dict import team.json`.

## Application

- **STT:** `faster-whisper` `hotwords="Priya kamag-anak hanggang ngayon"` (1.0.2+ PR731) + `initial_prompt="Kamusta! Priya, kamag-anak, hanggang ngayon — Taglish, do not translate."` per 01. Max 448 tokens.
- **LLM:** same terms injected into 02 system prompt proper-noun list.
- **Whisper.cpp fallback:** `prompt` param same string.

Code snippet:
```python
import json
d=json.load(open("~/.config/yawc/dictionary.json"))
hotwords=" ".join(x["term"] for x in d)
model.transcribe(wav, hotwords=hotwords, initial_prompt=",".join(hotwords)+" — Taglish, do not translate.")
```

Tagalog `ng` clusters boosted via hotwords weight 1.0 + initial_prompt phrase.

## Learning Loop

- Manual: `yawc dict add "Priya"` or Settings → Dictionary → Add.
- Auto-learn: if user undoes AI polish and types `kapatid` over `kasama` → toast `Add "kapatid" to dictionary? [Yes/No]` → on Yes append to JSON, next STT uses hotwords instantly (no retrain).
- Scope: default global; per-app scope via `"scope":"helium"` only for email names, else global to avoid EN/TL pollution (TL terms not applied when `language=en` prob >0.9).

## Sync

Local-only Phase 1; `dictionary.json` is plain text → `git` sync for team import: `yawc dict import --merge team.json`. No cloud.

## Done Test

Add `Priya` → `hotwords` includes it → `transcribe("kumusta Priya")` never returns `Priya`→`pria`.

