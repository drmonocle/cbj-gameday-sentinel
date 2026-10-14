import React from "react";
import { GameInfo, StandingsRecord, TeamPreset } from "../types";
import { getTeamLogoUrl } from "../config/teams";
import { formatTimeRemaining } from "../services/nhlApi";
import { Calendar, Tv, ExternalLink, Star, Flame, Swords } from "lucide-react";
import { openExternalUrl } from "../services/platform";

interface LiveBannerProps {
  game: GameInfo | null;
  nextGame: GameInfo | null;
  team: TeamPreset;
  landingData: Record<string, unknown> | null;
  spoilerMode: boolean;
  standings?: StandingsRecord[];
  schedule?: GameInfo[];
}

function getStandingAbbrev(s: StandingsRecord): string {
  return typeof s.teamAbbrev === "object"
    ? (s.teamAbbrev as { default: string }).default
    : String(s.teamAbbrev || "");
}

function formatCountdown(startTimeUTC: string): string {
  const diffMs = new Date(startTimeUTC).getTime() - Date.now();
  if (isNaN(diffMs) || diffMs <= 0) return "Starting Soon";
  const totalMinutes = Math.floor(diffMs / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const mins = totalMinutes % 60;
  if (days > 0) return `In ${days}d ${hours}h`;
  if (hours > 0) return `In ${hours}h ${mins}m`;
  return `In ${mins}m`;
}

export const LiveBanner: React.FC<LiveBannerProps> = ({
  game,
  nextGame,
  team,
  landingData,
  spoilerMode,
  standings = [],
  schedule = [],
}) => {
  const displayGame = game || nextGame;

  if (!displayGame) {
    return (
      <div className="bg-[#0b1726] border border-slate-800 rounded-lg p-6 text-center text-slate-400">
        <p className="font-semibold">No active or upcoming games scheduled right now.</p>
      </div>
    );
  }

  const isLive = displayGame.gameState === "LIVE" || displayGame.gameState === "CRIT";
  const isFinal = displayGame.gameState === "FINAL" || displayGame.gameState === "OFF";
  const isUpcoming = displayGame.gameState === "FUT" || displayGame.gameState === "PRE";

  const home = displayGame.homeTeam;
  const away = displayGame.awayTeam;

  const awayStanding = standings.find((s) => getStandingAbbrev(s) === away.abbrev);
  const homeStanding = standings.find((s) => getStandingAbbrev(s) === home.abbrev);

  const awayRecordStr = awayStanding
    ? `${awayStanding.wins}-${awayStanding.losses}-${awayStanding.otLosses} (${awayStanding.points} PTS)`
    : "Away";
  const homeRecordStr = homeStanding
    ? `${homeStanding.wins}-${homeStanding.losses}-${homeStanding.otLosses} (${homeStanding.points} PTS)`
    : "Home";

  const upcomingSlate = schedule
    .filter((g) => g.gameState === "FUT" || g.gameState === "PRE")
    .slice(0, 4);

  // Situation: Power play / Empty net
  const situation = displayGame.situation;
  let ppText = "";
  if (situation && situation.situationCode) {
    const code = situation.situationCode;
    if (code.length === 4) {
      const awayG = parseInt(code[0], 10);
      const awayS = parseInt(code[1], 10);
      const homeS = parseInt(code[2], 10);
      const homeG = parseInt(code[3], 10);
      const effAway = awayS - (awayG === 0 ? 1 : 0);
      const effHome = homeS - (homeG === 0 ? 1 : 0);
      if (effAway > effHome) {
        ppText = `PP ${away.abbrev} ${Math.max(awayS, homeS)}-on-${Math.min(awayS, homeS)}`;
      } else if (effHome > effAway) {
        ppText = `PP ${home.abbrev} ${Math.max(awayS, homeS)}-on-${Math.min(awayS, homeS)}`;
      }
      if (situation.timeRemaining) {
        ppText += ` (${situation.timeRemaining})`;
      }
    }
  }

  // TV Broadcasts
  const tvNets = (displayGame.tvBroadcasts || [])
    .filter((b) => b.countryCode === "US")
    .map((b) => b.network)
    .filter((v, i, a) => a.indexOf(v) === i)
    .join(", ");

  const watchUrl =
    team.id === "CBJ"
      ? "https://www.amazon.com/gp/video/channel/19bfae52-c58d-83c8-3909-2f61654f1afb"
      : "https://plus.espn.com/nhl";

  // Scoring Summary: only parse when viewing an active or recently completed game
  const scoringPeriods = !isUpcoming
    ? (((landingData?.summary as Record<string, unknown>)?.scoring as Array<Record<string, unknown>>) || [])
    : [];
  const goalsList: Array<{
    period: string;
    time: string;
    team: string;
    scorer: string;
    headshot?: string;
    assists?: string[];
    highlightUrl?: string;
    strength?: string;
  }> = [];

  if (!isUpcoming && scoringPeriods.length > 0) {
    for (const period of scoringPeriods) {
      const pd = period.periodDescriptor as Record<string, unknown>;
      const pNum = pd?.number || 1;
      const pType = pd?.periodType || "REG";
      const pLabel = pType === "OT" ? "OT" : pType === "SO" ? "SO" : `P${pNum}`;
      const pGoals = (period.goals as Array<Record<string, unknown>>) || [];
      for (const g of pGoals) {
        const tm = typeof g.teamAbbrev === "object" ? (g.teamAbbrev as { default: string }).default : String(g.teamAbbrev || "");
        const first = typeof g.firstName === "object" ? (g.firstName as { default: string }).default : String(g.firstName || "");
        const last = typeof g.lastName === "object" ? (g.lastName as { default: string }).default : String(g.lastName || g.name || "");
        const who = `${first} ${last}`.trim();
        const str = String(g.strength || "").toLowerCase();
        const tag = str === "pp" ? " (PPG)" : str === "sh" ? " (SHG)" : g.goalModifier === "empty-net" ? " (EN)" : "";
        const pid = g.playerId ? Number(g.playerId) : 0;
        const photo = String(
          g.headshot || (pid > 0 ? `https://assets.nhle.com/mugs/nhl/latest/${pid}.png` : "")
        );
        const rawAssists = (g.assists as Array<Record<string, unknown>>) || [];
        const astNames = rawAssists.map((a) => {
          const aFirst = typeof a.firstName === "object" ? (a.firstName as { default: string }).default : String(a.firstName || "");
          const aLast = typeof a.lastName === "object" ? (a.lastName as { default: string }).default : String(a.lastName || a.name || "");
          return `${aFirst} ${aLast}`.trim();
        }).filter(Boolean);

        goalsList.push({
          period: pLabel,
          time: String(g.timeInPeriod || ""),
          team: tm,
          scorer: `${who}${tag}`,
          headshot: photo,
          assists: astNames.length > 0 ? astNames : undefined,
          highlightUrl: String(g.highlightClipSharingUrl || ""),
        });
      }
    }
  } else if (!isUpcoming && displayGame.goals && displayGame.goals.length > 0) {
    for (const g of displayGame.goals) {
      const pd = g.periodDescriptor;
      const pNum = pd?.number || 1;
      const pType = pd?.periodType || "REG";
      const pLabel = pType === "OT" ? "OT" : pType === "SO" ? "SO" : `P${pNum}`;
      const tm = typeof g.teamAbbrev === "object" ? (g.teamAbbrev as { default: string }).default : String(g.teamAbbrev || "");
      const first = typeof g.firstName === "object" ? (g.firstName as { default: string }).default : String(g.firstName || "");
      const last = typeof g.lastName === "object" ? (g.lastName as { default: string }).default : String(g.lastName || g.name || "");
      const who = `${first} ${last}`.trim();
      const str = String(g.strength || "").toLowerCase();
      const tag = str === "pp" ? " (PPG)" : str === "sh" ? " (SHG)" : g.goalModifier === "empty-net" ? " (EN)" : "";
      const anyG = g as Record<string, unknown>;
      const pid = anyG.playerId ? Number(anyG.playerId) : 0;
      const photo = String(
        anyG.mugshot || anyG.headshot || (pid > 0 ? `https://assets.nhle.com/mugs/nhl/latest/${pid}.png` : "")
      );

      goalsList.push({
        period: pLabel,
        time: String(g.timeInPeriod || ""),
        team: tm,
        scorer: `${who}${tag}`,
        headshot: photo,
        highlightUrl: String(anyG.highlightClipSharingUrl || ""),
      });
    }
  }

  // Three Stars
  const starsList = !isUpcoming
    ? (((landingData?.summary as Record<string, unknown>)?.threeStars as Array<Record<string, unknown>>) || [])
    : [];

  return (
    <div className="flex flex-col gap-4">
      {/* Main Scoreboard Card */}
      <div className="bg-gradient-to-b from-[#0e1d30] to-[#091524] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
        {/* Glow Accent Strip */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{
            background: isLive
              ? "linear-gradient(90deg, #ff1744, #ff9100)"
              : `linear-gradient(90deg, ${team.primary}, ${team.secondary})`,
          }}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 items-center gap-6">
          {/* Away Team */}
          <div className="flex items-center justify-end gap-4 text-right">
            <div>
              <h2 className="text-base font-black text-slate-100 uppercase tracking-wide">
                {away.commonName?.default || away.name?.default || away.abbrev}
              </h2>
              <p className="text-xs text-slate-400">
                {!isUpcoming && away.sog !== undefined ? `${away.sog} SOG` : awayRecordStr}
              </p>
            </div>
            <img
              src={getTeamLogoUrl(away.abbrev)}
              alt={away.abbrev}
              className="w-14 h-14 object-contain drop-shadow"
              onError={(e) => {
                (e.target as HTMLImageElement).src = "/icon.png";
              }}
            />
          </div>

          {/* Center Score & Game Clock */}
          <div className="flex flex-col items-center justify-center text-center px-4">
            {isUpcoming ? (
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 font-bold text-xs uppercase tracking-wider border border-blue-700/50">
                    Next Game
                  </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-300 font-bold text-xs border border-emerald-700/40">
                    {formatCountdown(displayGame.startTimeUTC)}
                  </span>
                </div>
                <span className="text-lg font-black text-slate-100">
                  {new Date(displayGame.startTimeUTC).toLocaleDateString([], {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
                <span className="text-sm font-semibold text-amber-400 mt-0.5">
                  {new Date(displayGame.startTimeUTC).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            ) : spoilerMode ? (
              <div className="flex flex-col items-center py-2">
                <span className="text-xs uppercase tracking-widest font-bold text-slate-400">
                  {isFinal ? "Final" : "Game In Progress"}
                </span>
                <span className="text-sm text-amber-400 font-medium mt-1">
                  Scores Hidden (Spoiler Mode)
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-3 text-3xl font-black text-white tracking-wider">
                  <span>{away.score ?? 0}</span>
                  <span className="text-slate-600 font-light">-</span>
                  <span>{home.score ?? 0}</span>
                </div>
                <div className="flex items-center gap-1.5 mt-1.5 font-bold text-xs">
                  {isLive && (
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                  )}
                  <span className={isLive ? "text-amber-400" : "text-slate-400"}>
                    {formatTimeRemaining(displayGame)}
                  </span>
                </div>
              </div>
            )}

            {/* Situation Badge */}
            {ppText && (
              <div className="mt-2.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold animate-pulse">
                <Flame className="w-3.5 h-3.5" />
                <span>{ppText}</span>
              </div>
            )}
          </div>

          {/* Home Team */}
          <div className="flex items-center justify-start gap-4 text-left">
            <img
              src={getTeamLogoUrl(home.abbrev)}
              alt={home.abbrev}
              className="w-14 h-14 object-contain drop-shadow"
              onError={(e) => {
                (e.target as HTMLImageElement).src = "/icon.png";
              }}
            />
            <div>
              <h2 className="text-base font-black text-slate-100 uppercase tracking-wide">
                {home.commonName?.default || home.name?.default || home.abbrev}
              </h2>
              <p className="text-xs text-slate-400">
                {!isUpcoming && home.sog !== undefined ? `${home.sog} SOG` : homeRecordStr}
              </p>
            </div>
          </div>
        </div>

        {/* Footer info: Venue & Broadcasts */}
        <div className="mt-5 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>📍 {displayGame.venue?.default || "Arena"}</span>
            {tvNets && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1 text-slate-300">
                  <Tv className="w-3.5 h-3.5 text-blue-400" />
                  <span>{tvNets}</span>
                </span>
              </>
            )}
          </div>

          <button
            onClick={() => openExternalUrl(watchUrl)}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-blue-600/30 hover:bg-blue-600 text-blue-300 hover:text-white font-semibold text-xs border border-blue-500/30 transition cursor-pointer"
          >
            <span>Watch Stream</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Bottom Grid: Next Game Preview (when upcoming) OR Scoring Summary & 3 Stars (when live/final) */}
      {isUpcoming ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Matchup Tale of the Tape */}
          <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-4">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300 mb-3 flex items-center gap-2">
              <Swords className="w-4 h-4 text-blue-400" />
              <span>Matchup Tale of the Tape</span>
            </h3>

            {awayStanding && homeStanding ? (
              <div className="flex flex-col gap-2 text-xs">
                <div className="grid grid-cols-3 items-center py-1.5 border-b border-slate-800/80 font-bold text-slate-200">
                  <span className="text-left text-cyan-400">{away.abbrev} (Away)</span>
                  <span className="text-center text-[10px] uppercase tracking-wider text-slate-500">Metric</span>
                  <span className="text-right text-amber-400">{home.abbrev} (Home)</span>
                </div>

                {[
                  {
                    label: "Record",
                    awayVal: `${awayStanding.wins}-${awayStanding.losses}-${awayStanding.otLosses}`,
                    homeVal: `${homeStanding.wins}-${homeStanding.losses}-${homeStanding.otLosses}`,
                  },
                  {
                    label: "Points (PTS)",
                    awayVal: `${awayStanding.points} (#${awayStanding.divisionSequence} ${awayStanding.divisionAbbrev})`,
                    homeVal: `${homeStanding.points} (#${homeStanding.divisionSequence} ${homeStanding.divisionAbbrev})`,
                  },
                  {
                    label: "Goals For / Against",
                    awayVal: `${awayStanding.goalFor} GF / ${awayStanding.goalAgainst} GA`,
                    homeVal: `${homeStanding.goalFor} GF / ${homeStanding.goalAgainst} GA`,
                  },
                  {
                    label: "Goal Differential",
                    awayVal: awayStanding.goalDifferential > 0 ? `+${awayStanding.goalDifferential}` : `${awayStanding.goalDifferential}`,
                    homeVal: homeStanding.goalDifferential > 0 ? `+${homeStanding.goalDifferential}` : `${homeStanding.goalDifferential}`,
                  },
                  {
                    label: "Streak / L10",
                    awayVal: `${awayStanding.streakCode || ""}${awayStanding.streakCount || ""} (${awayStanding.l10Wins}-${awayStanding.l10Losses}-${awayStanding.l10OtLosses})`,
                    homeVal: `${homeStanding.streakCode || ""}${homeStanding.streakCount || ""} (${homeStanding.l10Wins}-${homeStanding.l10Losses}-${homeStanding.l10OtLosses})`,
                  },
                ].map((row, idx) => (
                  <div
                    key={idx}
                    className="grid grid-cols-3 items-center bg-[#0f1f33] px-3 py-2 rounded border border-slate-800/60"
                  >
                    <span className="font-semibold text-slate-100 text-left">{row.awayVal}</span>
                    <span className="text-[11px] text-slate-400 text-center font-medium">{row.label}</span>
                    <span className="font-semibold text-slate-100 text-right">{row.homeVal}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">Loading team comparison stats...</p>
            )}
          </div>

          {/* Upcoming Schedule Horizon */}
          <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-4">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300 mb-3 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              <span>Upcoming {team.short} Schedule</span>
            </h3>

            {upcomingSlate.length > 0 ? (
              <div className="flex flex-col gap-2">
                {upcomingSlate.map((g, idx) => {
                  const isHomeGame = g.homeTeam.abbrev === team.id;
                  const opp = isHomeGame ? g.awayTeam : g.homeTeam;
                  const dt = new Date(g.startTimeUTC);
                  const tv = (g.tvBroadcasts || [])
                    .filter((b) => b.countryCode === "US")
                    .map((b) => b.network)
                    .filter((v, i, a) => a.indexOf(v) === i)
                    .slice(0, 2)
                    .join(", ");

                  return (
                    <div
                      key={g.id || idx}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs ${
                        idx === 0
                          ? "bg-blue-950/30 border-blue-500/40"
                          : "bg-[#0f1f33] border-slate-800/70"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <img
                          src={getTeamLogoUrl(opp.abbrev)}
                          alt={opp.abbrev}
                          className="w-7 h-7 object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = "/icon.png";
                          }}
                        />
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                                isHomeGame
                                  ? "bg-blue-900/60 text-blue-300"
                                  : "bg-slate-800 text-slate-300"
                              }`}
                            >
                              {isHomeGame ? "VS" : "@"}
                            </span>
                            <span className="font-bold text-slate-100">
                              {opp.commonName?.default || opp.name?.default || opp.abbrev}
                            </span>
                            {idx === 0 && (
                              <span className="text-[10px] font-bold text-emerald-400">
                                • UP NEXT
                              </span>
                            )}
                          </div>
                          {tv && <p className="text-[10px] text-slate-400 mt-0.5">📺 {tv}</p>}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="font-bold text-slate-200">
                          {dt.toLocaleDateString([], {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })}
                        </div>
                        <div className="text-[11px] text-amber-400 font-semibold">
                          {dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No upcoming scheduled games found.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Scoring Summary */}
          <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-4">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300 mb-3 flex items-center gap-2">
              <span>🥅 Scoring Summary</span>
              <span className="text-[10px] text-slate-500 font-normal">
                ({goalsList.length} Goals)
              </span>
            </h3>

            {goalsList.length > 0 ? (
              <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
                {goalsList.map((g, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs bg-[#0f1f33] p-2 rounded-lg border border-slate-800/80 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center gap-2.5">
                      {/* Scorer Mugshot */}
                      {g.headshot ? (
                        <img
                          src={g.headshot}
                          alt={g.scorer}
                          className="w-8 h-8 rounded-full object-cover border border-amber-400/80 bg-[#041e42] shrink-0"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-amber-400 font-bold shrink-0">
                          ★
                        </div>
                      )}
                      <div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-bold text-amber-400 font-mono text-[11px] bg-slate-900/60 px-1 py-0.5 rounded">
                            {g.period} {g.time}
                          </span>
                          <span
                            className={`font-black text-xs ${
                              g.team === team.id ? "text-cyan-400" : "text-slate-300"
                            }`}
                          >
                            [{g.team}]
                          </span>
                          <span className="text-slate-100 font-bold">{g.scorer}</span>
                        </div>
                        {g.assists && g.assists.length > 0 && (
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            Assists: {g.assists.join(", ")}
                          </p>
                        )}
                      </div>
                    </div>

                    {g.highlightUrl && (
                      <button
                        onClick={() => openExternalUrl(g.highlightUrl!)}
                        className="px-2 py-1 rounded bg-blue-900/40 hover:bg-blue-600 text-blue-300 hover:text-white font-semibold text-[10px] border border-blue-500/30 transition shrink-0 ml-2"
                        title="Watch Goal Replay"
                      >
                        ▶ Replay
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No goals scored yet.</p>
            )}
          </div>

          {/* Three Stars of the Game */}
          <div className="bg-[#0b1726] border border-slate-800 rounded-xl p-4">
            <h3 className="text-xs uppercase tracking-wider font-bold text-slate-300 mb-3 flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-400" />
              <span>Three Stars of the Game</span>
            </h3>

            {starsList.length > 0 ? (
              <div className="flex flex-col gap-2.5">
                {starsList.map((s, idx) => {
                  const starNum = idx + 1;
                  const name = typeof s.name === "object" ? (s.name as { default: string }).default : String(s.name || "");
                  const tm = typeof s.teamAbbrev === "object" ? (s.teamAbbrev as { default: string }).default : String(s.teamAbbrev || "");
                  const goals = s.goals !== undefined ? `${s.goals}G ` : "";
                  const assists = s.assists !== undefined ? `${s.assists}A ` : "";
                  const statLine = `${goals}${assists}`.trim();

                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between bg-[#0f1f33] px-3 py-2 rounded border border-slate-800/60 text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-amber-400 font-black text-sm">
                          {"★".repeat(starNum)}
                        </span>
                        <span className="font-bold text-slate-100">{name}</span>
                        <span className="text-slate-400">({tm})</span>
                      </div>
                      {statLine && (
                        <span className="font-semibold text-blue-400 text-xs">
                          {statLine}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                Three stars will be selected following game conclusion.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

