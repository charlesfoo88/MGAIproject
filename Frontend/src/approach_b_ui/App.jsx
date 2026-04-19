import { useEffect, useRef, useState } from "react";
import "./badge.css";

const MOCK_DELAY_MS = 1000;
const LEAGUE_CODE = "epl";
const LEAGUE_TITLE = "Premier League";
const SEASON_CODE = "2025_2026";
const DEFAULT_MATCH_NAME = `${LEAGUE_CODE}_${SEASON_CODE}`;
const DEFAULT_MATCH_TITLE = "Personalized Highlight Reel";
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
const TEAM_PREVIEW_BADGE_SIZE = 184;
const REEL_BADGE_SIZE = 188;
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

const CARD_COLLECTION_STORAGE_KEY = "mgai_collectible_cards_v1";
const CARD_COLLECTION_LIMIT = 120;
const CARD_PULL_INVENTORY_STORAGE_KEY = "mgai_reel_pull_inventory_v1";
const CARD_STORAGE_BOOTSTRAP_KEY = "mgai_card_storage_bootstrap_v2";
const FACTUAL_INCONSISTENCY_DISAGREEMENT_THRESHOLD = 0.25;
const FACTUAL_INCONSISTENCY_POPUP_MS = 4200;
const HALLUCINATION_POPUP_MS = 12000;

function bootstrapCardStorageOnFirstLoad() {
  if (typeof window === "undefined") return;
  try {
    const alreadyBootstrapped = window.localStorage.getItem(CARD_STORAGE_BOOTSTRAP_KEY) === "1";
    if (alreadyBootstrapped) return;

    // First app open for this storage version: start with an empty collection/inventory.
    window.localStorage.removeItem(CARD_COLLECTION_STORAGE_KEY);
    window.localStorage.removeItem(CARD_PULL_INVENTORY_STORAGE_KEY);
    window.localStorage.setItem(CARD_STORAGE_BOOTSTRAP_KEY, "1");
  } catch {
    // Ignore storage access failures.
  }
}

function readCardCollection() {
  if (typeof window === "undefined") return [];
  bootstrapCardStorageOnFirstLoad();
  try {
    const raw = window.localStorage.getItem(CARD_COLLECTION_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((entry) => entry && typeof entry === "object") : [];
  } catch {
    return [];
  }
}

function writeCardCollection(entries) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      CARD_COLLECTION_STORAGE_KEY,
      JSON.stringify((Array.isArray(entries) ? entries : []).slice(0, CARD_COLLECTION_LIMIT))
    );
  } catch {
    // Ignore storage write failures (private mode, quota exceeded, etc.).
  }
}

function buildCardCollectionId(cardUrl, cardFilename) {
  const filename = String(cardFilename || "").trim();
  if (filename) return filename;
  return String(cardUrl || "").trim();
}

function extractCardNumber(cardFilename) {
  const match = String(cardFilename || "").match(/(\d{6})(?=\.svg$|$)/i);
  if (!match) return null;
  const numeric = Number(match[1]);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatCardNumber(cardNumber) {
  if (cardNumber === null || cardNumber === undefined || cardNumber === "") return "??????";
  if (!Number.isFinite(Number(cardNumber))) return "??????";
  return String(Number(cardNumber)).padStart(6, "0");
}

function deriveCardRarity(cardNumber) {
  if (!Number.isFinite(Number(cardNumber))) {
    return { key: "prototype", label: "Prototype" };
  }
  const value = Number(cardNumber);
  if (value % 50 === 0) return { key: "mythic", label: "Mythic" };
  if (value % 20 === 0) return { key: "legendary", label: "Legendary" };
  if (value % 10 === 0) return { key: "epic", label: "Epic" };
  if (value % 5 === 0) return { key: "rare", label: "Rare" };
  return { key: "uncommon", label: "Uncommon" };
}

function buildCardSetCode(matchupLabel) {
  const chunks = String(matchupLabel || "MGAI")
    .toUpperCase()
    .replace(/[^A-Z0-9 ]/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3);
  const initialism = chunks.map((chunk) => chunk[0]).join("");
  return initialism || "MGA";
}

function readCardPullInventory() {
  if (typeof window === "undefined") return {};
  bootstrapCardStorageOnFirstLoad();
  try {
    const raw = window.localStorage.getItem(CARD_PULL_INVENTORY_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

function writeCardPullInventory(inventory) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      CARD_PULL_INVENTORY_STORAGE_KEY,
      JSON.stringify(inventory && typeof inventory === "object" ? inventory : {})
    );
  } catch {
    // Ignore storage write failures.
  }
}

function normalizeHighlightScore(rawScore, fallback = 0.5) {
  const numeric = Number(rawScore);
  if (!Number.isFinite(numeric)) return fallback;

  const clipped = Math.max(0, numeric);
  if (clipped <= 1) return clipped;
  if (clipped <= 10) return Math.min(1, clipped / 10);
  if (clipped <= 100) return Math.min(1, clipped / 100);
  return 1;
}

function parseRateValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  if (numeric <= 1) return Math.max(0, numeric);
  if (numeric <= 100) return Math.min(1, Math.max(0, numeric / 100));
  return 1;
}

function normalizeSegmentId(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) return "";
  const match = raw.match(/segment[\s_-]*(\d+)/i);
  if (!match) return "";
  const digits = String(match[1] || "").trim();
  if (!digits) return "";
  const width = Math.max(3, digits.length);
  const numeric = Number(digits);
  if (!Number.isFinite(numeric)) return `segment_${digits.padStart(width, "0")}`;
  return `segment_${String(Math.max(0, Math.trunc(numeric))).padStart(width, "0")}`;
}

function assignRarityFromHighlightScore(score) {
  const normalized = normalizeHighlightScore(score, 0.5);
  if (normalized >= 0.9) return "ultra";
  if (normalized >= 0.75) return "rare";
  if (normalized >= 0.5) return "uncommon";
  return "common";
}

function rarityWeight(rarity) {
  // Pull probability profile by rarity (applied at spin time).
  if (rarity === "ultra") return 2;
  if (rarity === "rare") return 10;
  if (rarity === "uncommon") return 28;
  return 60;
}

function rarityLabel(rarity) {
  if (rarity === "ultra") return "Ultra Rare";
  if (rarity === "rare") return "Rare";
  if (rarity === "uncommon") return "Uncommon";
  return "Common";
}

function weightedPullCard(cards) {
  const normalized = (Array.isArray(cards) ? cards : []).filter(Boolean);
  if (normalized.length === 0) return null;

  const totalWeight = normalized.reduce((sum, card) => {
    const weight = Math.max(0, Number(card?.pullWeight) || rarityWeight(card?.rarity));
    return sum + weight;
  }, 0);
  if (totalWeight <= 0) {
    return normalized[Math.floor(Math.random() * normalized.length)] || null;
  }

  let cursor = Math.random() * totalWeight;
  for (const card of normalized) {
    cursor -= Math.max(0, Number(card?.pullWeight) || rarityWeight(card?.rarity));
    if (cursor <= 0) return card;
  }
  return normalized[normalized.length - 1] || null;
}

function summarizeSetRarity(cards) {
  return (Array.isArray(cards) ? cards : []).reduce((acc, card) => {
    const key = String(card?.rarity || "common");
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function normalizeMomentTextForDisplay(text) {
  const raw = String(text || "").trim();
  if (!raw) return raw;
  return raw
    .replace(/\bT\.\s*Partey\b/gi, "Thomas Partey")
    .replace(/\bM\.\s*Odegaard\b/gi, "Martin Odegaard");
}

function normalizeHighlightDetail(highlight, index = 0) {
  const isObject = highlight && typeof highlight === "object" && !Array.isArray(highlight);
  const rawCaption = isObject
    ? (
      highlight.caption
      || highlight.text
      || highlight.moment
      || highlight.commentary
      || highlight.description
      || highlight.narrative
      || highlight.label
      || highlight.title
      || ""
    )
    : String(highlight || "");
  const fallbackCaption = `Highlight ${index + 1}`;
  const caption = normalizeMomentTextForDisplay(rawCaption || fallbackCaption) || fallbackCaption;

  const rawScore = isObject
    ? (
      highlight.score
      ?? highlight.confidence
      ?? highlight.relevance
      ?? highlight.importance
    )
    : undefined;
  const rawAlignment = isObject ? highlight.alignment_score : undefined;
  const rawDisagreementRate = isObject
    ? (highlight.disagreement_rate ?? highlight.disagreementRate)
    : undefined;
  const rawHighDisagreement = isObject
    ? (highlight.high_disagreement ?? highlight.highDisagreement)
    : undefined;
  const alignmentScore = parseConfidenceValue(rawAlignment);
  const disagreementRate = parseRateValue(rawDisagreementRate);
  const highDisagreement = rawHighDisagreement === true || String(rawHighDisagreement || "").toLowerCase() === "true";
  const confidence = normalizeHighlightScore(rawScore, 0.5);

  return {
    caption,
    segment_id: isObject
      ? normalizeSegmentId(highlight.segment_id ?? highlight.segmentId)
      : "",
    consistency_score: parseConfidenceValue(isObject ? highlight.consistency_score : undefined),
    event_type: isObject ? String(highlight.event_type || "").trim() : "",
    alignment_score: Number.isFinite(alignmentScore) ? alignmentScore : null,
    disagreement_rate: Number.isFinite(disagreementRate) ? disagreementRate : null,
    high_disagreement: highDisagreement,
    confidence,
    score: confidence
  };
}

function buildHighlightDetails(highlights) {
  return (Array.isArray(highlights) ? highlights : [])
    .map((item, index) => normalizeHighlightDetail(item, index))
    .filter((item) => String(item?.caption || "").trim().length > 0);
}

function parseConfidenceValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return normalizeHighlightScore(numeric, 0.5);
}

function averageConfidenceFromDetails(details, limit = 0) {
  const values = (Array.isArray(details) ? details : [])
    .map((item) => parseConfidenceValue(item?.confidence ?? item?.score))
    .filter((item) => Number.isFinite(item));

  const scoped = (Number(limit) > 0 ? values.slice(0, Number(limit)) : values).filter((item) => Number.isFinite(item));
  if (scoped.length === 0) return null;
  return scoped.reduce((sum, value) => sum + value, 0) / scoped.length;
}

function formatConfidenceLabel(value) {
  const normalized = parseConfidenceValue(value);
  if (!Number.isFinite(normalized)) return "N/A";
  return `${(normalized * 100).toFixed(2)}%`;
}

function deriveLiveAlignmentScore(cueAlignment, reelAlignment, fallbackScore) {
  const cue = parseConfidenceValue(cueAlignment);
  const reel = parseConfidenceValue(reelAlignment);
  const fallback = parseConfidenceValue(fallbackScore);

  // Prefer cue-level alignment when available and non-zero.
  // Some legacy artifacts emit zero as a missing placeholder.
  if (Number.isFinite(cue) && cue > 0) return cue;
  if (Number.isFinite(reel)) return reel;
  return Number.isFinite(fallback) ? fallback : null;
}

function mergeCaptionsWithEvidence(captions, evidenceRows) {
  const captionList = Array.isArray(captions) ? captions : [];
  const evidenceList = Array.isArray(evidenceRows) ? evidenceRows : [];

  return captionList.map((caption, index) => {
    const evidence = evidenceList[index] && typeof evidenceList[index] === "object"
      ? evidenceList[index]
      : null;
    const score = evidence
      ? (evidence.importance_score ?? evidence.score ?? evidence.confidence)
      : undefined;

    if (caption && typeof caption === "object" && !Array.isArray(caption)) {
      return {
        ...caption,
        segment_id: normalizeSegmentId(caption.segment_id ?? caption.segmentId ?? evidence?.segment_id),
        score: caption.score ?? caption.confidence ?? score,
        confidence: caption.confidence ?? caption.score ?? score,
      };
    }

    return {
      caption: String(caption || "").trim(),
      score,
      confidence: score,
      segment_id: normalizeSegmentId(evidence?.segment_id),
    };
  });
}

function parseCaptionDetailRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const caption = String(
        row.caption
        || row.text
        || row.moment
        || row.commentary
        || ""
      ).trim();
      if (!caption) return null;
      const score = row?.evidence?.d15_fields?.importance_score
        ?? row?.importance_score
        ?? row?.score
        ?? row?.evidence?.d15_fields?.confidence
        ?? row?.confidence;
      const disagreementRate = row?.disagreement_rate ?? row?.disagreementRate;
      const highDisagreement = row?.high_disagreement ?? row?.highDisagreement;
      return {
        caption,
        score,
        confidence: score,
        segment_id: normalizeSegmentId(row?.segment_id),
        disagreement_rate: disagreementRate,
        high_disagreement: highDisagreement,
      };
    })
    .filter(Boolean);
}

