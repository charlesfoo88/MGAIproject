import { useEffect, useRef, useState } from "react";
import "./badge.css";

const MOCK_DELAY_MS = 1000;
const LEAGUE_CODE = "epl";
const LEAGUE_TITLE = "Premier League";
const SEASON_CODE = "2025_2026";
const DEFAULT_MATCH_NAME = `${LEAGUE_CODE}_${SEASON_CODE}`;
const DEFAULT_MATCH_TITLE = `${LEAGUE_TITLE} Personalized Highlight Reel`;
const DEFAULT_MATCH_VENUE = "Venue detected by pipeline";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const RUN_ENDPOINT = "/api/run";
const STATUS_ENDPOINT = "/api/status";
const SHOWCASE_ENDPOINT = "/api/showcase";
const WEBSITE_FEED_ENDPOINT = "/api/website/feed";
const PLAYERS_ENDPOINT = "/api/players";
const SHOWCASE_MATCH_BY_TEAM_PAIR = {
  "arsenal|manchester city": "arsenal_5_1_man_city_2025_02_02",
  "liverpool|manchester city": "liverpool_2_0_man_city_2024_12_01",
};
const EPL_RECENT_MATCHES_ENDPOINT = "https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4328";
const EPL_FIXTURES_ENDPOINT = "https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4328";
const EPL_TABLE_ENDPOINT = "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l=4328&s=2025-2026";
const EPL_STRIP_MAX_ITEMS = 10;
const FALLBACK_TEAM_LOGO = "/team-logos/premier-league.png";
const FALLBACK_PLAYER_HEADSHOT = "/player-headshots/player-placeholder.svg";
const WEATHER_ENDPOINT = "https://api.open-meteo.com/v1/forecast";
const FEED_REFRESH_MS = 60000;
const COMMENTARY_REFRESH_MS = 12000;
const HEADER_NAV_ITEMS = [
  { key: "scores", label: "Scores", metaLabel: "Recent EPL Scores" },
  { key: "fixtures", label: "Fixtures", metaLabel: "Upcoming EPL Fixtures" },
  { key: "highlights", label: "Highlights", metaLabel: "Commentary Highlights" },
  { key: "tables", label: "Tables", metaLabel: "Alphabetical Team Table" }
];

const WEATHER_CODE_LABELS = {
  0: "Clear sky",
  1: "Mostly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Fog",
  48: "Rime fog",
  51: "Light drizzle",
  53: "Drizzle",
  55: "Dense drizzle",
  61: "Light rain",
  63: "Rain",
  65: "Heavy rain",
  71: "Light snow",
  73: "Snow",
  75: "Heavy snow",
  80: "Rain showers",
  81: "Heavy showers",
  82: "Violent showers",
  95: "Thunderstorm"
};

function hasRealHeadshot(value) {
  const url = String(value || "").trim();
  if (!url) return false;
  return url !== FALLBACK_PLAYER_HEADSHOT;
}

