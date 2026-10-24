export interface TeamPreset {
  id: string; // "CBJ"
  name: string; // "Columbus Blue Jackets"
  short: string; // "Blue Jackets"
  city: string; // "Columbus"
  division: "M" | "A" | "C" | "P";
  conference: "E" | "W";
  nhl_id: number;
  espn_id: number;
  primary: string;
  secondary: string;
  accent: string;
  subreddit: string;
}

export interface ShotEvent {
  id: number;
  game_id: number | string;
  game_date: string;
  matchup: string;
  opponent: string;
  period: number;
  time: string;
  type: "goal" | "shot-on-goal" | "missed-shot" | "blocked-shot";
  shotType: string;
  x: number;
  y: number;
  dist: number;
  player: string;
  playerId?: number;
  headshot?: string;
  sweaterNumber?: number;
  assists?: string[];
  is_cbj: boolean; // true if favorite team
  team_abbrev: string;
  isHighDanger?: boolean;
}

export interface ShotChartData {
  game_id: number | string;
  game_date: string;
  matchup: string;
  opponent: string;
  venue?: string;
  target_score?: number;
  opp_score?: number;
  is_home?: boolean;
  games_count?: number;
  counts: {
    target_sog: number;
    target_goals: number;
    opp_sog: number;
    opp_goals: number;
    total_shots: number;
    target_sh_pct?: number;
    opp_sh_pct?: number;
    target_hdc?: number; // High Danger Chances
    opp_hdc?: number;
  };
  shots: ShotEvent[];
}

export interface GameOutcome {
  lastPeriodType?: string;
}

export interface TeamScoreInfo {
  id?: number;
  name?: { default: string };
  placeName?: { default: string };
  commonName?: { default: string };
  abbrev: string;
  score?: number;
  sog?: number;
  logo?: string;
}

export interface TvBroadcast {
  countryCode: string;
  network: string;
  market?: string;
}

export interface GameInfo {
  id: number;
  gameDate: string;
  startTimeUTC: string;
  gameState: "FUT" | "PRE" | "LIVE" | "CRIT" | "FINAL" | "OFF";
  gameType: number; // 1: Preseason, 2: Regular, 3: Playoffs
  homeTeam: TeamScoreInfo;
  awayTeam: TeamScoreInfo;
  periodDescriptor?: {
    number: number;
    periodType: string;
  };
  clock?: {
    timeRemaining: string;
    secondsRemaining: number;
    running: boolean;
    inIntermission: boolean;
  };
  situation?: {
    situationCode: string;
    timeRemaining?: string;
  };
  venue?: {
    default: string;
  };
  tvBroadcasts?: TvBroadcast[];
  goals?: Array<{
    periodDescriptor: { number: number; periodType: string };
    timeInPeriod: string;
    teamAbbrev: { default: string } | string;
    firstName?: { default: string } | string;
    lastName?: { default: string } | string;
    name?: { default: string } | string;
    strength?: string;
    goalModifier?: string;
  }>;
}

export interface StandingsRecord {
  teamAbbrev: { default: string } | string;
  teamName: { default: string } | string;
  conferenceAbbrev: string;
  divisionAbbrev: string;
  divisionSequence: number;
  conferenceSequence: number;
  wildcardSequence: number;
  gamesPlayed: number;
  wins: number;
  losses: number;
  otLosses: number;
  points: number;
  pointPctg: number;
  goalDifferential: number;
  goalFor: number;
  goalAgainst: number;
  l10Wins: number;
  l10Losses: number;
  l10OtLosses: number;
  streakCode: string;
  streakCount: number;
}

export interface PlayerBio {
  id: number;
  firstName: { default: string } | string;
  lastName: { default: string } | string;
  sweaterNumber: number;
  positionCode: string;
  shootsCatches: string;
  birthCity?: { default: string } | string;
  birthStateProvince?: { default: string } | string;
  birthCountry?: string;
  birthDate?: string;
  heightInInches?: number;
  weightInPounds?: number;
  headshot?: string;
  draftDetails?: {
    year: number;
    round: number;
    overallPick: number;
    teamAbbrev: string;
  };
  featuredStats?: {
    season?: number;
    regularSeason?: {
      subSeason?: {
        gamesPlayed: number;
        goals?: number;
        assists?: number;
        points?: number;
        plusMinus?: number;
        pim?: number;
        savePctg?: number;
        goalsAgainstAvg?: number;
        wins?: number;
        losses?: number;
        otLosses?: number;
        shutouts?: number;
      };
    };
  };
  careerTotals?: {
    regularSeason?: {
      gamesPlayed: number;
      goals?: number;
      assists?: number;
      points?: number;
      plusMinus?: number;
      pim?: number;
      savePctg?: number;
      goalsAgainstAvg?: number;
      wins?: number;
      losses?: number;
      otLosses?: number;
      shutouts?: number;
    };
  };
  last5Games?: Array<{
    gameDate: string;
    opponentAbbrev: string;
    goals: number;
    assists: number;
    points: number;
    plusMinus: number;
  }>;
}

export interface NewsItem {
  id: string;
  title: string;
  link: string;
  source: string;
  desc: string;
  ts: number;
}

export interface AppSettings {
  team: string; // e.g. "CBJ"
  sound: boolean;
  opponent_sound: boolean;
  volume: number; // 0..100
  toasts: boolean;
  puck_drop_reminder: boolean;
  spoiler_mode: boolean;
  start_with_windows: boolean;
  close_to_tray: boolean;
  watch: string;
  refresh_interval: number; // seconds
}
