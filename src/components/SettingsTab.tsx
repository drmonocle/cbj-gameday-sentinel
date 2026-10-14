import React from "react";
import { AppSettings, TeamPreset } from "../types";
import { TEAM_PRESETS } from "../config/teams";
import { playGoalHorn, playOpponentChime } from "../services/sound";
import { Volume2, Bell, EyeOff, Power, HardDrive, HelpCircle, Sparkles } from "lucide-react";

interface SettingsTabProps {
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
  team: TeamPreset;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({
  settings,
  onUpdateSettings,
  team,
}) => {
  return (
    <div className="flex flex-col gap-5 max-w-3xl mx-auto pb-8">
      {/* 32-Team Interchangeable Customizer */}
      <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-5 shadow">
        <div className="flex items-center gap-2.5 mb-3">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Favorite Team & Theme Preset
          </h3>
        </div>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed">
          Switching your team updates all schedule data, scoring summaries, rosters, and visual color themes instantly. Open source contributors can set their favorite team as default or rebrand with zero code changes.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Active NHL Franchise:
            </label>
            <select
              value={settings.team}
              onChange={(e) => onUpdateSettings({ team: e.target.value })}
              className="w-full bg-[#122033] border border-slate-700 text-slate-200 text-xs font-bold rounded-lg p-2.5 cursor-pointer focus:border-blue-500 focus:outline-none"
            >
              {Object.values(TEAM_PRESETS).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.city} {t.short} ({t.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Live Stream Watch Target:
            </label>
            <select
              value={settings.watch}
              onChange={(e) => onUpdateSettings({ watch: e.target.value })}
              className="w-full bg-[#122033] border border-slate-700 text-slate-200 text-xs font-bold rounded-lg p-2.5 cursor-pointer focus:border-blue-500 focus:outline-none"
            >
              {team.id === "CBJ" && (
                <option value="prime">Prime Video • Blue Jackets Hockey Network</option>
              )}
              <option value="espn">ESPN+ • NHL Power Play</option>
              <option value="fubo">Fubo TV</option>
              <option value="nhl">NHL.com Official Tune-In Guide</option>
            </select>
          </div>
        </div>
      </div>

      {/* Audio & Goal Horn Controls */}
      <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-5 shadow">
        <div className="flex items-center gap-2.5 mb-3">
          <Volume2 className="w-5 h-5 text-blue-400" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Audio Horn & Cannon Sound
          </h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          Procedurally synthesized goal horn with authentic arena acoustics and deep cannon blast reverb.
        </p>

        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Enable Goal Horn on {team.short} Goals
              </span>
              <span className="text-[11px] text-slate-400">
                Fires the goal horn and cannon blast when your team scores.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.sound}
              onChange={(e) => onUpdateSettings({ sound: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Play Subtle Chime on Opponent Goals
              </span>
              <span className="text-[11px] text-slate-400">
                Soft chime to alert you if the opposing team scores.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.opponent_sound}
              onChange={(e) => onUpdateSettings({ opponent_sound: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>

          <div className="pt-2 border-t border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300">
                Audio Volume: {settings.volume}%
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => playGoalHorn(settings.volume)}
                  className="px-3 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs transition cursor-pointer shadow"
                >
                  🔊 Test Goal Horn
                </button>
                <button
                  onClick={() => playOpponentChime(settings.volume)}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition cursor-pointer"
                >
                  🔔 Test Chime
                </button>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={settings.volume}
              onChange={(e) => onUpdateSettings({ volume: parseInt(e.target.value, 10) })}
              className="w-full accent-blue-500 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Notifications & Privacy */}
      <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-5 shadow">
        <div className="flex items-center gap-2.5 mb-3">
          <Bell className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Notifications & System Integration
          </h3>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Windows Toast Notifications
              </span>
              <span className="text-[11px] text-slate-400">
                Display native Windows toast notifications on goals and period ends.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.toasts}
              onChange={(e) => onUpdateSettings({ toasts: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Spoiler Free Mode
              </span>
              <span className="text-[11px] text-slate-400">
                Hides scores and results on all tabs until clicked.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.spoiler_mode}
              onChange={(e) => onUpdateSettings({ spoiler_mode: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Minimize to System Tray on Close
              </span>
              <span className="text-[11px] text-slate-400">
                Closing the window sends it to the Windows notification tray instead of quitting.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.close_to_tray}
              onChange={(e) => onUpdateSettings({ close_to_tray: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                Start with Windows
              </span>
              <span className="text-[11px] text-slate-400">
                Launches the Sentinel minimized to tray when your PC boots up.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.start_with_windows}
              onChange={(e) => onUpdateSettings({ start_with_windows: e.target.checked })}
              className="w-4 h-4 accent-blue-600 rounded cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* About & Open Source Forking Guide */}
      <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-5 shadow text-xs text-slate-400">
        <h4 className="font-bold text-slate-200 uppercase tracking-wider mb-2">
          About CBJ Gameday Sentinel
        </h4>
        <p className="mb-2 leading-relaxed">
          Version 2.0.0 • Built with Tauri v2, Rust, React 19, TypeScript, and Tailwind CSS.
          Published by <strong className="text-slate-200">Monocle Productions LLC</strong>.
        </p>
        <p className="leading-relaxed">
          <strong>GitHub Forking Instructions:</strong> To rebrand for any of the 32 NHL teams, simply edit <code className="text-amber-400 bg-slate-900 px-1 py-0.5 rounded">DEFAULT_TEAM</code> in <code className="text-blue-400 bg-slate-900 px-1 py-0.5 rounded">src/config/teams.ts</code> or select your franchise from the dropdown above. Settings are permanently preserved in <code className="text-slate-300 bg-slate-900 px-1 py-0.5 rounded">%APPDATA%\CBJGamedaySentinel\settings.json</code>.
        </p>
      </div>
    </div>
  );
};
