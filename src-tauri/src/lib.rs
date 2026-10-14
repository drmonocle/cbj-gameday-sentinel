use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager,
};
use tauri_plugin_opener::OpenerExt;

/// Whether closing the main window hides it to the tray (true) or quits the app (false).
static CLOSE_TO_TRAY: AtomicBool = AtomicBool::new(true);

#[tauri::command]
fn show_main(app: tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

#[tauri::command]
fn hide_main(app: tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.hide();
    }
}

#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    app.exit(0);
}

#[tauri::command]
fn set_close_to_tray(enabled: bool) {
    CLOSE_TO_TRAY.store(enabled, Ordering::Relaxed);
}

/// Shows a native desktop notification (goal alerts, puck drop reminders).
#[tauri::command]
fn send_notification(app: tauri::AppHandle, title: String, body: String) {
    use tauri_plugin_notification::NotificationExt;
    let _ = app.notification().builder().title(title).body(body).show();
}

/// Strict whitelist of permitted API domains to prevent SSRF and internal LAN probing.
fn is_allowed_api_host(host: &str) -> bool {
    let h = host.to_ascii_lowercase();
    // Deny local/private IP addresses or loopback
    if h == "localhost"
        || h == "127.0.0.1"
        || h == "::1"
        || h.starts_with("192.168.")
        || h.starts_with("10.")
        || h.starts_with("172.")
        || h.starts_with("169.254.")
    {
        return false;
    }

    // Strictly permitted sports data domains
    h == "api-web.nhle.com"
        || h == "assets.nhle.com"
        || h == "wsr.nhle.com"
        || h.ends_with(".nhle.com")
        || h.ends_with(".d3.nhle.com")
        || h.ends_with(".espn.com")
        || h.ends_with(".espncdn.com")
        || h.ends_with(".reddit.com")
        || h == "api.github.com"
}

/// Strict whitelist of permitted external browser navigation URLs.
fn is_allowed_external_url(parsed: &url::Url) -> bool {
    if parsed.scheme() != "https" {
        return false;
    }
    let host = match parsed.host_str() {
        Some(h) => h.to_ascii_lowercase(),
        None => return false,
    };
    if host == "localhost"
        || host == "127.0.0.1"
        || host == "::1"
        || host.starts_with("192.168.")
        || host.starts_with("10.")
    {
        return false;
    }

    host == "nhl.com"
        || host.ends_with(".nhl.com")
        || host == "espn.com"
        || host.ends_with(".espn.com")
        || host == "amazon.com"
        || host.ends_with(".amazon.com")
        || host == "reddit.com"
        || host.ends_with(".reddit.com")
        || host == "youtube.com"
        || host.ends_with(".youtube.com")
        || host == "github.com"
        || host.ends_with(".github.com")
}

/// Adds or removes the application from the current user's Windows startup list.
#[tauri::command]
fn set_autostart(enabled: bool) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        const RUN_KEY: &str = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run";

        let mut cmd = std::process::Command::new("reg");
        if enabled {
            let exe = std::env::current_exe().map_err(|e| e.to_string())?;
            let exe_str = exe.to_string_lossy();
            if exe_str.contains('"') || exe_str.contains('\n') || exe_str.contains('\r') {
                return Err("Security Violation: Executable path contains illegal characters".into());
            }
            let value = format!("\"{}\" --minimized", exe_str);
            cmd.args(["add", RUN_KEY, "/v", "CBJGamedaySentinel", "/t", "REG_SZ", "/d", &value, "/f"]);
        } else {
            cmd.args(["delete", RUN_KEY, "/v", "CBJGamedaySentinel", "/f"]);
        }
        let status = cmd
            .creation_flags(CREATE_NO_WINDOW)
            .status()
            .map_err(|e| e.to_string())?;
        if enabled && !status.success() {
            return Err("Could not add CBJ Gameday Sentinel to Windows startup".into());
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = enabled;
    }
    Ok(())
}

fn get_appdata_dir() -> PathBuf {
    if let Some(appdata) = std::env::var_os("APPDATA") {
        PathBuf::from(appdata).join("CBJGamedaySentinel")
    } else {
        PathBuf::from(".").join("CBJGamedaySentinel")
    }
}

/// Loads settings from %APPDATA%\CBJGamedaySentinel\settings.json with size validation.
#[tauri::command]
fn load_settings() -> Result<serde_json::Value, String> {
    let path = get_appdata_dir().join("settings.json");
    if path.exists() {
        if let Ok(meta) = std::fs::metadata(&path) {
            if meta.len() > 65536 {
                return Err("Security Violation: Settings file exceeds 64KB safety limit".into());
            }
        }
        match std::fs::read_to_string(&path) {
            Ok(content) => match serde_json::from_str(&content) {
                Ok(json) => Ok(json),
                Err(e) => Err(format!("Malformed settings.json: {}", e)),
            },
            Err(e) => Err(format!("Failed to read settings: {}", e)),
        }
    } else {
        Ok(serde_json::json!({}))
    }
}

/// Saves settings atomically to %APPDATA%\CBJGamedaySentinel\settings.json with size enforcement.
#[tauri::command]
fn save_settings(settings: serde_json::Value) -> Result<(), String> {
    if !settings.is_object() {
        return Err("Security Violation: Settings must be a JSON object".into());
    }
    let content = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    if content.len() > 65536 {
        return Err("Security Violation: Settings payload exceeds 64KB safety limit".into());
    }
    let dir = get_appdata_dir();
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("settings.json");
    let tmp_path = dir.join("settings.json.tmp");
    std::fs::write(&tmp_path, &content).map_err(|e| e.to_string())?;
    std::fs::rename(&tmp_path, &path).map_err(|e| e.to_string())
}

