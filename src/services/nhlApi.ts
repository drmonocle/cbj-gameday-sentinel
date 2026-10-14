import { invoke } from "@tauri-apps/api/core";
import { GameInfo, NewsItem, PlayerBio, ShotChartData, ShotEvent, StandingsRecord, TeamPreset } from "../types";

const NHL_API = "https://api-web.nhle.com/v1";

async function fetchJson<T>(url: string): Promise<T> {
  try {
    const raw = await invoke<string>("fetch_url", { url });
    const cleaned = (raw || "").replace(/^\uFEFF/, "").trim();
    if (!cleaned) throw new Error("Empty response from native fetch_url");
    return JSON.parse(cleaned);
  } catch (err) {
    console.warn(`Native fetch_url fallback for ${url}:`, err);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
}

export async function fetchScoreNow(): Promise<{ games: GameInfo[] }> {
  return fetchJson<{ games: GameInfo[] }>(`${NHL_API}/score/now`);
}

export async function fetchSchedule(team: string): Promise<{ games: GameInfo[] }> {
  return fetchJson<{ games: GameInfo[] }>(`${NHL_API}/club-schedule-season/${team}/now`);
}

export async function fetchStandings(): Promise<{ standings: StandingsRecord[] }> {
  return fetchJson<{ standings: StandingsRecord[] }>(`${NHL_API}/standings/now`);
}

export async function fetchRoster(team: string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`${NHL_API}/roster/${team}/current`);
}

export async function fetchClubStats(team: string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`${NHL_API}/club-stats/${team}/now`);
}

export async function fetchBoxscore(gameId: number | string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`${NHL_API}/gamecenter/${gameId}/boxscore`);
}

export async function fetchLanding(gameId: number | string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`${NHL_API}/gamecenter/${gameId}/landing`);
}

export async function fetchPlayByPlay(gameId: number | string): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(`${NHL_API}/gamecenter/${gameId}/play-by-play`);
}

export async function fetchPlayerBio(playerId: number | string): Promise<PlayerBio> {
  return fetchJson<PlayerBio>(`${NHL_API}/player/${playerId}/landing`);
}

export async function fetchTeamNews(teamPreset: TeamPreset): Promise<NewsItem[]> {
  const items: NewsItem[] = [];

  // 1. Official NHL Forge News
  try {
    const forgeUrl = `https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=teamid-${teamPreset.nhl_id}&context.slug=nhl&$limit=15`;
    const data = await fetchJson<{ items: Array<Record<string, unknown>> }>(forgeUrl);
    for (const item of data.items || []) {
      items.push({
        id: `nhl-${item.slug || Math.random()}`,
        title: String(item.headline || item.title || ""),
        link: `https://www.nhl.com/news/${item.slug}`,
        source: "NHL.com",
        desc: String(item.summary || ""),
        ts: item.contentDate ? new Date(String(item.contentDate)).getTime() : Date.now(),
      });
    }
  } catch (err) {
    console.warn("Forge news fetch failed:", err);
  }

  // 2. ESPN News
  try {
    const espnUrl = `https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?team=${teamPreset.espn_id}&limit=15`;
    const data = await fetchJson<{ articles: Array<Record<string, unknown>> }>(espnUrl);
    for (const a of data.articles || []) {
      const link = String((a.links as { web?: { href?: string } })?.web?.href || "");
      items.push({
        id: `espn-${a.id || Math.random()}`,
        title: String(a.headline || ""),
        link: link.replace("http://", "https://"),
        source: "ESPN",
        desc: String(a.description || ""),
        ts: a.published ? new Date(String(a.published)).getTime() : Date.now(),
      });
    }
  } catch (err) {
    console.warn("ESPN news fetch failed:", err);
  }

  // Sort newest first
  return items.sort((a, b) => b.ts - a.ts);
}

// -----------------------------------------------------------------------------
// Shot Chart Parser & Coordinate Normalization
// -----------------------------------------------------------------------------

function attackSign(play: Record<string, unknown>, owner: number, homeId: number, awayId: number): number | null {
  const side = String(play.homeTeamDefendingSide || "").toLowerCase();
  if ((side !== "left" && side !== "right") || (owner !== homeId && owner !== awayId) || homeId === awayId) {
    return null;
  }
  const homeAttacksRight = side === "left";
  return (owner === homeId) === homeAttacksRight ? 1 : -1;
}

