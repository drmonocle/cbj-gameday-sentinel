import React, { useState } from "react";
import { GameInfo, TeamPreset } from "../types";
import { getTeamLogoUrl } from "../config/teams";
import { Calendar, CheckCircle2, Clock, Tv, Crosshair, ChevronRight } from "lucide-react";

interface GamesTabProps {
  team: TeamPreset;
  schedule: GameInfo[];
  onSelectGameForShots: (gameId: number) => void;
  spoilerMode: boolean;
}

export const GamesTab: React.FC<GamesTabProps> = ({
  team,
  schedule,
  onSelectGameForShots,
  spoilerMode,
}) => {
  const [subTab, setSubTab] = useState<"past" | "upcoming">("past");

  // Separate past games from upcoming games
  const pastGames = schedule.filter(
    (g) => g.gameState === "FINAL" || g.gameState === "OFF"
  );
  const upcomingGames = schedule.filter(
    (g) => g.gameState !== "FINAL" && g.gameState !== "OFF"
  );

  // Compute season record
  let gp = 0;
  let w = 0;
  let l = 0;
  let otl = 0;
  let gf = 0;
  let ga = 0;

  for (const g of pastGames) {
    if (g.gameType !== 2 && g.gameType !== 3) continue; // Regular or playoff
    const isHome = g.homeTeam.abbrev === team.id;
    const us = isHome ? g.homeTeam : g.awayTeam;
    const them = isHome ? g.awayTeam : g.homeTeam;
    const ourScore = us.score ?? 0;
    const oppScore = them.score ?? 0;

    gp++;
    gf += ourScore;
    ga += oppScore;

    if (ourScore > oppScore) {
      w++;
    } else {
      const ptype = g.periodDescriptor?.periodType || "REG";
      if (ptype === "OT" || ptype === "SO") otl++;
      else l++;
    }
  }

  const pts = w * 2 + otl;

  return (
    <div className="flex flex-col gap-4">
      {/* Team Season Record Header */}
      <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xs uppercase tracking-wider font-bold text-slate-400">
            {team.name} • Season Record
          </h2>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-2xl font-black text-white">
              {w}-{l}-{otl}
            </span>
            <span className="px-2 py-0.5 rounded bg-blue-900/50 text-blue-300 font-bold text-xs border border-blue-700/40">
              {pts} PTS
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs text-slate-300">
          <div>
            <span className="text-slate-500 block">Games</span>
            <span className="font-bold text-white text-sm">{gp}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Goals For</span>
            <span className="font-bold text-cyan-400 text-sm">{gf}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Goals Against</span>
            <span className="font-bold text-red-400 text-sm">{ga}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Differential</span>
            <span
              className={`font-bold text-sm ${
                gf - ga >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {gf - ga > 0 ? `+${gf - ga}` : gf - ga}
            </span>
          </div>
        </div>
      </div>

      {/* Subtab Toggle Buttons */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setSubTab("past")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            subTab === "past"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Completed Games ({pastGames.length})</span>
        </button>
        <button
          onClick={() => setSubTab("upcoming")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            subTab === "upcoming"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Upcoming Schedule ({upcomingGames.length})</span>
        </button>
      </div>

      {/* Games List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {subTab === "past" ? (
          pastGames.slice(0, 14).map((g) => {
            const isHome = g.homeTeam.abbrev === team.id;
            const us = isHome ? g.homeTeam : g.awayTeam;
            const them = isHome ? g.awayTeam : g.homeTeam;
            const ourScore = us.score ?? 0;
            const oppScore = them.score ?? 0;
            const isWin = ourScore > oppScore;
            const lastType = g.periodDescriptor?.periodType || "REG";
            const outcome = isWin
              ? "W"
              : lastType === "OT"
              ? "OTL"
              : lastType === "SO"
              ? "SOL"
              : "L";

            return (
              <div
                key={g.id}
                className="bg-[#0b1726] border border-slate-800/80 hover:border-slate-700 rounded-xl p-3.5 flex items-center justify-between gap-3 transition"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={getTeamLogoUrl(them.abbrev)}
                    alt={them.abbrev}
                    className="w-10 h-10 object-contain drop-shadow"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/icon.png";
                    }}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-medium">
                        {isHome ? "vs" : "@"}
                      </span>
                      <span className="text-xs font-bold text-slate-100 uppercase">
                        {them.commonName?.default || them.name?.default || them.abbrev}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                      {new Date(g.startTimeUTC).toLocaleDateString([], {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {!spoilerMode ? (
                    <div className="flex items-center gap-2 text-right">
                      <div className="flex flex-col items-end">
                        <span className="text-sm font-black text-white font-mono">
                          {ourScore} - {oppScore}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">
                          {lastType !== "REG" ? lastType : "Final"}
                        </span>
                      </div>
                      <span
                        className={`px-2 py-1 rounded text-xs font-black uppercase ${
                          isWin
                            ? "bg-emerald-600/30 text-emerald-400 border border-emerald-500/40"
                            : outcome === "OTL" || outcome === "SOL"
                            ? "bg-amber-600/30 text-amber-400 border border-amber-500/40"
                            : "bg-rose-600/30 text-rose-400 border border-rose-500/40"
                        }`}
                      >
                        {outcome}
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-500 font-medium italic">
                      Hidden
                    </span>
                  )}

                  <button
                    onClick={() => onSelectGameForShots(g.id)}
                    className="p-1.5 rounded-lg bg-blue-900/30 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-700/30 transition cursor-pointer"
                    title="View Shot Chart for this game"
                  >
                    <Crosshair className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          upcomingGames.slice(0, 14).map((g) => {
            const isHome = g.homeTeam.abbrev === team.id;
            const them = isHome ? g.awayTeam : g.homeTeam;
            const tv = (g.tvBroadcasts || [])
              .filter((b) => b.countryCode === "US")
              .map((b) => b.network)
              .join(", ");

            return (
              <div
                key={g.id}
                className="bg-[#0b1726] border border-slate-800/80 rounded-xl p-3.5 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={getTeamLogoUrl(them.abbrev)}
                    alt={them.abbrev}
                    className="w-10 h-10 object-contain drop-shadow"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/icon.png";
                    }}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-medium">
                        {isHome ? "vs" : "@"}
                      </span>
                      <span className="text-xs font-bold text-slate-100 uppercase">
                        {them.commonName?.default || them.name?.default || them.abbrev}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-medium mt-0.5 flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-blue-400" />
                      <span>
                        {new Date(g.startTimeUTC).toLocaleDateString([], {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                        })}{" "}
                        •{" "}
                        {new Date(g.startTimeUTC).toLocaleTimeString([], {
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  {tv ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-300 bg-slate-800/70 px-2 py-0.5 rounded border border-slate-700/60">
                      <Tv className="w-3 h-3 text-blue-400" />
                      <span>{tv}</span>
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                      {g.venue?.default || "Arena"}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
