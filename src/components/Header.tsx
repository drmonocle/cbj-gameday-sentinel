import React from "react";
import { TeamPreset } from "../types";
import { getTeamLogoUrl, TEAM_PRESETS } from "../config/teams";
import {
  Activity,
  Calendar,
  Crosshair,
  Trophy,
  Newspaper,
  Users,
  Settings as SettingsIcon,
  RefreshCw,
  Tv,
} from "lucide-react";

interface HeaderProps {
  team: TeamPreset;
  onSelectTeam: (teamId: string) => void;
  activeTab: string;
  onSelectTab: (tab: string) => void;
  gameStateLabel?: string;
  isLive?: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  team,
  onSelectTeam,
  activeTab,
  onSelectTab,
  gameStateLabel,
  isLive,
  onRefresh,
  isRefreshing,
}) => {
  const tabs = [
    { id: "live", label: "Live Game", icon: Activity },
    { id: "shots", label: "Shot Chart", icon: Crosshair },
    { id: "games", label: "Games", icon: Calendar },
    { id: "standings", label: "Standings", icon: Trophy },
    { id: "news", label: "News", icon: Newspaper },
    { id: "roster", label: "Roster", icon: Users },
    { id: "settings", label: "Settings", icon: SettingsIcon },
  ];

  return (
    <header className="bg-[#07111e] border-b border-slate-800/90 px-4 py-2 flex flex-col md:flex-row items-center justify-between gap-3 select-none">
      {/* Team Branding & Live Badge */}
      <div className="flex items-center gap-3">
        <div className="relative group">
          <img
            src={getTeamLogoUrl(team.id)}
            alt={team.name}
            className="w-10 h-10 object-contain drop-shadow-md cursor-pointer transition-transform group-hover:scale-105"
            onError={(e) => {
              // Fallback to placeholder if offline
              (e.target as HTMLImageElement).src = "/icon.png";
            }}
          />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-black uppercase tracking-wider text-slate-100">
              {team.name}
            </h1>
            {isLive ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-red-600/90 text-white font-black text-[10px] tracking-widest animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-white"></span> LIVE
              </span>
            ) : gameStateLabel ? (
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-bold text-[10px] uppercase border border-slate-700">
                {gameStateLabel}
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Gameday Sentinel v2.0</span>
            <span>•</span>
            <select
              value={team.id}
              onChange={(e) => onSelectTeam(e.target.value)}
              className="bg-transparent text-xs text-blue-400 font-semibold cursor-pointer border-none outline-none hover:text-blue-300"
            >
              {Object.values(TEAM_PRESETS).map((t) => (
                <option key={t.id} value={t.id} className="bg-[#0b1726] text-slate-200">
                  {t.city} {t.short} ({t.id})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <nav className="flex items-center gap-1 bg-[#0b1726] p-1 rounded-lg border border-slate-800">
        {tabs.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onSelectTab(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                isActive
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Quick Action Refresh */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-1.5 rounded-md bg-[#0e1b2b] text-slate-400 hover:text-slate-100 hover:bg-slate-800 border border-slate-800 transition disabled:opacity-50 cursor-pointer"
          title="Refresh Data"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-blue-400" : ""}`} />
        </button>
      </div>
    </header>
  );
};