function stripDiacritics(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function normalizeEvidenceKey(value) {
  return slugifyText(stripDiacritics(String(value || "").replace(/\./g, " ")));
}

function extractEvidenceKeyFromFilename(filename) {
  const name = String(filename || "").trim().toLowerCase();
  if (!name.startsWith("evidence_log_") || !name.endsWith(".json")) return "";
  return name.slice("evidence_log_".length, -".json".length).trim();
}

function buildPreferredEvidenceKeyCandidates(preferenceType, preferenceDetail) {
  const type = String(preferenceType || "").trim().toLowerCase();
  const detailRaw = String(preferenceDetail || "").trim();
  const keys = [];
  const add = (value) => {
    const key = normalizeEvidenceKey(value);
    if (key) keys.push(key);
  };

  if (type === "team") {
    const resolvedTeam = resolveTeamName(detailRaw) || detailRaw;
    perspectiveKeysForTeam(resolvedTeam).forEach((key) => add(key));
    add(resolvedTeam);
  } else if (type === "individual") {
    const compactDetail = stripDiacritics(detailRaw)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");
    const odegaardAliases = [
      "odegaard",
      "odegard",
      "oedegaard",
      "oddegaard",
      "oddergard",
      "sorddergard",
      "modegaard",
      "martinodegaard"
    ];
    if (compactDetail && odegaardAliases.some((alias) => compactDetail.includes(alias) || alias.includes(compactDetail))) {
      // Force preferred lookup to hit evidence_log_odegaard.json first.
      add("odegaard");
    }

    add(detailRaw);
    const asciiTokens = stripDiacritics(detailRaw)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(Boolean);
    if (asciiTokens.length > 0) {
      add(asciiTokens.join("_"));
      add(asciiTokens[asciiTokens.length - 1]);
      const withoutInitials = asciiTokens.filter((token) => token.length > 1);
      if (withoutInitials.length > 0) {
        add(withoutInitials.join("_"));
        add(withoutInitials[withoutInitials.length - 1]);
      }
    }
  } else if (detailRaw) {
    add(detailRaw);
  }

  return Array.from(new Set(keys.filter(Boolean)));
}

function buildPreferredEvidenceFilenames(preferenceType, preferenceDetail, options = {}) {
  const files = [];
  const addFile = (filename) => {
    const name = String(filename || "").trim();
    if (!name) return;
    if (!files.includes(name)) files.push(name);
  };
  const addEvidenceFileForKey = (key) => {
    const normalized = normalizeEvidenceKey(key);
    if (!normalized) return;
    addFile(`evidence_log_${normalized}.json`);
  };

  const type = String(preferenceType || "").trim().toLowerCase();
  const preferredTeam = String(options?.preferredTeam || "").trim();

  // Priority order:
  // 1) Player evidence log (for individual preferences)
  // 2) Team evidence log (for team preferences, or fallback for individual)
  // 3) Generic evidence_log.json fallback
  if (type === "individual") {
    const playerKeys = buildPreferredEvidenceKeyCandidates(preferenceType, preferenceDetail);
    playerKeys.forEach((key) => addEvidenceFileForKey(key));

    if (preferredTeam) {
      perspectiveKeysForTeam(preferredTeam).forEach((key) => addEvidenceFileForKey(key));
      addEvidenceFileForKey(preferredTeam);
    }
  } else if (type === "team") {
    const resolvedTeam = resolveTeamName(preferenceDetail) || String(preferenceDetail || "").trim();
    perspectiveKeysForTeam(resolvedTeam).forEach((key) => addEvidenceFileForKey(key));
    addEvidenceFileForKey(resolvedTeam);

    const teamKeys = buildPreferredEvidenceKeyCandidates(preferenceType, preferenceDetail);
    teamKeys.forEach((key) => addEvidenceFileForKey(key));
  } else {
    const keys = buildPreferredEvidenceKeyCandidates(preferenceType, preferenceDetail);
    keys.forEach((key) => addEvidenceFileForKey(key));
  }

  addFile("evidence_log.json");
  return files;
}

async function fetchOutputJsonFile(matchName, filename) {
  const response = await fetch(
    `${API_BASE_URL}/api/output-files/${encodeURIComponent(matchName)}/${encodeURIComponent(filename)}`
  );
  if (!response.ok) return null;
  return response.json().catch(() => null);
}

async function fetchFirstExistingOutputJson(matchName, filenames = []) {
  for (const filename of Array.from(new Set((Array.isArray(filenames) ? filenames : []).filter(Boolean)))) {
    try {
      const payload = await fetchOutputJsonFile(matchName, filename);
      if (payload && typeof payload === "object") {
        return { payload, filename };
      }
    } catch {
      // Try next file candidate.
    }
  }
  return { payload: null, filename: "" };
}

function parseEvidenceClipRows(payload, options = {}) {
  const clipEvidence = Array.isArray(payload?.clip_evidence) ? payload.clip_evidence : [];
  const captionField = String(options?.captionField || "caption_reel_a");
  const fallbackCaptionField = String(options?.fallbackCaptionField || "caption_reel_b");
  const alignmentField = String(options?.alignmentField || "alignment_score_reel_a");

  return clipEvidence
    .map((entry, index) => {
      if (!entry || typeof entry !== "object") return null;
      const caption = normalizeMomentTextForDisplay(
        String(
          entry?.[captionField]
          ?? entry?.[fallbackCaptionField]
          ?? entry?.caption
          ?? entry?.text
          ?? entry?.d17_fields?.narrative
          ?? ""
        ).trim()
      );
      if (!caption) return null;
      const alignment = parseConfidenceValue(
        entry?.[alignmentField]
        ?? entry?.alignment_score_reel_a
        ?? entry?.alignment_score_reel_b
        ?? entry?.alignment_score
        ?? entry?.score
      );
      const score = entry?.d15_fields?.importance_score
        ?? entry?.d15_fields?.confidence
        ?? alignment
        ?? entry?.score
        ?? entry?.confidence;
      const segmentId = normalizeSegmentId(entry?.segment_id || `segment_${String(index + 1).padStart(3, "0")}`);
      return {
        caption,
        score,
        confidence: score,
        segment_id: segmentId,
        event_type: String(entry?.event_type || "").trim(),
        alignment_score: Number.isFinite(alignment) ? alignment : null
      };
    })
    .filter(Boolean);
}

function extractEvidenceSummaryAlignment(payload, preferredKeys = []) {
  const summary = payload?.summary && typeof payload.summary === "object"
    ? payload.summary
    : {};
  const keys = Array.isArray(preferredKeys) && preferredKeys.length > 0
    ? preferredKeys
    : ["reel_a_alignment_score", "reel_b_alignment_score"];

  for (const key of keys) {
    const value = parseConfidenceValue(summary?.[key] ?? payload?.[key]);
    if (Number.isFinite(value)) return value;
  }
  return null;
}

function extractHallucinationState(payload) {
  if (!payload || typeof payload !== "object") {
    return {
      flagged: false,
      unsupportedMentions: [],
      retryCount: null,
    };
  }

  const summary = payload?.summary && typeof payload.summary === "object"
    ? payload.summary
    : {};

  const rawFlag = summary?.hallucination_flagged ?? payload?.hallucination_flagged;
  const flagged = rawFlag === true || String(rawFlag || "").toLowerCase() === "true";

  const unsupportedMentionsRaw = Array.isArray(summary?.unsupported_mentions)
    ? summary.unsupported_mentions
    : (Array.isArray(payload?.unsupported_mentions) ? payload.unsupported_mentions : []);
  const unsupportedMentions = unsupportedMentionsRaw
    .map((value) => String(value || "").trim())
    .filter(Boolean);

  const retryRaw = summary?.total_retries ?? payload?.retry_count ?? payload?.total_retries;
  const retryCount = Number.isFinite(Number(retryRaw)) ? Number(retryRaw) : null;

  return {
    flagged,
    unsupportedMentions,
    retryCount,
  };
}

function extractHallucinationTotalsFromFullEvaluation(payload) {
  if (!payload || typeof payload !== "object") return null;
  const verifier = payload?.verifier_analysis && typeof payload.verifier_analysis === "object"
    ? payload.verifier_analysis
    : {};
  const total = Number(verifier?.total_hallucinations_detected ?? payload?.total_hallucinations_detected);
  return Number.isFinite(total) ? total : null;
}

function mapHallucinationMentionStream(reelLabel, fallbackStream = "Verifier") {
  const reel = String(reelLabel || "").trim().toUpperCase();
  if (reel === "A") return "Selected";
  if (reel === "B") return "Neutral";
  return String(fallbackStream || "").trim() || "Verifier";
}

function parseHallucinationUnsupportedMention(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;

  const reelMatch = raw.match(/^Reel\s*([AB])\s*\[\s*(segment[\s_-]*\d+)\s*\]\s*:\s*(.*)$/i);
  if (reelMatch) {
    return {
      reel: String(reelMatch[1] || "").trim().toUpperCase(),
      segment_id: normalizeSegmentId(reelMatch[2]),
      caption: String(reelMatch[3] || "").trim() || raw,
      raw,
    };
  }

  const segmentMatch = raw.match(/\[\s*(segment[\s_-]*\d+)\s*\]/i) || raw.match(/\b(segment[\s_-]*\d+)\b/i);
  const colonIndex = raw.indexOf(":");
  const caption = colonIndex >= 0
    ? String(raw.slice(colonIndex + 1) || "").trim() || raw
    : raw;

  return {
    reel: "",
    segment_id: normalizeSegmentId(segmentMatch?.[1]),
    caption,
    raw,
  };
}

function buildHallucinationCueSignals(candidates = [], options = {}) {
  const normalized = (Array.isArray(candidates) ? candidates : [])
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      stream: String(item?.stream || "").trim() || "Verifier",
      flagged: item?.flagged === true,
      unsupportedMentions: Array.isArray(item?.unsupportedMentions)
        ? item.unsupportedMentions.map((v) => String(v || "").trim()).filter(Boolean)
        : [],
      retryCount: Number.isFinite(Number(item?.retryCount)) ? Number(item.retryCount) : null,
    }))
    .filter((item) => item.flagged);

  const totalFromEval = Number(options?.totalHallucinationsDetected);
  const hasTotalFromEval = Number.isFinite(totalFromEval) && totalFromEval > 0;
  const rawSignals = [];

  normalized.forEach((item) => {
    if (item.unsupportedMentions.length === 0) {
      rawSignals.push({
        stream: item.stream,
        segment_id: "",
        cueIndex: null,
        retryCount: item.retryCount,
        totalHallucinationsDetected: hasTotalFromEval ? totalFromEval : null,
        caption: "Verifier detected unsupported content and recaptioned.",
      });
      return;
    }

    item.unsupportedMentions.forEach((mention) => {
      const parsed = parseHallucinationUnsupportedMention(mention);
      if (!parsed) return;
      rawSignals.push({
        stream: mapHallucinationMentionStream(parsed.reel, item.stream),
        segment_id: normalizeSegmentId(parsed.segment_id),
        cueIndex: null,
        retryCount: item.retryCount,
        totalHallucinationsDetected: hasTotalFromEval ? totalFromEval : item.unsupportedMentions.length,
        caption: parsed.caption || "Verifier detected unsupported content and recaptioned.",
      });
    });
  });

  if (rawSignals.length === 0 && hasTotalFromEval) {
    rawSignals.push({
      stream: "Verifier",
      segment_id: "",
      cueIndex: null,
      retryCount: null,
      totalHallucinationsDetected: totalFromEval,
      caption: "Verifier detected hallucinations in evaluation runs.",
    });
  }

  const deduped = [];
  const seen = new Set();
  rawSignals.forEach((item) => {
    const key = [
      String(item.stream || "").toLowerCase(),
      String(item.segment_id || "").toLowerCase(),
      String(item.caption || "").toLowerCase(),
    ].join("|");
    if (seen.has(key)) return;
    seen.add(key);
    deduped.push(item);
  });

  deduped.sort((a, b) => {
    const aSegment = a.segment_id ? 1 : 0;
    const bSegment = b.segment_id ? 1 : 0;
    if (aSegment !== bSegment) return bSegment - aSegment;
    const aTotal = Number.isFinite(a.totalHallucinationsDetected) ? a.totalHallucinationsDetected : -1;
    const bTotal = Number.isFinite(b.totalHallucinationsDetected) ? b.totalHallucinationsDetected : -1;
    if (aTotal !== bTotal) return bTotal - aTotal;
    const aRetry = Number.isFinite(a.retryCount) ? a.retryCount : -1;
    const bRetry = Number.isFinite(b.retryCount) ? b.retryCount : -1;
    return bRetry - aRetry;
  });

  return deduped;
}

function buildHallucinationAlertFromSignal(signal, options = {}) {
  if (!signal || typeof signal !== "object") return null;
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    stream: String(options?.stream || signal.stream || "").trim() || "Verifier",
    cueIndex: Number.isFinite(options?.cueIndex) ? Number(options.cueIndex) : null,
    segment_id: normalizeSegmentId(options?.segment_id ?? signal.segment_id),
    retryCount: Number.isFinite(signal.retryCount) ? signal.retryCount : null,
    caption: String(signal.caption || "").trim() || "Verifier detected unsupported content and recaptioned.",
    totalHallucinationsDetected: Number.isFinite(signal.totalHallucinationsDetected)
      ? signal.totalHallucinationsDetected
      : null,
  };
}

function buildPerClipAlignmentBySegment(payload) {
  const entries = Array.isArray(payload?.disagreement_analysis?.per_clip_disagreement)
    ? payload.disagreement_analysis.per_clip_disagreement
    : [];
  const lookup = {};
  entries.forEach((entry) => {
    const key = String(entry?.segment_id || "").trim();
    const consistencyScore = parseConfidenceValue(entry?.mean_pairwise_similarity);
    const disagreementRate = parseRateValue(entry?.disagreement_rate);
    const highDisagreement = entry?.high_disagreement === true || String(entry?.high_disagreement || "").toLowerCase() === "true";
    if (!key) return;
    lookup[key] = {
      consistency_score: Number.isFinite(consistencyScore) ? consistencyScore : null,
      disagreement_rate: Number.isFinite(disagreementRate) ? disagreementRate : null,
      high_disagreement: highDisagreement,
      event_type: String(entry?.event_type || "").trim(),
    };
  });
  return lookup;
}

function applyPerClipAlignmentToCaptionRows(rows, alignmentBySegment = {}) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  return rows.map((row) => {
    const key = String(row?.segment_id || "").trim();
    const mapped = alignmentBySegment?.[key];
    const mappedConsistency = parseConfidenceValue(mapped?.consistency_score);
    const mappedDisagreement = parseRateValue(mapped?.disagreement_rate);
    const mappedHighDisagreement = mapped?.high_disagreement === true || String(mapped?.high_disagreement || "").toLowerCase() === "true";
    if (
      !Number.isFinite(mappedConsistency)
      && !Number.isFinite(mappedDisagreement)
      && !mappedHighDisagreement
    ) {
      return row;
    }
    return {
      ...row,
      consistency_score: Number.isFinite(mappedConsistency) ? mappedConsistency : (row?.consistency_score ?? null),
      disagreement_rate: Number.isFinite(mappedDisagreement) ? mappedDisagreement : (row?.disagreement_rate ?? null),
      high_disagreement: mappedHighDisagreement || row?.high_disagreement === true,
      event_type: row?.event_type || String(mapped?.event_type || "").trim(),
    };
  });
}

