import React, { useState } from "react";
import { PlayerBio, TeamPreset } from "../types";
import { fetchPlayerBio } from "../services/nhlApi";
import { User, X, Award, MapPin, Calendar, Activity } from "lucide-react";

interface RosterTabProps {
  roster: Record<string, unknown> | null;
  team: TeamPreset;
  isLoading: boolean;
}

export const RosterTab: React.FC<RosterTabProps> = ({ roster, team, isLoading }) => {
  const [selectedPlayerBio, setSelectedPlayerBio] = useState<PlayerBio | null>(null);
  const [bioLoading, setBioLoading] = useState(false);

  const forwards = (roster?.forwards as Array<Record<string, unknown>>) || [];
  const defensemen = (roster?.defensemen as Array<Record<string, unknown>>) || [];
  const goalies = (roster?.goalies as Array<Record<string, unknown>>) || [];

  const handleOpenBio = async (playerId: number) => {
    try {
      setBioLoading(true);
      const bio = await fetchPlayerBio(playerId);
      setSelectedPlayerBio(bio);
    } catch (err) {
      console.error("Failed to load player bio:", err);
    } finally {
      setBioLoading(false);
    }
  };

  const renderSection = (players: Array<Record<string, unknown>>, title: string) => (
    <div className="bg-[#0b1726] border border-slate-800 rounded-xl overflow-hidden mb-4">
      <div className="bg-[#0e1b2b] px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
          {title} ({players.length})
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
        {players.map((p) => {
          const pid = Number(p.id || 0);
          const first = String(
            typeof p.firstName === "object"
              ? (p.firstName as { default?: string })?.default || ""
              : p.firstName || ""
          );
          const last = String(
            typeof p.lastName === "object"
              ? (p.lastName as { default?: string })?.default || ""
              : p.lastName || ""
          );
          const num = p.sweaterNumber !== undefined && p.sweaterNumber !== null ? String(p.sweaterNumber) : "";
          const pos = String(p.positionCode || "");
          const shoots = String(p.shootsCatches || "R");
          const photo = String(p.headshot || "");
          const city = String(
            typeof p.birthCity === "object"
              ? (p.birthCity as { default?: string })?.default || ""
              : p.birthCity || ""
          );

          return (
            <div
              key={pid}
              onClick={() => handleOpenBio(pid)}
              className="bg-[#0f1f33] hover:bg-[#142944] border border-slate-800/80 hover:border-blue-500/50 rounded-lg p-2.5 flex items-center gap-3 transition cursor-pointer group"
            >
              <div className="relative w-11 h-11 rounded-full bg-[#1b304c] overflow-hidden flex items-center justify-center shrink-0 border border-slate-700">
                {photo ? (
                  <img src={photo} alt={`${first} ${last}`} className="w-full h-full object-cover" />
                ) : (
                  <User className="w-6 h-6 text-slate-400" />
                )}
                {num && (
                  <span className="absolute bottom-0 right-0 bg-blue-600 text-white font-black text-[9px] px-1 rounded-tl-md">
                    #{num}
                  </span>
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-xs text-slate-100 group-hover:text-blue-400 truncate">
                    {first} {last}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                  <span className="font-semibold text-amber-400">{pos}</span>
                  <span>•</span>
                  <span>Shoots: {shoots}</span>
                  {city && (
                    <>
                      <span>•</span>
                      <span className="truncate">{city}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {isLoading && !roster ? (
        <div className="p-8 text-center text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <p className="text-xs">Loading active team roster...</p>
        </div>
      ) : (
        <>
          {renderSection(forwards, "Forwards")}
          {renderSection(defensemen, "Defensemen")}
          {renderSection(goalies, "Goalies")}
        </>
      )}

      {/* Player Bio Modal */}
      {selectedPlayerBio && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0b1726] border border-slate-700 rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl animate-in fade-in duration-200">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-blue-900 to-indigo-950 p-5 relative flex items-center gap-4">
              <button
                onClick={() => setSelectedPlayerBio(null)}
                className="absolute top-4 right-4 p-1.5 rounded-full bg-black/40 text-slate-300 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="w-16 h-16 rounded-full bg-slate-800 overflow-hidden border-2 border-white/20 shrink-0">
                {selectedPlayerBio.headshot ? (
                  <img src={selectedPlayerBio.headshot} alt="player" className="w-full h-full object-cover" />
                ) : (
                  <User className="w-10 h-10 text-slate-400 m-auto mt-2" />
                )}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-amber-400 font-mono font-bold text-sm">
                    #{selectedPlayerBio.sweaterNumber}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-700 text-white font-bold uppercase">
                    {selectedPlayerBio.positionCode}
                  </span>
                </div>
                <h3 className="text-lg font-black text-white mt-1">
                  {typeof selectedPlayerBio.firstName === "object"
                    ? (selectedPlayerBio.firstName as { default?: string }).default
                    : selectedPlayerBio.firstName}{" "}
                  {typeof selectedPlayerBio.lastName === "object"
                    ? (selectedPlayerBio.lastName as { default?: string }).default
                    : selectedPlayerBio.lastName}
                </h3>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-5 flex flex-col gap-4 text-xs">
              {/* Bio Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#08121f] p-3 rounded-xl border border-slate-800 text-slate-300">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Height</span>
                  <span className="font-bold text-white">
                    {selectedPlayerBio.heightInInches
                      ? `${Math.floor(selectedPlayerBio.heightInInches / 12)}'${selectedPlayerBio.heightInInches % 12}"`
                      : "-"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Weight</span>
                  <span className="font-bold text-white">
                    {selectedPlayerBio.weightInPounds ? `${selectedPlayerBio.weightInPounds} lbs` : "-"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Shoots</span>
                  <span className="font-bold text-white">{selectedPlayerBio.shootsCatches || "R"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Birthplace</span>
                  <span className="font-bold text-white truncate block">
                    {typeof selectedPlayerBio.birthCity === "object"
                      ? (selectedPlayerBio.birthCity as { default?: string }).default
                      : selectedPlayerBio.birthCity || "-"}
                  </span>
                </div>
              </div>

              {/* Current Season Stats */}
              <div>
                <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[11px] mb-2">
                  Featured Season Stats
                </h4>
                {selectedPlayerBio.featuredStats?.regularSeason?.subSeason ? (
                  <div className="grid grid-cols-6 gap-2 text-center bg-[#0e1b2b] p-3 rounded-xl border border-slate-800">
                    <div>
                      <span className="text-slate-500 text-[10px] block">GP</span>
                      <span className="font-bold text-white text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.gamesPlayed}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Goals</span>
                      <span className="font-bold text-cyan-400 text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.goals ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Assists</span>
                      <span className="font-bold text-white text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.assists ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">Points</span>
                      <span className="font-bold text-amber-400 text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.points ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">+/-</span>
                      <span className="font-bold text-slate-200 text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.plusMinus ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block">PIM</span>
                      <span className="font-bold text-slate-200 text-sm">
                        {selectedPlayerBio.featuredStats.regularSeason.subSeason.pim ?? "-"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-500 italic">No regular season stats recorded yet.</p>
                )}
              </div>

              {/* Career Totals */}
              {selectedPlayerBio.careerTotals?.regularSeason && (
                <div className="border-t border-slate-800 pt-3 flex items-center justify-between text-slate-300">
                  <span className="text-slate-500">NHL Career Totals:</span>
                  <span className="font-mono font-bold text-white">
                    {selectedPlayerBio.careerTotals.regularSeason.gamesPlayed} GP •{" "}
                    {selectedPlayerBio.careerTotals.regularSeason.goals} G •{" "}
                    {selectedPlayerBio.careerTotals.regularSeason.assists} A •{" "}
                    {selectedPlayerBio.careerTotals.regularSeason.points} PTS
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
