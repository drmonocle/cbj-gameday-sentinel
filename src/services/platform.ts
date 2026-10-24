import { invoke } from "@tauri-apps/api/core";

export async function openExternalUrl(url: string): Promise<void> {
  try {
    await invoke("open_external_url", { url });
  } catch {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

export async function sendDesktopNotification(title: string, body: string): Promise<void> {
  try {
    await invoke("send_notification", { title, body });
  } catch {
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body });
    }
  }
}

export async function updateTrayTooltip(tooltip: string): Promise<void> {
  try {
    await invoke("set_tray_tooltip", { tooltip });
  } catch {
    // ignore outside Tauri
  }
}

export async function syncCloseToTray(enabled: boolean): Promise<void> {
  try {
    await invoke("set_close_to_tray", { enabled });
  } catch {
    // ignore outside Tauri
  }
}
