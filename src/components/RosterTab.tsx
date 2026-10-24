import React, { useState, useMemo } from "react";
import { PlayerBio, TeamPreset } from "../types";
import { fetchPlayerBio } from "../services/nhlApi";
import { User, X, Trophy } from "lucide-react";

interface RosterTabProps {
  roster: Record<string, unknown> | null;
  clubStats?: Record<string, unknown> | null;
  team: TeamPreset;
  isLoading: boolean;
}

interface SkaterClubStat {
  playerId: number;
  headshot?: string;
  firstName?: { default?: string } | string;
  lastName?: { default?: string } | string;
  positionCode?: string;
  gamesPlayed: number;
  goals: number;
  assists: number;
  points: number;
  plusMinus: number;
}

interface GoalieClubStat {
  playerId: number;
  headshot?: string;
  firstName?: { default?: string } | string;
  lastName?: { default?: string } | string;
  gamesPlayed: number;
  wins: number;
  losses: number;
  overtimeLosses: number;
  goalsAgainstAverage: number;
  savePercentage: number;
  shutouts?: number;
}

export const RosterTab: React.FC<RosterTabProps> = ({
  roster,
  clubStats = null,
  team,
  isLoading,
}) => {
  const [selectedPlayerBio, setSelectedPlayerBio] = useState<PlayerBio | null>(null);
  const [, setBioLoading] = useState(false);

  const forwards = (roster?.forwards as Array<Record<string, unknown>>) || [];
  const defensemen = (roster?.defensemen as Array<Record<string, unknown>>) || [];
  const goalies = (roster?.goalies as Array<Record<string, unknown>>) || [];

  const { skaterMap, goalieMap, leaders } = useMemo(() => {
    const sList = ((clubStats?.skaters as SkaterClubStat[]) || []).filter(
      (s) => s && s.gamesPlayed > 0
    );
    const gList = ((clubStats?.goalies as GoalieClubStat[]) || []).filter(
      (g) => g && g.gamesPlayed > 0
    );

    const sMap = new Map<number, SkaterClubStat>();
    for (const s of sList) sMap.set(Number(s.playerId), s);

    const gMap = new Map<number, GoalieClubStat>();
    for (const g of gList) gMap.set(Number(g.playerId), g);

    const getName = (p: { firstName?: { default?: string } | string; lastName?: { default?: string } | string }) => {
      const f = typeof p.firstName === "object" ? p.firstName?.default || "" : p.firstName || "";
      const l = typeof p.lastName === "object" ? p.lastName?.default || "" : p.lastName || "";
      return `${f} ${l}`.trim();
    };

    const ptsLeader = [...sList].sort((a, b) => b.points - a.points || b.goals - a.goals)[0];
    const goalsLeader = [...sList].sort((a, b) => b.goals - a.goals || b.points - a.points)[0];
    const astLeader = [...sList].sort((a, b) => b.assists - a.assists || b.points - a.points)[0];
    const pmLeader = [...sList].sort((a, b) => b.plusMinus - a.plusMinus || b.points - a.points)[0];

    const leaderCards = [
      ptsLeader && {
        label: "Points Leader",
        playerId: ptsLeader.playerId,
        name: getName(ptsLeader),
        headshot: ptsLeader.headshot,
        value: `${ptsLeader.points} PTS`,
        sub: `${ptsLeader.goals}G, ${ptsLeader.assists}A`,
      },
      goalsLeader && {
        label: "Goals Leader",
        playerId: goalsLeader.playerId,
        name: getName(goalsLeader),
        headshot: goalsLeader.headshot,
        value: `${goalsLeader.goals} G`,
        sub: `${goalsLeader.gamesPlayed} GP`,
      },
      astLeader && {
        label: "Assists Leader",
        playerId: astLeader.playerId,
        name: getName(astLeader),
        headshot: astLeader.headshot,
        value: `${astLeader.assists} A`,
        sub: `${astLeader.points} PTS`,
      },
      pmLeader && {
        label: "Plus/Minus",
        playerId: pmLeader.playerId,
        name: getName(pmLeader),
        headshot: pmLeader.headshot,
        value: pmLeader.plusMinus > 0 ? `+${pmLeader.plusMinus}` : `${pmLeader.plusMinus}`,
        sub: `${pmLeader.gamesPlayed} GP`,
      },
    ].filter(Boolean) as Array<{
      label: string;
      playerId: number;
      name: string;
      headshot?: string;
      value: string;
      sub: string;
    }>;

    return { skaterMap: sMap, goalieMap: gMap, leaders: leaderCards };
  }, [clubStats]);

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
                  <span>{pos === "G" ? `Catches: ${shoots}` : `Shoots: ${shoots}`}</span>
                  {city && (
                    <>
                      <span>•</span>
                      <span className="truncate">{city}</span>
                    </>
                  )}
                </div>

                {/* Live Season Stats Pill from club-stats */}
                {pos === "G" && goalieMap.has(pid) ? (
                  (() => {
                    const gs = goalieMap.get(pid)!;
                    const svPct = gs.savePercentage
                      ? gs.savePercentage.toFixed(3).replace(/^0/, "")
                      : "-";
                    const gaa = gs.goalsAgainstAverage
                      ? gs.goalsAgainstAverage.toFixed(2)
                      : "-";
                    return (
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-300 mt-1 bg-[#0a1524] px-2 py-0.5 rounded border border-slate-800/80 w-fit">
                        <span>{gs.gamesPlayed} GP</span>
                        <span className="text-slate-600">•</span>
                        <span className="text-cyan-400 font-bold">
                          {gs.wins}-{gs.losses}-{gs.overtimeLosses}
                        </span>
                        <span className="text-slate-600">•</span>
                        <span className="text-amber-400 font-bold">{svPct} SV%</span>
                        <span className="text-slate-600">•</span>
                        <span>{gaa} GAA</span>
                      </div>
                    );
                  })()
                ) : skaterMap.has(pid) ? (
                  (() => {
                    const ss = skaterMap.get(pid)!;
                    const pmStr = ss.plusMinus > 0 ? `+${ss.plusMinus}` : `${ss.plusMinus}`;
                    return (
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-300 mt-1 bg-[#0a1524] px-2 py-0.5 rounded border border-slate-800/80 w-fit">
                        <span>{ss.gamesPlayed} GP</span>
                        <span className="text-slate-600">•</span>
                        <span className="text-cyan-400 font-bold">{ss.goals}G</span>
                        <span>{ss.assists}A</span>
                        <span className="text-amber-400 font-bold">{ss.points} PTS</span>
                        <span className="text-slate-500">({pmStr})</span>
                      </div>
                    );
                  })()
                ) : null}
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
          {/* Team Season Scoring Leaders Banner */}
          {leaders.length > 0 && (
            <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-3.5">
              <div className="flex items-center gap-2 mb-2.5">
                <Trophy className="w-4 h-4 text-amber-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  {team.short} Season Statistical Leaders
                </h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                {leaders.map((ldr, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleOpenBio(ldr.playerId)}
                    className="bg-[#0f1f33] hover:bg-[#142944] border border-slate-800/80 hover:border-blue-500/40 rounded-lg p-2.5 flex items-center gap-2.5 cursor-pointer transition"
                  >
                    {ldr.headshot ? (
                      <img
                        src={ldr.headshot}
                        alt={ldr.name}
                        className="w-10 h-10 rounded-full object-cover bg-[#1b304c] border border-amber-400/60 shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center shrink-0">
                        <User className="w-5 h-5 text-slate-400" />
                      </div>
                    )}
                    <div className="min-w-0">
                      <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400 block">
                        {ldr.label}
                      </span>
                      <span className="text-xs font-bold text-slate-100 truncate block">
                        {ldr.name}
                      </span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs font-black text-amber-400 font-mono">
                          {ldr.value}
                        </span>
                        <span className="text-[10px] text-slate-400">({ldr.sub})</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
                  selectedPlayerBio.positionCode === "G" ? (
                    <div className="grid grid-cols-5 gap-2 text-center bg-[#0e1b2b] p-3 rounded-xl border border-slate-800">
                      <div>
                        <span className="text-slate-500 text-[10px] block">GP</span>
                        <span className="font-bold text-white text-sm">
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.gamesPlayed}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Record</span>
                        <span className="font-bold text-cyan-400 text-sm">
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.wins ?? 0}-
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.losses ?? 0}-
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.otLosses ?? 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">SV%</span>
                        <span className="font-bold text-amber-400 text-sm">
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.savePctg !== undefined
                            ? selectedPlayerBio.featuredStats.regularSeason.subSeason.savePctg
                                .toFixed(3)
                                .replace(/^0/, "")
                            : "-"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">GAA</span>
                        <span className="font-bold text-white text-sm">
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.goalsAgainstAvg !== undefined
                            ? selectedPlayerBio.featuredStats.regularSeason.subSeason.goalsAgainstAvg.toFixed(2)
                            : "-"}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">SO</span>
                        <span className="font-bold text-slate-200 text-sm">
                          {selectedPlayerBio.featuredStats.regularSeason.subSeason.shutouts ?? 0}
                        </span>
                      </div>
                    </div>
                  ) : (
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
                  )
                ) : (
                  <p className="text-slate-500 italic">No regular season stats recorded yet.</p>
                )}
              </div>

              {/* Career Totals */}
              {selectedPlayerBio.careerTotals?.regularSeason && (
                <div className="border-t border-slate-800 pt-3 flex items-center justify-between text-slate-300">
                  <span className="text-slate-500">NHL Career Totals:</span>
                  {selectedPlayerBio.positionCode === "G" ? (
                    <span className="font-mono font-bold text-white">
                      {selectedPlayerBio.careerTotals.regularSeason.gamesPlayed} GP •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.wins ?? 0}-
                      {selectedPlayerBio.careerTotals.regularSeason.losses ?? 0}-
                      {selectedPlayerBio.careerTotals.regularSeason.otLosses ?? 0} •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.savePctg !== undefined
                        ? `${selectedPlayerBio.careerTotals.regularSeason.savePctg.toFixed(3).replace(/^0/, "")} SV%`
                        : ""}{" "}
                      •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.goalsAgainstAvg !== undefined
                        ? `${selectedPlayerBio.careerTotals.regularSeason.goalsAgainstAvg.toFixed(2)} GAA`
                        : ""}{" "}
                      • {selectedPlayerBio.careerTotals.regularSeason.shutouts ?? 0} SO
                    </span>
                  ) : (
                    <span className="font-mono font-bold text-white">
                      {selectedPlayerBio.careerTotals.regularSeason.gamesPlayed} GP •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.goals ?? 0} G •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.assists ?? 0} A •{" "}
                      {selectedPlayerBio.careerTotals.regularSeason.points ?? 0} PTS
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