function mergePerClipDisagreementIntoCaptionRows(rows, alignmentBySegment = {}) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  return rows.map((row) => {
    const key = String(row?.segment_id || "").trim();
    const mapped = alignmentBySegment?.[key];
    if (!mapped || typeof mapped !== "object") return row;
    const mappedConsistency = parseConfidenceValue(mapped?.consistency_score);
    const mappedDisagreement = parseRateValue(mapped?.disagreement_rate);
    const mappedHighDisagreement = mapped?.high_disagreement === true || String(mapped?.high_disagreement || "").toLowerCase() === "true";
    return {
      ...row,
      consistency_score: Number.isFinite(mappedConsistency) ? mappedConsistency : (row?.consistency_score ?? null),
      disagreement_rate: Number.isFinite(mappedDisagreement) ? mappedDisagreement : (row?.disagreement_rate ?? null),
      high_disagreement: mappedHighDisagreement || row?.high_disagreement === true,
      event_type: row?.event_type || String(mapped?.event_type || "").trim(),
    };
  });
}

function isFactualInconsistencyDetail(detail) {
  if (!detail || typeof detail !== "object") return false;
  const disagreementRate = parseRateValue(
    detail?.disagreement_rate
    ?? detail?.disagreementRate
  );
  return Number.isFinite(disagreementRate) && disagreementRate >= FACTUAL_INCONSISTENCY_DISAGREEMENT_THRESHOLD;
}

function extractAlignmentScoresFromFullEvaluation(payload, context = {}) {
  if (!payload || typeof payload !== "object") {
    return { selected: null, neutral: null };
  }

  const verifier = payload?.verifier_analysis && typeof payload.verifier_analysis === "object"
    ? payload.verifier_analysis
    : {};
  const avgSelected = parseConfidenceValue(
    verifier?.avg_reel_a_alignment
    ?? payload?.reel_a_alignment_score
    ?? payload?.selected_alignment_score
  );
  const avgNeutral = parseConfidenceValue(
    verifier?.avg_reel_b_alignment
    ?? payload?.reel_b_alignment_score
    ?? payload?.neutral_alignment_score
  );

  const runs = Array.isArray(verifier?.per_run_results) ? verifier.per_run_results : [];
  if (!runs.length) {
    return { selected: avgSelected, neutral: avgNeutral };
  }

  const preferenceDetail = String(context?.preferenceDetail || "").trim().toLowerCase();
  const preferenceType = String(context?.preferenceType || "").trim().toLowerCase();
  const wantsNeutral = String(context?.tone || "").trim().toLowerCase() === "neutral";

  const scored = runs
    .map((row) => {
      const preference = String(row?.preference || "").toLowerCase();
      let score = 0;
      if (row?.status === "success") score += 1;
      if (preferenceDetail && preference.includes(preferenceDetail)) score += 4;
      if (preferenceType === "team" && preference.includes("support")) score += 1;
      if (preferenceType === "individual" && preference.includes("favourite player")) score += 1;
      if (wantsNeutral && preference.includes("neutral viewer")) score += 2;
      return { row, score };
    })
    .sort((a, b) => b.score - a.score);

  const best = scored[0];
  if (!best || best.score <= 0) {
    return { selected: avgSelected, neutral: avgNeutral };
  }

  return {
    selected: parseConfidenceValue(best.row?.reel_a_alignment_score) ?? avgSelected,
    neutral: parseConfidenceValue(best.row?.reel_b_alignment_score) ?? avgNeutral,
  };
}

function normalizeHighlightItem(highlight, index, setId, setName, setIndex) {
  const detail = normalizeHighlightDetail(highlight, index);
  const caption = detail.caption;
  const highlightScore = detail.confidence;
  const rarity = assignRarityFromHighlightScore(highlightScore);

  return {
    id: `${setId}_card_${String(index + 1).padStart(2, "0")}`,
    setId,
    setName,
    setIndex,
    cardIndex: index + 1,
    moment: caption,
    caption,
    highlightScore,
    rarity,
    rarityLabel: rarityLabel(rarity),
    pullWeight: rarityWeight(rarity)
  };
}

function buildReelSetCatalog(result, matchInfo) {
  if (!result || !Array.isArray(result.reels)) {
    return { seasonCode: SEASON_CODE, sets: [] };
  }

  const sets = result.reels
    .map((reel, setIndex) => {
      const highlightsSource = Array.isArray(reel?.highlightsDetailed)
        ? reel.highlightsDetailed
        : Array.isArray(reel?.highlights)
        ? reel.highlights
        : (Array.isArray(reel?.captions) ? reel.captions : []);
      const normalizedHighlights = highlightsSource
        .filter((item) => item !== null && item !== undefined)
        .filter((item) => {
          if (typeof item === "string") return String(item).trim().length > 0;
          if (typeof item === "object") return true;
          return String(item).trim().length > 0;
        });
      if (normalizedHighlights.length === 0) return null;

      const rawSetName = String(reel?.title || reel?.side || `Reel Set ${setIndex + 1}`);
      const setId = `${slugifyText(result?.matchup || matchInfo?.matchTitle || "match")}_${slugifyText(rawSetName)}_${setIndex + 1}`;
      const cards = normalizedHighlights
        .map((highlight, momentIndex) => normalizeHighlightItem(highlight, momentIndex, setId, rawSetName, setIndex + 1))
        .filter(Boolean);

      return {
        id: setId,
        name: rawSetName,
        cardCount: cards.length,
        cards,
        rarityBreakdown: summarizeSetRarity(cards)
      };
    })
    .filter(Boolean);

  return { seasonCode: SEASON_CODE, sets };
}

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

const PLAYER_ALIAS_OVERRIDES = {
  odegaard: { canonical: "Martin Odegaard", team: "Arsenal" },
  odegard: { canonical: "Martin Odegaard", team: "Arsenal" },
  oedegaard: { canonical: "Martin Odegaard", team: "Arsenal" },
  oddegaard: { canonical: "Martin Odegaard", team: "Arsenal" },
  oddergard: { canonical: "Martin Odegaard", team: "Arsenal" },
  sorddergard: { canonical: "Martin Odegaard", team: "Arsenal" },
  modegaard: { canonical: "Martin Odegaard", team: "Arsenal" }
};

