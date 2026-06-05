import type { LiveMatchResponse, Match, MatchCenter } from "@/types/cricket";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
// Poll every 30 s — ESPN responses are cached server-side for 30 s (live) or 120 s (completed).
const POLL_MS = Number(process.env.NEXT_PUBLIC_POLL_INTERVAL_MS || 30000);

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      throw new Error(`Backend ${path} failed with ${response.status}`);
    }

    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getLiveMatchSlots(): Promise<LiveMatchResponse> {
  const fetchedAt = new Date().toISOString();

  try {
    const matches = await backendFetch<Match[]>("/api/matches/current");
    const live = pickLiveMatch(matches);
    const recent = pickRecentMatch(matches, live?.id);
    const upcoming = pickUpcomingMatch(matches, live?.id, recent?.id);

    const [liveMatch, recentMatch, upcomingMatch] = await Promise.all([
      live ? getCenterOrNull(live.id) : null,
      recent ? getCenterOrNull(recent.id) : null,
      upcoming ? getCenterOrNull(upcoming.id) : null,
    ]);

    return {
      liveMatch,
      recentMatch,
      upcomingMatch,
      fetchedAt,
    };
  } catch {
    return emptyResponse(fetchedAt);
  }
}

async function getCenterOrNull(matchId: string): Promise<MatchCenter | null> {
  try {
    return await backendFetch<MatchCenter>(`/api/matches/${matchId}/center`);
  } catch {
    return null;
  }
}

function pickLiveMatch(matches: Match[]): Match | null {
  return matches.find((match) => isLive(match)) || null;
}

function pickRecentMatch(matches: Match[], excludedId?: string): Match | null {
  return matches
    .filter((match) => match.id !== excludedId && isCompleted(match))
    .sort((a, b) => dateValue(b.start_time_utc) - dateValue(a.start_time_utc))[0] || null;
}

function pickUpcomingMatch(matches: Match[], ...excludedIds: Array<string | undefined>): Match | null {
  const excluded = new Set(excludedIds.filter(Boolean));
  return (
    matches
      .filter((match) => !excluded.has(match.id) && isUpcoming(match))
      .sort((a, b) => dateValue(a.start_time_utc) - dateValue(b.start_time_utc))[0] || null
  );
}

function isCompleted(match: Match): boolean {
  const combined = normalizeStatus(`${match.status} ${match.result_summary || ""}`);
  return (
    combined.includes("won") ||
    combined.includes("wkt") ||
    combined.includes("run") ||
    combined.includes("complete") ||
    combined.includes("finished") ||
    combined.includes("result") ||
    combined.includes("abandoned") ||
    combined.includes("no result") ||
    combined.includes("drawn") ||
    combined.includes("tied")
  );
}

function isUpcoming(match: Match): boolean {
  const status = normalizeStatus(match.status);
  // Exclude matches that are clearly live or completed
  if (isLive(match) || isCompleted(match)) return false;
  if (
    status.includes("upcoming") ||
    status.includes("scheduled") ||
    status.includes("not started") ||
    status.includes("starts") ||
    status.includes("match starts")
  ) {
    return true;
  }
  // Future date with no result = upcoming
  return dateValue(match.start_time_utc) > Date.now();
}

function isLive(match: Match): boolean {
  const status = normalizeStatus(match.status);
  return (
    status.includes("live") ||
    status.includes("in progress") ||
    // ESPN status like "CSK need 38 from 21 balls"
    (status.includes("need") && status.includes("balls"))
  );
}

function normalizeStatus(value: string) {
  return value.toLowerCase();
}

function dateValue(value?: string | null) {
  if (!value) return 0;
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? 0 : time;
}

function emptyResponse(fetchedAt: string): LiveMatchResponse {
  return {
    liveMatch: null,
    recentMatch: null,
    upcomingMatch: null,
    fetchedAt,
  };
}
