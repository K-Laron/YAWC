// ponytail: Tauri tray stub — Phase 1 daemon, toggle mic when niri bind blocked
// Real STT/LLM in yawc-daemon (Python), this binary is tray fallback + autostart entry

fn main() {
    // ponytail: no window, tray only — add tauri::tray when needed
    println!("yawc tray — use yawc-daemon for dictation (CapsLock) and command (Ctrl+Win+Alt)");
    // keep process alive for systemd --user
    #[cfg(target_os = "linux")]
    {
        println!("niri msg windows: try `niri msg -j windows | jq .[].app_id`");
        println!("wtype + wl-copy injection verified in prototype/03-niri-injection/");
    }
}
