import React, { useState, useMemo } from "react";
import { ShotChartData, ShotEvent, TeamPreset } from "../types";
import { Crosshair, Star, Info, Flame, ChevronDown, Sparkles } from "lucide-react";

interface ShotChartProps {
  team: TeamPreset;
  activeGameData: ShotChartData | null;
  pastGamesData: ShotChartData[];
  seasonCombinedData: ShotChartData | null;
  isLoading: boolean;
  selectedGameId?: string;
  onSelectGameId?: (gameId: string) => void;
}

export const ShotChart: React.FC<ShotChartProps> = ({
  team,
  activeGameData,
  pastGamesData,
  seasonCombinedData,
  isLoading,
  selectedGameId: controlledGameId,
  onSelectGameId,
}) => {
  const [internalGameId, setInternalGameId] = useState<string>("active");
  const selectedGameId = controlledGameId ?? internalGameId;
  const setSelectedGameId = (val: string) => {
    setInternalGameId(val);
    if (onSelectGameId) onSelectGameId(val);
  };
  const [filterTeam, setFilterTeam] = useState<"all" | "target" | "opp">("all");
  const [filterType, setFilterType] = useState<"all" | "sog" | "goals" | "missed">("all");
  const [filterDanger, setFilterDanger] = useState<"all" | "high">("all");
  const [filterPeriod, setFilterPeriod] = useState<number>(0); // 0 = all
  const [hoveredShot, setHoveredShot] = useState<ShotEvent | null>(null);

  // Resolve current active dataset based on user selection
  const currentChartData = useMemo(() => {
    if (selectedGameId === "active") {
      return activeGameData || pastGamesData[0] || null;
    }
    if (selectedGameId === "combined") {
      return seasonCombinedData;
    }
    return pastGamesData.find((g) => String(g.game_id) === selectedGameId) || null;
  }, [selectedGameId, activeGameData, pastGamesData, seasonCombinedData]);

  // Filter shots
  const filteredShots = useMemo(() => {
    if (!currentChartData) return [];
    return currentChartData.shots.filter((s) => {
      // Must be in offensive half (x >= 0)
      if (s.x < 0) return false;

      // Team filter
      if (filterTeam === "target" && !s.is_cbj) return false;
      if (filterTeam === "opp" && s.is_cbj) return false;

      // Type filter
      if (filterType === "goals" && s.type !== "goal") return false;
      if (filterType === "sog" && !["goal", "shot-on-goal"].includes(s.type)) return false;
      if (filterType === "missed" && ["goal", "shot-on-goal"].includes(s.type)) return false;

      // High danger filter
      if (filterDanger === "high" && !s.isHighDanger) return false;

      // Period filter
      if (filterPeriod !== 0 && s.period !== filterPeriod) return false;

      return true;
    });
  }, [currentChartData, filterTeam, filterType, filterDanger, filterPeriod]);

  // Separate regular shots and goals so goals render on top
  const regularShots = useMemo(
    () => filteredShots.filter((s) => s.type !== "goal"),
    [filteredShots]
  );
  const goalShots = useMemo(
    () => filteredShots.filter((s) => s.type === "goal"),
    [filteredShots]
  );

  // Compute stats for current filter
  const stats = useMemo(() => {
    let tSog = 0;
    let tGoals = 0;
    let oSog = 0;
    let oGoals = 0;
    let tHdc = 0;
    let oHdc = 0;
    const totalFiltered = filteredShots.length;

    for (const s of filteredShots) {
      if (s.type === "goal") {
        if (s.is_cbj) {
          tGoals++;
          tSog++;
        } else {
          oGoals++;
          oSog++;
        }
      } else if (s.type === "shot-on-goal") {
        if (s.is_cbj) tSog++;
        else oSog++;
      }

      if (s.isHighDanger) {
        if (s.is_cbj) tHdc++;
        else oHdc++;
      }
    }

    return { tSog, tGoals, oSog, oGoals, tHdc, oHdc, totalFiltered };
  }, [filteredShots]);

  // SVG coordinate transformation:
  // x: 0 (center red line) to 100 (end boards)
  // y: -42.5 (left boards) to 42.5 (right boards)
  // ViewBox: 0 0 600 300
  const mapPoint = (nx: number, ny: number) => {
    const padX = 24;
    const padY = 16;
    const rw = 600 - padX * 2;
    const rh = 300 - padY * 2;
    const px = padX + (nx / 100.0) * rw;
    const py = padY + ((ny + 42.5) / 85.0) * rh;
    return { px, py };
  };

  return (
    <div className="flex flex-col h-full bg-[#0a1420] text-slate-100 rounded-lg overflow-hidden border border-slate-800">
      {/* Game Selector Bar & Banner */}
      <div className="bg-[#0e1b2b] px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-blue-900/40 text-blue-400">
            <Crosshair className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-bold text-blue-400">
                Interactive Shot Chart
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs font-semibold text-amber-400">
                {currentChartData?.game_id === "combined"
                  ? `Combined Season Dataset (${currentChartData.games_count} Games)`
                  : currentChartData?.matchup || "No Game Selected"}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {currentChartData?.game_date && `${currentChartData.game_date} • `}
              {currentChartData?.venue && `${currentChartData.venue} • `}
              {currentChartData?.target_score !== undefined &&
                `Score: ${team.id} ${currentChartData.target_score} - ${currentChartData.opp_score} ${currentChartData.opponent}`}
            </p>
          </div>
        </div>

        {/* Dropdown Game Selector */}
        <div className="relative">
          <select
            value={selectedGameId}
            onChange={(e) => setSelectedGameId(e.target.value)}
            className="bg-[#142338] border border-slate-700 text-xs font-semibold text-slate-200 rounded-lg px-3 py-1.5 pr-8 appearance-none cursor-pointer focus:outline-none focus:border-blue-500"
          >
            <option value="active">
              Current / Latest Game ({activeGameData?.opponent ? `vs ${activeGameData.opponent}` : "Latest"})
            </option>
            {seasonCombinedData && (
              <option value="combined">
                ★ All Season Games Combined ({seasonCombinedData.games_count} Games)
              </option>
            )}
            <optgroup label="Past Season Games">
              {pastGamesData.map((g) => (
                <option key={g.game_id} value={String(g.game_id)}>
                  {g.game_date} - {g.matchup} ({g.target_score}-{g.opp_score})
                </option>
              ))}
            </optgroup>
          </select>
          <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
        </div>
      </div>

      {/* Filter Controls Row */}
      <div className="bg-[#0b1726] px-4 py-2 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Team Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">Team:</span>
            <div className="inline-flex rounded-md p-0.5 bg-[#122033] border border-slate-700/60">
              <button
                onClick={() => setFilterTeam("all")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterTeam === "all" ? "bg-red-700 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Both
              </button>
              <button
                onClick={() => setFilterTeam("target")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterTeam === "target" ? "bg-red-700 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {team.id} Only
              </button>
              <button
                onClick={() => setFilterTeam("opp")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterTeam === "opp" ? "bg-red-700 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {currentChartData?.opponent || "Opp"} Only
              </button>
            </div>
          </div>

          {/* Shot Type Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">Type:</span>
            <div className="inline-flex rounded-md p-0.5 bg-[#122033] border border-slate-700/60">
              <button
                onClick={() => setFilterType("all")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterType === "all" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterType("goals")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterType === "goals" ? "bg-amber-500 text-slate-950 font-black" : "text-amber-400 hover:text-amber-300"
                }`}
              >
                ★ Goals ({stats.tGoals + stats.oGoals})
              </button>
              <button
                onClick={() => setFilterType("sog")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterType === "sog" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                SOG
              </button>
              <button
                onClick={() => setFilterType("missed")}
                className={`px-2 py-1 rounded text-xs font-semibold transition ${
                  filterType === "missed" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Miss/Block
              </button>
            </div>
          </div>

          {/* High Danger Filter */}
          <button
            onClick={() => setFilterDanger((prev) => (prev === "all" ? "high" : "all"))}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold transition border ${
              filterDanger === "high"
                ? "bg-amber-500/30 text-amber-300 border-amber-500/70 shadow-sm shadow-amber-500/20"
                : "bg-[#122033] text-slate-400 border-slate-700/60 hover:text-amber-400"
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-amber-400" />
            <span>Slot High Danger</span>
          </button>

          {/* Period Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">Period:</span>
            <div className="inline-flex rounded-md p-0.5 bg-[#122033] border border-slate-700/60">
              {[0, 1, 2, 3, 4].map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPeriod(p)}
                  className={`px-2 py-1 rounded text-xs font-semibold transition ${
                    filterPeriod === p ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  {p === 0 ? "All" : p === 4 ? "OT" : `P${p}`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-slate-400 text-xs">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3.5 h-3.5 rounded-full border border-amber-400 bg-amber-500/30 text-center leading-3 text-[9px] font-bold text-amber-300">
              ★
            </span>{" "}
            Goal Headshot
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400"></span> {team.id} SOG
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-slate-300"></span> Opp SOG
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full border border-slate-500"></span> Miss/Block
          </span>
        </div>
      </div>

      {/* Rink Canvas Area */}
      <div className="relative flex-1 bg-[#06101c] p-3 flex items-center justify-center min-h-[340px]">
        {isLoading && (
          <div className="absolute inset-0 bg-[#06101c]/80 flex items-center justify-center z-30">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        )}

        <svg
          viewBox="0 0 600 300"
          className="w-full h-full max-h-[480px] drop-shadow-2xl select-none"
        >
          <defs>
            {/* Ice Texture Gradient */}
            <radialGradient id="rink-ice" cx="65%" cy="50%" r="55%">
              <stop offset="0%" stopColor="#0e2338" />
              <stop offset="60%" stopColor="#091727" />
              <stop offset="100%" stopColor="#06121f" />
            </radialGradient>

            {/* Nylon Goal Net Mesh Pattern */}
            <pattern
              id="goal-net-mesh"
              width="4"
              height="4"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 0 0 L 4 4 M 4 0 L 0 4"
                stroke="rgba(255, 255, 255, 0.35)"
                strokeWidth="0.6"
              />
            </pattern>

            {/* Alternating Diamond Pattern for Center Red Line */}
            <pattern
              id="nhl-red-line"
              width="8"
              height="8"
              patternUnits="userSpaceOnUse"
            >
              <rect width="8" height="8" fill="#c62828" />
              <polygon points="4,1 7,4 4,7 1,4" fill="#ffffff" />
            </pattern>

            {/* Goal Glow Filter */}
            <filter id="goal-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>

            {/* Circular Clip Paths for Each Goal Scorer */}
            {goalShots.map((shot) => {
              const shotUid = `${shot.game_id}-${shot.id}`;
              const { px, py } = mapPoint(shot.x, shot.y);
              const isHovered = hoveredShot?.id === shot.id && hoveredShot?.game_id === shot.game_id;
              const r = isHovered ? 21 : 16;
              return (
                <clipPath id={`avatar-clip-${shotUid}`} key={`clip-${shotUid}`}>
                  <circle cx={px} cy={py} r={r} />
                </clipPath>
              );
            })}
          </defs>

          {/* Rink Ice Surface */}
          <rect
            x="24"
            y="16"
            width="552"
            height="268"
            fill="url(#rink-ice)"
            stroke="#1d3859"
            strokeWidth="2.5"
            rx="56"
          />

          {/* Outer Dashed Board Ring / Arena Railing */}
          <rect
            x="22"
            y="14"
            width="556"
            height="272"
            fill="none"
            stroke="#0b1726"
            strokeWidth="3"
            rx="58"
          />

          {/* Center Red Line (x = 0) with NHL Diamond Pattern */}
          <line
            x1="24"
            y1="16"
            x2="24"
            y2="284"
            stroke="url(#nhl-red-line)"
            strokeWidth="5"
          />

          {/* Neutral Zone Faceoff Dots (x = 20, y = ±22) */}
          <circle cx={mapPoint(20, -22).px} cy={mapPoint(20, -22).py} r="4.5" fill="#c62828" />
          <circle cx={mapPoint(20, 22).px} cy={mapPoint(20, 22).py} r="4.5" fill="#c62828" />

          {/* Blue Line (x = 25) - 12-inch regulation */}
          <line
            x1={mapPoint(25, 0).px}
            y1="16"
            x2={mapPoint(25, 0).px}
            y2="284"
            stroke="#1565c0"
            strokeWidth="5"
          />

          {/* Faceoff Circles (x = 69, y = ±22, r = 15 ft) */}
          {[-22, 22].map((yDot) => {
            const { px, py } = mapPoint(69, yDot);
            const rPxX = (15 / 100) * (600 - 48);
            const rPxY = (15 / 85) * (300 - 32);
            return (
              <g key={yDot}>
                <ellipse
                  cx={px}
                  cy={py}
                  rx={rPxX}
                  ry={rPxY}
                  fill="none"
                  stroke="#c62828"
                  strokeWidth="1.6"
                />
                {/* Center Faceoff Dot */}
                <circle cx={px} cy={py} r="4" fill="#c62828" />
                {/* Regulation Hash Marks */}
                <line x1={px - rPxX - 3.5} y1={py - 6} x2={px - rPxX + 3.5} y2={py - 6} stroke="#c62828" strokeWidth="1.6" />
                <line x1={px + rPxX - 3.5} y1={py - 6} x2={px + rPxX + 3.5} y2={py - 6} stroke="#c62828" strokeWidth="1.6" />
                <line x1={px - rPxX - 3.5} y1={py + 6} x2={px - rPxX + 3.5} y2={py + 6} stroke="#c62828" strokeWidth="1.6" />
                <line x1={px + rPxX - 3.5} y1={py + 6} x2={px + rPxX + 3.5} y2={py + 6} stroke="#c62828" strokeWidth="1.6" />
              </g>
            );
          })}

          {/* High Danger Scoring Area (Slot / Home Plate) */}
          <polygon
            points={`
              ${mapPoint(89, -9).px},${mapPoint(89, -9).py}
              ${mapPoint(69, -12).px},${mapPoint(69, -12).py}
              ${mapPoint(69, 12).px},${mapPoint(69, 12).py}
              ${mapPoint(89, 9).px},${mapPoint(89, 9).py}
            `}
            fill="#ff9800"
            fillOpacity={filterDanger === "high" ? 0.12 : 0.04}
            stroke="#ff9800"
            strokeOpacity={filterDanger === "high" ? 0.45 : 0.2}
            strokeWidth="1.5"
            strokeDasharray={filterDanger === "high" ? "none" : "4 4"}
          />

          {/* Goal Line (x = 89) */}
          <line
            x1={mapPoint(89, 0).px}
            y1="24"
            x2={mapPoint(89, 0).px}
            y2="276"
            stroke="#c62828"
            strokeWidth="2.5"
          />

          {/* Goal Crease (x = 89, semi-circle facing center) */}
          <path
            d={`M ${mapPoint(89, -4.5).px} ${mapPoint(89, -4.5).py} A 19 19 0 0 0 ${mapPoint(89, 4.5).px} ${mapPoint(89, 4.5).py} Z`}
            fill="#38bdf8"
            fillOpacity="0.45"
            stroke="#c62828"
            strokeWidth="1.8"
          />

          {/* Trapezoid Lines (x = 89 to 100, y = ±11 to ±14) */}
          <line
            x1={mapPoint(89, -11).px}
            y1={mapPoint(89, -11).py}
            x2={mapPoint(100, -14).px}
            y2={mapPoint(100, -14).py}
            stroke="#c62828"
            strokeWidth="1.6"
          />
          <line
            x1={mapPoint(89, 11).px}
            y1={mapPoint(89, 11).py}
            x2={mapPoint(100, 14).px}
            y2={mapPoint(100, 14).py}
            stroke="#c62828"
            strokeWidth="1.6"
          />

          {/* Goal Net (x = 89 to 93, y = -3 to 3) */}
          <g>
            <rect
              x={mapPoint(89, -3).px}
              y={mapPoint(89, -3).py}
              width={(4 / 100) * (600 - 48)}
              height={(6 / 85) * (300 - 32)}
              fill="url(#goal-net-mesh)"
              stroke="#d32f2f"
              strokeWidth="2"
              rx="2"
            />
            {/* White crossbar line */}
            <line
              x1={mapPoint(89, -3).px}
              y1={mapPoint(89, -3).py}
              x2={mapPoint(89, -3).px}
              y2={mapPoint(89, 3).py}
              stroke="#ffffff"
              strokeWidth="2.5"
            />
          </g>

          {/* 1. REGULAR SHOT MARKERS (Rendered first so goals stay on top) */}
          {regularShots.map((shot) => {
            const shotUid = `${shot.game_id}-${shot.id}`;
            const { px, py } = mapPoint(shot.x, shot.y);
            const isHovered = hoveredShot?.id === shot.id && hoveredShot?.game_id === shot.game_id;

            if (shot.type === "shot-on-goal") {
              const fillColor = shot.is_cbj ? "#00e5ff" : "#eceff1";
              const strokeColor = shot.is_cbj ? "#002654" : "#37474f";
              return (
                <circle
                  key={shotUid}
                  cx={px}
                  cy={py}
                  r={isHovered ? 7.5 : 4.5}
                  fill={fillColor}
                  stroke={isHovered ? "#ffeb3b" : strokeColor}
                  strokeWidth={isHovered ? 2.5 : 1.2}
                  className="cursor-pointer transition-all duration-150"
                  onMouseEnter={() => setHoveredShot(shot)}
                  onMouseLeave={() => setHoveredShot(null)}
                />
              );
            }

            // Missed or Blocked shot
            return (
              <circle
                key={shotUid}
                cx={px}
                cy={py}
                r={isHovered ? 6 : 3.5}
                fill="none"
                stroke={isHovered ? "#ffeb3b" : "#78909c"}
                strokeWidth={isHovered ? 2 : 1}
                strokeDasharray="2.5 2.5"
                className="cursor-pointer transition-all duration-150"
                onMouseEnter={() => setHoveredShot(shot)}
                onMouseLeave={() => setHoveredShot(null)}
              />
            );
          })}

          {/* 2. REALISTIC GOAL MARKERS (Rendered with Player Headshots!) */}
          {goalShots.map((shot) => {
            const shotUid = `${shot.game_id}-${shot.id}`;
            const { px, py } = mapPoint(shot.x, shot.y);
            const isHovered = hoveredShot?.id === shot.id && hoveredShot?.game_id === shot.game_id;
            const r = isHovered ? 21 : 16;
            const lastName = shot.player.split(" ").slice(-1)[0] || "Goal";
            const headshotUrl =
              shot.headshot ||
              (shot.playerId ? `https://assets.nhle.com/mugs/nhl/latest/${shot.playerId}.png` : "");
            const ringColor = shot.is_cbj ? "#ffb300" : "#38bdf8";

            return (
              <g
                key={shotUid}
                className="cursor-pointer transition-transform duration-150"
                onMouseEnter={() => setHoveredShot(shot)}
                onMouseLeave={() => setHoveredShot(null)}
              >
                {/* Glowing Outer Halo */}
                <circle
                  cx={px}
                  cy={py}
                  r={r + (isHovered ? 4 : 2.5)}
                  fill="none"
                  stroke={isHovered ? "#ffd700" : ringColor}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  strokeOpacity={isHovered ? 0.9 : 0.6}
                  filter="url(#goal-glow)"
                />

                {/* Solid Circular Backing (prevents ice markings from showing through) */}
                <circle
                  cx={px}
                  cy={py}
                  r={r}
                  fill={shot.is_cbj ? "#041e42" : "#1a2332"}
                />

                {/* Player Headshot Photo */}
                {headshotUrl ? (
                  <image
                    href={headshotUrl}
                    x={px - r}
                    y={py - r}
                    width={r * 2}
                    height={r * 2}
                    clipPath={`url(#avatar-clip-${shotUid})`}
                    preserveAspectRatio="xMidYMid slice"
                  />
                ) : (
                  /* Fallback Initials Avatar */
                  <text
                    x={px}
                    y={py + 4}
                    textAnchor="middle"
                    fill="#ffd700"
                    fontSize={isHovered ? 13 : 10}
                    fontWeight="black"
                  >
                    ★
                  </text>
                )}

                {/* Polished Border Ring */}
                <circle
                  cx={px}
                  cy={py}
                  r={r}
                  fill="none"
                  stroke={isHovered ? "#ffffff" : ringColor}
                  strokeWidth={isHovered ? 2.5 : 1.8}
                />

                {/* Mini Sweater Number Badge / Goal Star at Bottom-Right */}
                <g transform={`translate(${px + r * 0.65}, ${py + r * 0.65})`}>
                  <circle
                    r="6.5"
                    fill="#c62828"
                    stroke="#ffffff"
                    strokeWidth="1.2"
                  />
                  <text
                    textAnchor="middle"
                    y="2.8"
                    fill="#ffffff"
                    fontSize="7"
                    fontWeight="bold"
                  >
                    {shot.sweaterNumber ? `#${shot.sweaterNumber}` : "★"}
                  </text>
                </g>

                {/* Player Surname Label Pill Underneath */}
                <g transform={`translate(${px}, ${py + r + 10})`}>
                  <rect
                    x={-Math.max(lastName.length * 3.5 + 8, 24)}
                    y={-6.5}
                    width={Math.max(lastName.length * 7 + 16, 48)}
                    height={13}
                    rx={3.5}
                    fill="#0b1726"
                    fillOpacity="0.88"
                    stroke={shot.is_cbj ? "#ffb300" : "#38bdf8"}
                    strokeWidth="1"
                  />
                  <text
                    textAnchor="middle"
                    y="3"
                    fill="#ffffff"
                    fontSize="8.5"
                    fontWeight="bold"
                    letterSpacing="0.3"
                  >
                    {lastName}
                  </text>
                </g>
              </g>
            );
          })}
        </svg>

        {filteredShots.length === 0 && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-xs">
            No shots recorded matching this filter selection.
          </div>
        )}
      </div>

      {/* Bottom Status Readout & Rich Hover HUD Bar */}
      <div className="bg-[#0b1726] px-4 py-2.5 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Dynamic Status / Rich Hover HUD */}
        <div className="flex-1 min-w-[320px]">
          {hoveredShot ? (
            <div className="flex items-center gap-2.5">
              {/* Scorer Mugshot Avatar Thumbnail in HUD */}
              {hoveredShot.headshot && (
                <img
                  src={hoveredShot.headshot}
                  alt={hoveredShot.player}
                  className="w-7 h-7 rounded-full object-cover border border-amber-400/80 bg-[#041e42] shadow-sm"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              )}
              <span
                className={`px-1.5 py-0.5 rounded font-black uppercase tracking-wider text-[10px] ${
                  hoveredShot.type === "goal"
                    ? "bg-amber-400 text-slate-950"
                    : hoveredShot.is_cbj
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 text-slate-200"
                }`}
              >
                {hoveredShot.type === "goal" ? "🚨 GOAL" : hoveredShot.type.replace("-", " ")}
              </span>
              <span className="font-bold text-slate-100">
                {hoveredShot.player}
                {hoveredShot.sweaterNumber ? ` (#${hoveredShot.sweaterNumber})` : ""}
              </span>
              <span className="text-slate-400">({hoveredShot.team_abbrev})</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-200 font-medium capitalize">
                {hoveredShot.shotType} • {hoveredShot.dist} ft
              </span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300 font-mono">
                P{hoveredShot.period} {hoveredShot.time}
              </span>
              {hoveredShot.isHighDanger && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold text-[10px] border border-amber-500/40">
                  <Flame className="w-3 h-3 text-amber-400" />
                  <span>High Danger Slot</span>
                </span>
              )}
              {hoveredShot.assists && hoveredShot.assists.length > 0 && (
                <span className="text-slate-400 text-[11px] truncate max-w-xs">
                  (Ast: {hoveredShot.assists.join(", ")})
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-slate-400">
              <Info className="w-4 h-4 text-blue-400 shrink-0" />
              <span>Hover over any goal avatar or shot marker on the ice to view detailed broadcast metrics.</span>
            </div>
          )}
        </div>

        {/* Filter Counts Breakdown & High-Danger Stats */}
        <div className="flex items-center gap-3 font-semibold text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="text-cyan-400 font-bold">{team.id}:</span>
            <span>
              {stats.tSog} SOG ({stats.tGoals} G)
            </span>
            <span className="text-amber-400/90 text-[11px]">
              • HDC: {stats.tHdc}
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-bold">{currentChartData?.opponent || "Opp"}:</span>
            <span>
              {stats.oSog} SOG ({stats.oGoals} G)
            </span>
            <span className="text-amber-400/90 text-[11px]">
              • HDC: {stats.oHdc}
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="text-slate-400">
            Filtered: <span className="text-amber-400 font-bold">{stats.totalFiltered}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
