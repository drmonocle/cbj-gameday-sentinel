import React, { useState } from "react";
import { StandingsRecord, TeamPreset } from "../types";
import { getTeamLogoUrl } from "../config/teams";
import { Trophy } from "lucide-react";

interface StandingsTabProps {
  standings: StandingsRecord[];
  team: TeamPreset;
}

export const StandingsTab: React.FC<StandingsTabProps> = ({ standings, team }) => {
  const [view, setView] = useState<"division" | "wildcard" | "conference">("division");

  // Division standings
  const divisionRows = standings
    .filter((s) => s.divisionAbbrev === team.division)
    .sort((a, b) => a.divisionSequence - b.divisionSequence);

  // Conference leaders & Wildcard
  const confRows = standings.filter((s) => s.conferenceAbbrev === team.conference);
  const divisionLeaders = confRows
    .filter((s) => s.divisionSequence <= 3)
    .sort((a, b) => {
      if (a.divisionAbbrev !== b.divisionAbbrev) return a.divisionAbbrev.localeCompare(b.divisionAbbrev);
      return a.divisionSequence - b.divisionSequence;
    });

  const wildcardRows = confRows
    .filter((s) => s.divisionSequence > 3)
    .sort((a, b) => a.wildcardSequence - b.wildcardSequence);

  const renderTable = (rows: StandingsRecord[], title: string, cutoffIndex?: number) => (
    <div className="bg-[#0b1726] border border-slate-800 rounded-xl overflow-hidden mb-4 shadow">
      <div className="bg-[#0e1b2b] px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
          {title}
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="bg-[#07111e] text-slate-400 font-bold border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3 text-center w-8">#</th>
              <th className="py-2.5 px-3">Team</th>
              <th className="py-2.5 px-2 text-center">GP</th>
              <th className="py-2.5 px-2 text-center">W</th>
              <th className="py-2.5 px-2 text-center">L</th>
              <th className="py-2.5 px-2 text-center">OTL</th>
              <th className="py-2.5 px-3 text-center font-black text-amber-400">PTS</th>
              <th className="py-2.5 px-2 text-center">P%</th>
              <th className="py-2.5 px-2 text-center">DIFF</th>
              <th className="py-2.5 px-3 text-center">L10</th>
              <th className="py-2.5 px-2 text-center">STRK</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-medium">
            {rows.map((row, idx) => {
              const abbrev =
                typeof row.teamAbbrev === "object"
                  ? (row.teamAbbrev as { default: string }).default
                  : String(row.teamAbbrev);
              const tmName =
                typeof row.teamName === "object"
                  ? (row.teamName as { default: string }).default
                  : String(row.teamName || abbrev);

              const isFav = abbrev === team.id;
              const isCutoff = cutoffIndex !== undefined && idx === cutoffIndex;

              return (
                <React.Fragment key={abbrev}>
                  {isCutoff && (
                    <tr className="bg-red-950/40 border-t-2 border-red-500/60">
                      <td colSpan={11} className="py-1 px-3 text-[10px] uppercase tracking-widest font-black text-red-400 text-center">
                        ── Playoff Cutoff Line ──
                      </td>
                    </tr>
                  )}
                  <tr
                    className={`transition hover:bg-slate-800/40 ${
                      isFav ? "bg-blue-900/30 text-white font-bold" : "text-slate-300"
                    }`}
                  >
                    <td className="py-2.5 px-3 text-center text-slate-500 font-mono text-[11px]">
                      {idx + 1}
                    </td>
                    <td className="py-2.5 px-3 flex items-center gap-2.5">
                      <img
                        src={getTeamLogoUrl(abbrev)}
                        alt={abbrev}
                        className="w-5 h-5 object-contain"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = "/icon.png";
                        }}
                      />
                      <span className={isFav ? "text-cyan-400 font-black" : "text-slate-200"}>
                        {tmName}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-center font-mono">{row.gamesPlayed}</td>
                    <td className="py-2.5 px-2 text-center font-mono">{row.wins}</td>
                    <td className="py-2.5 px-2 text-center font-mono">{row.losses}</td>
                    <td className="py-2.5 px-2 text-center font-mono">{row.otLosses}</td>
                    <td className="py-2.5 px-3 text-center font-black font-mono text-amber-400 text-sm">
                      {row.points}
                    </td>
                    <td className="py-2.5 px-2 text-center font-mono text-slate-400">
                      {row.pointPctg.toFixed(3)}
                    </td>
                    <td
                      className={`py-2.5 px-2 text-center font-mono ${
                        row.goalDifferential > 0
                          ? "text-emerald-400"
                          : row.goalDifferential < 0
                          ? "text-rose-400"
                          : "text-slate-400"
                      }`}
                    >
                      {row.goalDifferential > 0 ? `+${row.goalDifferential}` : row.goalDifferential}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-[11px] text-slate-400">
                      {row.l10Wins}-{row.l10Losses}-{row.l10OtLosses}
                    </td>
                    <td className="py-2.5 px-2 text-center font-mono text-xs">
                      {row.streakCode ? `${row.streakCode}${row.streakCount}` : "-"}
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Subtab Toggle */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setView("division")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            view === "division" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
          }`}
        >
          Division Standings
        </button>
        <button
          onClick={() => setView("wildcard")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            view === "wildcard" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
          }`}
        >
          Wildcard Race
        </button>
        <button
          onClick={() => setView("conference")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            view === "conference" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
          }`}
        >
          Full Conference
        </button>
      </div>

      {view === "division" && renderTable(divisionRows, `${team.division === "M" ? "Metropolitan" : team.division} Division`)}
      {view === "wildcard" && (
        <>
          {renderTable(divisionLeaders, "Division Leaders (Top 3 per Division)")}
          {renderTable(wildcardRows, "Wildcard Race (Top 2 Qualify)", 2)}
        </>
      )}
      {view === "conference" && renderTable(confRows.sort((a, b) => b.points - a.points), `${team.conference === "E" ? "Eastern" : "Western"} Conference`)}
    </div>
  );
};
