import React, { useState, useEffect, useRef, useCallback } from "react";
import { AppSettings, GameInfo, NewsItem, ShotChartData, StandingsRecord, TeamPreset } from "./types";
import { DEFAULT_SETTINGS, loadAppSettings, saveAppSettings } from "./services/settings";
import { getTeamPreset } from "./config/teams";
import {
  fetchScoreNow,
  fetchSchedule,
  fetchStandings,
  fetchRoster,
  fetchLanding,
  fetchPlayByPlay,
  fetchTeamNews,
  parsePlayByPlay,
  combineShotCharts,
  isCompletedGameStale,
} from "./services/nhlApi";
import { playGoalHorn, playOpponentChime } from "./services/sound";
import { sendDesktopNotification } from "./services/platform";
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
  const [news, setNews] = useState<NewsItem[]>([]);
  const [landingData, setLandingData] = useState<Record<string, unknown> | null>(null);

  // Shot chart data
  const [activeShotChart, setActiveShotChart] = useState<ShotChartData | null>(null);
  const [pastShotCharts, setPastShotCharts] = useState<ShotChartData[]>([]);
  const [seasonCombinedShots, setSeasonCombinedShots] = useState<ShotChartData | null>(null);
  const [shotsLoading, setShotsLoading] = useState<boolean>(false);

  // Goal tracking ref to prevent false alarms
  const lastScoreRef = useRef<{ gameId: number | null; ourScore: number | null; oppScore: number | null }>({
    gameId: null,
    ourScore: null,
    oppScore: null,
  });

  const team: TeamPreset = getTeamPreset(settings.team);

  // Load initial settings
  useEffect(() => {
    loadAppSettings().then((s) => setSettings(s));
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

  // Main Data Refresh function
  const refreshData = useCallback(async () => {
    try {
      setIsRefreshing(true);

      // 1. Fetch live scores and schedule in parallel with independent resilience
      const [scoreRes, schedRes] = await Promise.allSettled([
        fetchScoreNow(),
        fetchSchedule(team.id),
      ]);

      const allGames = scoreRes.status === "fulfilled" ? scoreRes.value.games || [] : [];
      const schedGames = schedRes.status === "fulfilled" ? schedRes.value.games || [] : [];
      if (schedGames.length > 0) {
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
        const curOurScore = isHome ? candidateGame.homeTeam.score ?? 0 : candidateGame.awayTeam.score ?? 0;
        const curOppScore = isHome ? candidateGame.awayTeam.score ?? 0 : candidateGame.homeTeam.score ?? 0;

        if (
          lastScoreRef.current.gameId === candidateGame.id &&
          lastScoreRef.current.ourScore !== null
        ) {
          if (curOurScore > lastScoreRef.current.ourScore) {
            if (settings.sound) playGoalHorn(settings.volume);
            if (settings.toasts) {
              sendDesktopNotification(
                "🚨 GOAL! 🏒",
                `${team.name} scored! (Lead: ${curOurScore}-${curOppScore})`
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

        // Fetch live/fresh landing & play-by-play
        fetchLanding(candidateGame.id)
          .then((l) => setLandingData(l))
          .catch(() => {});

        fetchPlayByPlay(candidateGame.id)
          .then((pbp) => {
            const chart = parsePlayByPlay(pbp, team.nhl_id, team.id);
            setActiveShotChart(chart);
          })
          .catch(() => {});
      } else {
        // More than ~3 hours after the game ended (or off-day): transition Live tab to Next Game
        setLiveGame(null);
        setLandingData(null);

        // Still populate activeShotChart from the most recent completed game for the Shot Chart tab
        if (recentCompleted) {
          fetchPlayByPlay(recentCompleted.id)
            .then((pbp) => {
              const chart = parsePlayByPlay(pbp, team.nhl_id, team.id);
              setActiveShotChart(chart);
            })
            .catch(() => {});
        }
      }

      // 3. Standings
      fetchStandings()
        .then((s) => setStandings(s.standings || []))
        .catch(() => {});

      // 4. News
      fetchTeamNews(team)
        .then((n) => setNews(n))
        .catch(() => {});

      // 5. Roster
      fetchRoster(team.id)
        .then((r) => setRoster(r))
        .catch(() => {});
    } catch (err) {
      console.error("Error refreshing data:", err);
    } finally {
      setIsRefreshing(false);
    }
  }, [team, settings.sound, settings.opponent_sound, settings.volume, settings.toasts]);

  // Load past games shot charts for the Shot Chart tab
  const loadHistoricalShotCharts = useCallback(async () => {
    if (schedule.length === 0) return;
    try {
      setShotsLoading(true);
      const completed = schedule
        .filter((g) => g.gameState === "FINAL" || g.gameState === "OFF")
        .slice(-8); // Load last 8 completed games

      const charts: ShotChartData[] = [];
      for (const g of completed) {
        try {
          const pbp = await fetchPlayByPlay(g.id);
          const parsed = parsePlayByPlay(pbp, team.nhl_id, team.id);
          charts.push(parsed);
        } catch {
          // ignore single game failure
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
    refreshData();
  }, [refreshData]);

  // When switching to the shots tab, load historical charts if not loaded yet
  useEffect(() => {
    if (activeTab === "shots" && pastShotCharts.length === 0) {
      loadHistoricalShotCharts();
    }
  }, [activeTab, pastShotCharts.length, loadHistoricalShotCharts]);

  // Polling cadence timer
  useEffect(() => {
    const isLive = liveGame?.gameState === "LIVE" || liveGame?.gameState === "CRIT";
    const intervalSec = isLive ? 20 : 60;
    const timer = setInterval(() => {
      refreshData();
    }, intervalSec * 1000);
    return () => clearInterval(timer);
  }, [liveGame, refreshData]);

  const handleSelectGameForShots = (gameId: number) => {
    setActiveTab("shots");
  };

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
        onRefresh={refreshData}
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
            spoilerMode={settings.spoiler_mode}
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
          <RosterTab roster={roster} team={team} isLoading={isRefreshing} />
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