export function parsePlayByPlay(
  pbp: Record<string, unknown>,
  targetId: number,
  targetAbbrev: string
): ShotChartData {
  if (!pbp || typeof pbp !== "object") {
    return {
      game_id: 0,
      game_date: "",
      matchup: "",
      opponent: "OPP",
      counts: { target_sog: 0, target_goals: 0, opp_sog: 0, opp_goals: 0, total_shots: 0 },
      shots: [],
    };
  }

  const players: Record<number, string> = {};
  const playerHeadshots: Record<number, string> = {};
  const playerSweaters: Record<number, number> = {};
  const rosterSpots = (pbp.rosterSpots as Array<Record<string, unknown>>) || [];
  for (const p of rosterSpots) {
    const pid = p.playerId as number;
    if (pid) {
      const first = typeof p.firstName === "object" ? (p.firstName as { default: string }).default : p.firstName || "";
      const last = typeof p.lastName === "object" ? (p.lastName as { default: string }).default : p.lastName || "";
      players[pid] = `${first} ${last}`.trim();
      if (p.headshot) {
        playerHeadshots[pid] = String(p.headshot);
      }
      if (p.sweaterNumber !== undefined && p.sweaterNumber !== null) {
        playerSweaters[pid] = Number(p.sweaterNumber);
      }
    }
  }

  const home = (pbp.homeTeam as Record<string, unknown>) || {};
  const away = (pbp.awayTeam as Record<string, unknown>) || {};
  const homeId = (home.id as number) || 0;
  const awayId = (away.id as number) || 0;
  const homeAbbrev = typeof home.abbrev === "object" ? (home.abbrev as { default: string }).default : String(home.abbrev || "");
  const awayAbbrev = typeof away.abbrev === "object" ? (away.abbrev as { default: string }).default : String(away.abbrev || "");

  const isHomeTarget = homeId === targetId || homeAbbrev === targetAbbrev;
  const resolvedTargetId = isHomeTarget ? homeId : awayId;
  const oppAbbrev = (isHomeTarget ? awayAbbrev : homeAbbrev) || "OPP";
  const gameDate = String(pbp.gameDate || "");
  const homeScore = Number(home.score || 0);
  const awayScore = Number(away.score || 0);
  const venue = (pbp.venue as { default?: string })?.default || "";
  const matchup = `${awayAbbrev} @ ${homeAbbrev}`;
  const targetScore = isHomeTarget ? homeScore : awayScore;
  const oppScore = isHomeTarget ? awayScore : homeScore;

  const shots: ShotEvent[] = [];
  let targetSog = 0;
  let targetGoals = 0;
  let oppSog = 0;
  let oppGoals = 0;
  let targetHdc = 0;
  let oppHdc = 0;

  const plays = (pbp.plays as Array<Record<string, unknown>>) || [];
  for (const p of plays) {
    const typeKey = String(p.typeDescKey || "");
    if (!["goal", "shot-on-goal", "missed-shot", "blocked-shot"].includes(typeKey)) {
      continue;
    }

    const pd = (p.periodDescriptor as Record<string, unknown>) || {};
    if (pd.periodType === "SO") {
      continue; // exclude shootout attempts from regulation rink geometry
    }

    const det = (p.details as Record<string, unknown>) || {};
    const rawX = det.xCoord;
    const rawY = det.yCoord;
    if (rawX === undefined || rawX === null || rawY === undefined || rawY === null) {
      continue;
    }

    const fx = Number(rawX);
    const fy = Number(rawY);
    if (isNaN(fx) || isNaN(fy)) continue;

    const owner = Number(det.eventOwnerTeamId || 0);
    let sign = typeKey === "blocked-shot" ? null : attackSign(p, owner, homeId, awayId);
    if (sign === null) {
      sign = fx < 0 ? -1 : 1;
    }

    // Normalize so offensive shot attacks the net at (89, 0)
    const nx = fx * sign;
    const ny = fy * sign;
    const dist = Math.round(Math.sqrt(Math.pow(89.0 - nx, 2) + Math.pow(ny, 2)) * 10) / 10;
    const isHighDanger = dist <= 22 && Math.abs(ny) <= 12;

    let isTarget = owner === resolvedTargetId || (targetId ? owner === targetId : false);
    if (owner && !isTarget) {
      if (isHomeTarget && owner === homeId) isTarget = true;
      else if (!isHomeTarget && owner === awayId) isTarget = true;
    }

    if (typeKey === "goal") {
      if (isTarget) {
        targetGoals++;
        targetSog++;
      } else {
        oppGoals++;
        oppSog++;
      }
    } else if (typeKey === "shot-on-goal") {
      if (isTarget) targetSog++;
      else oppSog++;
    }

    if (isHighDanger && ["goal", "shot-on-goal", "missed-shot"].includes(typeKey)) {
      if (isTarget) targetHdc++;
      else oppHdc++;
    }

    const pid = Number(det.scoringPlayerId || det.shootingPlayerId || det.blockingPlayerId || 0);
    const playerName = players[pid] || "Unknown";
    const teamAbbrevVal = isTarget ? targetAbbrev : oppAbbrev;
    const headshotUrl =
      playerHeadshots[pid] ||
      (pid > 0 ? `https://assets.nhle.com/mugs/nhl/latest/${pid}.png` : undefined);
    const sweater = playerSweaters[pid];

    const assistsList: string[] = [];
    if (typeKey === "goal") {
      const a1Id = det.assist1PlayerId ? Number(det.assist1PlayerId) : 0;
      const a2Id = det.assist2PlayerId ? Number(det.assist2PlayerId) : 0;
      if (a1Id && players[a1Id]) assistsList.push(players[a1Id]);
      if (a2Id && players[a2Id]) assistsList.push(players[a2Id]);
    }

    shots.push({
      id: Number(p.eventId || 0),
      game_id: pbp.id as number,
      game_date: gameDate,
      matchup,
      opponent: oppAbbrev,
      period: Number(pd.number || 1),
      time: String(p.timeInPeriod || ""),
      type: typeKey as ShotEvent["type"],
      shotType: String(det.shotType || "shot"),
      x: nx,
      y: ny,
      dist,
      player: playerName,
      playerId: pid,
      headshot: headshotUrl,
      sweaterNumber: sweater,
      assists: assistsList.length > 0 ? assistsList : undefined,
      is_cbj: isTarget,
      team_abbrev: teamAbbrevVal,
      isHighDanger,
    });
  }

  return {
    game_id: pbp.id as number,
    game_date: gameDate,
    matchup,
    opponent: oppAbbrev,
    venue,
    target_score: targetScore,
    opp_score: oppScore,
    is_home: isHomeTarget,
    counts: {
      target_sog: targetSog,
      target_goals: targetGoals,
      opp_sog: oppSog,
      opp_goals: oppGoals,
      total_shots: shots.length,
      target_sh_pct: targetSog > 0 ? Math.round((targetGoals / targetSog) * 1000) / 10 : 0,
      opp_sh_pct: oppSog > 0 ? Math.round((oppGoals / oppSog) * 1000) / 10 : 0,
      target_hdc: targetHdc,
      opp_hdc: oppHdc,
    },
    shots,
  };
}

