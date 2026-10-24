import React, { useState, useEffect, useRef, useCallback } from "react";
import { AppSettings, GameInfo, NewsItem, ShotChartData, StandingsRecord, TeamPreset } from "./types";
import { DEFAULT_SETTINGS, loadAppSettings, saveAppSettings } from "./services/settings";
import { getTeamPreset } from "./config/teams";
import {
  fetchScoreNow,
  fetchSchedule,
  fetchStandings,
  fetchRoster,
  fetchClubStats,
  fetchLanding,
  fetchRightRail,
  fetchTeamNews,
  fetchAndParseShotChart,
  combineShotCharts,
  formatTimeRemaining,
  isCompletedGameStale,
} from "./services/nhlApi";
import { playGoalHorn, playOpponentChime } from "./services/sound";
import { sendDesktopNotification, syncCloseToTray, updateTrayTooltip } from "./services/platform";
import { Header } from "./components/Header";
import { LiveBanner } from "./components/LiveBanner";
import { ShotChart } from "./components/ShotChart";
import { GamesTab } from "./components/GamesTab";
import { StandingsTab } from "./components/StandingsTab";
import { NewsTab } from "./components/NewsTab";
import { RosterTab } from "./components/RosterTab";
import { SettingsTab } from "./components/SettingsTab";