function normalizePlayerKey(value) {
  return stripDiacritics(String(value || ""))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactPlayerKey(value) {
  return normalizePlayerKey(value).replace(/\s+/g, "");
}

function resolvePreferredPlayerSelection(preferenceDetail, players = []) {
  const raw = String(preferenceDetail || "").trim();
  if (!raw) return { name: "", team: "" };

  const normalized = normalizePlayerKey(raw);
  const compact = compactPlayerKey(raw);
  const pool = Array.isArray(players) ? players.filter(Boolean) : [];

  const toResult = (name, team) => ({
    name: String(name || raw).trim() || raw,
    team: resolveTeamName(team) || String(team || "").trim()
  });

  const exact = pool.find((player) => normalizePlayerKey(player?.name) === normalized);
  if (exact) return toResult(exact.name, exact.team);

  const compactExact = pool.find((player) => compactPlayerKey(player?.name) === compact);
  if (compactExact) return toResult(compactExact.name, compactExact.team);

  if (compact.length >= 6) {
    const containsMatch = pool.find((player) => {
      const playerCompact = compactPlayerKey(player?.name);
      return playerCompact && (playerCompact.includes(compact) || compact.includes(playerCompact));
    });
    if (containsMatch) return toResult(containsMatch.name, containsMatch.team);
  }

  const override = PLAYER_ALIAS_OVERRIDES[compact]
    || Object.entries(PLAYER_ALIAS_OVERRIDES).find(([alias]) => compact.includes(alias) || alias.includes(compact))?.[1]
    || null;

  if (override) {
    const canonicalCompact = compactPlayerKey(override.canonical);
    const canonicalFromPool = pool.find((player) => compactPlayerKey(player?.name) === canonicalCompact)
      || pool.find((player) => {
        const playerCompact = compactPlayerKey(player?.name);
        return playerCompact && (playerCompact.includes(canonicalCompact) || canonicalCompact.includes(playerCompact));
      });
    if (canonicalFromPool) return toResult(canonicalFromPool.name, canonicalFromPool.team);
    return toResult(override.canonical, override.team);
  }

  return { name: raw, team: "" };
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
const TEAM_NAME_TO_ALIAS_KEYS = EPL_TEAM_DATABASE.reduce((lookup, team) => {
  const aliases = new Set([
    normalizeTeamKey(team.name),
    ...(Array.isArray(team.aliases) ? team.aliases.map((alias) => normalizeTeamKey(alias)) : [])
  ]);
  lookup[team.name] = Array.from(aliases).filter(Boolean).sort((a, b) => b.length - a.length);
  return lookup;
}, {});

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

function collectTeamMentionStats(text) {
  const normalized = normalizeTeamKey(text);
  if (!normalized) return [];

  const stats = {};

  TEAM_ALIAS_KEYS_DESC.forEach((aliasKey) => {
    const teamName = TEAM_ALIAS_TO_NAME[aliasKey];
    if (!teamName) return;

    const matcher = new RegExp(`(^|\\s)${escapeRegExp(aliasKey)}(?=\\s|$)`, "g");
    let match = matcher.exec(normalized);
    while (match) {
      const offset = String(match[1] || "").length;
      const mentionIndex = match.index + offset;
      if (!stats[teamName]) {
        stats[teamName] = { teamName, count: 0, firstIndex: mentionIndex };
      }
      stats[teamName].count += 1;
      stats[teamName].firstIndex = Math.min(stats[teamName].firstIndex, mentionIndex);
      match = matcher.exec(normalized);
    }
  });

  return Object.values(stats).sort((a, b) =>
    b.count - a.count
    || a.firstIndex - b.firstIndex
    || a.teamName.localeCompare(b.teamName)
  );
}

function scoreTeamPreferenceFromPrompt(normalizedPrompt, teamName) {
  const aliases = TEAM_NAME_TO_ALIAS_KEYS[teamName]
    || [normalizeTeamKey(teamName)].filter(Boolean);
  if (!normalizedPrompt || aliases.length === 0) return 0;

  const addWeightedMatches = (pattern, weight) => {
    const matches = normalizedPrompt.match(pattern);
    return (Array.isArray(matches) ? matches.length : 0) * weight;
  };

  return aliases.reduce((score, aliasKey) => {
    const aliasPattern = escapeRegExp(aliasKey);
    let nextScore = score;
    nextScore += addWeightedMatches(new RegExp(`\\b(?:support|back|root(?:ing)?\\s+for|cheer(?:ing)?\\s+for|fan\\s+of|prefer|favo(?:u)?r|focus\\s+on)\\s+${aliasPattern}\\b`, "g"), 4);
    nextScore += addWeightedMatches(new RegExp(`\\bfrom\\s+${aliasPattern}\\s+perspective\\b`, "g"), 4);
    nextScore += addWeightedMatches(new RegExp(`\\b${aliasPattern}\\s+(?:fan|perspective|to\\s+win|winning|all\\s+the\\s+way)\\b`, "g"), 3);
    nextScore += addWeightedMatches(new RegExp(`\\bfor\\s+${aliasPattern}\\b`, "g"), 1);
    return nextScore;
  }, 0);
}

function inferPromptMatchAndPreference(promptText) {
  const rawPrompt = String(promptText || "").trim();
  if (!rawPrompt) {
    return { teams: [], preferredTeam: "" };
  }

  const normalizedPrompt = normalizeTeamKey(rawPrompt);
  const mentionStats = collectTeamMentionStats(rawPrompt);
  const teams = mentionStats.slice(0, 2).map((item) => item.teamName);

  let preferredTeam = "";
  let highestPreferenceScore = 0;
  let bestPreferenceIndex = Number.POSITIVE_INFINITY;

  mentionStats.forEach((item) => {
    const score = scoreTeamPreferenceFromPrompt(normalizedPrompt, item.teamName);
    if (score > highestPreferenceScore) {
      highestPreferenceScore = score;
      preferredTeam = item.teamName;
      bestPreferenceIndex = item.firstIndex;
      return;
    }
    if (score > 0 && score === highestPreferenceScore && item.firstIndex < bestPreferenceIndex) {
      preferredTeam = item.teamName;
      bestPreferenceIndex = item.firstIndex;
    }
  });

  if (!preferredTeam && teams.length === 1) {
    const hasPreferenceIntent = /\b(?:support|back|root|rooting|fan|prefer|favour|favor|focus|perspective)\b/.test(normalizedPrompt);
    if (hasPreferenceIntent) {
      preferredTeam = teams[0];
    }
  }

  return { teams, preferredTeam };
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

function buildFallbackScoreMatches(limit = EPL_STRIP_MAX_ITEMS) {
  const teams = (Array.isArray(EPL_TEAMS) ? EPL_TEAMS : []).filter(Boolean);
  if (teams.length < 2) return [];

  const count = Math.max(1, Math.min(Number(limit) || EPL_STRIP_MAX_ITEMS, EPL_STRIP_MAX_ITEMS));
  const now = new Date();

  return Array.from({ length: count }, (_, index) => {
    const home = teams[(index * 2) % teams.length];
    const away = teams[(index * 2 + 1) % teams.length] || teams[(index * 2 + 2) % teams.length] || "Away";
    const day = new Date(now);
    day.setDate(now.getDate() - (index + 1));
    const isoDate = day.toISOString().slice(0, 10);
    return {
      id: `fallback-score-${index}`,
      home,
      away: away === home ? (teams[(index * 2 + 3) % teams.length] || "Away") : away,
      homeScore: String((index + 2) % 4),
      awayScore: String((index + 1) % 3),
      dateLabel: formatEplStripDate(isoDate, "19:45:00"),
      kickoffLabel: formatEplStripDateTime(isoDate, "19:45:00"),
      status: "FT"
    };
  });
}

function buildFallbackFixtureMatches(limit = EPL_STRIP_MAX_ITEMS) {
  const teams = (Array.isArray(EPL_TEAMS) ? EPL_TEAMS : []).filter(Boolean);
  if (teams.length < 2) return [];

  const count = Math.max(1, Math.min(Number(limit) || EPL_STRIP_MAX_ITEMS, EPL_STRIP_MAX_ITEMS));
  const now = new Date();

  return Array.from({ length: count }, (_, index) => {
    const home = teams[(index * 2 + 1) % teams.length];
    const away = teams[(index * 2 + 2) % teams.length] || teams[(index * 2 + 3) % teams.length] || "Away";
    const day = new Date(now);
    day.setDate(now.getDate() + (index + 1));
    const isoDate = day.toISOString().slice(0, 10);
    return {
      id: `fallback-fixture-${index}`,
      home,
      away: away === home ? (teams[(index * 2 + 4) % teams.length] || "Away") : away,
      kickoffLabel: formatEplStripDateTime(isoDate, "20:00:00"),
      status: "Scheduled"
    };
  });
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
    if (teamA && teamB && teamA !== teamB) {
      return {
        matchName: `text_${slugifyText(teamA)}_vs_${slugifyText(teamB)}_${LEAGUE_CODE}_${SEASON_CODE}`,
        matchTitle: `${teamA} vs ${teamB} - Custom Prompt`,
        venue: DEFAULT_MATCH_VENUE
      };
    }

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
    const inferredMatchup = teamA && teamB && teamA !== teamB
      ? ` Inferred matchup from prompt cues: ${teamA} vs ${teamB}.`
      : "";
    const inferredTeamPreference = (
      String(preferenceType || "").toLowerCase() === "team"
      && String(preferenceDetail || "").trim()
    )
      ? ` Inferred preferred team from prompt cues: ${preferenceDetail}.`
      : "";

    return `Source mode: text. User request: ${sourcePrompt}. `
      + `${inferredMatchup}${inferredTeamPreference}`
      + "Extract football entities from this request and generate the best available personalized and neutral football highlights."
      + " Keep the output strictly football-focused and grounded in available match events.";
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
    const secondaryCrest = idx % 2 === 0 ? logoB : logoA;
    const bannerLogos = Array.from({ length: 12 }, (_, logoIdx) => {
      const bannerCrest = logoIdx % 2 === 0 ? crest : secondaryCrest;
      return `<image href="${bannerCrest}" x="${160 + (logoIdx * 48)}" y="713" width="32" height="32" preserveAspectRatio="xMidYMid meet" opacity="0.78"/>`;
    }).join("");
    return `<g class="${frameClass}">
      <rect x="84" y="292" width="732" height="650" rx="26" class="${fillClass}"/>
      <image href="${crest}" x="282" y="388" width="336" height="336" preserveAspectRatio="xMidYMid meet" opacity="0.16"/>
      <text x="450" y="356" class="frameLabel">FEATURE REEL ${idx + 1}</text>
      ${lineNodes}
      <rect x="146" y="706" width="608" height="46" rx="13" class="teamBannerBg"/>
      ${bannerLogos}
      <rect x="146" y="760" width="608" height="112" rx="14" class="frameTagBg"/>
      <text x="450" y="814" class="frameTag">Animated screen capture sequence</text>
    </g>`;
  }).join("");

  const recapLines = wrappedCommentary.slice(0, 5);
  const recapPanelBottom = 1242;
  const recapPanelY = 980;
  const recapPanelHeight = recapPanelBottom - recapPanelY;
  const recapTitleY = recapPanelY + 34;
  const recapBodyStartY = recapPanelY + 70;
  const recapSvg = recapLines.map(
    (line, idx) => `<text x="84" y="${recapBodyStartY + (idx * 28)}" class="body">${escapeXml(line)}</text>`
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
    <rect x="70" y="${recapPanelY}" width="760" height="${recapPanelHeight}" rx="18" class="recapShell"/>
    <text x="84" y="${recapTitleY}" class="tilelabel">MATCH STORYLINE</text>
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
      .teamBannerBg { fill: rgba(2,6,23,0.56); stroke: rgba(250,204,21,0.28); stroke-width:1.2; }
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
  const leftHighlights = buildReelHighlights(teamA, teamB, preferenceDetail);
  const rightHighlights = buildReelHighlights(teamB, teamA, preferenceDetail);
  const leftHighlightsDetailed = buildHighlightDetails(leftHighlights);
  const rightHighlightsDetailed = buildHighlightDetails(rightHighlights);
  const leftReel = {
    side: "Left Reel",
    title: `${teamA} Analysis Feed`,
    logo: TEAM_LOGOS[teamA],
    teamName: teamA,
    highlights: leftHighlights,
    highlightsDetailed: leftHighlightsDetailed
  };

  const rightReel = {
    side: "Right Reel",
    title: `${teamB} Analysis Feed`,
    logo: TEAM_LOGOS[teamB],
    teamName: teamB,
    highlights: rightHighlights,
    highlightsDetailed: rightHighlightsDetailed
  };
  const cardMoments = [...leftReel.highlights.slice(0, 2), ...rightReel.highlights.slice(0, 2)];
  const neutralCommentary = buildNeutralCommentary(teamA, teamB, preferenceDetail);
  const preferredTeamName = String(preferenceType || "").toLowerCase() === "team"
    ? (resolveTeamName(preferenceDetail) || String(preferenceDetail || "").trim())
    : "";
  const preferredMockReel = preferredTeamName
    ? [leftReel, rightReel].find((reel) => reel.teamName === preferredTeamName) || null
    : null;
  const reels = preferredMockReel
    ? [{ ...preferredMockReel, side: "Preferred Reel" }]
    : [leftReel, rightReel];

  return {
    title: "Dual-Reel Analyst Output",
    context: `${matchInfo.matchTitle} (${matchInfo.matchName})`,
    matchup: `${teamA} vs ${teamB}`,
    venue: matchInfo.venue,
    commentary: neutralCommentary,
    neutralCommentary,
    commentaryConfidence: averageConfidenceFromDetails(leftHighlightsDetailed, 2),
    neutralCommentaryConfidence: averageConfidenceFromDetails(rightHighlightsDetailed, 2),
    neutralHighlightsDetailed: rightHighlightsDetailed,
    reels,
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

function buildPipelineResult(
  pipelineData,
  sourceMode,
  teamA,
  teamB,
  matchInfo,
  youtubeUrl,
  preferenceType = "",
  preferenceDetail = ""
) {
  const inferredTeams = sourceMode !== "teams"
    ? inferTeamsFromPipelineData(pipelineData)
    : { leftTeam: teamA, rightTeam: teamB };

  const leftTeam = inferredTeams.leftTeam || (sourceMode === "teams" ? teamA : "Detected Team A");
  const rightTeam = inferredTeams.rightTeam || (sourceMode === "teams" ? teamB : "Detected Team B");
  const leftHighlightsDetailed = buildHighlightDetails(
    mergeCaptionsWithEvidence(
      pipelineData.reel_a_captions?.length
        ? pipelineData.reel_a_captions
        : ["No personalized captions returned."],
      pipelineData.reel_a_evidence
    )
  );
  const rightHighlightsDetailed = buildHighlightDetails(
    mergeCaptionsWithEvidence(
      pipelineData.reel_b_captions?.length
        ? pipelineData.reel_b_captions
        : ["No neutral captions returned."],
      pipelineData.reel_b_evidence
    )
  );
  const leftHighlights = leftHighlightsDetailed.map((item) => item.caption);
  const rightHighlights = rightHighlightsDetailed.map((item) => item.caption);
  const neutralCommentary = rightHighlights.slice(0, 2).join(" ");
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
  const reelAVideoUrl = pipelineData.reel_a_path
    ? `${API_BASE_URL}/api/videos/reel_a?match_name=${encodeURIComponent(matchInfo.matchName)}`
    : "";
  const reelBVideoUrl = pipelineData.reel_b_path
    ? `${API_BASE_URL}/api/videos/reel_b?match_name=${encodeURIComponent(matchInfo.matchName)}`
    : "";
  const reelAVttUrl = pipelineData.reel_a_path
    ? `${API_BASE_URL}/api/output-files/${encodeURIComponent(matchInfo.matchName)}/reel_a.vtt`
    : "";
  const reelBVttUrl = pipelineData.reel_b_path
    ? `${API_BASE_URL}/api/output-files/${encodeURIComponent(matchInfo.matchName)}/reel_b.vtt`
    : "";
  const selectedAlignmentScore = parseConfidenceValue(
    pipelineData?.reel_a_alignment_score
    ?? pipelineData?.selected_alignment_score
  );
  const neutralAlignmentScore = parseConfidenceValue(
    pipelineData?.reel_b_alignment_score
    ?? pipelineData?.neutral_alignment_score
  );
  const leftReel = {
    side: "Left Reel",
    title: `${leftTeam} Analysis Feed`,
    logo: TEAM_LOGOS[leftTeam],
    teamName: leftTeam,
    highlights: leftHighlights,
    highlightsDetailed: leftHighlightsDetailed,
    videoUrl: reelAVideoUrl,
    vttUrl: reelAVttUrl
  };
  const rightReel = {
    side: "Right Reel",
    title: `${rightTeam} Analysis Feed`,
    logo: TEAM_LOGOS[rightTeam],
    teamName: rightTeam,
    highlights: rightHighlights,
    highlightsDetailed: rightHighlightsDetailed,
    videoUrl: reelBVideoUrl,
    vttUrl: reelBVttUrl
  };
  const prefersTeam = String(preferenceType || "").trim().toLowerCase() === "team";
  const preferredTeamName = prefersTeam
    ? (resolveTeamName(preferenceDetail) || String(preferenceDetail || "").trim())
    : "";
  const preferredPipelineReel = preferredTeamName
    ? [leftReel, rightReel].find((reel) => reel.teamName === preferredTeamName) || null
    : null;
  const reels = prefersTeam
    ? [{ ...(preferredPipelineReel || leftReel), side: "Preferred Reel" }]
    : [leftReel, rightReel];
  const outputTitle = reels.length > 1 ? "Dual-Reel Analyst Output" : "Preferred-Team Reel Output";

  return {
    title: outputTitle,
    context: `${matchInfo.matchTitle} (${matchInfo.matchName})`,
    matchup: sourceMode === "teams"
      ? `${teamA} vs ${teamB}`
      : (sourceMode === "youtube" ? "Matchup detected from YouTube source" : "Matchup inferred from custom prompt"),
    venue: matchInfo.venue,
    sourceUrl: sourceMode === "youtube" ? youtubeUrl : "",
    commentary: pipelineData.match_recap
      || "Video sent to deep-learning pipeline for detection, extraction, and summarization.",
    neutralCommentary,
    selectedAlignmentScore,
    neutralAlignmentScore,
    reel_a_alignment_score: selectedAlignmentScore,
    reel_b_alignment_score: neutralAlignmentScore,
    commentaryConfidence: averageConfidenceFromDetails(leftHighlightsDetailed, 2)
      ?? selectedAlignmentScore
      ?? parseConfidenceValue(
        pipelineData?.match_recap_confidence
        ?? pipelineData?.commentary_confidence
        ?? pipelineData?.selected_confidence
      ),
    neutralCommentaryConfidence: averageConfidenceFromDetails(rightHighlightsDetailed, 2)
      ?? neutralAlignmentScore
      ?? parseConfidenceValue(
        pipelineData?.neutral_commentary_confidence
        ?? pipelineData?.neutral_confidence
      ),
    neutralHighlightsDetailed: rightHighlightsDetailed,
    reels,
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
      return { cue, index: idx };
    }
  }
  return null;
}

function buildReelCaptionKey(reel) {
  return [
    String(reel?.perspective || "").trim().toLowerCase(),
    String(reel?.side || "").trim().toLowerCase(),
    String(reel?.title || "").trim().toLowerCase(),
    String(reel?.teamName || "").trim().toLowerCase(),
  ].join("|");
}

function ReelVideoWithTimedCaptions({ reel, onActiveCaptionChange }) {
  const videoRef = useRef(null);
  const [timedCues, setTimedCues] = useState(() => buildSyntheticTimedCues(reel.highlights));
  const lastBroadcastSignatureRef = useRef("");

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
      const nextText = String(current?.cue?.text || "");
      const nextIndex = Number.isInteger(current?.index) ? current.index : -1;
      if (typeof onActiveCaptionChange === "function") {
        const signature = `${nextIndex}|${nextText}`;
        if (lastBroadcastSignatureRef.current !== signature) {
          lastBroadcastSignatureRef.current = signature;
          onActiveCaptionChange({ text: nextText, index: nextIndex });
        }
      }
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
  }, [timedCues, onActiveCaptionChange]);

  return (
    reel.videoUrl ? (
      <div className="reel-video-wrap">
        <video ref={videoRef} controls preload="metadata" className="reel-video-player" src={reel.videoUrl}>
          {reel.vttUrl && (
            <track kind="subtitles" srcLang="en" label="English" src={reel.vttUrl} default />
          )}
        </video>
      </div>
    ) : null
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
    selectedAlignmentScore: selectedAlignmentFromOptions = null,
    neutralAlignmentScore: neutralAlignmentFromOptions = null,
    selectedCaptionDetails = [],
    neutralCaptionDetails = [],
    selectedPerspectiveKey = "",
    captionDetailsByPerspective = {},
  } = options;
  const reels = Array.isArray(showcaseData?.reels) ? showcaseData.reels : [];
  const mappedAllReels = reels.map((reel, index) => {
    const perspective = String(reel?.perspective || "").trim().toLowerCase();
    const teamName = resolvePerspectiveTeamName(perspective, teamA, teamB);
    const mappedCaptionDetails = Array.isArray(captionDetailsByPerspective?.[perspective])
      ? captionDetailsByPerspective[perspective]
      : [];
    const hasSelectedEvidenceForPerspective = (
      perspective === String(selectedPerspectiveKey || "").trim().toLowerCase()
      && Array.isArray(selectedCaptionDetails)
      && selectedCaptionDetails.length > 0
    );
    const hasNeutralEvidenceForPerspective = (
      perspective === "neutral"
      && Array.isArray(neutralCaptionDetails)
      && neutralCaptionDetails.length > 0
    );
    const highlightSource = Array.isArray(reel?.captions_detailed)
      ? reel.captions_detailed
      : hasSelectedEvidenceForPerspective
        ? selectedCaptionDetails
        : hasNeutralEvidenceForPerspective
          ? neutralCaptionDetails
          : (mappedCaptionDetails.length > 0 ? mappedCaptionDetails : (Array.isArray(reel?.captions) ? reel.captions : []));
    const highlightsDetailed = buildHighlightDetails(highlightSource);
    const highlights = highlightsDetailed.map((item) => item.caption);

    return {
      perspective,
      side: perspective === "neutral" ? "Neutral Reel" : `Perspective ${index + 1}`,
      title: String(reel?.label || "Pre-generated Reel"),
      logo: perspective === "neutral" ? "" : (TEAM_LOGOS[teamName] || ""),
      teamName,
      highlights,
      highlightsDetailed,
      alignmentScore: parseConfidenceValue(reel?.alignment_score),
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
  const neutralCommentary = Array.isArray(byPerspective?.neutral?.highlights)
    ? byPerspective.neutral.highlights.slice(0, 2).join(" ")
    : "";
  const selectedAlignmentScore = parseConfidenceValue(
    selectedAlignmentFromOptions
    ?? showcaseData?.reel_a_alignment_score
    ?? showcaseData?.selected_alignment_score
  );
  const neutralAlignmentScore = parseConfidenceValue(
    neutralAlignmentFromOptions
    ?? showcaseData?.reel_b_alignment_score
    ?? showcaseData?.neutral_alignment_score
  );
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
    const preferredExpressive = preferredTeamName ? findReelForTeam(preferredTeamName) : null;
    if (preferredExpressive) {
      mappedReels = [{
        ...preferredExpressive,
        side: "Preferred Reel",
      }];
      commentaryTitle = "Expressive Commentary";
      commentary = preferredExpressive.highlights[0]
        ? `${preferredExpressive.teamName}: ${preferredExpressive.highlights[0]}`
        : commentary;
    } else {
      const expressive = [findReelForTeam(teamA), findReelForTeam(teamB)].filter(Boolean);
      if (expressive.length > 0) {
        mappedReels = [{
          ...expressive[0],
          side: "Preferred Reel",
        }];
        commentaryTitle = "Expressive Commentary";
        commentary = expressive
          .map((reel) => reel?.highlights?.[0] ? `${reel.teamName}: ${reel.highlights[0]}` : "")
          .find(Boolean)
          || commentary;
      }
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
    neutralCommentary,
    selectedAlignmentScore,
    neutralAlignmentScore,
    reel_a_alignment_score: selectedAlignmentScore,
    reel_b_alignment_score: neutralAlignmentScore,
    commentaryConfidence: averageConfidenceFromDetails(mappedReels.flatMap((reel) => reel?.highlightsDetailed || []), 2)
      ?? selectedAlignmentScore,
    neutralCommentaryConfidence: averageConfidenceFromDetails(byPerspective?.neutral?.highlightsDetailed || [], 2)
      ?? neutralAlignmentScore,
    neutralHighlightsDetailed: byPerspective?.neutral?.highlightsDetailed || [],
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

function TeamFoilBadge({ logoSrc, teamName, size = TEAM_PREVIEW_BADGE_SIZE, speed = "11s" }) {
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
      <TeamFoilBadge logoSrc={logoSrc} teamName={teamName} size={TEAM_PREVIEW_BADGE_SIZE} speed="10s" />
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [cardCollectionItems, setCardCollectionItems] = useState(() => readCardCollection());
  const [cardCollectionCount, setCardCollectionCount] = useState(() => readCardCollection().length);
  const [cardPullInventory, setCardPullInventory] = useState(() => readCardPullInventory());
  const [isSpinningCard, setIsSpinningCard] = useState(false);
  const [revealedPulledCard, setRevealedPulledCard] = useState(null);
  const [selectedSetId, setSelectedSetId] = useState("");
  const [lastPulledCard, setLastPulledCard] = useState(null);
  const [hasUsedSpinForResult, setHasUsedSpinForResult] = useState(false);
  const [hasCollectedForResult, setHasCollectedForResult] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState("");
  const [healthStatusKind, setHealthStatusKind] = useState("");
  const [youtubeTitle, setYoutubeTitle] = useState("");
  const [youtubeTitleLoading, setYoutubeTitleLoading] = useState(false);
  const [liveReelCaptions, setLiveReelCaptions] = useState({});
  const [liveReelCaptionIndices, setLiveReelCaptionIndices] = useState({});
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
  const [factualInconsistencyAlert, setFactualInconsistencyAlert] = useState(null);
  const [hallucinationAlert, setHallucinationAlert] = useState(null);
  const [hallucinationCueSignals, setHallucinationCueSignals] = useState([]);
  const alertDismissTimerRef = useRef(null);
  const hallucinationDismissTimerRef = useRef(null);
  const lastAlertSignatureRef = useRef("");
  const lastHallucinationSignatureRef = useRef("");
  const previousCueIndicesRef = useRef({ selected: -1, neutral: -1 });
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
  const reelSetCatalog = buildReelSetCatalog(result, matchInfo);
  const selectedReelSet = reelSetCatalog.sets.find((set) => set.id === selectedSetId) || reelSetCatalog.sets[0] || null;
  const activePullPool = selectedReelSet?.cards || [];
  const selectedSetOwnedCount = selectedReelSet
    ? selectedReelSet.cards.filter((card) => cardCollectionItems.some((owned) => owned?.id === card.id)).length
    : 0;
  const reelVideoBySetName = Object.fromEntries(
    (Array.isArray(result?.reels) ? result.reels : [])
      .map((reel) => [String(reel?.title || "").trim(), String(reel?.videoUrl || "").trim()])
      .filter(([setName, videoUrl]) => Boolean(setName) && Boolean(videoUrl))
  );
  const spinFeatureVideo = Array.isArray(result?.reels)
    ? (result.reels.find((reel) => String(reel?.videoUrl || "").trim())?.videoUrl || "")
    : "";
  const neutralCommentaryComparison = (() => {
    const direct = String(result?.neutralCommentary || "").trim();
    if (direct) return direct;
    const reels = Array.isArray(result?.reels) ? result.reels : [];
    const neutralReel = reels.find((reel) => {
      const side = String(reel?.side || "").toLowerCase();
      const title = String(reel?.title || "").toLowerCase();
      const perspective = String(reel?.perspective || "").toLowerCase();
      return side.includes("neutral") || title.includes("neutral") || perspective === "neutral";
    });
    if (!neutralReel || !Array.isArray(neutralReel?.highlights)) return "";
    return neutralReel.highlights
      .map((line) => String(line || "").trim())
      .filter(Boolean)
      .slice(0, 2)
      .join(" ");
  })();
  const reelsForDisplay = Array.isArray(result?.reels) ? result.reels : [];
  const selectedReelForLive = reelsForDisplay[0] || null;
  const neutralReelForLive = reelsForDisplay.find((reel) => {
    const side = String(reel?.side || "").toLowerCase();
    const title = String(reel?.title || "").toLowerCase();
    const perspective = String(reel?.perspective || "").toLowerCase();
    return side.includes("neutral") || title.includes("neutral") || perspective === "neutral";
  }) || null;
  const selectedLiveCommentary = selectedReelForLive
    ? String(liveReelCaptions[buildReelCaptionKey(selectedReelForLive)] || "").trim()
    : "";
  const neutralLiveCommentary = neutralReelForLive
    ? String(liveReelCaptions[buildReelCaptionKey(neutralReelForLive)] || "").trim()
    : "";
  const selectedLiveCueIndex = selectedReelForLive
    ? Number(liveReelCaptionIndices[buildReelCaptionKey(selectedReelForLive)])
    : -1;
  const neutralLiveCueIndex = neutralReelForLive
    ? Number(liveReelCaptionIndices[buildReelCaptionKey(neutralReelForLive)])
    : -1;
  const neutralSyncedByIndex = (() => {
    if (!Number.isFinite(selectedLiveCueIndex) || selectedLiveCueIndex < 0) return "";
    const neutralDetails = Array.isArray(result?.neutralHighlightsDetailed) ? result.neutralHighlightsDetailed : [];
    const detailMatch = neutralDetails[selectedLiveCueIndex];
    const detailCaption = String(detailMatch?.caption || detailMatch?.moment || "").trim();
    if (detailCaption) return detailCaption;

    const neutralReel = (Array.isArray(result?.reels) ? result.reels : []).find((reel) => {
      const side = String(reel?.side || "").toLowerCase();
      const title = String(reel?.title || "").toLowerCase();
      const perspective = String(reel?.perspective || "").toLowerCase();
      return side.includes("neutral") || title.includes("neutral") || perspective === "neutral";
    });
    if (!neutralReel || !Array.isArray(neutralReel?.highlights)) return "";
    return String(neutralReel.highlights[selectedLiveCueIndex] || "").trim();
  })();
  const selectedCommentaryDisplay = selectedLiveCommentary || String(result?.commentary || "").trim();
  const neutralCommentaryDisplay = neutralLiveCommentary || neutralSyncedByIndex || neutralCommentaryComparison;
  const hasNeutralDiffComparison = Boolean(neutralCommentaryDisplay);
  const selectedLiveCueDetail = (() => {
    if (!Number.isFinite(selectedLiveCueIndex) || selectedLiveCueIndex < 0) return null;
    const selectedDetails = Array.isArray(selectedReelForLive?.highlightsDetailed)
      ? selectedReelForLive.highlightsDetailed
      : [];
    return selectedDetails[selectedLiveCueIndex] || null;
  })();
  const neutralLiveCueDetail = (() => {
    if (Number.isFinite(neutralLiveCueIndex) && neutralLiveCueIndex >= 0) {
      const reelDetails = Array.isArray(neutralReelForLive?.highlightsDetailed)
        ? neutralReelForLive.highlightsDetailed
        : [];
      const byNeutralIndex = reelDetails[neutralLiveCueIndex];
      if (byNeutralIndex) return byNeutralIndex;
    }
    if (Number.isFinite(selectedLiveCueIndex) && selectedLiveCueIndex >= 0) {
      const neutralDetails = Array.isArray(result?.neutralHighlightsDetailed) ? result.neutralHighlightsDetailed : [];
      return neutralDetails[selectedLiveCueIndex] || null;
    }
    return null;
  })();
  const selectedLiveCueAlignment = (() => {
    const value = parseConfidenceValue(selectedLiveCueDetail?.alignment_score);
    return Number.isFinite(value) ? value : null;
  })();
  const neutralLiveCueAlignment = (() => {
    const value = parseConfidenceValue(neutralLiveCueDetail?.alignment_score);
    if (Number.isFinite(value)) return value;
    return null;
  })();
  const selectedCommentaryConfidence = (() => {
    const reelAlignment = parseConfidenceValue(
      result?.selectedAlignmentScore
      ?? result?.reel_a_alignment_score
    );
    return deriveLiveAlignmentScore(
      selectedLiveCueAlignment,
      reelAlignment,
      selectedLiveCueDetail?.score ?? selectedLiveCueDetail?.confidence
    );
  })();
  const neutralCommentaryConfidence = (() => {
    const reelAlignment = parseConfidenceValue(
      result?.neutralAlignmentScore
      ?? result?.reel_b_alignment_score
    );
    return deriveLiveAlignmentScore(
      neutralLiveCueAlignment,
      reelAlignment,
      neutralLiveCueDetail?.score ?? neutralLiveCueDetail?.confidence
    );
  })();
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
  const resolvedPreferredPlayer = String(preferenceType || "").toLowerCase() === "individual"
    ? resolvePreferredPlayerSelection(preferenceDetail, selectablePlayers)
    : { name: "", team: "" };
  const effectivePreferenceDetail = String(preferenceType || "").toLowerCase() === "individual"
    ? (resolvedPreferredPlayer.name || preferenceDetail)
    : preferenceDetail;
  const effectivePreferredTeamFromPlayer = String(preferenceType || "").toLowerCase() === "individual"
    ? (resolvedPreferredPlayer.team || "")
    : "";

  const preferenceTypeOptions = ["team", "individual"];

  const teamDetails = sourceMode === "teams"
    ? [teamA, teamB].filter(Boolean)
    : ["Detected Team A", "Detected Team B"];

  const preferenceDetailMap = {
    team: teamDetails,
    individual: availablePlayerNames
  };

  const detailOptions = preferenceType ? preferenceDetailMap[preferenceType] || [] : [];
  const autoTone = preferenceType && preferenceDetail ? "expressive" : "";
  const resetFactualInconsistencyAlert = () => {
    if (alertDismissTimerRef.current) {
      clearTimeout(alertDismissTimerRef.current);
      alertDismissTimerRef.current = null;
    }
    lastAlertSignatureRef.current = "";
    previousCueIndicesRef.current = { selected: -1, neutral: -1 };
    setFactualInconsistencyAlert(null);
  };
  const resetHallucinationAlert = () => {
    if (hallucinationDismissTimerRef.current) {
      clearTimeout(hallucinationDismissTimerRef.current);
      hallucinationDismissTimerRef.current = null;
    }
    lastHallucinationSignatureRef.current = "";
    setHallucinationCueSignals([]);
    setHallucinationAlert(null);
  };

  const hasValidSource = sourceMode === "teams"
    ? teamA && teamB && teamA !== teamB
    : (sourceMode === "youtube" ? isValidYouTubeUrl(youtubeUrl) : sourcePrompt.trim().length > 0);

  const isFormComplete = sourceMode === "text"
    ? hasValidSource
    : (
      hasValidSource &&
      preferenceType &&
      preferenceDetail
    );

  const handleSourceModeChange = (nextMode) => {
    resetFactualInconsistencyAlert();
    resetHallucinationAlert();
    setSourceMode(nextMode);
    setTeamA("");
    setTeamB("");
    setYoutubeUrl("");
    setSourcePrompt("");
    setYoutubeTitle("");
    setYoutubeTitleLoading(false);
    setPreferenceType("");
    setPreferenceDetail("");
    setDynamicPlayers([]);
    setPlayersLoading(false);
    setPlayerPoolMessage("");
    setPlayerHeadshotFailed({});
    setError("");
    setResult(null);
    setIsSpinningCard(false);
    setRevealedPulledCard(null);
    setLastPulledCard(null);
    setHasUsedSpinForResult(false);
    setHasCollectedForResult(false);
    setLiveReelCaptions({});
    setLiveReelCaptionIndices({});
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

        const safeScoreMatches = scoreMatches.length > 0 ? scoreMatches : buildFallbackScoreMatches();
        const safeFixtureMatches = fixtureMatches.length > 0 ? fixtureMatches : buildFallbackFixtureMatches();

        setEplTickerMatches(safeScoreMatches);
        setEplFixtureMatches(safeFixtureMatches);
        setEplTableRows(tableRows.length > 0 ? tableRows : fallbackAlphabeticalTable);
        setSelectedTickerMatch((prev) => prev || safeScoreMatches[0] || safeFixtureMatches[0] || null);
      } catch (err) {
        if (err?.name !== "AbortError") {
          setEplTickerMatches(buildFallbackScoreMatches());
          setEplFixtureMatches(buildFallbackFixtureMatches());
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
    if (sourceMode !== "text") return;

    const inference = inferPromptMatchAndPreference(sourcePrompt);
    const nextTeamA = inference.teams[0] || "";
    const nextTeamB = inference.teams[1] || "";
    const nextPreferredTeam = inference.preferredTeam || "";

    if (teamA !== nextTeamA) setTeamA(nextTeamA);
    if (teamB !== nextTeamB) setTeamB(nextTeamB);

    if (nextPreferredTeam) {
      if (preferenceType !== "team") setPreferenceType("team");
      if (preferenceDetail !== nextPreferredTeam) setPreferenceDetail(nextPreferredTeam);
    } else if (preferenceType === "team" || (preferenceType === "" && preferenceDetail)) {
      if (preferenceType) setPreferenceType("");
      if (preferenceDetail) setPreferenceDetail("");
    }
  }, [sourceMode, sourcePrompt, teamA, teamB, preferenceType, preferenceDetail]);

  useEffect(() => {
    if (preferenceType !== "individual") return;
    if (!preferenceDetail) return;
    if (availablePlayerNames.includes(preferenceDetail)) return;
    const resolved = resolvePreferredPlayerSelection(preferenceDetail, selectablePlayers);
    if (resolved.name && availablePlayerNames.includes(resolved.name)) {
      if (resolved.name !== preferenceDetail) setPreferenceDetail(resolved.name);
      return;
    }
    setPreferenceDetail("");
  }, [preferenceType, preferenceDetail, availablePlayerNames, selectablePlayers]);

  useEffect(() => {
    if (!preferenceType) return;
    if (preferenceType === "team" || preferenceType === "individual") return;
    setPreferenceType("");
    setPreferenceDetail("");
  }, [preferenceType]);

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

  useEffect(() => {
    const totalCollected = cardCollectionItems.reduce(
      (sum, entry) => sum + Math.max(1, Number(entry?.quantity) || 1),
      0
    );
    setCardCollectionCount(totalCollected);
  }, [cardCollectionItems]);

  useEffect(() => {
    if (!reelSetCatalog.sets.length) {
      setSelectedSetId("");
      return;
    }
    const stillValid = reelSetCatalog.sets.some((set) => set.id === selectedSetId);
    if (!selectedSetId || !stillValid) {
      setSelectedSetId(reelSetCatalog.sets[0].id);
    }
  }, [reelSetCatalog, selectedSetId]);

  useEffect(() => {
    setLiveReelCaptions({});
    setLiveReelCaptionIndices({});
    resetFactualInconsistencyAlert();
  }, [result]);

  useEffect(() => {
    return () => {
      if (alertDismissTimerRef.current) {
        clearTimeout(alertDismissTimerRef.current);
        alertDismissTimerRef.current = null;
      }
      if (hallucinationDismissTimerRef.current) {
        clearTimeout(hallucinationDismissTimerRef.current);
        hallucinationDismissTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!factualInconsistencyAlert) return;
    if (alertDismissTimerRef.current) {
      clearTimeout(alertDismissTimerRef.current);
    }
    alertDismissTimerRef.current = setTimeout(() => {
      setFactualInconsistencyAlert(null);
      alertDismissTimerRef.current = null;
    }, FACTUAL_INCONSISTENCY_POPUP_MS);
    return () => {
      if (alertDismissTimerRef.current) {
        clearTimeout(alertDismissTimerRef.current);
        alertDismissTimerRef.current = null;
      }
    };
  }, [factualInconsistencyAlert]);

  useEffect(() => {
    if (!hallucinationAlert) return;
    if (hallucinationDismissTimerRef.current) {
      clearTimeout(hallucinationDismissTimerRef.current);
    }
    hallucinationDismissTimerRef.current = setTimeout(() => {
      setHallucinationAlert(null);
      hallucinationDismissTimerRef.current = null;
    }, HALLUCINATION_POPUP_MS);
    return () => {
      if (hallucinationDismissTimerRef.current) {
        clearTimeout(hallucinationDismissTimerRef.current);
        hallucinationDismissTimerRef.current = null;
      }
    };
  }, [hallucinationAlert]);

  useEffect(() => {
    const currentSelected = Number.isFinite(selectedLiveCueIndex) ? selectedLiveCueIndex : -1;
    const currentNeutral = Number.isFinite(neutralLiveCueIndex) ? neutralLiveCueIndex : -1;
    const previous = previousCueIndicesRef.current || { selected: -1, neutral: -1 };

    const selectedRewound = currentSelected >= 0 && previous.selected >= 0 && currentSelected < previous.selected;
    const neutralRewound = currentNeutral >= 0 && previous.neutral >= 0 && currentNeutral < previous.neutral;

    if (selectedRewound || neutralRewound) {
      // Allow alert to re-fire when user replays/seeks backward.
      lastAlertSignatureRef.current = "";
      lastHallucinationSignatureRef.current = "";
    }

    previousCueIndicesRef.current = {
      selected: currentSelected,
      neutral: currentNeutral
    };
  }, [selectedLiveCueIndex, neutralLiveCueIndex]);

  useEffect(() => {
    if (!result) return;

    const candidates = [];
    if (selectedLiveCueDetail && isFactualInconsistencyDetail(selectedLiveCueDetail)) {
      candidates.push({
        stream: "Selected",
        cueIndex: selectedLiveCueIndex,
        caption: String(selectedLiveCueDetail?.caption || selectedCommentaryDisplay || "").trim(),
        importance: parseConfidenceValue(
          selectedLiveCueDetail?.importance_score
          ?? selectedLiveCueDetail?.score
          ?? selectedLiveCueDetail?.confidence
        ),
        alignment: parseConfidenceValue(selectedLiveCueDetail?.consistency_score ?? selectedLiveCueDetail?.alignment_score),
        disagreement: parseRateValue(selectedLiveCueDetail?.disagreement_rate),
        highDisagreement: selectedLiveCueDetail?.high_disagreement === true,
      });
    }
    if (neutralLiveCueDetail && isFactualInconsistencyDetail(neutralLiveCueDetail)) {
      candidates.push({
        stream: "Neutral",
        cueIndex: Number.isFinite(neutralLiveCueIndex) && neutralLiveCueIndex >= 0
          ? neutralLiveCueIndex
          : selectedLiveCueIndex,
        caption: String(neutralLiveCueDetail?.caption || neutralCommentaryDisplay || "").trim(),
        importance: parseConfidenceValue(
          neutralLiveCueDetail?.importance_score
          ?? neutralLiveCueDetail?.score
          ?? neutralLiveCueDetail?.confidence
        ),
        alignment: parseConfidenceValue(neutralLiveCueDetail?.consistency_score ?? neutralLiveCueDetail?.alignment_score),
        disagreement: parseRateValue(neutralLiveCueDetail?.disagreement_rate),
        highDisagreement: neutralLiveCueDetail?.high_disagreement === true,
      });
    }
    if (!candidates.length) return;

    candidates.sort((a, b) => {
      const aSeverity = (Number.isFinite(a.disagreement) ? a.disagreement : 0) + (a.highDisagreement ? 1 : 0);
      const bSeverity = (Number.isFinite(b.disagreement) ? b.disagreement : 0) + (b.highDisagreement ? 1 : 0);
      if (aSeverity !== bSeverity) return bSeverity - aSeverity;
      const aAlignment = Number.isFinite(a.alignment) ? a.alignment : 1;
      const bAlignment = Number.isFinite(b.alignment) ? b.alignment : 1;
      if (aAlignment !== bAlignment) return aAlignment - bAlignment;
      const aImportance = Number.isFinite(a.importance) ? a.importance : 1;
      const bImportance = Number.isFinite(b.importance) ? b.importance : 1;
      return aImportance - bImportance;
    });

    const top = candidates[0];
    const signature = [
      String(result?.matchup || ""),
      top.stream,
      Number.isFinite(top.cueIndex) ? top.cueIndex : "na",
      Number.isFinite(top.importance) ? top.importance.toFixed(3) : "na",
      Number.isFinite(top.alignment) ? top.alignment.toFixed(3) : "na",
      Number.isFinite(top.disagreement) ? top.disagreement.toFixed(3) : "na",
      top.highDisagreement ? "high" : "normal",
      top.caption
    ].join("|");

    if (lastAlertSignatureRef.current === signature) return;
    lastAlertSignatureRef.current = signature;

    setFactualInconsistencyAlert({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      stream: top.stream,
      cueIndex: top.cueIndex,
      caption: top.caption || "High-disagreement clip triggered disagreement challenge.",
      importance: top.importance,
      alignment: top.alignment,
      disagreement: top.disagreement,
      highDisagreement: top.highDisagreement,
    });
  }, [
    result,
    selectedLiveCueIndex,
    neutralLiveCueIndex,
    selectedCommentaryDisplay,
    neutralCommentaryDisplay,
    selectedLiveCueDetail?.caption,
    selectedLiveCueDetail?.consistency_score,
    selectedLiveCueDetail?.alignment_score,
    selectedLiveCueDetail?.score,
    selectedLiveCueDetail?.confidence,
    selectedLiveCueDetail?.disagreement_rate,
    selectedLiveCueDetail?.high_disagreement,
    neutralLiveCueDetail?.caption,
    neutralLiveCueDetail?.consistency_score,
    neutralLiveCueDetail?.alignment_score,
    neutralLiveCueDetail?.score,
    neutralLiveCueDetail?.confidence,
    neutralLiveCueDetail?.disagreement_rate,
    neutralLiveCueDetail?.high_disagreement,
  ]);

  useEffect(() => {
    if (!result) return;
    if (!Array.isArray(hallucinationCueSignals) || hallucinationCueSignals.length === 0) return;

    const selectedSegmentId = normalizeSegmentId(selectedLiveCueDetail?.segment_id);
    const neutralSegmentId = normalizeSegmentId(neutralLiveCueDetail?.segment_id);
    if (!selectedSegmentId && !neutralSegmentId) return;

    const candidates = [];
    hallucinationCueSignals.forEach((signal) => {
      const signalSegmentId = normalizeSegmentId(signal?.segment_id);
      if (!signalSegmentId) return;

      const streamKey = String(signal?.stream || "").trim().toLowerCase();
      if (streamKey === "selected") {
        if (selectedSegmentId && selectedSegmentId === signalSegmentId) {
          candidates.push({
            ...signal,
            stream: "Selected",
            cueIndex: Number.isFinite(selectedLiveCueIndex) ? selectedLiveCueIndex : null,
            segment_id: signalSegmentId,
          });
        }
        return;
      }

      if (streamKey === "neutral") {
        if (neutralSegmentId && neutralSegmentId === signalSegmentId) {
          candidates.push({
            ...signal,
            stream: "Neutral",
            cueIndex: Number.isFinite(neutralLiveCueIndex) ? neutralLiveCueIndex : null,
            segment_id: signalSegmentId,
          });
        }
        return;
      }

      if (selectedSegmentId && selectedSegmentId === signalSegmentId) {
        candidates.push({
          ...signal,
          stream: "Selected",
          cueIndex: Number.isFinite(selectedLiveCueIndex) ? selectedLiveCueIndex : null,
          segment_id: signalSegmentId,
        });
      }
      if (neutralSegmentId && neutralSegmentId === signalSegmentId) {
        candidates.push({
          ...signal,
          stream: "Neutral",
          cueIndex: Number.isFinite(neutralLiveCueIndex) ? neutralLiveCueIndex : null,
          segment_id: signalSegmentId,
        });
      }
    });

    if (!candidates.length) return;

    candidates.sort((a, b) => {
      const aTotal = Number.isFinite(a.totalHallucinationsDetected) ? a.totalHallucinationsDetected : -1;
      const bTotal = Number.isFinite(b.totalHallucinationsDetected) ? b.totalHallucinationsDetected : -1;
      if (aTotal !== bTotal) return bTotal - aTotal;
      const aRetry = Number.isFinite(a.retryCount) ? a.retryCount : -1;
      const bRetry = Number.isFinite(b.retryCount) ? b.retryCount : -1;
      if (aRetry !== bRetry) return bRetry - aRetry;
      const aStreamPriority = String(a.stream || "").toLowerCase() === "selected" ? 0 : 1;
      const bStreamPriority = String(b.stream || "").toLowerCase() === "selected" ? 0 : 1;
      return aStreamPriority - bStreamPriority;
    });

    const top = candidates[0];
    const signature = [
      String(result?.matchup || ""),
      String(top.stream || ""),
      String(top.segment_id || ""),
      Number.isFinite(top.cueIndex) ? String(top.cueIndex) : "na",
      String(top.caption || ""),
    ].join("|");

    if (lastHallucinationSignatureRef.current === signature) return;
    lastHallucinationSignatureRef.current = signature;

    const alert = buildHallucinationAlertFromSignal(top, {
      stream: top.stream,
      cueIndex: top.cueIndex,
      segment_id: top.segment_id,
    });
    if (alert) {
      setHallucinationAlert(alert);
    }
  }, [
    result,
    hallucinationCueSignals,
    selectedLiveCueIndex,
    neutralLiveCueIndex,
    selectedLiveCueDetail?.segment_id,
    neutralLiveCueDetail?.segment_id,
  ]);

  const handleGenerate = async () => {
    if (!isFormComplete) return;

    resetFactualInconsistencyAlert();
    resetHallucinationAlert();
    setLoading(true);
    setError("");
    setResult(null);
    setIsSpinningCard(false);
    setRevealedPulledCard(null);
    setLastPulledCard(null);
    setHasUsedSpinForResult(false);
    setHasCollectedForResult(false);
    setLiveReelCaptions({});
    setLiveReelCaptionIndices({});

    try {
      const showcaseMatchName = ((sourceMode === "teams" || sourceMode === "text") && teamA && teamB)
        ? getShowcaseMatchForTeams(teamA, teamB)
        : "";

      if (showcaseMatchName) {
        const showcaseResponse = await fetch(`${API_BASE_URL}${SHOWCASE_ENDPOINT}/${showcaseMatchName}`);
        if (!showcaseResponse.ok) {
          const payload = await showcaseResponse.json().catch(() => ({}));
          throw new Error(payload.detail || `Showcase request failed: ${showcaseResponse.status}`);
        }
        const showcaseData = await showcaseResponse.json();

        const perspectives = Array.from(
          new Set(
            (Array.isArray(showcaseData?.reels) ? showcaseData.reels : [])
              .map((reel) => String(reel?.perspective || "").trim().toLowerCase())
              .filter(Boolean)
          )
        );
        const captionDetailsByPerspective = {};
        await Promise.all(
          perspectives.map(async (perspective) => {
            try {
              const response = await fetch(
                `${API_BASE_URL}/api/output-files/${encodeURIComponent(showcaseMatchName)}/captions_${encodeURIComponent(perspective)}.json`
              );
              if (!response.ok) return;
              const payload = await response.json().catch(() => null);
              const rows = parseCaptionDetailRows(payload?.captions);
              if (rows.length > 0) {
                captionDetailsByPerspective[perspective] = rows;
              }
            } catch {
              // Ignore missing perspective caption files.
            }
          })
        );

        let showcaseAlignmentPayload = null;
        try {
          const captionsResponse = await fetch(
            `${API_BASE_URL}/api/output-files/${encodeURIComponent(showcaseMatchName)}/captions.json`
          );
          if (captionsResponse.ok) {
            showcaseAlignmentPayload = await captionsResponse.json();
          }
        } catch {
          showcaseAlignmentPayload = null;
        }

        let fullEvaluationPayload = null;
        try {
          const fullEvalResponse = await fetch(
            `${API_BASE_URL}/api/output-files/${encodeURIComponent(showcaseMatchName)}/full_evaluation_results.json`
          );
          if (fullEvalResponse.ok) {
            fullEvaluationPayload = await fullEvalResponse.json();
          }
        } catch {
          fullEvaluationPayload = null;
        }

        const selectedEvidenceFileCandidates = buildPreferredEvidenceFilenames(
          preferenceType,
          effectivePreferenceDetail,
          { preferredTeam: effectivePreferredTeamFromPlayer }
        );
        const [selectedEvidenceResult, neutralEvidenceResult] = await Promise.all([
          fetchFirstExistingOutputJson(showcaseMatchName, selectedEvidenceFileCandidates),
          fetchFirstExistingOutputJson(showcaseMatchName, ["evidence_log_neutral.json", "evidence_log.json"])
        ]);

        const fullEvalAlignment = extractAlignmentScoresFromFullEvaluation(fullEvaluationPayload, {
          preferenceType,
          preferenceDetail: effectivePreferenceDetail,
          tone: autoTone
        });
        const perClipAlignmentBySegment = buildPerClipAlignmentBySegment(fullEvaluationPayload);
        const perspectiveKeys = Object.keys(captionDetailsByPerspective);
        perspectiveKeys.forEach((key) => {
          captionDetailsByPerspective[key] = applyPerClipAlignmentToCaptionRows(
            captionDetailsByPerspective[key],
            perClipAlignmentBySegment
          );
        });

        const selectedEvidenceRows = mergePerClipDisagreementIntoCaptionRows(
          parseEvidenceClipRows(selectedEvidenceResult?.payload, {
            captionField: "caption_reel_a",
            fallbackCaptionField: "caption_reel_b",
            alignmentField: "alignment_score_reel_a"
          }),
          perClipAlignmentBySegment
        );
        const neutralEvidenceRows = mergePerClipDisagreementIntoCaptionRows(
          parseEvidenceClipRows(neutralEvidenceResult?.payload, {
            captionField: "caption_reel_b",
            fallbackCaptionField: "caption_reel_a",
            alignmentField: "alignment_score_reel_b"
          }),
          perClipAlignmentBySegment
        );
        const selectedEvidenceSummaryAlignment = extractEvidenceSummaryAlignment(
          selectedEvidenceResult?.payload,
          ["reel_a_alignment_score", "reel_b_alignment_score"]
        );
        const neutralEvidenceSummaryAlignment = extractEvidenceSummaryAlignment(
          neutralEvidenceResult?.payload,
          ["reel_b_alignment_score", "reel_a_alignment_score"]
        );
        const showcaseHallucinationCandidates = [
          {
            stream: "Selected",
            ...extractHallucinationState(selectedEvidenceResult?.payload),
          },
          {
            stream: "Neutral",
            ...extractHallucinationState(neutralEvidenceResult?.payload),
          },
        ];
        const showcaseHallucinationSignals = buildHallucinationCueSignals(
          showcaseHallucinationCandidates,
          {
            totalHallucinationsDetected: extractHallucinationTotalsFromFullEvaluation(fullEvaluationPayload),
          }
        );
        const showcaseHallucinationAlert = buildHallucinationAlertFromSignal(
          showcaseHallucinationSignals.find((item) => !item.segment_id) || null
        );

        const preferredPerspectiveKey = (() => {
          const normalizedPreferenceType = String(preferenceType || "").toLowerCase();
          if (normalizedPreferenceType === "team" && effectivePreferenceDetail) {
            const candidateKeys = perspectiveKeysForTeam(effectivePreferenceDetail);
            if (!candidateKeys.length) return "";
            return candidateKeys.find((key) => perspectives.includes(key))
              || candidateKeys.find((key) => Array.isArray(captionDetailsByPerspective[key]) && captionDetailsByPerspective[key].length > 0)
              || candidateKeys[0];
          }
          if (normalizedPreferenceType === "individual" && effectivePreferredTeamFromPlayer) {
            const candidateKeys = perspectiveKeysForTeam(effectivePreferredTeamFromPlayer);
            if (!candidateKeys.length) return "";
            return candidateKeys.find((key) => perspectives.includes(key))
              || candidateKeys.find((key) => Array.isArray(captionDetailsByPerspective[key]) && captionDetailsByPerspective[key].length > 0)
              || candidateKeys[0];
          }
          return "";
        })();
        const selectedEvidencePerspectiveKey = (() => {
          const key = extractEvidenceKeyFromFilename(selectedEvidenceResult?.filename);
          if (!key) return "";
          if (perspectives.includes(key)) return key;
          if (key === "man_city" && perspectives.includes("manchester_city")) return "manchester_city";
          return "";
        })();
        const fallbackSelectedPerspective = perspectives.find((key) => key !== "neutral") || "";
        const selectedPerspectiveKey = preferredPerspectiveKey || selectedEvidencePerspectiveKey || fallbackSelectedPerspective;

        const fallbackSelectedCaptionDetails = (
          Array.isArray(captionDetailsByPerspective[selectedPerspectiveKey]) && captionDetailsByPerspective[selectedPerspectiveKey].length > 0
            ? captionDetailsByPerspective[selectedPerspectiveKey]
            : applyPerClipAlignmentToCaptionRows(
              parseCaptionDetailRows(showcaseAlignmentPayload?.reel_a_captions),
              perClipAlignmentBySegment
            )
        );
        const fallbackNeutralCaptionDetails = (
          Array.isArray(captionDetailsByPerspective.neutral) && captionDetailsByPerspective.neutral.length > 0
            ? captionDetailsByPerspective.neutral
            : applyPerClipAlignmentToCaptionRows(
              parseCaptionDetailRows(showcaseAlignmentPayload?.reel_b_captions),
              perClipAlignmentBySegment
            )
        );

        const resolvedNeutralCaptionDetails = (
          fallbackNeutralCaptionDetails.length > 0
            ? fallbackNeutralCaptionDetails
            : neutralEvidenceRows
        );

        setHallucinationCueSignals(showcaseHallucinationSignals);
        setResult(buildShowcaseResult(showcaseData, {
          tone: autoTone,
          teamA,
          teamB,
          preferenceType,
          preferenceDetail: effectivePreferenceDetail,
          selectedAlignmentScore: fullEvalAlignment.selected ?? selectedEvidenceSummaryAlignment ?? showcaseAlignmentPayload?.reel_a_alignment_score,
          neutralAlignmentScore: fullEvalAlignment.neutral ?? neutralEvidenceSummaryAlignment ?? showcaseAlignmentPayload?.reel_b_alignment_score,
          selectedCaptionDetails: selectedEvidenceRows.length > 0 ? selectedEvidenceRows : fallbackSelectedCaptionDetails,
          neutralCaptionDetails: resolvedNeutralCaptionDetails,
          selectedPerspectiveKey,
          captionDetailsByPerspective,
        }));
        if (showcaseHallucinationAlert) {
          setHallucinationAlert(showcaseHallucinationAlert);
        }
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
              effectivePreferenceDetail,
              autoTone,
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
        const pipelineHallucinationCandidates = [
          {
            stream: "Verifier",
            ...extractHallucinationState(pipelineData),
          }
        ];
        const pipelineHallucinationSignals = buildHallucinationCueSignals(pipelineHallucinationCandidates);
        const pipelineHallucinationAlert = buildHallucinationAlertFromSignal(
          pipelineHallucinationSignals.find((item) => !item.segment_id) || null
        );
        setHallucinationCueSignals(pipelineHallucinationSignals);
        setResult(buildPipelineResult(
          pipelineData,
          sourceMode,
          teamA,
          teamB,
          matchInfo,
          youtubeUrl,
          preferenceType,
          effectivePreferenceDetail
        ));
        if (pipelineHallucinationAlert) {
          setHallucinationAlert(pipelineHallucinationAlert);
        }
      } else {
        await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS));
        setResult(buildMockResult(teamA, teamB, preferenceType, effectivePreferenceDetail, autoTone, matchInfo));
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

  const handleSpinPull = () => {
    if (isSpinningCard) return;
    if (hasUsedSpinForResult) return;
    if (!activePullPool.length) return;

    setIsSpinningCard(true);
    setHasUsedSpinForResult(true);
    setHasCollectedForResult(false);
    setRevealedPulledCard(null);
    const pulled = weightedPullCard(activePullPool);
    if (!pulled) {
      setIsSpinningCard(false);
      setHasUsedSpinForResult(false);
      return;
    }

    setTimeout(() => {
      const nextInventory = {
        ...cardPullInventory,
        [pulled.id]: (Number(cardPullInventory[pulled.id]) || 0) + 1
      };
      writeCardPullInventory(nextInventory);
      setCardPullInventory(nextInventory);

      const pulledWithMeta = {
        ...pulled,
        pulledAt: new Date().toISOString(),
        ownedCount: nextInventory[pulled.id] || 1
      };
      setLastPulledCard(pulledWithMeta);
      setRevealedPulledCard(pulledWithMeta);
      setIsSpinningCard(false);
    }, 1800);
  };

  const handleCollectPulledCard = () => {
    if (!revealedPulledCard) return;
    if (hasCollectedForResult) return;
    const reelVideoUrl = reelVideoBySetName[String(revealedPulledCard.setName || "").trim()] || "";
    const existingIndex = cardCollectionItems.findIndex((entry) => entry?.id === revealedPulledCard.id);

    if (existingIndex >= 0) {
      const nextCollection = cardCollectionItems.map((entry, idx) => {
        if (idx !== existingIndex) return entry;
        return {
          ...entry,
          quantity: Math.max(1, Number(entry?.quantity) || 1) + 1,
          caption: entry?.caption || entry?.moment || revealedPulledCard.caption || revealedPulledCard.moment,
          highlightScore: Number.isFinite(Number(entry?.highlightScore))
            ? normalizeHighlightScore(entry.highlightScore, 0.5)
            : normalizeHighlightScore(revealedPulledCard.highlightScore, 0.5),
          reelVideoUrl: entry?.reelVideoUrl || reelVideoUrl,
          lastCollectedAt: new Date().toISOString()
        };
      });
      writeCardCollection(nextCollection);
      setCardCollectionItems(nextCollection);
      setHasCollectedForResult(true);
      return;
    }

    const collectibleEntry = {
      id: revealedPulledCard.id,
      setId: revealedPulledCard.setId,
      setName: revealedPulledCard.setName,
      cardIndex: revealedPulledCard.cardIndex,
      rarity: revealedPulledCard.rarity,
      rarityLabel: revealedPulledCard.rarityLabel,
      caption: revealedPulledCard.caption || revealedPulledCard.moment,
      moment: revealedPulledCard.moment,
      highlightScore: normalizeHighlightScore(revealedPulledCard.highlightScore, 0.5),
      quantity: 1,
      reelVideoUrl,
      collectedAt: new Date().toISOString()
    };

    const nextCollection = [collectibleEntry, ...cardCollectionItems].slice(0, CARD_COLLECTION_LIMIT);
    writeCardCollection(nextCollection);
    setCardCollectionItems(nextCollection);
    setHasCollectedForResult(true);
  };

  const liveBannerWeatherText = (() => {
    if (!widgetMatch) return "Select a match for live weather.";
    if (weatherLoading) return "Weather: loading...";
    if (weatherError) return "Weather unavailable";
    if (!weatherData) return "Weather pending";
    return `${weatherLabelFromCode(weatherData.weatherCode)} ${weatherData.temperature ?? "-"}°C`;
  })();

  const liveBannerCommentaryText = (() => {
    if (!widgetMatch) return "Waiting for live match data.";
    if (backendFeedError) return backendFeedError;
    return liveCommentary[0] || "Live commentary warming up...";
  })();

  return (
    <div className="generator-shell">
      {hallucinationAlert && (
        <div className="factual-alert-toast hallucination-alert-toast" role="status" aria-live="polite">
          <div className="factual-alert-row">
            <p className="factual-alert-title hallucination-alert-title">Hallucination Check Triggered</p>
            <button
              type="button"
              className="factual-alert-dismiss"
              onClick={() => setHallucinationAlert(null)}
            >
              Dismiss
            </button>
          </div>
          <p className="factual-alert-meta hallucination-alert-meta">
            {hallucinationAlert.stream || "Verifier"}
            {Number.isFinite(hallucinationAlert.cueIndex)
              ? ` • Cue #${Number(hallucinationAlert.cueIndex) + 1}`
              : ""}
            {hallucinationAlert.segment_id
              ? ` • ${hallucinationAlert.segment_id}`
              : ""}
            {Number.isFinite(hallucinationAlert.retryCount)
              ? ` • Retries ${Number(hallucinationAlert.retryCount)}`
              : ""}
            {Number.isFinite(hallucinationAlert.totalHallucinationsDetected)
              ? ` • Flagged ${Number(hallucinationAlert.totalHallucinationsDetected)}`
              : ""}
          </p>
          <p className="factual-alert-caption">{hallucinationAlert.caption}</p>
        </div>
      )}
      {factualInconsistencyAlert && (
        <div className="factual-alert-toast" role="status" aria-live="polite">
          <div className="factual-alert-row">
            <p className="factual-alert-title">Disagreement Challenge Triggered</p>
            <button
              type="button"
              className="factual-alert-dismiss"
              onClick={() => setFactualInconsistencyAlert(null)}
            >
              Dismiss
            </button>
          </div>
          <p className="factual-alert-meta">
            {factualInconsistencyAlert.stream} cue
            {Number.isFinite(factualInconsistencyAlert.cueIndex) ? ` #${Number(factualInconsistencyAlert.cueIndex) + 1}` : ""}
            {Number.isFinite(factualInconsistencyAlert.importance)
              ? ` • Importance ${formatConfidenceLabel(factualInconsistencyAlert.importance)}`
              : ""}
            {" "}• Consistency {formatConfidenceLabel(factualInconsistencyAlert.alignment)}
            {Number.isFinite(factualInconsistencyAlert.disagreement)
              ? ` • Disagreement ${(factualInconsistencyAlert.disagreement * 100).toFixed(2)}%`
              : ""}
          </p>
          <p className="factual-alert-caption">{factualInconsistencyAlert.caption}</p>
        </div>
      )}
      <header className="espn-header" aria-label="Recent EPL matches">
        <div className="espn-topbar">
          <div className="espn-brand">MGAI MATCHCENTER</div>
          <div className="espn-live-center" aria-label="Live centre widgets">
            <section className="espn-live-widget espn-live-weather-widget" aria-label="Weather broadcast">
              <p className="espn-live-widget-title">Weather Broadcast</p>
              <p className="espn-live-matchline">
                {widgetMatch
                  ? `${widgetMatch.home} ${widgetMatch.homeScore ?? "-"} - ${widgetMatch.awayScore ?? "-"} ${widgetMatch.away}`
                  : "Live Match"}
              </p>
              <p className="espn-live-weather">{liveBannerWeatherText}</p>
              <p className="espn-live-weather">Updated: {commentaryUpdatedAt || "Now"}</p>
            </section>
            <section className="espn-live-widget espn-live-highlight-widget" aria-label="Current match highlights">
              <p className="espn-live-widget-title">Current Match Highlights</p>
              <p className="espn-live-commentary">{liveBannerCommentaryText}</p>
            </section>
          </div>
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
            <option value="teams">Team Selection</option>
            <option value="youtube">YouTube Link</option>
            <option value="text">Custom Text Prompt</option>
          </select>
        </div>
      </div>

      {sourceMode === "teams" ? (
        <>
          <div className="select-block">
            <label className="select-label">Home Team</label>
            <div className="select-wrap">
              <select
                className="fifa-select"
                value={teamA}
                onChange={(e) => setTeamA(e.target.value)}
              >
                <option value="">Select Home Team</option>
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
                <label className="select-label">Away Team</label>
                <div className="select-wrap">
                  <select
                    className="fifa-select"
                    value={teamB}
                    onChange={(e) => setTeamB(e.target.value)}
                  >
                    <option value="">Select Away Team</option>
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
            placeholder="Type what you want to focus on in football. The pipeline will extract football entities and return the best available highlights."
          />
          {sourcePrompt.trim() && (
            <p className="output-context" style={{ marginTop: "10px", marginBottom: "0" }}>
              Prompt detection: {teamA && teamB
                ? `${teamA} vs ${teamB}`
                : (teamA || "No clear matchup detected yet")}
              {String(preferenceType || "").toLowerCase() === "team" && preferenceDetail
                ? ` | Preferred: ${preferenceDetail}`
                : ""}
            </p>
          )}
        </div>
      )}

      {sourceMode !== "text" && hasValidSource && (
        <div className="select-block">
          <label className="select-label">Preference Type</label>
          <div className="preference-type-toggle" role="radiogroup" aria-label="Preference type">
            {preferenceTypeOptions.map((option) => {
              const isSelected = preferenceType === option;
              return (
                <button
                  key={option}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  className={`preference-type-btn${isSelected ? " active" : ""}`}
                  onClick={() => {
                    if (isSelected) return;
                    setPreferenceType(option);
                    setPreferenceDetail("");
                  }}
                >
                  {option === "team" ? "Team" : "Individual"}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {sourceMode !== "text" && preferenceType && (
        <div className="select-block">
          <label className="select-label">{preferenceType === "team" ? "Preferred Team" : "Preferred Player"}</label>
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
                <option value="">{preferenceType === "team" ? "Select preferred team" : "Select preferred player"}</option>
                {detailOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </div>
          )}
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

      </div>
      {error && <div className="generator-error">{error}</div>}

      {result && (
        <>
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

          <div className="reels-grid">
            {result.reels.map((reel) => (
              <article key={reel.side} className="reel-panel">
                <header className="reel-header">
                  <span className="reel-side">{reel.side}</span>
                  <h3>{reel.title}</h3>
                </header>

                {String(reel.logo || "").trim() && String(reel.logo || "").trim() !== FALLBACK_TEAM_LOGO && (
                  <div className="reel-badge-wrap">
                    <TeamFoilBadge logoSrc={reel.logo} teamName={reel.teamName} size={REEL_BADGE_SIZE} speed="12s" />
                  </div>
                )}

                <div className="reel-feed-status">Live pull: Active</div>

                <ReelVideoWithTimedCaptions
                  reel={reel}
                  onActiveCaptionChange={(payload) => {
                    const key = buildReelCaptionKey(reel);
                    const text = String(payload?.text || "");
                    const index = Number.isFinite(Number(payload?.index)) ? Number(payload.index) : -1;
                    setLiveReelCaptions((prev) => {
                      if (prev[key] === text) return prev;
                      return { ...prev, [key]: text };
                    });
                    setLiveReelCaptionIndices((prev) => {
                      if (prev[key] === index) return prev;
                      return { ...prev, [key]: index };
                    });
                  }}
                />
              </article>
            ))}
          </div>

          <div className="commentary-box below-reel-commentary">
            {hasNeutralDiffComparison ? (
              <>
                <p className="commentary-current-compare">
                  <span className="commentary-compare-label">Selected</span>
                  <span className="commentary-compare-score">Alignment {formatConfidenceLabel(selectedCommentaryConfidence)}</span>
                  {selectedCommentaryDisplay}
                </p>
                <p className="commentary-neutral-compare">
                  <span className="commentary-compare-label">Neutral</span>
                  <span className="commentary-compare-score">Alignment {formatConfidenceLabel(neutralCommentaryConfidence)}</span>
                  {neutralCommentaryDisplay}
                </p>
              </>
            ) : (
              <p>{selectedCommentaryDisplay}</p>
            )}
          </div>
        </section>

          {reelSetCatalog.sets.length > 0 && (
            <section className="pokemon-card-section pokemon-card-section-standalone">
              <h3>Reel Highlight Cards</h3>
              <p className="output-context" style={{ marginTop: "6px", marginBottom: "10px" }}>
                Spin first, reveal after, then collect.
              </p>

              <div className="collectible-meta-row" aria-label="Selected reel metadata">
                <span className="collectible-chip">{selectedReelSet?.name || "No Set"}</span>
                <span className="collectible-chip">Total {selectedReelSet?.cardCount || 0}</span>
                <span className="collectible-chip">Owned {selectedSetOwnedCount}/{selectedReelSet?.cardCount || 0}</span>
              </div>

              <div className="spin-stage">
                {!isSpinningCard && !revealedPulledCard && (
                  <div className="spin-placeholder">Spin to reveal card</div>
                )}

                {isSpinningCard && (
                  <div className="spin-spinner-wrap" aria-live="polite">
                    <div className="spin-spinner" />
                    <p>Spinning...</p>
                  </div>
                )}

                {!isSpinningCard && revealedPulledCard && (
                  <div className="spin-reveal-card-wrap">
                    {result?.pokemonCardUrl ? (
                      <div className={`pokemon-card-shell rarity-${revealedPulledCard.rarity}`}>
                        {isSvgAssetUrl(result.pokemonCardUrl) ? (
                          <object
                            className="pokemon-card-image"
                            type="image/svg+xml"
                            data={result.pokemonCardUrl}
                            aria-label="Generated recap wallpaper card"
                          />
                        ) : (
                          <img className="pokemon-card-image" src={result.pokemonCardUrl} alt="Generated recap wallpaper card" />
                        )}
                        {spinFeatureVideo && (
                          <div className="pokemon-card-feature-window" aria-hidden="true">
                            <video
                              className="pokemon-card-feature-video"
                              src={spinFeatureVideo}
                              autoPlay
                              muted
                              loop
                              playsInline
                            />
                          </div>
                        )}
                        <span className="pokemon-card-holo" aria-hidden="true" />
                        <span className="pokemon-card-glint" aria-hidden="true" />
                      </div>
                    ) : (
                      <article className={`pulled-highlight-card rarity-${revealedPulledCard.rarity}`}>
                        <div className="pulled-highlight-shell">
                          <span className="pulled-highlight-holo" aria-hidden="true" />
                          <span className="pulled-highlight-glint" aria-hidden="true" />
                          <header className="pulled-highlight-top">
                            <span className={`collectible-chip rarity-chip rarity-${revealedPulledCard.rarity}`}>
                              {revealedPulledCard.rarityLabel}
                            </span>
                            <span className="pulled-highlight-number">
                              Card {String(revealedPulledCard.cardIndex).padStart(2, "0")}
                            </span>
                          </header>
                          <div className="pulled-highlight-title-row">
                            <h4>{revealedPulledCard.setName}</h4>
                            <span className="pulled-highlight-set-code">{buildCardSetCode(revealedPulledCard.setName)}</span>
                          </div>
                          <div className="pulled-highlight-body">
                            <p>{revealedPulledCard.caption || revealedPulledCard.moment}</p>
                          </div>
                        </div>
                      </article>
                    )}

                    <div className="spin-reveal-meta">
                      <span className={`collectible-chip rarity-chip rarity-${revealedPulledCard.rarity}`}>
                        {revealedPulledCard.rarityLabel}
                      </span>
                      <span className="collectible-chip">Card {String(revealedPulledCard.cardIndex).padStart(2, "0")}</span>
                      <span className="collectible-chip">{revealedPulledCard.setName}</span>
                      <span className="collectible-chip">Score {normalizeHighlightScore(revealedPulledCard.highlightScore, 0.5).toFixed(2)}</span>
                    </div>
                    <p className="spin-reveal-moment">Pulled highlight: {revealedPulledCard.caption || revealedPulledCard.moment}</p>
                  </div>
                )}
              </div>

              <div className="spin-button-row">
                <button
                  type="button"
                  className="generate-btn reel-spin-btn"
                  onClick={handleSpinPull}
                  disabled={!activePullPool.length || isSpinningCard || hasUsedSpinForResult}
                >
                  {isSpinningCard ? "Spinning..." : (hasUsedSpinForResult ? "Spin Used - Regenerate" : "Spin for Card")}
                </button>
                {revealedPulledCard && (
                  <button
                    type="button"
                    className="pokemon-card-link collect-btn"
                    onClick={handleCollectPulledCard}
                    disabled={hasCollectedForResult}
                  >
                    {hasCollectedForResult ? "Collected This Round" : (() => {
                      const existingQty = Math.max(
                        0,
                        Number(
                          cardCollectionItems.find((entry) => entry?.id === revealedPulledCard.id)?.quantity
                        ) || 0
                      );
                      return existingQty > 0 ? `Collect +1 (Current ${existingQty}x)` : "Collect Card";
                    })()}
                  </button>
                )}
                {revealedPulledCard && result?.pokemonCardUrl && (
                  <a className="pokemon-card-link" href={result.pokemonCardUrl} target="_blank" rel="noreferrer">
                    Open Card
                  </a>
                )}
                {revealedPulledCard && result?.pokemonCardUrl && (
                  <a
                    className="pokemon-card-link download"
                    href={result.pokemonCardUrl}
                    download={result.pokemonCardFilename || "generated_recap_card.svg"}
                  >
                    Download Card
                  </a>
                )}
              </div>
              {hasUsedSpinForResult && (
                <p className="spin-lock-note">One spin used for this run. Click Generate again to spin another card.</p>
              )}
              {hasCollectedForResult && (
                <p className="spin-lock-note">One collect used for this run. Click Generate to collect again.</p>
              )}

              {cardCollectionItems.length > 0 && (
                <section className="my-collection-section" aria-label="My collectible cards">
                  <div className="my-collection-header">
                    <h4>My Collection</h4>
                    <span>{cardCollectionCount} cards</span>
                  </div>
                  <div className="my-collection-grid">
                    {cardCollectionItems.map((card, index) => {
                      const rarityKey = String(card?.rarity || "common").toLowerCase();
                      const cardNumber = String(card?.cardIndex || "").padStart(2, "0");
                      const isLatest = String(revealedPulledCard?.id || "") === String(card?.id || "");
                      const quantity = Math.max(1, Number(card?.quantity) || 1);
                      const collectionVideoUrl = String(
                        card?.reelVideoUrl
                        || reelVideoBySetName[String(card?.setName || "").trim()]
                        || spinFeatureVideo
                        || ""
                      ).trim();
                      return (
                        <article
                          key={String(card?.id || `${card?.setId}-${card?.cardIndex}-${index}`)}
                          className={`collection-mini-card rarity-${rarityKey}${isLatest ? " latest" : ""}`}
                        >
                          <div className="collection-mini-shell">
                            <span className="collection-mini-holo" aria-hidden="true" />
                            <span className="collection-mini-glint" aria-hidden="true" />
                            <header className="collection-mini-top">
                              <span className={`collectible-chip rarity-chip rarity-${rarityKey}`}>
                                {String(card?.rarityLabel || card?.rarity || "Unknown")}
                              </span>
                              <span className="collection-mini-no">#{cardNumber}</span>
                            </header>
                            {quantity > 1 && <span className="collection-mini-qty">{quantity}x</span>}
                            <div className="collection-mini-title-row">
                              <h5>{String(card?.setName || "Set")}</h5>
                            </div>
                            <div className={`collection-mini-preview${collectionVideoUrl ? "" : " placeholder"}`}>
                              {collectionVideoUrl && (
                                <video
                                  className="collection-mini-video"
                                  src={collectionVideoUrl}
                                  autoPlay
                                  muted
                                  loop
                                  playsInline
                                  preload="metadata"
                                />
                              )}
                            </div>
                            <div className="collection-mini-body">
                              <p className="collection-mini-moment">{String(card?.caption || card?.moment || "")}</p>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </section>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