export function combineShotCharts(charts: ShotChartData[], targetAbbrev: string): ShotChartData {
  const valid = charts.filter((c) => c && c.shots && c.shots.length > 0);
  const combinedShots: ShotEvent[] = [];
  let tSog = 0;
  let tGoals = 0;
  let oSog = 0;
  let oGoals = 0;
  let tHdc = 0;
  let oHdc = 0;

  for (const c of valid) {
    combinedShots.push(...c.shots);
    tSog += c.counts.target_sog;
    tGoals += c.counts.target_goals;
    oSog += c.counts.opp_sog;
    oGoals += c.counts.opp_goals;
    tHdc += c.counts.target_hdc || 0;
    oHdc += c.counts.opp_hdc || 0;
  }

  return {
    game_id: "combined",
    game_date: "Season Summary",
    matchup: `All Season Games Combined (${valid.length} Games)`,
    opponent: "All Opponents",
    venue: "Multiple Venues",
    games_count: valid.length,
    target_score: tGoals,
    opp_score: oGoals,
    is_home: true,
    counts: {
      target_sog: tSog,
      target_goals: tGoals,
      opp_sog: oSog,
      opp_goals: oGoals,
      total_shots: combinedShots.length,
      target_sh_pct: tSog > 0 ? Math.round((tGoals / tSog) * 1000) / 10 : 0,
      opp_sh_pct: oSog > 0 ? Math.round((oGoals / oSog) * 1000) / 10 : 0,
      target_hdc: tHdc,
      opp_hdc: oHdc,
    },
    shots: combinedShots,
  };
}

export function formatTimeRemaining(game: GameInfo): string {
  if (game.gameState === "FINAL" || game.gameState === "OFF") return "Final";
  if (game.gameState === "PRE" || game.gameState === "FUT") {
    const d = new Date(game.startTimeUTC);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  const pd = game.periodDescriptor;
  const num = pd?.number || 1;
  const ptype = pd?.periodType || "REG";
  let plabel = `${num}th`;
  if (num === 1) plabel = "1st";
  else if (num === 2) plabel = "2nd";
  else if (num === 3) plabel = "3rd";
  if (ptype === "OT") plabel = num <= 4 ? "OT" : `${num - 3}OT`;
  if (ptype === "SO") plabel = "SO";

  if (game.clock?.inIntermission) {
    return `${plabel} Intermission (${game.clock?.timeRemaining || ""})`;
  }

  return `${plabel} ${game.clock?.timeRemaining || ""}`;
}

/**
 * Returns true if a completed game ("FINAL" or "OFF") ended more than `postGameHours` ago.
 * Standard NHL games last ~2.75 hours from startTimeUTC, so (2.75 + postGameHours) hours
 * after startTimeUTC marks the rollover point to the next scheduled game.
 */
export function isCompletedGameStale(game: GameInfo, postGameHours = 3): boolean {
  if (game.gameState !== "FINAL" && game.gameState !== "OFF") {
    return false;
  }
  if (!game.startTimeUTC) {
    return false;
  }
  const startMs = new Date(game.startTimeUTC).getTime();
  if (isNaN(startMs)) {
    return false;
  }
  const estimatedGameDurationHours = 2.75;
  const rolloverWindowMs = (estimatedGameDurationHours + postGameHours) * 3600 * 1000;
  return Date.now() - startMs > rolloverWindowMs;
}