export const App: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [activeTab, setActiveTab] = useState<string>("live");
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Data states
  const [liveGame, setLiveGame] = useState<GameInfo | null>(null);
  const [nextGame, setNextGame] = useState<GameInfo | null>(null);
  const [schedule, setSchedule] = useState<GameInfo[]>([]);
  const [standings, setStandings] = useState<StandingsRecord[]>([]);
  const [roster, setRoster] = useState<Record<string, unknown> | null>(null);
  const [clubStats, setClubStats] = useState<Record<string, unknown> | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [landingData, setLandingData] = useState<Record<string, unknown> | null>(null);
  const [rightRailData, setRightRailData] = useState<Record<string, unknown> | null>(null);

  // Shot chart data
  const [activeShotChart, setActiveShotChart] = useState<ShotChartData | null>(null);
  const [pastShotCharts, setPastShotCharts] = useState<ShotChartData[]>([]);
  const [seasonCombinedShots, setSeasonCombinedShots] = useState<ShotChartData | null>(null);
  const [shotsLoading, setShotsLoading] = useState<boolean>(false);
  const [selectedShotGameId, setSelectedShotGameId] = useState<string>("active");

  // Goal tracking ref to prevent false alarms
  const lastScoreRef = useRef<{ gameId: number | null; ourScore: number | null; oppScore: number | null }>({
    gameId: null,
    ourScore: null,
    oppScore: null,
  });

  // Caching & rate-limiting refs for background endpoints
  const scheduleRef = useRef<GameInfo[]>([]);
  const lastSlowFetchRef = useRef<{ teamId: string; ts: number }>({ teamId: "", ts: 0 });
  const remindedGamesRef = useRef<Set<number>>(new Set());

  const team: TeamPreset = getTeamPreset(settings.team);

  // Load initial settings and sync close-to-tray state with Rust backend
  useEffect(() => {
    loadAppSettings().then((s) => {
      setSettings(s);
      syncCloseToTray(s.close_to_tray);
    });
  }, []);

  // Listen for tray event "test-goal-horn"
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    import("@tauri-apps/api/event")
      .then(({ listen }) => {
        listen("test-goal-horn", () => {
          playGoalHorn(settings.volume);
        }).then((u) => {
          unlisten = u;
        });
      })
      .catch(() => {});
    return () => {
      if (unlisten) unlisten();
    };
  }, [settings.volume]);

  // Update and save settings
  const handleUpdateSettings = (newPartial: Partial<AppSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newPartial };
      saveAppSettings(updated);
      return updated;
    });
  };

  // Reset historical shot charts when switching teams
  useEffect(() => {
    setPastShotCharts([]);
    setSeasonCombinedShots(null);
    setActiveShotChart(null);
    setSelectedShotGameId("active");
    scheduleRef.current = [];
  }, [team.id]);

  // Main Data Refresh function (decouples fast 20s score polling from 15m background metadata)
  const refreshData = useCallback(
    async (forceSlow: boolean = false) => {
      try {
        setIsRefreshing(true);

        const now = Date.now();
        const shouldFetchSlow =
          forceSlow ||
          lastSlowFetchRef.current.teamId !== team.id ||
          now - lastSlowFetchRef.current.ts > 15 * 60 * 1000 ||
          scheduleRef.current.length === 0;

        // 1. Fetch live scores (always) and schedule (when due or forced)
        const [scoreRes, schedRes] = await Promise.allSettled([
          fetchScoreNow(),
          shouldFetchSlow
            ? fetchSchedule(team.id)
            : Promise.resolve({ games: scheduleRef.current }),
        ]);

        const allGames = scoreRes.status === "fulfilled" ? scoreRes.value.games || [] : [];
        const schedGames =
          schedRes.status === "fulfilled" ? schedRes.value.games || [] : scheduleRef.current;

        if (schedGames.length > 0 && shouldFetchSlow) {
          scheduleRef.current = schedGames;
          setSchedule(schedGames);
        }

        const currentTeamGame = allGames.find(
          (g) => g.homeTeam.abbrev === team.id || g.awayTeam.abbrev === team.id
        );

        // Always resolve the next upcoming game from the schedule (or score/now fallback)
        const nextScheduled =
          schedGames.find((g) => g.gameState === "FUT" || g.gameState === "PRE") ||
          (currentTeamGame && (currentTeamGame.gameState === "FUT" || currentTeamGame.gameState === "PRE")
            ? currentTeamGame
            : null);
        setNextGame(nextScheduled);

        // Puck-drop reminder notification (15 minutes before start or when entering PRE)
        if (settings.toasts && settings.puck_drop_reminder) {
          const reminderTarget =
            currentTeamGame?.gameState === "PRE" ? currentTeamGame : nextScheduled;
          if (reminderTarget && !remindedGamesRef.current.has(reminderTarget.id)) {
            const minsUntil =
              (new Date(reminderTarget.startTimeUTC).getTime() - Date.now()) / 60000;
            if (reminderTarget.gameState === "PRE" || (minsUntil > 0 && minsUntil <= 15)) {
              remindedGamesRef.current.add(reminderTarget.id);
              const startTimeStr = new Date(reminderTarget.startTimeUTC).toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
              });
              sendDesktopNotification(
                "🏒 Puck Drop Soon!",
                `${reminderTarget.awayTeam.abbrev} @ ${reminderTarget.homeTeam.abbrev} starts at ${startTimeStr}`
              );
            }
          }
        }

        const recentCompleted = schedGames
          .filter((g) => g.gameState === "FINAL" || g.gameState === "OFF")
          .pop();

        // Determine if currentTeamGame is actively live/pregame OR finished within the last ~3 hours
        const candidateGame = currentTeamGame || recentCompleted || null;
        const isLiveOrPregame =
          candidateGame &&
          (candidateGame.gameState === "LIVE" ||
            candidateGame.gameState === "CRIT" ||
            candidateGame.gameState === "PRE");
        const isFreshlyCompleted =
          candidateGame &&
          (candidateGame.gameState === "FINAL" || candidateGame.gameState === "OFF") &&
          !isCompletedGameStale(candidateGame, 3);

        // Show live/recent game ONLY if it's in progress or ended less than ~3 hours ago
        if (candidateGame && (isLiveOrPregame || isFreshlyCompleted)) {
          setLiveGame(candidateGame);

          // Check for goals and fire horn
          const isHome = candidateGame.homeTeam.abbrev === team.id;
          const curOurScore = isHome
            ? candidateGame.homeTeam.score ?? 0
            : candidateGame.awayTeam.score ?? 0;
          const curOppScore = isHome
            ? candidateGame.awayTeam.score ?? 0
            : candidateGame.homeTeam.score ?? 0;

          if (
            lastScoreRef.current.gameId === candidateGame.id &&
            lastScoreRef.current.ourScore !== null
          ) {
            if (curOurScore > lastScoreRef.current.ourScore) {
              if (settings.sound) playGoalHorn(settings.volume);
              if (settings.toasts) {
                sendDesktopNotification(
                  "🚨 GOAL! 🏒",
                  `${team.name} scored! (Score: ${curOurScore}-${curOppScore})`
                );
              }
            } else if (curOppScore > (lastScoreRef.current.oppScore ?? 0)) {
              if (settings.opponent_sound) playOpponentChime(settings.volume);
            }
          }

          lastScoreRef.current = {
            gameId: candidateGame.id,
            ourScore: curOurScore,
            oppScore: curOppScore,
          };

          // Fetch live/fresh landing, right-rail boxscore stats, & play-by-play
          fetchLanding(candidateGame.id)
            .then((l) => setLandingData(l))
            .catch(() => {});

          fetchRightRail(candidateGame.id)
            .then((rr) => setRightRailData(rr))
            .catch(() => {});

          fetchAndParseShotChart(
            candidateGame.id,
            team.nhl_id,
            team.id,
            !isLiveOrPregame
          )
            .then((chart) => setActiveShotChart(chart))
            .catch(() => {});
        } else {
          // More than ~3 hours after the game ended (or off-day): transition Live tab to Next Game
          setLiveGame(null);
          setLandingData(null);
          setRightRailData(null);

          // Still populate activeShotChart from the most recent completed game (cached) for the Shot Chart tab
          if (recentCompleted) {
            fetchAndParseShotChart(recentCompleted.id, team.nhl_id, team.id, true)
              .then((chart) => setActiveShotChart(chart))
              .catch(() => {});
          }
        }

        // 3. Background metadata (Standings, News, Roster, Club Stats) — refreshed every 15m or on manual refresh
        if (shouldFetchSlow) {
          lastSlowFetchRef.current = { teamId: team.id, ts: now };

          fetchStandings()
            .then((s) => setStandings(s.standings || []))
            .catch(() => {});

          fetchTeamNews(team)
            .then((n) => setNews(n))
            .catch(() => {});

          fetchRoster(team.id)
            .then((r) => setRoster(r))
            .catch(() => {});

          fetchClubStats(team.id)
            .then((cs) => setClubStats(cs))
            .catch(() => {});
        }
      } catch (err) {
        console.error("Error refreshing data:", err);
      } finally {
        setIsRefreshing(false);
      }
    },
    [
      team,
      settings.sound,
      settings.opponent_sound,
      settings.volume,
      settings.toasts,
      settings.puck_drop_reminder,
    ]
  );

  // Dynamically update the Windows System Tray tooltip with live game or next game status
  useEffect(() => {
    if (liveGame && !settings.spoiler_mode) {
      const away = liveGame.awayTeam;
      const home = liveGame.homeTeam;
      const status = formatTimeRemaining(liveGame);
      updateTrayTooltip(
        `${team.short} Sentinel • ${away.abbrev} ${away.score ?? 0} - ${home.score ?? 0} ${home.abbrev} (${status})`
      );
    } else if (nextGame) {
      const dt = new Date(nextGame.startTimeUTC);
      const dayStr = dt.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
      const timeStr = dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
      updateTrayTooltip(
        `${team.short} Sentinel • Next: ${nextGame.awayTeam.abbrev} @ ${nextGame.homeTeam.abbrev} (${dayStr} ${timeStr})`
      );
    } else {
      updateTrayTooltip(`${team.name} • Gameday Sentinel`);
    }
  }, [liveGame, nextGame, team, settings.spoiler_mode]);

  // Load past games shot charts in parallel with caching for the Shot Chart tab
  const loadHistoricalShotCharts = useCallback(async () => {
    if (schedule.length === 0) return;
    try {
      setShotsLoading(true);
      const completed = schedule
        .filter((g) => g.gameState === "FINAL" || g.gameState === "OFF")
        .slice(-8); // Load last 8 completed games in parallel

      const results = await Promise.allSettled(
        completed.map((g) => fetchAndParseShotChart(g.id, team.nhl_id, team.id, true))
      );

      const charts: ShotChartData[] = [];
      for (const res of results) {
        if (res.status === "fulfilled" && res.value.shots.length > 0) {
          charts.push(res.value);
        }
      }

      setPastShotCharts(charts);
      setSeasonCombinedShots(combineShotCharts(charts, team.id));
    } catch (err) {
      console.error("Failed to load historical shot charts:", err);
    } finally {
      setShotsLoading(false);
    }
  }, [schedule, team]);

  // Initial fetch and team change effect
  useEffect(() => {
    refreshData(true);
  }, [refreshData]);

  // When switching to the shots tab, load historical charts if not loaded yet
  useEffect(() => {
    if (activeTab === "shots" && pastShotCharts.length === 0 && schedule.length > 0) {
      loadHistoricalShotCharts();
    }
  }, [activeTab, pastShotCharts.length, schedule.length, loadHistoricalShotCharts]);

  // Polling cadence timer
  useEffect(() => {
    const isLive = liveGame?.gameState === "LIVE" || liveGame?.gameState === "CRIT";
    const intervalSec = isLive ? 20 : 60;
    const timer = setInterval(() => {
      refreshData(false);
    }, intervalSec * 1000);
    return () => clearInterval(timer);
  }, [liveGame, refreshData]);

  const handleSelectGameForShots = useCallback(
    async (gameId: number) => {
      const idStr = String(gameId);
      setSelectedShotGameId(idStr);
      setActiveTab("shots");

      // If this game isn't already in pastShotCharts (e.g. older than last 8 games), fetch and add it
      if (!pastShotCharts.some((c) => String(c.game_id) === idStr)) {
        try {
          setShotsLoading(true);
          const chart = await fetchAndParseShotChart(gameId, team.nhl_id, team.id, true);
          if (chart.shots.length > 0) {
            setPastShotCharts((prev) =>
              prev.some((c) => String(c.game_id) === idStr) ? prev : [chart, ...prev]
            );
          }
        } catch {
          // ignore
        } finally {
          setShotsLoading(false);
        }
      }
    },
    [pastShotCharts, team]
  );

  return (
    <div className="flex flex-col h-screen bg-[#07111e] text-slate-100 font-sans select-none overflow-hidden">
      {/* Top Header & Navigation */}
      <Header
        team={team}
        onSelectTeam={(teamId) => handleUpdateSettings({ team: teamId })}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isLive={liveGame?.gameState === "LIVE" || liveGame?.gameState === "CRIT"}
        gameStateLabel={
          liveGame?.gameState === "LIVE" || liveGame?.gameState === "CRIT"
            ? "LIVE"
            : liveGame?.gameState === "PRE"
            ? "PREGAME"
            : liveGame?.gameState === "FINAL" || liveGame?.gameState === "OFF"
            ? "FINAL"
            : nextGame
            ? "NEXT GAME"
            : undefined
        }
        onRefresh={() => refreshData(true)}
        isRefreshing={isRefreshing}
      />

      {/* Main Tab Content */}
      <main className="flex-1 overflow-y-auto p-4 max-w-6xl w-full mx-auto">
        {activeTab === "live" && (
          <LiveBanner
            game={liveGame}
            nextGame={nextGame}
            team={team}
            landingData={landingData}
            rightRailData={rightRailData}
            spoilerMode={settings.spoiler_mode}
            watchTarget={settings.watch}
            standings={standings}
            schedule={schedule}
          />
        )}

        {activeTab === "shots" && (
          <ShotChart
            team={team}
            activeGameData={activeShotChart}
            pastGamesData={pastShotCharts}
            seasonCombinedData={seasonCombinedShots}
            isLoading={shotsLoading}
            selectedGameId={selectedShotGameId}
            onSelectGameId={setSelectedShotGameId}
          />
        )}

        {activeTab === "games" && (
          <GamesTab
            team={team}
            schedule={schedule}
            onSelectGameForShots={handleSelectGameForShots}
            spoilerMode={settings.spoiler_mode}
          />
        )}

        {activeTab === "standings" && (
          <StandingsTab standings={standings} team={team} />
        )}

        {activeTab === "news" && (
          <NewsTab news={news} team={team} isLoading={isRefreshing} />
        )}

        {activeTab === "roster" && (
          <RosterTab
            roster={roster}
            clubStats={clubStats}
            team={team}
            isLoading={isRefreshing}
          />
        )}

        {activeTab === "settings" && (
          <SettingsTab
            settings={settings}
            onUpdateSettings={handleUpdateSettings}
            team={team}
          />
        )}
      </main>
    </div>
  );
};