/// Opens a web link in the user's default browser after strict URL validation and domain whitelisting.
#[tauri::command]
fn open_external_url(app: tauri::AppHandle, url: String) -> Result<(), String> {
    let parsed = url::Url::parse(url.trim()).map_err(|e| format!("Invalid URL: {}", e))?;
    if !is_allowed_external_url(&parsed) {
        return Err(format!("Security Violation: Blocked external link to '{}'", url));
    }
    app.opener().open_url(parsed.as_str(), None::<&str>).map_err(|e| e.to_string())
}

/// Native HTTPS proxy bypassing browser CORS with SSRF protection, argument injection immunity, and size caps.
#[tauri::command]
fn fetch_url(url: String) -> Result<String, String> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;

        let parsed = url::Url::parse(url.trim()).map_err(|e| format!("Invalid URL: {}", e))?;
        if parsed.scheme() != "https" {
            return Err("Security Violation: Only https:// URLs are permitted".into());
        }

        let host = parsed.host_str().ok_or_else(|| "URL has no valid host".to_string())?;
        if !is_allowed_api_host(host) {
            return Err(format!("Security Violation: Host '{}' is not in the allowed API whitelist", host));
        }

        let clean_url = parsed.to_string();

        let output = Command::new("curl.exe")
            .args([
                "-L", "-s", "-S",
                "--proto", "=https",
                "--proto-redir", "=https",
                "--max-time", "15",
                "--max-filesize", "15728640", // 15 MB cap prevents memory exhaustion
                "-H", "User-Agent: CBJGamedaySentinel/2.0",
                "-H", "Accept: application/json, text/plain, */*",
                "--",
                clean_url.as_str(),
            ])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
            .map_err(|e| format!("Failed to spawn curl.exe: {}", e))?;

        if output.status.success() {
            let text = String::from_utf8_lossy(&output.stdout).to_string();
            let clean = text.trim_start_matches('\u{feff}').to_string();
            Ok(clean)
        } else {
            let err = String::from_utf8_lossy(&output.stderr);
            Err(format!("Curl error: {}", err))
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = url;
        Err("Unsupported OS".into())
    }
}

#[cfg(target_os = "windows")]
fn is_another_instance_running() -> bool {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    extern "system" {
        fn CreateMutexW(
            lpMutexAttributes: *mut std::ffi::c_void,
            bInitialOwner: i32,
            lpName: *const u16,
        ) -> *mut std::ffi::c_void;
        fn GetLastError() -> u32;
        fn CloseHandle(hObject: *mut std::ffi::c_void) -> i32;
        fn FindWindowW(lpClassName: *const u16, lpWindowName: *const u16) -> *mut std::ffi::c_void;
        fn ShowWindow(hWnd: *mut std::ffi::c_void, nCmdShow: i32) -> i32;
        fn SetForegroundWindow(hWnd: *mut std::ffi::c_void) -> i32;
    }
    const ERROR_ALREADY_EXISTS: u32 = 183;
    const SW_RESTORE: i32 = 9;

    let mutex_name: Vec<u16> = OsStr::new("Local\\CBJGamedaySentinelSingleInstance")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let handle = unsafe { CreateMutexW(std::ptr::null_mut(), 0, mutex_name.as_ptr()) };
    if handle.is_null() {
        return false;
    }

    if unsafe { GetLastError() } == ERROR_ALREADY_EXISTS {
        let win_title: Vec<u16> = OsStr::new("CBJ Gameday Sentinel")
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();
        let hwnd = unsafe { FindWindowW(std::ptr::null(), win_title.as_ptr()) };
        if !hwnd.is_null() {
            unsafe {
                ShowWindow(hwnd, SW_RESTORE);
                SetForegroundWindow(hwnd);
                CloseHandle(handle);
            }
            return true;
        }
    }
    false
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[cfg(target_os = "windows")]
    {
        if is_another_instance_running() {
            std::process::exit(0);
        }
    }

    let is_minimized_start = std::env::args().any(|a| a == "--minimized");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            show_main,
            hide_main,
            quit_app,
            set_close_to_tray,
            send_notification,
            set_autostart,
            load_settings,
            save_settings,
            open_external_url,
            fetch_url
        ])
        .setup(move |app| {
            // Build system tray
            let show_i = MenuItem::with_id(app, "show", "Show Sentinel", true, None::<&str>)?;
            let horn_i = MenuItem::with_id(app, "horn", "\u{1F514} Test Goal Horn", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let sep1 = PredefinedMenuItem::separator(app)?;
            let sep2 = PredefinedMenuItem::separator(app)?;

            let menu = Menu::with_items(app, &[&show_i, &sep1, &horn_i, &sep2, &quit_i])?;

            let tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("CBJ Gameday Sentinel")
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        show_main(app.clone());
                    }
                    "horn" => {
                        let _ = app.emit("test-goal-horn", ());
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main(tray.app_handle().clone());
                    }
                })
                .build(app)?;

            let _ = tray.set_icon(app.default_window_icon().cloned());

            if let Some(main_win) = app.get_webview_window("main") {
                if is_minimized_start {
                    let _ = main_win.hide();
                }

                // Window close intercept: hide to tray
                let w_clone = main_win.clone();
                main_win.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        if CLOSE_TO_TRAY.load(Ordering::Relaxed) {
                            api.prevent_close();
                            let _ = w_clone.hide();
                        }
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running CBJ Gameday Sentinel");
}