function normalizeTeamKey(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const EPL_TEAM_DATABASE = [
  {
    name: "Arsenal",
    logo: "/team-logos/arsenal.png",
    aliases: ["Arsenal", "ARS", "Gunners"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Aston Villa",
    logo: "/team-logos/aston-villa.png",
    aliases: ["Aston Villa", "AVL", "Villa"],
    tuning: { scale: 1.04, y: 0 }
  },
  {
    name: "Bournemouth",
    logo: "/team-logos/bournemouth.png",
    aliases: ["Bournemouth", "AFC Bournemouth", "BOU", "Cherries"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Brentford",
    logo: "/team-logos/brentford.svg",
    aliases: ["Brentford", "BRE", "Bees"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Brighton & Hove Albion",
    logo: "/team-logos/brighton-hove-albion.png",
    aliases: ["Brighton & Hove Albion", "Brighton", "BHA", "Seagulls"],
    tuning: { scale: 1.04, y: 0 }
  },
  {
    name: "Burnley",
    logo: "/team-logos/premier-league.png",
    aliases: ["Burnley", "BUR", "Clarets"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Chelsea",
    logo: "/team-logos/chelsea.png",
    aliases: ["Chelsea", "CHE", "Blues"],
    tuning: { scale: 1.04, y: 0 }
  },
  {
    name: "Crystal Palace",
    logo: "/team-logos/crystal-palace.png",
    aliases: ["Crystal Palace", "Palace", "CRY", "Eagles"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Everton",
    logo: "/team-logos/everton.png",
    aliases: ["Everton", "EVE", "Toffees"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Fulham",
    logo: "/team-logos/fulham.png",
    aliases: ["Fulham", "FUL", "Cottagers"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Ipswich Town",
    logo: "/team-logos/ipswich-town.svg",
    aliases: ["Ipswich Town", "Ipswich", "IPS", "Tractor Boys"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Leicester City",
    logo: "/team-logos/leicester-city.png",
    aliases: ["Leicester City", "Leicester", "LEI", "Foxes"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Leeds United",
    logo: "/team-logos/premier-league.png",
    aliases: ["Leeds United", "Leeds", "LEE", "Whites"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Liverpool",
    logo: "/team-logos/liverpool.png",
    aliases: ["Liverpool", "LIV", "Reds"],
    tuning: { scale: 1.24, y: 4 }
  },
  {
    name: "Manchester City",
    logo: "/team-logos/manchester-city.png",
    aliases: ["Manchester City", "Man City", "MCI", "Citizens"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Manchester United",
    logo: "/team-logos/manchester-united.png",
    aliases: ["Manchester United", "Man United", "Manchester Utd", "MUN", "Red Devils"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Newcastle United",
    logo: "/team-logos/newcastle-united.png",
    aliases: ["Newcastle United", "Newcastle", "NEW", "Magpies"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Nottingham Forest",
    logo: "/team-logos/nottingham-forest.svg",
    aliases: ["Nottingham Forest", "Nottm Forest", "NFO", "Tricky Trees"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Southampton",
    logo: "/team-logos/southampton.png",
    aliases: ["Southampton", "SOU", "Saints"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Sunderland",
    logo: "/team-logos/premier-league.png",
    aliases: ["Sunderland", "SUN", "Black Cats"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Tottenham Hotspur",
    logo: "/team-logos/tottenham-hotspur.png",
    aliases: ["Tottenham Hotspur", "Tottenham", "Spurs", "TOT"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "West Ham United",
    logo: "/team-logos/west-ham-united.png",
    aliases: ["West Ham United", "West Ham", "WHU", "Hammers"],
    tuning: { scale: 1.02, y: 0 }
  },
  {
    name: "Wolverhampton Wanderers",
    logo: "/team-logos/wolverhampton-wanderers.png",
    aliases: ["Wolverhampton Wanderers", "Wolves", "WOL"],
    tuning: { scale: 1.02, y: 0 }
  }
];

const TEAM_WEATHER_LOCATIONS = {
  Arsenal: { label: "London (Emirates)", latitude: 51.5549, longitude: -0.1084 },
  "Aston Villa": { label: "Birmingham (Villa Park)", latitude: 52.5092, longitude: -1.8848 },
  Bournemouth: { label: "Bournemouth (Vitality)", latitude: 50.7352, longitude: -1.8383 },
  Brentford: { label: "London (Brentford)", latitude: 51.4907, longitude: -0.2889 },
  "Brighton & Hove Albion": { label: "Brighton (Amex)", latitude: 50.8616, longitude: -0.0837 },
  Burnley: { label: "Burnley (Turf Moor)", latitude: 53.789, longitude: -2.2304 },
  Chelsea: { label: "London (Stamford Bridge)", latitude: 51.4817, longitude: -0.191 },
  "Crystal Palace": { label: "London (Selhurst Park)", latitude: 51.3983, longitude: -0.0856 },
  Everton: { label: "Liverpool (Goodison)", latitude: 53.4388, longitude: -2.9664 },
  Fulham: { label: "London (Craven Cottage)", latitude: 51.4749, longitude: -0.2217 },
  "Ipswich Town": { label: "Ipswich (Portman Road)", latitude: 52.056, longitude: 1.1454 },
  "Leicester City": { label: "Leicester (King Power)", latitude: 52.6203, longitude: -1.1422 },
  "Leeds United": { label: "Leeds (Elland Road)", latitude: 53.7778, longitude: -1.5721 },
  Liverpool: { label: "Liverpool (Anfield)", latitude: 53.4308, longitude: -2.9608 },
  "Manchester City": { label: "Manchester (Etihad)", latitude: 53.4831, longitude: -2.2004 },
  "Manchester United": { label: "Manchester (Old Trafford)", latitude: 53.4631, longitude: -2.2913 },
  "Newcastle United": { label: "Newcastle (St James Park)", latitude: 54.9756, longitude: -1.6216 },
  "Nottingham Forest": { label: "Nottingham (City Ground)", latitude: 52.9399, longitude: -1.1323 },
  Southampton: { label: "Southampton (St Marys)", latitude: 50.9058, longitude: -1.3911 },
  Sunderland: { label: "Sunderland (Stadium of Light)", latitude: 54.9142, longitude: -1.3884 },
  "Tottenham Hotspur": { label: "London (Tottenham Hotspur Stadium)", latitude: 51.6043, longitude: -0.0664 },
  "West Ham United": { label: "London (London Stadium)", latitude: 51.5386, longitude: -0.0166 },
  "Wolverhampton Wanderers": { label: "Wolverhampton (Molineux)", latitude: 52.5903, longitude: -2.1304 }
};

const FALLBACK_PLAYER_DATABASE = [
  { name: "Bukayo Saka", team: "Arsenal", headshot: "/player-headshots/bukayo-saka.svg" },
  { name: "Martin Odegaard", team: "Arsenal", headshot: "/player-headshots/martin-odegaard.svg" },
  { name: "Erling Haaland", team: "Manchester City", headshot: "/player-headshots/erling-haaland.svg" },
  { name: "Kevin De Bruyne", team: "Manchester City", headshot: "/player-headshots/kevin-de-bruyne.svg" },
  { name: "Mohamed Salah", team: "Liverpool", headshot: "/player-headshots/mohamed-salah.svg" },
  { name: "Cole Palmer", team: "Chelsea", headshot: "/player-headshots/cole-palmer.svg" },
  { name: "Bruno Fernandes", team: "Manchester United", headshot: "/player-headshots/bruno-fernandes.svg" },
  { name: "Son Heung-min", team: "Tottenham Hotspur", headshot: "/player-headshots/son-heung-min.svg" },
  { name: "Alexander Isak", team: "Newcastle United", headshot: "/player-headshots/alexander-isak.svg" },
  { name: "Ollie Watkins", team: "Aston Villa", headshot: "/player-headshots/ollie-watkins.svg" },
  { name: "Jarrod Bowen", team: "West Ham United", headshot: "/player-headshots/jarrod-bowen.svg" },
  { name: "Eberechi Eze", team: "Crystal Palace", headshot: "/player-headshots/eberechi-eze.svg" }
];

const EPL_TEAMS = EPL_TEAM_DATABASE.map((team) => team.name);

const TEAM_LOGOS = Object.fromEntries(
  EPL_TEAM_DATABASE.map((team) => [team.name, team.logo])
);

const TEAM_LOGO_TUNING = Object.fromEntries(
  EPL_TEAM_DATABASE.map((team) => [team.name, team.tuning || { scale: 1, y: 0 }])
);

const TEAM_ALIAS_TO_NAME = EPL_TEAM_DATABASE.reduce((lookup, team) => {
  lookup[normalizeTeamKey(team.name)] = team.name;
  (team.aliases || []).forEach((alias) => {
    lookup[normalizeTeamKey(alias)] = team.name;
  });
  return lookup;
}, {});

const TEAM_ALIAS_KEYS_DESC = Object.keys(TEAM_ALIAS_TO_NAME).sort((a, b) => b.length - a.length);

function resolveTeamName(candidate) {
  const normalized = normalizeTeamKey(candidate);
  return TEAM_ALIAS_TO_NAME[normalized] || "";
}

function detectTeamMentionsFromText(text) {
  const normalized = normalizeTeamKey(text);
  if (!normalized) return [];

  const found = [];

  TEAM_ALIAS_KEYS_DESC.forEach((aliasKey) => {
    const matcher = new RegExp(`(^|\\s)${escapeRegExp(aliasKey)}(\\s|$)`);
    if (matcher.test(normalized)) {
      const teamName = TEAM_ALIAS_TO_NAME[aliasKey];
      if (!found.includes(teamName)) {
        found.push(teamName);
      }
    }
  });

  return found;
}

function collectTeamFromEvents(events) {
  if (!Array.isArray(events) || events.length === 0) return "";

  const counts = {};

  const bump = (teamName, weight = 1) => {
    if (!teamName) return;
    counts[teamName] = (counts[teamName] || 0) + weight;
  };

  events.forEach((event) => {
    const directTeam = resolveTeamName(event?.team || event?.team_name || event?.club || "");
    bump(directTeam, 3);

    const textFields = [
      event?.caption,
      event?.description,
      event?.summary,
      event?.context?.narrative,
      event?.text
    ].filter(Boolean);

    textFields.forEach((value) => {
      detectTeamMentionsFromText(value).forEach((teamName) => bump(teamName, 1));
    });
  });

  const ranked = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return ranked[0]?.[0] || "";
}

function inferTeamsFromPipelineData(pipelineData) {
  const directLeft = resolveTeamName(
    pipelineData?.left_team
    || pipelineData?.reel_a_team
    || pipelineData?.team_a
    || pipelineData?.match_context?.home_team
  );
  const directRight = resolveTeamName(
    pipelineData?.right_team
    || pipelineData?.reel_b_team
    || pipelineData?.team_b
    || pipelineData?.match_context?.away_team
  );

  let leftTeam = directLeft || collectTeamFromEvents(pipelineData?.reel_a_events);
  let rightTeam = directRight || collectTeamFromEvents(pipelineData?.reel_b_events);

  const globalTeamCounts = {};
  const bumpGlobal = (teamName, weight = 1) => {
    if (!teamName) return;
    globalTeamCounts[teamName] = (globalTeamCounts[teamName] || 0) + weight;
  };

  [
    pipelineData?.match_recap,
    ...(pipelineData?.reel_a_captions || []),
    ...(pipelineData?.reel_b_captions || [])
  ]
    .filter(Boolean)
    .forEach((value) => {
      detectTeamMentionsFromText(value).forEach((teamName) => bumpGlobal(teamName, 1));
    });

  const rankedGlobal = Object.entries(globalTeamCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([teamName]) => teamName);

  if (!leftTeam) leftTeam = rankedGlobal[0] || "";
  if (!rightTeam) rightTeam = rankedGlobal.find((name) => name !== leftTeam) || "";

  if (leftTeam && rightTeam && leftTeam === rightTeam) {
    rightTeam = rankedGlobal.find((name) => name !== leftTeam) || "";
  }

  return { leftTeam, rightTeam };
}

function slugifyText(value) {
  return value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function teamPairKey(teamA, teamB) {
  const parts = [resolveTeamName(teamA) || String(teamA || "").trim(), resolveTeamName(teamB) || String(teamB || "").trim()]
    .map((name) => normalizeTeamKey(name))
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right));
  return parts.join("|");
}

function getShowcaseMatchForTeams(teamA, teamB) {
  return SHOWCASE_MATCH_BY_TEAM_PAIR[teamPairKey(teamA, teamB)] || "";
}

function extractYouTubeVideoId(url) {
  if (!url) return "";

  try {
    const parsed = new URL(url);

    if (parsed.hostname.includes("youtu.be")) {
      return parsed.pathname.replace("/", "").trim();
    }

    if (parsed.searchParams.has("v")) {
      return parsed.searchParams.get("v")?.trim() || "";
    }

    const parts = parsed.pathname.split("/").filter(Boolean);
    const embedIndex = parts.findIndex((part) => part === "embed" || part === "shorts");

    if (embedIndex >= 0 && parts[embedIndex + 1]) {
      return parts[embedIndex + 1].trim();
    }
  } catch {
    return "";
  }

  return "";
}

function isValidYouTubeUrl(url) {
  return extractYouTubeVideoId(url).length > 0;
}
function formatEplStripDate(dateStr, timeStr) {
  if (!dateStr) return "";
  const parsed = new Date(`${dateStr}T${timeStr || "00:00:00"}`);
  if (Number.isNaN(parsed.getTime())) return dateStr;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatEplStripDateTime(dateStr, timeStr) {
  if (!dateStr) return "";
  const parsed = new Date(`${dateStr}T${timeStr || "00:00:00"}`);
  if (Number.isNaN(parsed.getTime())) return dateStr;
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function normalizeScore(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? String(numberValue) : "-";
}

function weatherLabelFromCode(code) {
  const numeric = Number(code);
  if (!Number.isFinite(numeric)) return "Unknown";
  return WEATHER_CODE_LABELS[numeric] || "Variable";
}

function buildCommentaryLine(match, sequence = 0) {
  const home = String(match?.home || "Home");
  const away = String(match?.away || "Away");
  const homeScore = String(match?.homeScore ?? "-");
  const awayScore = String(match?.awayScore ?? "-");
  const kickoff = String(match?.kickoffLabel || match?.dateLabel || "Matchday");
  const status = String(match?.status || "").trim();

  const templates = [
    `${kickoff}: ${home} ${homeScore}-${awayScore} ${away}.`,
    `Pressing phase update: ${home} and ${away} are trading possession lanes.`,
    `Transition watch: wide channels are opening for both sides.`,
    `Set-piece alert: scoreline currently ${homeScore}-${awayScore}.`,
    `Commentary pulse: tactical compactness is shaping this game state.`
  ];

  const line = templates[sequence % templates.length];
  if (!status) return line;
  return `${line} Status: ${status}.`;
}

function buildHighlightTickerItems(scores, fixtures) {
  const highlights = [];

  (scores || []).slice(0, 5).forEach((match, index) => {
    highlights.push({
      id: `score-highlight-${match.id || index}`,
      headline: `${match.home} ${match.homeScore}-${match.awayScore} ${match.away}`,
      detail: `Final whistle recap: compact shape changes and transition phases defined this matchday.`
    });
  });

  (fixtures || []).slice(0, 5).forEach((match, index) => {
    highlights.push({
      id: `fixture-highlight-${match.id || index}`,
      headline: `${match.home} vs ${match.away}`,
      detail: `Preview focus: possession battle, pressing triggers, and set-piece threat before kickoff.`
    });
  });

  if (highlights.length === 0) {
    return [
      {
        id: "highlight-fallback-1",
        headline: "EPL Commentary Wire",
        detail: "Live tactical commentary banner will populate when feed data is available."
      },
      {
        id: "highlight-fallback-2",
        headline: "Matchday Focus",
        detail: "Expect transitions, width overloads, and high press triggers to shape outcomes."
      }
    ];
  }

  return highlights;
}

function getMatchInfo(sourceMode, teamA, teamB, youtubeUrl, youtubeTitle, sourcePrompt) {
  if (sourceMode === "youtube") {
    const videoId = extractYouTubeVideoId(youtubeUrl);

    if (!videoId) {
      return {
        matchName: `youtube_pending_${DEFAULT_MATCH_NAME}`,
        matchTitle: "YouTube Video",
        venue: DEFAULT_MATCH_VENUE
      };
    }

    return {
      matchName: `youtube_${videoId}_${LEAGUE_CODE}_${SEASON_CODE}`,
      matchTitle: youtubeTitle || "YouTube Video",
      venue: DEFAULT_MATCH_VENUE
    };
  }

  if (sourceMode === "text") {
    const trimmedPrompt = String(sourcePrompt || "").trim();
    const promptKey = slugifyText(trimmedPrompt).slice(0, 36) || "freeform";

    return {
      matchName: `text_${promptKey}_${LEAGUE_CODE}_${SEASON_CODE}`,
      matchTitle: "SOCCER SEARCH BAR",
      venue: DEFAULT_MATCH_VENUE
    };
  }

  if (!teamA || !teamB) {
    return {
      matchName: DEFAULT_MATCH_NAME,
      matchTitle: DEFAULT_MATCH_TITLE,
      venue: DEFAULT_MATCH_VENUE
    };
  }

  return {
    matchName: `${slugifyText(teamA)}_vs_${slugifyText(teamB)}_${LEAGUE_CODE}_${SEASON_CODE}`,
    matchTitle: `${teamA} vs ${teamB} - ${LEAGUE_TITLE}`,
    venue: DEFAULT_MATCH_VENUE
  };
}

function buildReelHighlights(teamName, opponentName, focus) {
  return [
    `${teamName} begin in a structured 4-3-3 shape and press ${opponentName}'s first pass.`,
    `A transition window opens after midfield recovery, creating direct lane access.`,
    `The final-third sequence emphasizes ${focus.toLowerCase()} with repeated overloads.`,
    `${opponentName} respond with compact blocks, reducing central passing options.`,
    "Late phases shift to controlled possession and game-state management."
  ];
}

function buildNeutralCommentary(teamA, teamB, preferenceDetail) {
  return `${teamA} and ${teamB} are trading control through alternating possession phases. `
    + `The current sequence highlights ${preferenceDetail.toLowerCase()} while both sides maintain compact defensive spacing. `
    + "Overall tempo is high but structured, with the match flow determined by transitions and set-piece efficiency.";
}

function buildUserPreference(
  sourceMode,
  teamA,
  teamB,
  preferenceType,
  preferenceDetail,
  tone,
  youtubeUrl,
  sourcePrompt
) {
  if (sourceMode === "text") {
    return `Source mode: text. User request: ${sourcePrompt}. `
      + "Extract key terms/entities from this request and generate the best available personalized and neutral highlights."
      + " If the request is broad or non-football, still produce a meaningful recap from available match events.";
  }

  const base = `Preference type: ${preferenceType}; detail: ${preferenceDetail}; tone: ${tone}.`;

  if (sourceMode === "youtube") {
    return `${base} Source mode: youtube. Source URL: ${youtubeUrl}. `
      + "Please run match detection on this video before generating highlight reels.";
  }

  return `${base} Source mode: teams. Matchup: ${teamA} vs ${teamB}.`;
}

function buildLocalRecapCardDataUri(
  matchTitle,
  preferenceDetail,
  commentary,
  teamA = "",
  teamB = "",
  featureMoments = []
) {
  const escapeXml = (value) => String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const wrapText = (value, width = 46) => {
    const regex = new RegExp(`.{1,${width}}(\\s|$)`, "g");
    return String(value || "").match(regex) || [String(value || "").trim()];
  };
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const logoAPath = TEAM_LOGOS[teamA] || FALLBACK_TEAM_LOGO;
  const logoBPath = TEAM_LOGOS[teamB] || FALLBACK_TEAM_LOGO;
  const logoA = `${origin}${logoAPath}`;
  const logoB = `${origin}${logoBPath}`;

  const wrappedCommentary = wrapText(commentary, 52)
    .map((line) => line.trim())
    .filter(Boolean);
  const fallbackMoments = wrappedCommentary.slice(0, 4);
  const moments = (Array.isArray(featureMoments) ? featureMoments : [])
    .map((line) => String(line || "").trim())
    .filter(Boolean)
    .slice(0, 4);
  while (moments.length < 4) {
    moments.push(fallbackMoments[moments.length] || `Significant moment ${moments.length + 1}.`);
  }

  const framePalette = [
    "featureFillA",
    "featureFillB",
    "featureFillC",
    "featureFillD"
  ];

  const frameSvg = moments.map((moment, idx) => {
    const momentLines = wrapText(moment, 34).slice(0, 3).map((line) => line.trim());
    const lineNodes = momentLines.map(
      (line, lineIdx) => `<text x="450" y="${592 + (lineIdx * 36)}" class="featureText">${escapeXml(line)}</text>`
    ).join("");
    const frameClass = `featureFrame frame${idx + 1}`;
    const fillClass = framePalette[idx % framePalette.length];
    const crest = idx % 2 === 0 ? logoA : logoB;
    return `<g class="${frameClass}">
      <rect x="84" y="292" width="732" height="650" rx="26" class="${fillClass}"/>
      <image href="${crest}" x="282" y="388" width="336" height="336" preserveAspectRatio="xMidYMid meet" opacity="0.16"/>
      <text x="450" y="356" class="frameLabel">FEATURE REEL ${idx + 1}</text>
      ${lineNodes}
      <rect x="146" y="760" width="608" height="112" rx="14" class="frameTagBg"/>
      <text x="450" y="814" class="frameTag">Animated screen capture sequence</text>
    </g>`;
  }).join("");

  const recapLines = wrappedCommentary.slice(0, 5);
  const recapSvg = recapLines.map(
    (line, idx) => `<text x="84" y="${1040 + (idx * 28)}" class="body">${escapeXml(line)}</text>`
  ).join("");

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1300" viewBox="0 0 900 1300" role="img" aria-label="Shiny recap trading card">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#070b16"/>
        <stop offset="100%" stop-color="#172554"/>
      </linearGradient>
      <linearGradient id="foil" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.15"/>
        <stop offset="30%" stop-color="#f472b6" stop-opacity="0.2"/>
        <stop offset="65%" stop-color="#facc15" stop-opacity="0.15"/>
        <stop offset="100%" stop-color="#60a5fa" stop-opacity="0.18"/>
      </linearGradient>
      <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#f59e0b"/>
        <stop offset="50%" stop-color="#fde68a"/>
        <stop offset="100%" stop-color="#f59e0b"/>
      </linearGradient>
      <pattern id="scan" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(25)">
        <rect width="12" height="12" fill="transparent"/>
        <rect width="2" height="12" fill="#93c5fd" fill-opacity="0.08"/>
      </pattern>
      <linearGradient id="shineBand" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
        <stop offset="50%" stop-color="#ffffff" stop-opacity="0.34"/>
        <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="prismBand" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#22d3ee" stop-opacity="0"/>
        <stop offset="24%" stop-color="#c084fc" stop-opacity="0.28"/>
        <stop offset="52%" stop-color="#f472b6" stop-opacity="0.26"/>
        <stop offset="76%" stop-color="#facc15" stop-opacity="0.24"/>
        <stop offset="100%" stop-color="#60a5fa" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="featureA" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#2563eb" stop-opacity="0.26"/>
        <stop offset="100%" stop-color="#020617" stop-opacity="0.82"/>
      </linearGradient>
      <linearGradient id="featureB" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#dc2626" stop-opacity="0.26"/>
        <stop offset="100%" stop-color="#020617" stop-opacity="0.82"/>
      </linearGradient>
      <linearGradient id="featureC" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#0e7490" stop-opacity="0.26"/>
        <stop offset="100%" stop-color="#020617" stop-opacity="0.82"/>
      </linearGradient>
      <linearGradient id="featureD" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#a855f7" stop-opacity="0.26"/>
        <stop offset="100%" stop-color="#020617" stop-opacity="0.82"/>
      </linearGradient>
    </defs>
    <rect width="900" height="1300" fill="url(#bg)"/>
    <rect width="900" height="1300" fill="url(#foil)"/>
    <rect width="900" height="1300" fill="url(#scan)"/>
    <rect x="-460" y="0" width="360" height="1300" fill="url(#prismBand)" transform="rotate(14 450 650)">
      <animate attributeName="x" values="-460;980" dur="4.8s" repeatCount="indefinite"/>
    </rect>
    <rect x="-420" y="0" width="220" height="1300" fill="url(#shineBand)" transform="rotate(14 450 650)">
      <animate attributeName="x" values="-420;960" dur="3.2s" repeatCount="indefinite"/>
    </rect>
    <rect x="24" y="24" width="852" height="1252" rx="28" fill="none" stroke="url(#edge)" stroke-width="6"/>
    <rect x="42" y="42" width="816" height="1216" rx="20" class="panel"/>
    <rect x="56" y="60" width="788" height="56" rx="12" class="badge"/>
    <text x="450" y="98" class="badgeText">LIMITED SHINY SOCCER CARD</text>
    <circle cx="104" cy="152" r="30" class="logoRing"/>
    <image href="${logoA}" x="78" y="126" width="52" height="52" preserveAspectRatio="xMidYMid meet"/>
    <circle cx="796" cy="152" r="30" class="logoRing"/>
    <image href="${logoB}" x="770" y="126" width="52" height="52" preserveAspectRatio="xMidYMid meet"/>
    <text x="450" y="170" class="title">MGAI FEATURE CARD</text>
    <text x="72" y="210" class="sub">${escapeXml(matchTitle)}</text>
    <text x="72" y="256" class="label">Focus: ${escapeXml(preferenceDetail)}</text>
    <rect x="70" y="278" width="760" height="680" rx="28" class="featureShell"/>
    ${frameSvg}
    <rect x="70" y="970" width="760" height="188" rx="18" class="recapShell"/>
    <text x="84" y="1004" class="tilelabel">MATCH STORYLINE</text>
    ${recapSvg}
    <style>
      .title { fill:#f8fafc; font:900 46px Arial,sans-serif; text-anchor:middle; }
      .sub { fill:#bfdbfe; font:700 24px Arial,sans-serif; }
      .label { fill:#67e8f9; font:700 24px Arial,sans-serif; }
      .body { fill:#dbeafe; font:600 22px Arial,sans-serif; }
      .panel { fill: rgba(15,23,42,0.62); stroke: rgba(148,163,184,0.24); stroke-width:2; }
      .badge { fill: rgba(127,29,29,0.72); stroke: rgba(252,165,165,0.35); stroke-width:1.5; }
      .badgeText { fill:#fff1f2; font:800 18px Arial,sans-serif; letter-spacing:0.08em; text-anchor:middle; }
      .logoRing { fill: rgba(2,6,23,0.82); stroke: rgba(250,204,21,0.48); stroke-width:2; }
      .featureShell { fill: rgba(2,6,23,0.58); stroke: rgba(125,211,252,0.24); stroke-width:2; }
      .featureFillA { fill: url(#featureA); }
      .featureFillB { fill: url(#featureB); }
      .featureFillC { fill: url(#featureC); }
      .featureFillD { fill: url(#featureD); }
      .frameLabel { fill:#e0f2fe; font:800 24px Arial,sans-serif; letter-spacing:0.08em; text-anchor:middle; }
      .featureText { fill:#ffffff; font:700 34px Arial,sans-serif; text-anchor:middle; }
      .frameTagBg { fill: rgba(2,6,23,0.58); stroke: rgba(186,230,253,0.24); stroke-width:1.5; }
      .frameTag { fill:#a5f3fc; font:700 24px Arial,sans-serif; text-anchor:middle; }
      .featureFrame { opacity:0; animation: frameCycle 12s linear infinite; }
      .frame1 { animation-delay:0s; }
      .frame2 { animation-delay:3s; }
      .frame3 { animation-delay:6s; }
      .frame4 { animation-delay:9s; }
      .recapShell { fill: rgba(2,6,23,0.66); stroke: rgba(125,211,252,0.24); stroke-width:2; }
      .tilelabel { fill:#fef9c3; font:800 18px Arial,sans-serif; letter-spacing:0.06em; }
      @keyframes frameCycle {
        0% { opacity: 1; }
        22% { opacity: 1; }
        25% { opacity: 0; }
        100% { opacity: 0; }
      }
    </style>
  </svg>`;

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function buildMockResult(teamA, teamB, preferenceType, preferenceDetail, tone, matchInfo) {
  const leftReel = {
    side: "Left Reel",
    title: `${teamA} Analysis Feed`,
    logo: TEAM_LOGOS[teamA],
    teamName: teamA,
    highlights: buildReelHighlights(teamA, teamB, preferenceDetail)
  };

  const rightReel = {
    side: "Right Reel",
    title: `${teamB} Analysis Feed`,
    logo: TEAM_LOGOS[teamB],
    teamName: teamB,
    highlights: buildReelHighlights(teamB, teamA, preferenceDetail)
  };
  const cardMoments = [...leftReel.highlights.slice(0, 2), ...rightReel.highlights.slice(0, 2)];
  const neutralCommentary = buildNeutralCommentary(teamA, teamB, preferenceDetail);

  return {
    title: "Dual-Reel Analyst Output",
    context: `${matchInfo.matchTitle} (${matchInfo.matchName})`,
    matchup: `${teamA} vs ${teamB}`,
    venue: matchInfo.venue,
    commentary: neutralCommentary,
    reels: [leftReel, rightReel],
    preferenceType,
    preferenceDetail,
    tone,
    pokemonCardUrl: buildLocalRecapCardDataUri(
      matchInfo.matchTitle,
      preferenceDetail,
      neutralCommentary,
      teamA,
      teamB,
      cardMoments
    ),
    pokemonCardFilename: "mock_recap_card.svg"
  };
}

function buildPipelineResult(pipelineData, sourceMode, teamA, teamB, matchInfo, youtubeUrl) {
  const inferredTeams = sourceMode !== "teams"
    ? inferTeamsFromPipelineData(pipelineData)
    : { leftTeam: teamA, rightTeam: teamB };

  const leftTeam = inferredTeams.leftTeam || (sourceMode === "teams" ? teamA : "Detected Team A");
  const rightTeam = inferredTeams.rightTeam || (sourceMode === "teams" ? teamB : "Detected Team B");
  const leftHighlights = pipelineData.reel_a_captions?.length
    ? pipelineData.reel_a_captions
    : ["No personalized captions returned."];
  const rightHighlights = pipelineData.reel_b_captions?.length
    ? pipelineData.reel_b_captions
    : ["No neutral captions returned."];
  const fallbackFeatureMoments = [...leftHighlights.slice(0, 2), ...rightHighlights.slice(0, 2)];
  const fallbackCardUrl = buildLocalRecapCardDataUri(
    matchInfo.matchTitle,
    "Pipeline recap",
    pipelineData.match_recap || "Generated from detected highlights.",
    leftTeam,
    rightTeam,
    fallbackFeatureMoments
  );
  const pokemonCardUrl = pipelineData.pokemon_card_url
    ? `${API_BASE_URL}${pipelineData.pokemon_card_url}`
    : fallbackCardUrl;
  const pokemonCardFilename = pipelineData.pokemon_card_filename || "pipeline_recap_card.svg";

  return {
    title: "Dual-Reel Analyst Output",
    context: `${matchInfo.matchTitle} (${matchInfo.matchName})`,
    matchup: sourceMode === "teams"
      ? `${teamA} vs ${teamB}`
      : (sourceMode === "youtube" ? "Matchup detected from YouTube source" : "Matchup inferred from custom prompt"),
    venue: matchInfo.venue,
    sourceUrl: sourceMode === "youtube" ? youtubeUrl : "",
    commentary: pipelineData.match_recap
      || "Video sent to deep-learning pipeline for detection, extraction, and summarization.",
    reels: [
      {
        side: "Left Reel",
        title: `${leftTeam} Analysis Feed`,
        logo: TEAM_LOGOS[leftTeam],
        teamName: leftTeam,
        highlights: leftHighlights
      },
      {
        side: "Right Reel",
        title: `${rightTeam} Analysis Feed`,
        logo: TEAM_LOGOS[rightTeam],
        teamName: rightTeam,
        highlights: rightHighlights
      }
    ],
    pokemonCardUrl,
    pokemonCardFilename
  };
}

function perspectiveKeyForTeam(teamName) {
  const resolved = resolveTeamName(teamName) || String(teamName || "").trim();
  const normalized = String(resolved).trim().toLowerCase();
  if (!normalized) return "";
  if (normalized === "manchester city") return "man_city";
  return slugifyText(normalized);
}

function parseVttTimestampToSeconds(value) {
  const text = String(value || "").trim();
  const parts = text.split(":");
  if (parts.length < 2) return 0;

  let hours = 0;
  let minutes = 0;
  let seconds = 0;

  if (parts.length === 3) {
    hours = Number(parts[0]) || 0;
    minutes = Number(parts[1]) || 0;
    seconds = Number(parts[2]) || 0;
  } else {
    minutes = Number(parts[0]) || 0;
    seconds = Number(parts[1]) || 0;
  }

  return (hours * 3600) + (minutes * 60) + seconds;
}

function parseRawVttCues(vttText) {
  const lines = String(vttText || "").split(/\r?\n/);
  const cues = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line || line === "WEBVTT" || /^\d+$/.test(line)) {
      index += 1;
      continue;
    }

    if (line.includes("-->")) {
      const [startText, endText] = line.split("-->");
      const start = parseVttTimestampToSeconds(startText);
      const end = parseVttTimestampToSeconds(endText);

      index += 1;
      const textLines = [];
      while (index < lines.length && lines[index].trim()) {
        textLines.push(lines[index].trim());
        index += 1;
      }

      const text = textLines.join(" ").trim();
      if (text) {
        cues.push({ start, end, text });
      }
      continue;
    }

    index += 1;
  }

  return cues;
}

function buildSyntheticTimedCues(highlights = []) {
  return (Array.isArray(highlights) ? highlights : [])
    .map((text, idx) => {
      const start = idx * 8;
      const displayEnd = start + 6;
      return {
        start,
        end: displayEnd,
        displayEnd,
        text: String(text || "").trim(),
      };
    })
    .filter((cue) => cue.text);
}

function buildTimedCuesFromVtt(vttText, fallbackHighlights = []) {
  const rawCues = parseRawVttCues(vttText);
  if (rawCues.length === 0) return buildSyntheticTimedCues(fallbackHighlights);

  const merged = [];
  let active = null;

  const flush = () => {
    if (!active) return;
    const finalText = String(active.text || "").trim();
    if (finalText.length >= 8) {
      merged.push({ start: active.start, end: active.end, text: finalText });
    }
    active = null;
  };

  rawCues.forEach((cue) => {
    const text = String(cue.text || "").trim();
    if (!text) return;

    if (!active) {
      active = { start: cue.start, end: cue.end, text };
      return;
    }

    const gap = cue.start - active.end;
    const growsFromPrevious = text.startsWith(active.text);
    const sameText = text === active.text;

    if ((growsFromPrevious || sameText) && gap <= 0.5) {
      active.text = text;
      active.end = cue.end;
      return;
    }

    flush();
    active = { start: cue.start, end: cue.end, text };
  });

  flush();

  if (merged.length === 0) return buildSyntheticTimedCues(fallbackHighlights);

  return merged.map((cue, idx) => {
    const nextCue = merged[idx + 1];
    const naturalEnd = Math.max(cue.end, cue.start + 2.6);
    const boundedEnd = nextCue ? Math.min(naturalEnd, nextCue.start - 0.08) : naturalEnd;
    return {
      ...cue,
      displayEnd: Math.max(cue.start + 1.2, boundedEnd),
    };
  });
}

function findActiveTimedCue(cues, playbackTime) {
  for (let idx = 0; idx < cues.length; idx += 1) {
    const cue = cues[idx];
    if (playbackTime >= cue.start && playbackTime <= cue.displayEnd) {
      return cue;
    }
  }
  return null;
}

function ReelVideoWithTimedCaptions({ reel }) {
  const videoRef = useRef(null);
  const [timedCues, setTimedCues] = useState(() => buildSyntheticTimedCues(reel.highlights));
  const [activeText, setActiveText] = useState("");

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadTimedCues = async () => {
      if (!reel?.vttUrl) {
        setTimedCues(buildSyntheticTimedCues(reel.highlights));
        return;
      }

      try {
        const response = await fetch(reel.vttUrl, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`VTT load failed (${response.status})`);
        }
        const text = await response.text();
        if (!isMounted) return;
        setTimedCues(buildTimedCuesFromVtt(text, reel.highlights));
      } catch {
        if (!isMounted) return;
        setTimedCues(buildSyntheticTimedCues(reel.highlights));
      }
    };

    loadTimedCues();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [reel?.vttUrl, JSON.stringify(reel?.highlights || [])]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return undefined;

    const updateActiveCue = () => {
      const current = findActiveTimedCue(timedCues, video.currentTime || 0);
      setActiveText(current?.text || "");
    };

    updateActiveCue();
    video.addEventListener("timeupdate", updateActiveCue);
    video.addEventListener("seeked", updateActiveCue);
    video.addEventListener("play", updateActiveCue);
    video.addEventListener("loadedmetadata", updateActiveCue);

    return () => {
      video.removeEventListener("timeupdate", updateActiveCue);
      video.removeEventListener("seeked", updateActiveCue);
      video.removeEventListener("play", updateActiveCue);
      video.removeEventListener("loadedmetadata", updateActiveCue);
    };
  }, [timedCues]);

  return (
    <>
      {reel.videoUrl && (
        <div className="reel-video-wrap">
          <video ref={videoRef} controls preload="metadata" className="reel-video-player" src={reel.videoUrl}>
            {reel.vttUrl && (
              <track kind="subtitles" srcLang="en" label="English" src={reel.vttUrl} default />
            )}
          </video>
        </div>
      )}

      <div className="reel-captions-live" aria-live="polite">
        {activeText ? (
          <p className="reel-caption-live" key={activeText}>{activeText}</p>
        ) : (
          <p className="reel-caption-live placeholder">Caption will appear during playback.</p>
        )}
      </div>
    </>
  );
}

function resolvePerspectiveTeamName(perspective, teamA, teamB) {
  const key = String(perspective || "").trim().toLowerCase();
  if (!key || key === "neutral") return "Neutral";
  if (key === perspectiveKeyForTeam(teamA)) return teamA || "Neutral";
  if (key === perspectiveKeyForTeam(teamB)) return teamB || "Neutral";

  const guessed = resolveTeamName(key.replace(/_/g, " "));
  return guessed || "Neutral";
}

function perspectiveKeysForTeam(teamName) {
  const resolved = resolveTeamName(teamName) || String(teamName || "").trim();
  const normalized = String(resolved).trim().toLowerCase();
  if (!normalized) return [];
  if (normalized === "manchester city") {
    return ["man_city", "manchester_city"];
  }
  return [slugifyText(normalized)];
}

function buildShowcaseResult(showcaseData, options = {}) {
  const {
    tone = "",
    teamA = "",
    teamB = "",
    preferenceType = "",
    preferenceDetail = "",
  } = options;
  const reels = Array.isArray(showcaseData?.reels) ? showcaseData.reels : [];
  const mappedAllReels = reels.map((reel, index) => {
    const perspective = String(reel?.perspective || "").trim().toLowerCase();
    const teamName = resolvePerspectiveTeamName(perspective, teamA, teamB);
    const highlights = Array.isArray(reel?.captions)
      ? reel.captions
        .map((line) => String(line || "").trim())
        .filter(Boolean)
      : [];

    return {
      perspective,
      side: perspective === "neutral" ? "Neutral Reel" : `Perspective ${index + 1}`,
      title: String(reel?.label || "Pre-generated Reel"),
      logo: perspective === "neutral" ? FALLBACK_TEAM_LOGO : TEAM_LOGOS[teamName],
      teamName,
      highlights,
      videoUrl: reel?.video_url ? `${API_BASE_URL}${reel.video_url}` : "",
      vttUrl: reel?.vtt_url ? `${API_BASE_URL}${reel.vtt_url}` : ""
    };
  });

  const byPerspective = Object.fromEntries(
    mappedAllReels.map((reel) => [String(reel.perspective || "").toLowerCase(), reel])
  );

  let mappedReels = mappedAllReels;
  const toneKey = String(tone || "").toLowerCase();
  const isExpressive = toneKey === "expressive";
  const preferredTeamName = (
    String(preferenceType || "").toLowerCase() === "team"
      ? (resolveTeamName(preferenceDetail) || String(preferenceDetail || "").trim())
      : ""
  );
  const findReelForTeam = (teamName) => {
    const resolvedTeam = resolveTeamName(teamName) || String(teamName || "").trim();
    if (!resolvedTeam) return null;
    const keys = perspectiveKeysForTeam(resolvedTeam);
    return mappedAllReels.find((reel) =>
      keys.includes(String(reel.perspective || "").toLowerCase())
      || reel.teamName === resolvedTeam
    ) || null;
  };

  let commentary = "Using stored reels and VTT captions from Charles backend output.";
  let commentaryTitle = "Commentary";

  if (toneKey === "neutral") {
    const neutral = byPerspective.neutral;
    if (neutral) {
      mappedReels = [{
        ...neutral,
        side: "Neutral Reel",
      }];
      commentaryTitle = "Neutral Commentary";
      commentary = neutral.highlights.slice(0, 2).join(" ") || commentary;
    }
  } else if (isExpressive) {
    const expressive = [findReelForTeam(teamA), findReelForTeam(teamB)].filter(Boolean);
    if (expressive.length > 0) {
      const orderedExpressive = preferredTeamName
        ? [...expressive].sort((a, b) => {
          const aPreferred = a.teamName === preferredTeamName ? 1 : 0;
          const bPreferred = b.teamName === preferredTeamName ? 1 : 0;
          return bPreferred - aPreferred;
        })
        : expressive;

      mappedReels = orderedExpressive.map((reel, idx) => ({
        ...reel,
        side: idx === 0 ? "Left Reel" : "Right Reel",
      }));
      commentaryTitle = "Expressive Commentary";
      commentary = orderedExpressive
        .map((reel) => {
          const firstLine = reel.highlights[0];
          if (!firstLine) return "";
          return `${reel.teamName}: ${firstLine}`;
        })
        .filter(Boolean)
        .join(" ")
        || commentary;
    }
  } else {
    const neutral = byPerspective.neutral;
    if (neutral?.highlights?.length) {
      commentary = neutral.highlights.slice(0, 2).join(" ");
      commentaryTitle = "Commentary";
    }
  }

  return {
    title: "",
    context: "",
    matchup: teamA && teamB ? `${teamA} vs ${teamB}` : "Showcase Match",
    venue: "Venue from showcase output",
    sourceUrl: "",
    commentaryTitle,
    commentary,
    reels: mappedReels,
    pokemonCardUrl: buildLocalRecapCardDataUri(
      teamA && teamB ? `${teamA} vs ${teamB}` : "Showcase Match",
      preferenceDetail || tone || "Showcase recap",
      commentary,
      teamA || "",
      teamB || "",
      mappedReels.flatMap((reel) => reel.highlights).slice(0, 4)
    ),
    pokemonCardFilename: `${slugifyText(teamA || "team_a")}_vs_${slugifyText(teamB || "team_b")}_showcase_card.svg`
  };
}

function TeamFoilBadge({ logoSrc, teamName, size = 220, speed = "11s" }) {
  const tuning = TEAM_LOGO_TUNING[teamName] || { scale: 1, y: 0 };
  const effectiveLogoSrc = logoSrc || FALLBACK_TEAM_LOGO;
  const isFallbackLogo = !logoSrc;
  const logoStyle = {
    transform: `translateY(${tuning.y}px) scale(${tuning.scale})`
  };

  return (
    <div
      className="badge-stage"
      style={{
        "--badge-size": `${size}px`,
        "--badge-speed": speed
      }}
      aria-label={`${teamName} rotating foil badge`}
    >
      <div className="badge-orbit">
        <div className="badge-aura" aria-hidden="true" />
        <div className="badge-core">
          <div className="badge-face badge-front">
            <img
              src={effectiveLogoSrc}
              alt={isFallbackLogo ? "Premier League logo placeholder" : `${teamName} official logo`}
              style={logoStyle}
            />
          </div>
          <div className="badge-face badge-back">
            <img src={effectiveLogoSrc} alt="" aria-hidden="true" style={logoStyle} />
          </div>
          <div className="badge-glare" aria-hidden="true" />
          <div className="badge-sheen" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

function TeamLogoPreview({ teamName }) {
  if (!teamName) return null;
  const logoSrc = TEAM_LOGOS[teamName];

  return (
    <div
      style={{
        marginTop: "16px",
        marginBottom: "20px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px"
      }}
    >
      <TeamFoilBadge logoSrc={logoSrc} teamName={teamName} size={220} speed="10s" />
      <strong style={{ fontSize: "15px" }}>
        {logoSrc ? `${teamName} official logo` : `${teamName} logo unavailable - showing league crest`}
      </strong>
    </div>
  );
}

function isSvgAssetUrl(url) {
  const value = String(url || "").trim().toLowerCase();
  return value.startsWith("data:image/svg+xml") || value.endsWith(".svg");
}

export default function App() {
  const [sourceMode, setSourceMode] = useState("teams");
  const [teamA, setTeamA] = useState("");
  const [teamB, setTeamB] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [sourcePrompt, setSourcePrompt] = useState("");
  const [preferenceType, setPreferenceType] = useState("");
  const [preferenceDetail, setPreferenceDetail] = useState("");
  const [tone, setTone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState("");
  const [healthStatusKind, setHealthStatusKind] = useState("");
  const [youtubeTitle, setYoutubeTitle] = useState("");
  const [youtubeTitleLoading, setYoutubeTitleLoading] = useState(false);
  const [headerMode, setHeaderMode] = useState("scores");
  const [eplTickerMatches, setEplTickerMatches] = useState([]);
  const [eplFixtureMatches, setEplFixtureMatches] = useState([]);
  const [eplTableRows, setEplTableRows] = useState([]);
  const [eplTickerLoading, setEplTickerLoading] = useState(true);
  const [selectedTickerMatch, setSelectedTickerMatch] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState("");
  const [liveCommentary, setLiveCommentary] = useState([]);
  const [commentaryUpdatedAt, setCommentaryUpdatedAt] = useState("");
  const [backendFeed, setBackendFeed] = useState(null);
  const [backendFeedError, setBackendFeedError] = useState("");
  const [dynamicPlayers, setDynamicPlayers] = useState([]);
  const [playersLoading, setPlayersLoading] = useState(false);
  const [playerPoolMessage, setPlayerPoolMessage] = useState("");
  const [playerHeadshotFailed, setPlayerHeadshotFailed] = useState({});
  const headerMetaLabel = HEADER_NAV_ITEMS.find((item) => item.key === headerMode)?.metaLabel || "Recent EPL Scores";
  const backendHighlights = Array.isArray(backendFeed?.highlights)
    ? backendFeed.highlights.slice(0, EPL_STRIP_MAX_ITEMS).map((item, index) => ({
      id: String(item?.id || item?.segment_id || `backend-highlight-${index}`),
      headline: String(item?.time || "").trim()
        ? `[${String(item?.time || "").trim()}] ${String(item?.event_type || "Event").replace(/_/g, " ")}`
        : String(item?.event_type || "Match event").replace(/_/g, " "),
      detail: String(item?.narrative || item?.commentary || "Backend feed event").trim()
    }))
    : [];
  const highlightTickerItems = backendHighlights.length > 0
    ? backendHighlights
    : buildHighlightTickerItems(eplTickerMatches, eplFixtureMatches);
  const headerCarouselItems = headerMode === "fixtures"
    ? eplFixtureMatches
    : (headerMode === "highlights"
      ? highlightTickerItems
      : (headerMode === "tables" ? eplTableRows : eplTickerMatches));
  const loopedHeaderCarouselItems = headerCarouselItems.length > 0
    ? [...headerCarouselItems, ...headerCarouselItems]
    : [];

  const tickerTeamOptions = [...eplTickerMatches, ...eplFixtureMatches]
    .flatMap((match) => [match?.home, match?.away])
    .filter(Boolean);
  const teamOptions = Array.from(new Set([...EPL_TEAMS, ...tickerTeamOptions]));
  const selectedTeams = [teamA, teamB].filter(Boolean);
  const backendContext = backendFeed?.match_context || {};
  const backendScorePieces = String(backendContext?.final_score || "")
    .split("-")
    .map((piece) => piece.trim())
    .filter((piece) => piece.length > 0);
  const backendWidgetMatch = backendContext?.home_team && backendContext?.away_team
    ? {
      id: `backend-${backendContext.match_id || "match"}`,
      home: backendContext.home_team,
      away: backendContext.away_team,
      homeScore: backendScorePieces[0] || "-",
      awayScore: backendScorePieces[1] || "-",
      dateLabel: backendContext.date || "",
      kickoffLabel: backendContext.date || "",
      status: backendContext.final_score ? "FT" : "Live"
    }
    : null;
  const matchFromTeams = selectedTeams.length === 2
    ? [...eplTickerMatches, ...eplFixtureMatches].find((item) => {
      const left = resolveTeamName(item?.home) || String(item?.home || "").trim();
      const right = resolveTeamName(item?.away) || String(item?.away || "").trim();
      return (
        (left === teamA && right === teamB)
        || (left === teamB && right === teamA)
      );
    }) || null
    : null;
  const widgetMatch = matchFromTeams || selectedTickerMatch || backendWidgetMatch || eplTickerMatches[0] || eplFixtureMatches[0] || null;
  const weatherLocation = TEAM_WEATHER_LOCATIONS[widgetMatch?.home] || TEAM_WEATHER_LOCATIONS[teamA] || null;
  const matchInfo = getMatchInfo(sourceMode, teamA, teamB, youtubeUrl, youtubeTitle, sourcePrompt);
  const fallbackPlayers = sourceMode === "teams"
    ? FALLBACK_PLAYER_DATABASE.filter((player) => selectedTeams.includes(player.team))
    : FALLBACK_PLAYER_DATABASE;
  const availablePlayers = sourceMode === "teams" && dynamicPlayers.length > 0
    ? dynamicPlayers
    : fallbackPlayers;
  const uniqueAvailablePlayers = Array.from(
    new Map(availablePlayers.map((player) => [`${player.team}::${player.name}`, player])).values()
  ).filter((player) => {
    const playerKey = `${player.team}::${player.name}`;
    return hasRealHeadshot(player.headshot) && !playerHeadshotFailed[playerKey];
  });
  const selectablePlayers = uniqueAvailablePlayers.filter((player) =>
    sourceMode !== "teams" || selectedTeams.includes(player.team)
  );
  const availablePlayerNames = Array.from(new Set(selectablePlayers.map((player) => player.name)));

  const preferenceTypeOptions = [
    "team",
    "individual",
    "event category",
    "general recap"
  ];

  const teamDetails = sourceMode === "teams"
    ? [teamA, teamB].filter(Boolean)
    : ["Detected Team A", "Detected Team B"];

  const preferenceDetailMap = {
    team: teamDetails,
    individual: availablePlayerNames,
    "event category": ["Key moments", "Turning points", "High impact moments"],
    "general recap": ["Overview", "Condensed summary", "Narrative recap"]
  };

  const detailOptions = preferenceType ? preferenceDetailMap[preferenceType] || [] : [];

  const hasValidSource = sourceMode === "teams"
    ? teamA && teamB && teamA !== teamB
    : (sourceMode === "youtube" ? isValidYouTubeUrl(youtubeUrl) : sourcePrompt.trim().length > 0);

  const isFormComplete = sourceMode === "text"
    ? hasValidSource
    : (
      hasValidSource &&
      preferenceType &&
      preferenceDetail &&
      tone
    );

  const handleSourceModeChange = (nextMode) => {
    setSourceMode(nextMode);
    setTeamA("");
    setTeamB("");
    setYoutubeUrl("");
    setSourcePrompt("");
    setYoutubeTitle("");
    setYoutubeTitleLoading(false);
    setPreferenceType("");
    setPreferenceDetail("");
    setTone("");
    setDynamicPlayers([]);
    setPlayersLoading(false);
    setPlayerPoolMessage("");
    setPlayerHeadshotFailed({});
    setError("");
    setResult(null);
  };

  const handleTickerMatchSelect = (match) => {
    const resolvedHome = resolveTeamName(match?.home) || String(match?.home || "").trim();
    const resolvedAway = resolveTeamName(match?.away) || String(match?.away || "").trim();

    if (!resolvedHome || !resolvedAway || resolvedHome === resolvedAway) {
      return;
    }

    handleSourceModeChange("teams");
    setTeamA(resolvedHome);
    setTeamB(resolvedAway);
    setSelectedTickerMatch({
      ...match,
      home: resolvedHome,
      away: resolvedAway
    });
  };

  useEffect(() => {
    const controller = new AbortController();

    const loadHeaderFeeds = async () => {
      setEplTickerLoading(true);
      try {
        const loadFeed = async (url) => {
          const response = await fetch(url, { signal: controller.signal });
          if (!response.ok) {
            throw new Error(`Feed error (${response.status})`);
          }
          return response.json().catch(() => ({}));
        };

        const [scoresPayload, fixturesPayload, tablePayload] = await Promise.all([
          loadFeed(EPL_RECENT_MATCHES_ENDPOINT).catch(() => ({})),
          loadFeed(EPL_FIXTURES_ENDPOINT).catch(() => ({})),
          loadFeed(EPL_TABLE_ENDPOINT).catch(() => ({}))
        ]);

        const scoreEvents = Array.isArray(scoresPayload?.events) ? scoresPayload.events : [];
        const fixtureEvents = Array.isArray(fixturesPayload?.events) ? fixturesPayload.events : [];
        const tableEvents = Array.isArray(tablePayload?.table) ? tablePayload.table : [];

        const scoreMatches = scoreEvents.slice(0, EPL_STRIP_MAX_ITEMS).map((event, index) => ({
          id: event?.idEvent || `${event?.dateEvent || "event"}-${index}`,
          home: event?.strHomeTeam || "Home",
          away: event?.strAwayTeam || "Away",
          homeScore: normalizeScore(event?.intHomeScore),
          awayScore: normalizeScore(event?.intAwayScore),
          dateLabel: formatEplStripDate(event?.dateEvent, event?.strTime),
          kickoffLabel: formatEplStripDateTime(event?.dateEvent, event?.strTime),
          status: String(event?.strStatus || "FT").trim()
        }));

        const fixtureMatches = fixtureEvents.slice(0, EPL_STRIP_MAX_ITEMS).map((event, index) => ({
          id: event?.idEvent || `fixture-${event?.dateEvent || "event"}-${index}`,
          home: event?.strHomeTeam || "Home",
          away: event?.strAwayTeam || "Away",
          kickoffLabel: formatEplStripDateTime(event?.dateEvent, event?.strTime),
          status: String(event?.strStatus || "Scheduled").trim(),
        }));

        const fallbackAlphabeticalTable = [...EPL_TEAMS]
          .sort((a, b) => a.localeCompare(b))
          .map((teamName, index) => ({
            id: `fallback-table-${index}`,
            team: teamName,
            played: "-",
            points: "-",
            goalDiff: "-"
          }));

        const tableRows = tableEvents
          .map((row, index) => {
            const teamName = resolveTeamName(row?.strTeam) || String(row?.strTeam || "").trim();
            if (!teamName) return null;
            return {
              id: row?.idStanding || `table-${teamName}-${index}`,
              team: teamName,
              played: normalizeScore(row?.intPlayed),
              points: normalizeScore(row?.intPoints),
              goalDiff: normalizeScore(row?.intGoalDifference),
            };
          })
          .filter(Boolean)
          .sort((a, b) => a.team.localeCompare(b.team));

        setEplTickerMatches(scoreMatches);
        setEplFixtureMatches(fixtureMatches);
        setEplTableRows(tableRows.length > 0 ? tableRows : fallbackAlphabeticalTable);
        setSelectedTickerMatch((prev) => prev || scoreMatches[0] || fixtureMatches[0] || null);
      } catch (err) {
        if (err?.name !== "AbortError") {
          setEplTickerMatches([]);
          setEplFixtureMatches([]);
          setEplTableRows(
            [...EPL_TEAMS]
              .sort((a, b) => a.localeCompare(b))
              .map((teamName, index) => ({
                id: `fallback-table-${index}`,
                team: teamName,
                played: "-",
                points: "-",
                goalDiff: "-"
              }))
          );
          setSelectedTickerMatch((prev) => prev || null);
        }
      } finally {
        setEplTickerLoading(false);
      }
    };

    loadHeaderFeeds();
    const pollId = setInterval(loadHeaderFeeds, FEED_REFRESH_MS);
    return () => {
      clearInterval(pollId);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    const loadBackendFeed = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}${WEBSITE_FEED_ENDPOINT}?limit=20`);
        if (!response.ok) {
          throw new Error(`Website feed request failed (${response.status})`);
        }
        const payload = await response.json().catch(() => ({}));
        if (!isActive) return;
        setBackendFeed(payload && typeof payload === "object" ? payload : null);
        setBackendFeedError("");
      } catch (err) {
        if (!isActive) return;
        setBackendFeed(null);
        setBackendFeedError(err?.message || "Backend website feed unavailable");
      }
    };

    loadBackendFeed();
    const pollId = setInterval(loadBackendFeed, FEED_REFRESH_MS);
    return () => {
      isActive = false;
      clearInterval(pollId);
    };
  }, []);

  useEffect(() => {
    if (sourceMode !== "teams") {
      setDynamicPlayers([]);
      setPlayersLoading(false);
      setPlayerPoolMessage("");
      return;
    }

    if (selectedTeams.length === 0) {
      setDynamicPlayers([]);
      setPlayersLoading(false);
      setPlayerPoolMessage("");
      return;
    }

    const controller = new AbortController();

    const loadTeamPlayers = async () => {
      setPlayersLoading(true);
      setPlayerPoolMessage("Loading players from recent EPL pool...");

      try {
        const params = new URLSearchParams({
          teams: selectedTeams.join(","),
          years: "2",
          limit_per_team: "60",
          require_real_headshot: "true",
        });

        const response = await fetch(`${API_BASE_URL}${PLAYERS_ENDPOINT}?${params.toString()}`, {
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error(`Player pool request failed: ${response.status}`);
        }

        const payload = await response.json().catch(() => ({}));
        const rows = Array.isArray(payload?.players) ? payload.players : [];
        const skippedMissingHeadshot = Number(payload?.skipped_missing_headshot || 0);

        const mapped = rows
          .map((player) => {
            const name = String(player?.name || "").trim();
            if (!name) return null;

            const resolvedTeam = resolveTeamName(player?.team) || String(player?.team || "").trim() || "Unknown Team";
            const headshot = String(player?.headshot || "").trim();
            if (!hasRealHeadshot(headshot)) return null;

            return {
              name,
              team: resolvedTeam,
              headshot
            };
          })
          .filter(Boolean);

        if (mapped.length > 0) {
          setDynamicPlayers(mapped);
          const skippedNote = skippedMissingHeadshot > 0
            ? ` (${skippedMissingHeadshot} without verified headshots hidden)`
            : "";
          setPlayerPoolMessage(`${mapped.length} players loaded with real headshots from the last 2 EPL seasons.${skippedNote}`);
        } else {
          setDynamicPlayers([]);
          setPlayerPoolMessage("No players with verified real headshots returned from the recent pool.");
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        setDynamicPlayers([]);
        setPlayerPoolMessage("Could not load recent player pool right now.");
      } finally {
        setPlayersLoading(false);
      }
    };

    loadTeamPlayers();
    return () => controller.abort();
  }, [sourceMode, teamA, teamB]);

  useEffect(() => {
    if (preferenceType !== "individual") return;
    if (!preferenceDetail) return;
    if (availablePlayerNames.includes(preferenceDetail)) return;
    setPreferenceDetail("");
  }, [preferenceType, preferenceDetail, availablePlayerNames]);

  useEffect(() => {
    if (sourceMode !== "youtube") {
      setYoutubeTitle("");
      setYoutubeTitleLoading(false);
      return;
    }

    if (!isValidYouTubeUrl(youtubeUrl)) {
      setYoutubeTitle("");
      setYoutubeTitleLoading(false);
      return;
    }

    const controller = new AbortController();
    const sourceUrl = youtubeUrl.trim();

    const loadYoutubeTitle = async () => {
      setYoutubeTitleLoading(true);
      setYoutubeTitle("");

      try {
        const endpoints = [
          `https://www.youtube.com/oembed?url=${encodeURIComponent(sourceUrl)}&format=json`,
          `https://www.youtube-nocookie.com/oembed?url=${encodeURIComponent(sourceUrl)}&format=json`
        ];

        for (const endpoint of endpoints) {
          const response = await fetch(endpoint, { signal: controller.signal });
          if (!response.ok) continue;

          const payload = await response.json();
          const title = String(payload?.title || "").trim();
          if (title) {
            setYoutubeTitle(title);
            return;
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
      } finally {
        setYoutubeTitleLoading(false);
      }
    };

    loadYoutubeTitle();
    return () => controller.abort();
  }, [sourceMode, youtubeUrl]);

  useEffect(() => {
    if (selectedTeams.length !== 2 || !matchFromTeams) return;
    setSelectedTickerMatch(matchFromTeams);
  }, [teamA, teamB, eplTickerMatches, eplFixtureMatches, selectedTeams.length, matchFromTeams]);

  useEffect(() => {
    if (!weatherLocation || !widgetMatch) {
      setWeatherData(null);
      setWeatherError("");
      setWeatherLoading(false);
      return;
    }

    const controller = new AbortController();
    const loadWeather = async () => {
      setWeatherLoading(true);
      setWeatherError("");

      try {
        const params = new URLSearchParams({
          latitude: String(weatherLocation.latitude),
          longitude: String(weatherLocation.longitude),
          current: "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
          timezone: "auto"
        });
        const response = await fetch(`${WEATHER_ENDPOINT}?${params.toString()}`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Weather request failed (${response.status})`);
        }
        const payload = await response.json().catch(() => ({}));
        const current = payload?.current || {};
        setWeatherData({
          location: weatherLocation.label,
          temperature: current?.temperature_2m,
          apparent: current?.apparent_temperature,
          precipitation: current?.precipitation,
          wind: current?.wind_speed_10m,
          weatherCode: current?.weather_code,
          updatedAt: current?.time || ""
        });
      } catch (err) {
        if (err?.name === "AbortError") return;
        setWeatherData(null);
        setWeatherError(err?.message || "Weather feed unavailable");
      } finally {
        setWeatherLoading(false);
      }
    };

    loadWeather();
    return () => controller.abort();
  }, [weatherLocation, widgetMatch]);

  useEffect(() => {
    if (!widgetMatch) {
      setLiveCommentary([]);
      setCommentaryUpdatedAt("");
      return;
    }

    const backendCommentary = Array.isArray(backendFeed?.commentary)
      ? backendFeed.commentary
        .map((row) => String(row?.commentary || row?.narrative || "").trim())
        .filter(Boolean)
      : [];
    if (backendCommentary.length > 0) {
      const parsedUpdatedAt = backendFeed?.updated_at ? new Date(backendFeed.updated_at) : null;
      const updatedLabel = parsedUpdatedAt && !Number.isNaN(parsedUpdatedAt.getTime())
        ? parsedUpdatedAt.toLocaleTimeString()
        : new Date().toLocaleTimeString();
      setLiveCommentary(backendCommentary.slice(0, 7));
      setCommentaryUpdatedAt(updatedLabel);
      return;
    }

    let sequence = 0;
    const firstBatch = [0, 1, 2].map((idx) => buildCommentaryLine(widgetMatch, idx));
    setLiveCommentary(firstBatch);
    setCommentaryUpdatedAt(new Date().toLocaleTimeString());

    const intervalId = setInterval(() => {
      sequence += 1;
      setLiveCommentary((prev) => [buildCommentaryLine(widgetMatch, sequence + 2), ...prev].slice(0, 7));
      setCommentaryUpdatedAt(new Date().toLocaleTimeString());
    }, COMMENTARY_REFRESH_MS);

    return () => clearInterval(intervalId);
  }, [
    widgetMatch?.id,
    widgetMatch?.home,
    widgetMatch?.away,
    widgetMatch?.homeScore,
    widgetMatch?.awayScore,
    widgetMatch?.status,
    widgetMatch?.kickoffLabel,
    widgetMatch?.dateLabel,
    backendFeed?.updated_at,
    backendFeed?.commentary
  ]);

  const handleGenerate = async () => {
    if (!isFormComplete) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const showcaseMatchName = sourceMode === "teams"
        ? getShowcaseMatchForTeams(teamA, teamB)
        : "";

      if (showcaseMatchName) {
        const showcaseResponse = await fetch(`${API_BASE_URL}${SHOWCASE_ENDPOINT}/${showcaseMatchName}`);
        if (!showcaseResponse.ok) {
          const payload = await showcaseResponse.json().catch(() => ({}));
          throw new Error(payload.detail || `Showcase request failed: ${showcaseResponse.status}`);
        }
        const showcaseData = await showcaseResponse.json();
        setResult(buildShowcaseResult(showcaseData, {
          tone,
          teamA,
          teamB,
          preferenceType,
          preferenceDetail
        }));
        return;
      }

      if (sourceMode === "youtube" || sourceMode === "text") {
        const sourceModeValue = sourceMode === "youtube" ? "youtube" : "text";
        const response = await fetch(`${API_BASE_URL}${RUN_ENDPOINT}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            match_name: matchInfo.matchName,
            user_preference: buildUserPreference(
              sourceMode,
              teamA,
              teamB,
              preferenceType,
              preferenceDetail,
              tone,
              youtubeUrl,
              sourcePrompt
            ),
            youtube_url: sourceMode === "youtube" ? youtubeUrl : null,
            source_mode: sourceModeValue
          })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(async () => {
            const text = await response.text().catch(() => "");
            return { detail: text };
          });
          throw new Error(errorData.detail || `Pipeline request failed: ${response.status}`);
        }

        const pipelineData = await response.json();
        if (pipelineData.status && pipelineData.status !== "success") {
          throw new Error(pipelineData.error_message || "Pipeline returned error status.");
        }
        setResult(buildPipelineResult(pipelineData, sourceMode, teamA, teamB, matchInfo, youtubeUrl));
      } else {
        await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS));
        setResult(buildMockResult(teamA, teamB, preferenceType, preferenceDetail, tone, matchInfo));
      }
    } catch (err) {
      setError(
        err?.message
        || `Failed to generate output. Ensure backend is running and reachable at ${API_BASE_URL}.`
      );
    } finally {
      setLoading(false);
    }
  };

  const handleHealthCheck = async () => {
    setHealthLoading(true);
    setHealthStatus("");
    setHealthStatusKind("");

    try {
      const response = await fetch(`${API_BASE_URL}${STATUS_ENDPOINT}`);
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const data = await response.json().catch(() => ({}));
      const statusLabel = data?.status || "unknown";
      const demoModeLabel =
        typeof data?.demo_mode === "boolean" ? `, demo_mode=${data.demo_mode}` : "";

      setHealthStatus(`Backend reachable at ${API_BASE_URL} (status=${statusLabel}${demoModeLabel}).`);
      setHealthStatusKind("ok");
    } catch (err) {
      setHealthStatus(
        err?.message || `Backend unreachable at ${API_BASE_URL}. Start the FastAPI server and retry.`
      );
      setHealthStatusKind("error");
    } finally {
      setHealthLoading(false);
    }
  };

  return (
    <div className="generator-shell">
      <header className="espn-header" aria-label="Recent EPL matches">
        <div className="espn-topbar">
          <div className="espn-brand">MGAI MATCHCENTER</div>
          <nav className="espn-nav" aria-label="Sports navigation">
            {HEADER_NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`espn-nav-btn${headerMode === item.key ? " active" : ""}`}
                onClick={() => setHeaderMode(item.key)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="espn-meta-row">
          <span className="espn-league-badge">EPL</span>
          <span className="espn-meta-label">{headerMetaLabel}</span>
        </div>
        <div className="epl-strip-track espn-scoreboard-track">
          {eplTickerLoading && (
            <span className="epl-pill muted">Loading {headerMetaLabel.toLowerCase()}...</span>
          )}
          {!eplTickerLoading && headerCarouselItems.length === 0 && (
            <span className="epl-pill muted">Carousel feed unavailable.</span>
          )}
          {!eplTickerLoading && headerCarouselItems.length > 0 && (
            <div className="epl-strip-marquee">
              {loopedHeaderCarouselItems.map((item, index) => (
                (() => {
                  const isClone = index >= headerCarouselItems.length;

                  if (headerMode === "highlights") {
                    return (
                      <span
                        key={`${item.id}-${index}`}
                        className="epl-pill espn-highlight-pill muted-pill"
                        aria-hidden={isClone}
                      >
                        <span className="espn-pill-date">COMMENTARY</span>
                        <span className="espn-pill-match">{item.headline}</span>
                        <span className="espn-pill-detail">{item.detail}</span>
                      </span>
                    );
                  }

                  if (headerMode === "tables") {
                    return (
                      <span
                        key={`${item.id}-${index}`}
                        className="epl-pill espn-table-pill muted-pill"
                        aria-hidden={isClone}
                      >
                        <span className="espn-pill-date">TABLE</span>
                        <span className="espn-table-team">{item.team}</span>
                        <span className="espn-table-stats">P {item.played} | GD {item.goalDiff} | PTS {item.points}</span>
                      </span>
                    );
                  }

                  const isSelectable = !!String(item?.home || "").trim() && !!String(item?.away || "").trim();
                  const baseClass = `epl-pill espn-score-pill${isSelectable ? " clickable" : " muted-pill"}`;
                  const dateText = headerMode === "fixtures" ? item.kickoffLabel : item.dateLabel;
                  const matchupText = headerMode === "fixtures"
                    ? `${item.home} vs ${item.away}`
                    : `${item.home} ${item.homeScore} - ${item.awayScore} ${item.away}`;

                  if (isSelectable) {
                    return (
                      <button
                        key={`${item.id}-${index}`}
                        type="button"
                        className={baseClass}
                        onClick={() => handleTickerMatchSelect(item)}
                        title={`Use ${item.home} vs ${item.away}`}
                        tabIndex={isClone ? -1 : 0}
                        aria-hidden={isClone || undefined}
                      >
                        <span className="espn-pill-date">{dateText}</span>
                        <span className="espn-pill-match">{matchupText}</span>
                      </button>
                    );
                  }

                  return (
                    <span
                      key={`${item.id}-${index}`}
                      className={baseClass}
                      aria-hidden={isClone}
                    >
                      <span className="espn-pill-date">{dateText}</span>
                      <span className="espn-pill-match">{matchupText}</span>
                    </span>
                  );
                })()
              ))}
            </div>
          )}
        </div>
      </header>
      <div className="generator-main">
        <div className="generator-primary">
      <h1 className="generator-title">{matchInfo.matchTitle}</h1>
      <p className="output-context" style={{ marginBottom: "8px" }}>
        Match Name: {matchInfo.matchName}
      </p>
      {sourceMode === "youtube" && (
        <p className="output-context" style={{ marginBottom: "20px" }}>
          Source URL is sent to deep-learning match detection pipeline.
        </p>
      )}
      {sourceMode === "text" && (
        <p className="output-context" style={{ marginBottom: "20px" }}>
          Free-text request is sent to pipeline for keyword extraction and highlight generation.
        </p>
      )}

      <div className="select-block">
        <label className="select-label">Source Mode</label>
        <div className="select-wrap">
          <select
            className="fifa-select"
            value={sourceMode}
            onChange={(e) => handleSourceModeChange(e.target.value)}
          >
            <option value="teams">Team A/B Selection</option>
            <option value="youtube">YouTube Link</option>
            <option value="text">Custom Text Prompt</option>
          </select>
        </div>
      </div>

      {sourceMode === "teams" ? (
        <>
          <div className="select-block">
            <label className="select-label">Team A</label>
            <div className="select-wrap">
              <select
                className="fifa-select"
                value={teamA}
                onChange={(e) => setTeamA(e.target.value)}
              >
                <option value="">Select Team A</option>
                {teamOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </div>
          </div>
          <TeamLogoPreview teamName={teamA} />

          {teamA && (
            <>
              <div className="select-block">
                <label className="select-label">Team B</label>
                <div className="select-wrap">
                  <select
                    className="fifa-select"
                    value={teamB}
                    onChange={(e) => setTeamB(e.target.value)}
                  >
                    <option value="">Select Team B</option>
                    {teamOptions
                      .filter((option) => option !== teamA)
                      .map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                  </select>
                </div>
              </div>
              <TeamLogoPreview teamName={teamB} />
            </>
          )}
        </>
      ) : sourceMode === "youtube" ? (
        <div className="select-block">
          <label className="select-label">YouTube Match Link</label>
          <input
            className="fifa-select"
            type="url"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            style={{ paddingRight: "22px" }}
          />
          {youtubeUrl && !isValidYouTubeUrl(youtubeUrl) && (
            <p className="output-context" style={{ marginTop: "10px", color: "#fecaca" }}>
              Enter a valid YouTube URL before generating.
            </p>
          )}
          {youtubeUrl && isValidYouTubeUrl(youtubeUrl) && youtubeTitleLoading && (
            <p className="output-context" style={{ marginTop: "10px" }}>
              Fetching YouTube title...
            </p>
          )}
          {youtubeTitle && (
            <p className="output-context" style={{ marginTop: "10px" }}>
              Video Title: {youtubeTitle}
            </p>
          )}
        </div>
      ) : (
        <div className="select-block">
          <label className="select-label">Custom Request</label>
          <textarea
            className="fifa-select source-textarea"
            value={sourcePrompt}
            onChange={(e) => setSourcePrompt(e.target.value)}
            placeholder="Type anything you want to focus on (football or non-football). The pipeline will extract keywords and return the best available highlights."
          />
        </div>
      )}

      {sourceMode !== "text" && hasValidSource && (
        <div className="select-block">
          <label className="select-label">Preference Type</label>
          <div className="select-wrap">
            <select
              className="fifa-select"
              value={preferenceType}
              onChange={(e) => {
                setPreferenceType(e.target.value);
                setPreferenceDetail("");
              }}
            >
              <option value="">Select preference type</option>
              {preferenceTypeOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {preferenceType && (
        <div className="select-block">
          <label className="select-label">Preference Detail</label>
          {preferenceType === "individual" ? (
            <>
              <p className="player-pool-status">
                {playersLoading ? "Refreshing player pool..." : playerPoolMessage}
              </p>
              <div className="player-picker-grid" role="listbox" aria-label="Player selection">
              {selectablePlayers.map((player) => {
                const playerKey = `${player.team}::${player.name}`;
                const isSelected = preferenceDetail === player.name;

                return (
                  <button
                    key={playerKey}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    className={`player-option-btn${isSelected ? " selected" : ""}`}
                    onClick={() => setPreferenceDetail(player.name)}
                  >
                    <span className="player-headshot-wrap">
                      <img
                        src={player.headshot}
                        alt={`${player.name} headshot`}
                        className="player-headshot"
                        loading="lazy"
                        onError={() => {
                          setPlayerHeadshotFailed((prev) => ({ ...prev, [playerKey]: true }));
                        }}
                      />
                    </span>
                    <span className="player-option-meta">
                      <span className="player-option-name">{player.name}</span>
                      <span className="player-option-team">{player.team}</span>
                    </span>
                  </button>
                );
              })}
              {selectablePlayers.length === 0 && (
                <p className="output-context" style={{ margin: "4px 0 0", color: "#fecaca" }}>
                  No players with verified real headshots available for the selected teams.
                </p>
              )}
              </div>
            </>
          ) : (
            <div className="select-wrap">
              <select
                className="fifa-select"
                value={preferenceDetail}
                onChange={(e) => setPreferenceDetail(e.target.value)}
              >
                <option value="">Select preference detail</option>
                {detailOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {preferenceDetail && (
        <div className="select-block">
          <label className="select-label">Tone</label>
          <div className="select-wrap">
            <select
              className="fifa-select"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
            >
              <option value="">Select tone</option>
              <option value="neutral">Neutral</option>
              <option value="expressive">Expressive</option>
            </select>
          </div>
        </div>
      )}

      <div className="action-row">
        <button className="generate-btn" disabled={!isFormComplete || loading} onClick={handleGenerate}>
          {loading ? "Generating..." : sourceMode === "teams" ? "Generate" : "Send to Pipeline"}
        </button>
        <button
          className="generate-btn secondary-btn"
          type="button"
          disabled={healthLoading}
          onClick={handleHealthCheck}
        >
          {healthLoading ? "Checking..." : "Check Backend"}
        </button>
      </div>

      {healthStatus && (
        <p className={`health-status ${healthStatusKind}`}>{healthStatus}</p>
      )}

        </div>

        <aside className="match-live-widget" aria-label="Live match widget">
          <div className="widget-box weather-widget">
            <h3>Match Weather</h3>
            {widgetMatch ? (
              <>
                <p className="widget-matchline">{widgetMatch.home} vs {widgetMatch.away}</p>
                {!weatherLoading && !weatherError && weatherData && (
                  <p className="widget-weather-summary">
                    {widgetMatch.home} vs {widgetMatch.away}: {weatherLabelFromCode(weatherData.weatherCode)}, {weatherData.temperature ?? "-"}°C
                  </p>
                )}
                {weatherLoading && <p className="widget-meta">Loading weather...</p>}
                {!weatherLoading && weatherError && <p className="widget-meta">{weatherError}</p>}
                {!weatherLoading && !weatherError && weatherData && (
                  <div className="widget-weather-grid">
                    <p><strong>Venue:</strong> {weatherData.location}</p>
                    <p><strong>Condition:</strong> {weatherLabelFromCode(weatherData.weatherCode)}</p>
                    <p><strong>Temp:</strong> {weatherData.temperature ?? "-"}°C</p>
                    <p><strong>Feels Like:</strong> {weatherData.apparent ?? "-"}°C</p>
                    <p><strong>Wind:</strong> {weatherData.wind ?? "-"} km/h</p>
                    <p><strong>Rain:</strong> {weatherData.precipitation ?? "-"} mm</p>
                  </div>
                )}
              </>
            ) : (
              <p className="widget-meta">Select a match to view weather.</p>
            )}
          </div>

          <div className="widget-box commentary-widget">
            <h3>Live Commentary</h3>
            {widgetMatch ? (
              <>
                <p className="widget-scoreline">
                  {widgetMatch.home} {widgetMatch.homeScore ?? "-"} - {widgetMatch.awayScore ?? "-"} {widgetMatch.away}
                </p>
                <p className="widget-meta">Updated: {commentaryUpdatedAt || "Now"}</p>
                {backendFeedError && <p className="widget-meta">{backendFeedError}</p>}
                <div className="widget-commentary-log">
                  {liveCommentary.map((line, index) => (
                    <p key={`${widgetMatch.id || "match"}-${index}`}>{line}</p>
                  ))}
                </div>
              </>
            ) : (
              <p className="widget-meta">Waiting for live match data.</p>
            )}
          </div>
        </aside>
      </div>
      {error && (
        <div
          style={{
            marginTop: "16px",
            color: "#fecaca",
            fontWeight: 700
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <section className="analyst-output">
          {result.title && <h2>{result.title}</h2>}
          {result.context && <p className="output-context">{result.context}</p>}
          <p className="output-context" style={{ marginTop: "8px" }}>
            {result.matchup} - {result.venue}
          </p>
          {result.sourceUrl && (
            <p className="output-context" style={{ marginTop: "8px" }}>
              Source: {result.sourceUrl}
            </p>
          )}

          <div className="commentary-box">
            <h3>{result.commentaryTitle || "Commentary"}</h3>
            <p>{result.commentary}</p>
          </div>

          <div className="reels-grid">
            {result.reels.map((reel) => (
              <article key={reel.side} className="reel-panel">
                <header className="reel-header">
                  <span className="reel-side">{reel.side}</span>
                  <h3>{reel.title}</h3>
                </header>

                <div className="reel-badge-wrap">
                  <TeamFoilBadge logoSrc={reel.logo} teamName={reel.teamName} size={220} speed="12s" />
                </div>

                <div className="reel-feed-status">Live pull: Active</div>

                <ReelVideoWithTimedCaptions reel={reel} />
              </article>
            ))}
          </div>

          {result.pokemonCardUrl && (
            <section className="pokemon-card-section">
              <h3>Recap Wallpaper Card</h3>
              <p className="output-context" style={{ marginTop: "6px", marginBottom: "10px" }}>
                Generated from your request and recap summary.
              </p>
              <div className="pokemon-card-shell">
                {result.reels?.some((reel) => reel.videoUrl) && (
                  <div className="pokemon-card-feature-window" aria-hidden="true">
                    <video
                      className="pokemon-card-feature-video"
                      src={result.reels.find((reel) => reel.videoUrl)?.videoUrl}
                      autoPlay
                      muted
                      loop
                      playsInline
                      preload="metadata"
                    />
                  </div>
                )}
                {isSvgAssetUrl(result.pokemonCardUrl) ? (
                  <object
                    className="pokemon-card-image"
                    data={result.pokemonCardUrl}
                    type="image/svg+xml"
                    aria-label="Animated recap wallpaper card"
                  >
                    <img
                      className="pokemon-card-image"
                      src={result.pokemonCardUrl}
                      alt="Recap wallpaper card"
                      loading="lazy"
                    />
                  </object>
                ) : (
                  <img
                    className="pokemon-card-image"
                    src={result.pokemonCardUrl}
                    alt="Recap wallpaper card"
                    loading="lazy"
                  />
                )}
                <span className="pokemon-card-holo" aria-hidden="true" />
                <span className="pokemon-card-glint" aria-hidden="true" />
              </div>
              <div className="pokemon-card-actions">
                <a
                  href={result.pokemonCardUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="pokemon-card-link"
                >
                  Open wallpaper ({result.pokemonCardFilename || "recap_wallpaper.svg"})
                </a>
                <a
                  href={result.pokemonCardUrl}
                  download={result.pokemonCardFilename || "recap_wallpaper.svg"}
                  className="pokemon-card-link download"
                >
                  Download wallpaper
                </a>
              </div>
            </section>
          )}
        </section>
      )}
    </div>
  );
}

