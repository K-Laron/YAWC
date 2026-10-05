I'm Kenneth. You're my agent. We'll be working together a lot, so I thought it'd be worth introducing myself. I like ambitious ideas, simple systems, and software that feels obvious. Do not preserve complexity just because it already exists. Do not introduce machinery because it looks architecturally impressive. Understand the real constraint, then fight for the smallest model that makes the correct behavior unsurprising.

YAWC (Yet Another Wispr Clone) is a local, 100% offline speech-to-text dictation daemon and formatter for CachyOS + niri + NVIDIA RTX 3050. Hold Right Alt, speak in English, Tagalog, or mid-sentence Taglish, release, and polished text appears in whatever application has focus.

You can think of YAWC as a zero-cloud, privacy-guaranteed personal Wispr Flow tuned specifically to one machine, where audio never leaves the box.

Here is a brief list of the things we can never compromise on:

### 1. Offline means offline
Audio and transcripts never leave this machine. After installation, speech recognition (STT) and LLM formatting run entirely on-device. `packaging/offline-proof.sh` must show zero non-loopback sockets. If a proposed feature requires internet access, it does not ship.

### 2. Taglish is first-class
Code-switching is not a translation problem. *"Punta tayo sa meeting tomorrow actually sa Friday na lang pala"* becomes *"Punta tayo sa meeting sa Friday na lang pala."* It drops cancelled plans, keeps the Taglish, and translates nothing. The do-not-translate eval gate must pass at $\ge 0.90$.

### 3. Strict 4GB VRAM ceiling
Tuned strictly for an NVIDIA RTX 3050 with 4GB VRAM. Heavy models or quantizations that spill into system RAM introduce stutter and destroy real-time latency.

### 4. One machine, deep modules
No multi-distro portability bloat or speculative abstraction layers. Every module hides internal complexity behind a tiny interface, and every performance claim has a measured number behind it.

---

## Operating rules

- **Questions are read-only.** If I ask about audio buffering, uinput hooks, or latency metrics, explain it. Do not alter files on question turns.
- **Match ceremony to the task.** Tune a prompt or adjust an injection threshold directly. No elaborate multi-agent review delegations for single-file tweaks.
- **Do not edit real components first.** When proposing new UI overlays or status pills, author a standalone HTML plan with Option A/B/C cards using `$html-communication` before modifying code.
- **Never open draft PRs.** Open real, non-draft PRs so automated CI and review bots trigger immediately.

---

## A small glossary
When communicating, use this language:

- **you** means the agent reading this file and modifying YAWC.
- **we, us, and maintainers** mean Kenneth and the people building YAWC.
- **user** means the human dictating into the machine.
- **daemon** means `yawc-daemon`, the resident process managing audio capture and hotkey triggers.
- **engine** means the local STT (Whisper/Moonshine) pipeline.
- **formatter** means the local LLM cleanup stage that handles punctuation, fillers, and backtracking.
- **injector** means the Wayland/uinput virtual keyboard module typing text into focused windows.

---

## The three ways to hurt yourself
1. **Leaking audio or telemetry.** Never add network sockets, remote error trackers, or cloud fallbacks. Any PR that opens a non-loopback socket fails immediately.
2. **Killing system audio by pattern.** Never `pkill -f python` or kill PipeWire/WirePlumber processes. Kill only the exact PID of `yawc-daemon`.
3. **Breaking Wayland input permissions.** Never substitute native uinput/ydotool injection with X11-only tools like `xdotool`.

---

## Hit every surface
Before declaring dictation work complete, verify:

- **Focused apps.** Does injection work properly in terminal emulators (kitty/alacritty), Electron apps (Slack/VS Code), and native GTK/Qt browsers?
- **Cancels & Backtracks.** Does releasing the key without speaking abort cleanly without leaving zombie audio buffers?
- **Taglish evaluation.** Did you verify the prompt against Taglish benchmarks in `eval/`?

---

## Dev servers & verification
- Start daemon locally: `./yawc-daemon --debug`
- Check offline isolation: `bash packaging/offline-proof.sh`
- Stop what you started, by the tracked PID.

### Verifying
- Smallest proof that the change works:
  - Unit tests: `pytest tests/test_<module>.py`
  - Eval benchmarks: `python eval/run_benchmarks.py --gate do-not-translate`
- **Do not run full evaluation sweeps** unless instructed.

---

## Pull requests
- Never make a PR unless I explicitly ask you to do so.
- Always branch off fresh `main`: `git checkout main && git pull origin main && git checkout -b feature/<task>`.
- Immediately call `link_pull_request` in T3 Code to register the PR with this thread.
- Conventional commit titles: `fix(formatter): preserve Tagalog clitics in negative constructions`.
- Body: the problem in a sentence or two, then how you fixed it. End with the model and harness.
- Visual/Audio proof: For UI overlay changes or latency fixes, record a short terminal demo video. Attach via `gh pr create --attach "/tmp/pr-media/..."`. Never commit binaries to git.
- One concern per PR. If the description says "also", split it.
- When babysitting (`$babysit`): poll checks and comments newer than the last push, verify each bot finding against source, fix real ones, dismiss false positives with a written reason. Stay quiet when nothing is new. Stop when bots are green on the latest commit.
