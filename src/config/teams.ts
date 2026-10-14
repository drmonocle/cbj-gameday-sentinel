import { TeamPreset } from "../types";

export const TEAM_PRESETS: Record<string, TeamPreset> = {
  // Metropolitan (Eastern)
  CAR: { id: "CAR", name: "Carolina Hurricanes", short: "Hurricanes", city: "Raleigh", division: "M", conference: "E", nhl_id: 12, espn_id: 7, primary: "#CC0000", secondary: "#000000", accent: "#A2AAAD", subreddit: "canes" },
  CBJ: { id: "CBJ", name: "Columbus Blue Jackets", short: "Blue Jackets", city: "Columbus", division: "M", conference: "E", nhl_id: 29, espn_id: 29, primary: "#041E42", secondary: "#C8102E", accent: "#A2AAAD", subreddit: "BlueJackets" },
  NJD: { id: "NJD", name: "New Jersey Devils", short: "Devils", city: "New Jersey", division: "M", conference: "E", nhl_id: 1, espn_id: 11, primary: "#CE1126", secondary: "#000000", accent: "#FFFFFF", subreddit: "devils" },
  NYI: { id: "NYI", name: "New York Islanders", short: "Islanders", city: "New York", division: "M", conference: "E", nhl_id: 2, espn_id: 12, primary: "#00539B", secondary: "#F47920", accent: "#FFFFFF", subreddit: "NewYorkIslanders" },
  NYR: { id: "NYR", name: "New York Rangers", short: "Rangers", city: "New York", division: "M", conference: "E", nhl_id: 3, espn_id: 13, primary: "#0038A8", secondary: "#CE1126", accent: "#FFFFFF", subreddit: "rangers" },
  PHI: { id: "PHI", name: "Philadelphia Flyers", short: "Flyers", city: "Philadelphia", division: "M", conference: "E", nhl_id: 4, espn_id: 15, primary: "#F74902", secondary: "#000000", accent: "#FFFFFF", subreddit: "Flyers" },
  PIT: { id: "PIT", name: "Pittsburgh Penguins", short: "Penguins", city: "Pittsburgh", division: "M", conference: "E", nhl_id: 5, espn_id: 16, primary: "#000000", secondary: "#FCB514", accent: "#CFC493", subreddit: "penguins" },
  WSH: { id: "WSH", name: "Washington Capitals", short: "Capitals", city: "Washington", division: "M", conference: "E", nhl_id: 15, espn_id: 23, primary: "#041E42", secondary: "#C8102E", accent: "#FFFFFF", subreddit: "capitals" },

  // Atlantic (Eastern)
  BOS: { id: "BOS", name: "Boston Bruins", short: "Bruins", city: "Boston", division: "A", conference: "E", nhl_id: 6, espn_id: 1, primary: "#000000", secondary: "#FFB81C", accent: "#FFFFFF", subreddit: "BostonBruins" },
  BUF: { id: "BUF", name: "Buffalo Sabres", short: "Sabres", city: "Buffalo", division: "A", conference: "E", nhl_id: 7, espn_id: 2, primary: "#002654", secondary: "#FCB514", accent: "#ADAFAA", subreddit: "sabres" },
  DET: { id: "DET", name: "Detroit Red Wings", short: "Red Wings", city: "Detroit", division: "A", conference: "E", nhl_id: 17, espn_id: 5, primary: "#CE1126", secondary: "#FFFFFF", accent: "#CE1126", subreddit: "DetroitRedWings" },
  FLA: { id: "FLA", name: "Florida Panthers", short: "Panthers", city: "Sunrise", division: "A", conference: "E", nhl_id: 13, espn_id: 26, primary: "#041E42", secondary: "#C8102E", accent: "#B9975B", subreddit: "FloridaPanthers" },
  MTL: { id: "MTL", name: "Montreal Canadiens", short: "Canadiens", city: "Montreal", division: "A", conference: "E", nhl_id: 8, espn_id: 10, primary: "#AF1E2D", secondary: "#192168", accent: "#FFFFFF", subreddit: "Habs" },
  OTT: { id: "OTT", name: "Ottawa Senators", short: "Senators", city: "Ottawa", division: "A", conference: "E", nhl_id: 9, espn_id: 14, primary: "#C8102E", secondary: "#000000", accent: "#D69F0F", subreddit: "OttawaSenators" },
  TBL: { id: "TBL", name: "Tampa Bay Lightning", short: "Lightning", city: "Tampa", division: "A", conference: "E", nhl_id: 14, espn_id: 20, primary: "#002868", secondary: "#FFFFFF", accent: "#002868", subreddit: "TampaBayLightning" },
  TOR: { id: "TOR", name: "Toronto Maple Leafs", short: "Maple Leafs", city: "Toronto", division: "A", conference: "E", nhl_id: 10, espn_id: 21, primary: "#00205B", secondary: "#FFFFFF", accent: "#00205B", subreddit: "leafs" },

  // Central (Western)
  CHI: { id: "CHI", name: "Chicago Blackhawks", short: "Blackhawks", city: "Chicago", division: "C", conference: "W", nhl_id: 16, espn_id: 4, primary: "#CF0A2C", secondary: "#000000", accent: "#FFD100", subreddit: "hawks" },
  COL: { id: "COL", name: "Colorado Avalanche", short: "Avalanche", city: "Denver", division: "C", conference: "W", nhl_id: 21, espn_id: 17, primary: "#6F263D", secondary: "#236192", accent: "#A2AAAD", subreddit: "ColoradoAvalanche" },
  DAL: { id: "DAL", name: "Dallas Stars", short: "Stars", city: "Dallas", division: "C", conference: "W", nhl_id: 25, espn_id: 9, primary: "#006847", secondary: "#8F8F8C", accent: "#111111", subreddit: "DallasStars" },
  MIN: { id: "MIN", name: "Minnesota Wild", short: "Wild", city: "Saint Paul", division: "C", conference: "W", nhl_id: 30, espn_id: 30, primary: "#154734", secondary: "#A6192E", accent: "#EAAA00", subreddit: "wildhockey" },
  NSH: { id: "NSH", name: "Nashville Predators", short: "Predators", city: "Nashville", division: "C", conference: "W", nhl_id: 18, espn_id: 27, primary: "#FFB81C", secondary: "#041E42", accent: "#FFFFFF", subreddit: "Predators" },
  STL: { id: "STL", name: "St. Louis Blues", short: "Blues", city: "St. Louis", division: "C", conference: "W", nhl_id: 19, espn_id: 19, primary: "#002F87", secondary: "#FCB514", accent: "#041E42", subreddit: "stlouisblues" },
  UTA: { id: "UTA", name: "Utah Mammoth", short: "Mammoth", city: "Salt Lake City", division: "C", conference: "W", nhl_id: 59, espn_id: 140656, primary: "#010101", secondary: "#69B3E7", accent: "#FFFFFF", subreddit: "Utah_Hockey" },
  WPG: { id: "WPG", name: "Winnipeg Jets", short: "Jets", city: "Winnipeg", division: "C", conference: "W", nhl_id: 52, espn_id: 28, primary: "#041E42", secondary: "#004C97", accent: "#AC162C", subreddit: "winnipegjets" },

  // Pacific (Western)
  ANA: { id: "ANA", name: "Anaheim Ducks", short: "Ducks", city: "Anaheim", division: "P", conference: "W", nhl_id: 24, espn_id: 25, primary: "#F47A38", secondary: "#B9975B", accent: "#000000", subreddit: "AnaheimDucks" },
  CGY: { id: "CGY", name: "Calgary Flames", short: "Flames", city: "Calgary", division: "P", conference: "W", nhl_id: 20, espn_id: 3, primary: "#C8102E", secondary: "#F1BE48", accent: "#111111", subreddit: "CalgaryFlames" },
  EDM: { id: "EDM", name: "Edmonton Oilers", short: "Oilers", city: "Edmonton", division: "P", conference: "W", nhl_id: 22, espn_id: 6, primary: "#041E42", secondary: "#FF4C00", accent: "#FFFFFF", subreddit: "EdmontonOilers" },
  LAK: { id: "LAK", name: "Los Angeles Kings", short: "Kings", city: "Los Angeles", division: "P", conference: "W", nhl_id: 26, espn_id: 8, primary: "#111111", secondary: "#A2AAAD", accent: "#FFFFFF", subreddit: "losangeleskings" },
  SJS: { id: "SJS", name: "San Jose Sharks", short: "Sharks", city: "San Jose", division: "P", conference: "W", nhl_id: 28, espn_id: 18, primary: "#006D75", secondary: "#EA7200", accent: "#000000", subreddit: "SanJoseSharks" },
  SEA: { id: "SEA", name: "Seattle Kraken", short: "Kraken", city: "Seattle", division: "P", conference: "W", nhl_id: 55, espn_id: 124292, primary: "#001628", secondary: "#99D9D9", accent: "#E9072B", subreddit: "SeattleKraken" },
  VAN: { id: "VAN", name: "Vancouver Canucks", short: "Canucks", city: "Vancouver", division: "P", conference: "W", nhl_id: 23, espn_id: 22, primary: "#00205B", secondary: "#00843D", accent: "#041C2C", subreddit: "canucks" },
  VGK: { id: "VGK", name: "Vegas Golden Knights", short: "Golden Knights", city: "Las Vegas", division: "P", conference: "W", nhl_id: 54, espn_id: 37, primary: "#B4975A", secondary: "#333F48", accent: "#000000", subreddit: "goldenknights" },
};

export const DEFAULT_TEAM = "CBJ";

export function getTeamPreset(teamId: string): TeamPreset {
  const upper = teamId?.toUpperCase();
  return TEAM_PRESETS[upper] || TEAM_PRESETS[DEFAULT_TEAM];
}

const ESPN_LOGO_SLUGS: Record<string, string> = {
  NJD: "nj",
  TBL: "tb",
  SJS: "sj",
  LAK: "la",
};

export function getTeamLogoUrl(teamAbbrev: string): string {
  const abbrev = teamAbbrev?.toUpperCase() || "CBJ";
  const slug = ESPN_LOGO_SLUGS[abbrev] || abbrev.toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nhl/500/${slug}.png`;
}
