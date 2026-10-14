import { invoke } from "@tauri-apps/api/core";
import { AppSettings } from "../types";

export const DEFAULT_SETTINGS: AppSettings = {
  team: "CBJ",
  sound: true,
  opponent_sound: false,
  volume: 80,
  toasts: true,
  puck_drop_reminder: true,
  spoiler_mode: false,
  start_with_windows: false,
  close_to_tray: true,
  watch: "prime",
  refresh_interval: 20,
};

const STORAGE_KEY = "cbj_sentinel_settings";

export async function loadAppSettings(): Promise<AppSettings> {
  try {
    const raw = await invoke<Record<string, unknown>>("load_settings");
    if (raw && typeof raw === "object" && Object.keys(raw).length > 0) {
      return { ...DEFAULT_SETTINGS, ...raw } as AppSettings;
    }
  } catch (err) {
    console.warn("Could not load from backend, checking localStorage:", err);
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch {
    // fallback
  }

  return { ...DEFAULT_SETTINGS };
}

export async function saveAppSettings(settings: AppSettings): Promise<void> {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // ignore
  }

  try {
    await invoke("save_settings", { settings });
  } catch (err) {
    console.error("Failed to save settings to backend:", err);
  }

  try {
    await invoke("set_autostart", { enabled: settings.start_with_windows });
  } catch {
    // ignore
  }

  try {
    await invoke("set_close_to_tray", { enabled: settings.close_to_tray });
  } catch {
    // ignore
  }
}
