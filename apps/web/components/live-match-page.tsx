"use client";

import {
  Activity,
  Award,
  CalendarClock,
  ChevronRight,
  Clock3,
  Gauge,
  Radio,
  RefreshCcw,
  Shield,
  Swords,
  Trophy,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { AlertTriangle, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

import type {
  CommentaryBall,
  InningsScore,
  LiveMatchResponse,
  MatchCenter,
  OverForecast,
  Team,
} from "@/types/cricket";

const pollMs = Number(process.env.NEXT_PUBLIC_POLL_INTERVAL_MS || 15000);

type MatchKind = "live" | "recent" | "upcoming" | "empty";

type Props = {
  initialData: LiveMatchResponse;
};

export function LiveMatchPage({ initialData }: Props) {
  const [data, setData] = useState(initialData);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);
  const [selectedKind, setSelectedKind] = useState<MatchKind>(() =>
    getDefaultKind(initialData)
  );

  async function refresh() {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/live/match", { cache: "no-store" });
      const nextData = (await response.json()) as LiveMatchResponse;
      setData(nextData);
      setPollError(null);
    } catch {
      setPollError("Connection lost — retrying...");
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = window.setInterval(() => {
      refresh().catch(console.error);
    }, pollMs);
    return () => window.clearInterval(timer);
  }, []);

  // Auto-switch selectedKind when a live match appears
  useEffect(() => {
    if (data.liveMatch && selectedKind !== "live") setSelectedKind("live");
  }, [data.liveMatch]);

  const center = getCenterFor(data, selectedKind);
  const matchKind: MatchKind = center ? selectedKind : "empty";
  const isSimulation = center?.data_mode === "simulation";
  const isESPN = center?.data_mode === "espn";

  const [selectedTab, setSelectedTab] = useState<"commentary" | "scorecard" | "squads">(
    defaultTabForKind(matchKind)
  );

  useEffect(() => {
    setSelectedTab(defaultTabForKind(matchKind));
  }, [matchKind]);

  return (
    <main className="min-h-screen">
      <TopBar
        fetchedAt={data.fetchedAt}
        isRefreshing={isRefreshing}
        onRefresh={refresh}
        isSimulation={isSimulation}
        isESPN={isESPN}
      />

      {pollError && (
        <div className="mx-auto flex max-w-[1480px] items-center justify-between gap-3 rounded-b-lg bg-amber-50 px-4 py-2 text-sm text-amber-800">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {pollError}
          </span>
          <button onClick={() => setPollError(null)} type="button" className="rounded p-1 hover:bg-amber-100">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {isSimulation && (
        <div className="simulation-banner mx-auto max-w-[1480px] px-3 pt-3">
          <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 px-4 py-3">
            <div className="sim-pulse-dot h-3 w-3 rounded-full bg-amber-500" />
            <div className="flex-1">
              <p className="text-sm font-black text-amber-900">
                ⚡ Simulation Mode — no API key configured
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                Set{" "}
                <code className="rounded bg-amber-100 px-1 font-mono">CRICAPI_API_KEY</code> in{" "}
                <code className="rounded bg-amber-100 px-1 font-mono">.env</code> for real data · ESPN real data is active by default
              </p>
            </div>
            <Zap className="h-5 w-5 text-amber-600 shrink-0" />
          </div>
        </div>
      )}

      {isESPN && (
        <div className="mx-auto max-w-[1480px] px-3 pt-3">
          <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 px-4 py-3">
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <p className="flex-1 text-xs text-emerald-800">
              <span className="font-black">Real IPL data</span> sourced from ESPN Cricinfo · updates every 15–30s · no API key required
            </p>
          </div>
        </div>
      )}

      <div className="mx-auto grid max-w-[1480px] grid-cols-1 gap-4 px-3 py-4 md:px-5 xl:grid-cols-[300px_minmax(0,1fr)_380px]">
        <MatchRail
          activeKind={matchKind}
          selectedKind={selectedKind}
          data={data}
          onSelect={setSelectedKind}
        />

        {center ? (
          <>
            <section className="min-w-0 space-y-4">
              <ScoreHero center={center} matchKind={matchKind} isSimulation={isSimulation} />
              <ContextStrip center={center} />
              {matchKind === "recent" && <RecentMatchSummary center={center} />}
              {matchKind === "upcoming" && <UpcomingMatchSummary center={center} />}
              <Tabs selectedTab={selectedTab} onSelect={setSelectedTab} />
              <section className="rounded-xl border border-line bg-white shadow-panel overflow-hidden">
                {selectedTab === "commentary" && <CommentaryPanel center={center} />}
                {selectedTab === "scorecard" && <ScorecardPanel innings={center.innings} />}
                {selectedTab === "squads" && <SquadsPanel center={center} />}
              </section>
            </section>

            <aside className="space-y-4 xl:sticky xl:top-[84px] xl:max-h-[calc(100vh-96px)] xl:overflow-auto">
              {matchKind !== "recent" && <PredictionPanel forecast={center.forecast} />}
              <CurrentPlayers center={center} />
            </aside>
          </>
        ) : (
          <EmptyLiveState />
        )}
      </div>
    </main>
  );
}

function TopBar({
  fetchedAt,
  isRefreshing,
  onRefresh,
  isSimulation,
  isESPN,
}: {
  fetchedAt: string;
  isRefreshing: boolean;
  onRefresh: () => void;
  isSimulation: boolean;
  isESPN: boolean;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-brand-900 text-white">
      <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 font-black text-white shadow-lg">
            CA
          </div>
          <div>
            <p className="font-black leading-tight">CricketAI</p>
            <p className="text-xs text-emerald-200">Live Match Centre</p>
          </div>
        </div>

        <nav className="flex items-center gap-2 text-sm text-emerald-50">
          <Link className="rounded-lg px-3 py-2 font-semibold hover:bg-white/10 transition-colors" href="/">
            Live
          </Link>
        </nav>

        <div className="flex items-center gap-3 text-sm text-emerald-50">
          {isSimulation && (
            <span className="flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-500/20 px-3 py-1 text-xs font-black text-amber-200">
              <span className="sim-pulse-dot h-2 w-2 rounded-full bg-amber-400" />
              SIM
            </span>
          )}
          {isESPN && (
            <span className="flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/20 px-3 py-1 text-xs font-black text-emerald-200">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              ESPN LIVE
            </span>
          )}
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_0_5px_rgba(110,231,183,0.16)]" />
            {formatTime(fetchedAt)}
          </span>
          <button
            className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-white/10 px-3 font-semibold hover:bg-white/20 transition-colors"
            onClick={onRefresh}
            type="button"
          >
            <RefreshCcw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>
    </header>
  );
}

function MatchRail({
  data,
  activeKind,
  selectedKind,
  onSelect,
}: {
  data: LiveMatchResponse;
  activeKind: MatchKind;
  selectedKind: MatchKind;
  onSelect: (kind: MatchKind) => void;
}) {
  const cards: [MatchKind, MatchCenter | null][] = [
    ["live", data.liveMatch],
    ["recent", data.recentMatch],
    ["upcoming", data.upcomingMatch],
  ];
  const visibleCards = cards.filter(([, center]) => Boolean(center));

  return (
    <aside className="xl:sticky xl:top-[84px] xl:self-start">
      <div className="mb-3 flex items-center justify-between">
        <h1 className="text-lg font-black">Matches</h1>
        <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-black text-brand-700">
          {visibleCards.length}
        </span>
      </div>
      <div className="grid gap-3">
        {visibleCards.length ? (
          visibleCards.map(([kind, center]) => {
            const isSelected = selectedKind === kind;
            const isLive = kind === "live";
            return (
              <button
                key={kind}
                onClick={() => onSelect(kind)}
                type="button"
                className={`w-full text-left rounded-xl border p-4 shadow-panel transition-all duration-200 hover:scale-[1.01] hover:shadow-lg ${
                  isSelected
                    ? "border-brand-500 bg-gradient-to-br from-brand-50 to-emerald-50 ring-1 ring-brand-300"
                    : "border-line bg-white hover:border-brand-200"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <StatusPill status={center!.match.status} />
                  {isSelected && <ChevronRight className="h-4 w-4 text-brand-500 mt-0.5 shrink-0" />}
                </div>
                <p className="mt-3 font-black leading-snug text-sm">{center!.match.name}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted line-clamp-2">
                  {summaryFor(kind, center!)}
                </p>
                <div className="mt-3 grid gap-1.5 text-xs text-muted">
                  <span className="flex items-center gap-1.5">
                    <Trophy className="h-3.5 w-3.5 shrink-0" />
                    {center!.match.series || "Series unavailable"}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <CalendarClock className="h-3.5 w-3.5 shrink-0" />
                    {formatDate(center!.match.start_time_utc)}
                  </span>
                </div>
              </button>
            );
          })
        ) : (
          <div className="rounded-xl border border-line bg-white p-4 shadow-panel">
            <p className="text-sm leading-relaxed text-muted">No matches available.</p>
          </div>
        )}
      </div>
    </aside>
  );
}

function ScoreHero({
  center,
  matchKind,
  isSimulation,
}: {
  center: MatchCenter;
  matchKind: MatchKind;
  isSimulation: boolean;
}) {
  const [batting, bowling] = heroTeams(center);
  const winProb = center.forecast?.win_probability ?? null;
  const battingWin = winProb !== null ? Math.round(winProb * 100) : null;
  const bowlingWin = battingWin !== null ? 100 - battingWin : null;

  // Current players from state
  const striker = center.state.striker;
  const nonStriker = center.state.non_striker;
  const bowler = center.state.bowler;
  const strikerCard = center.innings[0]?.batting.find(b => b.is_batting);
  const nonStrikerCard = center.innings[0]?.batting.filter(b => b.is_batting)[1];
  const bowlerCard = center.innings[0]?.bowling.at(-1);

  const isLive = matchKind === "live";

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-white shadow-panel">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-gradient-to-r from-[#f7f9f6] to-emerald-50 px-4 py-3">
        <div>
          <p className="font-black">{center.match.series || "Live Cricket"}</p>
          <p className="text-sm text-muted">{center.match.match_number || center.match.venue}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={center.match.status} isLiveGlow={isSimulation && matchKind === "live"} />
        </div>
      </div>

      {/* Toss info */}
      {center.match.status && center.match.status.toLowerCase().includes("toss") && (
        <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs font-black text-amber-800">
          🏏 {center.match.status}
        </div>
      )}

      {/* Score area */}
      <div className="grid gap-4 px-5 pt-5 pb-3 md:grid-cols-2">
        <TeamScoreBlock innings={batting.innings} team={batting.team} side="batting" />
        <TeamScoreBlock alignRight innings={bowling.innings} team={bowling.team} side="bowling" />
      </div>

      {/* Win probability bar */}
      {battingWin !== null && bowlingWin !== null && (
        <div className="mx-4 mb-3">
          <div className="mb-1 flex items-center justify-between text-xs font-black">
            <span className="text-brand-700">{batting.team?.short_name || batting.team?.name} {battingWin}%</span>
            <span className="text-rose-700">{bowling.team?.short_name || bowling.team?.name} {bowlingWin}%</span>
          </div>
          <div className="flex h-2.5 overflow-hidden rounded-full">
            <div
              className="bg-gradient-to-r from-brand-600 to-emerald-500 transition-all duration-700"
              style={{ width: `${battingWin}%` }}
            />
            <div
              className="bg-gradient-to-r from-rose-500 to-red-700 transition-all duration-700"
              style={{ width: `${bowlingWin}%` }}
            />
          </div>
        </div>
      )}

      {/* Current batsmen + bowler mini-table (live only) */}
      {isLive && (strikerCard || bowlerCard) && (
        <div className="mx-4 mb-4 overflow-x-auto rounded-xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-teal-50">
          <table className="w-full min-w-[400px] text-sm">
            <thead className="text-left text-xs font-black uppercase text-muted border-b border-emerald-100">
              <tr>
                <th className="px-3 py-2 w-[40%]">Batter</th>
                <th className="px-3 py-2 text-right">R</th>
                <th className="px-3 py-2 text-right">B</th>
                <th className="px-3 py-2 text-right">4s</th>
                <th className="px-3 py-2 text-right">6s</th>
                <th className="px-3 py-2 text-right">SR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-emerald-100">
              {strikerCard && (
                <tr className="bg-emerald-50/80">
                  <td className="px-3 py-2 font-black">
                    {strikerCard.player.name}
                    <span className="ml-1 text-brand-600">*</span>
                  </td>
                  <td className="px-3 py-2 text-right font-black text-base">{strikerCard.runs}</td>
                  <td className="px-3 py-2 text-right text-muted">{strikerCard.balls}</td>
                  <td className="px-3 py-2 text-right">{strikerCard.fours}</td>
                  <td className="px-3 py-2 text-right">{strikerCard.sixes}</td>
                  <td className="px-3 py-2 text-right">{strikerCard.strike_rate.toFixed(1)}</td>
                </tr>
              )}
              {nonStrikerCard && (
                <tr>
                  <td className="px-3 py-2 font-black">{nonStrikerCard.player.name}</td>
                  <td className="px-3 py-2 text-right font-black">{nonStrikerCard.runs}</td>
                  <td className="px-3 py-2 text-right text-muted">{nonStrikerCard.balls}</td>
                  <td className="px-3 py-2 text-right">{nonStrikerCard.fours}</td>
                  <td className="px-3 py-2 text-right">{nonStrikerCard.sixes}</td>
                  <td className="px-3 py-2 text-right">{nonStrikerCard.strike_rate.toFixed(1)}</td>
                </tr>
              )}
            </tbody>
          </table>
          {bowlerCard && (
            <table className="w-full min-w-[400px] text-sm border-t border-emerald-200">
              <thead className="text-left text-xs font-black uppercase text-muted bg-teal-50/60">
                <tr>
                  <th className="px-3 py-2 w-[40%]">Bowler</th>
                  <th className="px-3 py-2 text-right">O</th>
                  <th className="px-3 py-2 text-right">M</th>
                  <th className="px-3 py-2 text-right">R</th>
                  <th className="px-3 py-2 text-right">W</th>
                  <th className="px-3 py-2 text-right">ER</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-3 py-2 font-black">{bowlerCard.player.name}</td>
                  <td className="px-3 py-2 text-right">{bowlerCard.overs}</td>
                  <td className="px-3 py-2 text-right">{bowlerCard.maidens}</td>
                  <td className="px-3 py-2 text-right">{bowlerCard.runs}</td>
                  <td className="px-3 py-2 text-right font-black">{bowlerCard.wickets}</td>
                  <td className="px-3 py-2 text-right">{bowlerCard.economy.toFixed(2)}</td>
                </tr>
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Status bar */}
      <div className="mx-4 mb-5 rounded-xl border border-emerald-100 bg-gradient-to-br from-brand-50 to-teal-50 p-4 text-center">
        <p className="font-black text-brand-700">
          {matchKind === "upcoming" ? "Upcoming match details" : center.status_line}
        </p>
        <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
          {matchKind === "upcoming" ? (
            <>
              <Metric label="Date" value={formatShortDate(center.match.start_time_utc)} />
              <Metric label="Time" value={formatShortTime(center.match.start_time_utc)} />
              <Metric label="Venue" value={center.match.venue ? "Ready" : "-"} />
            </>
          ) : (
            <>
              <Metric label="CRR" value={center.state.current_run_rate.toFixed(2)} />
              <Metric label="RRR" value={center.state.required_run_rate?.toFixed(2) || "-"} />
              <Metric label="Balls" value={center.state.balls_remaining ?? "-"} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function TeamScoreBlock({
  team,
  innings,
  alignRight = false,
  side = "batting",
}: {
  team?: Team;
  innings?: InningsScore;
  alignRight?: boolean;
  side?: "batting" | "bowling";
}) {
  const gradient =
    side === "bowling"
      ? "bg-gradient-to-br from-rose-700 to-red-900 md:order-last"
      : "bg-gradient-to-br from-brand-700 to-teal-800";
  return (
    <div className={`flex items-center gap-3 ${alignRight ? "md:justify-end md:text-right" : ""}`}>
      <div
        className={`grid h-16 w-16 shrink-0 place-items-center rounded-xl font-black text-white text-sm shadow-md ${gradient}`}
      >
        {team?.short_name || initials(team?.name)}
      </div>
      <div className="min-w-0">
        <h2 className="truncate text-base font-black">{team?.name || "Team"}</h2>
        <p className="text-3xl font-black tracking-tight">
          {innings ? `${innings.runs}/${innings.wickets}` : "Yet to bat"}
        </p>
        <p className="text-sm text-muted">
          {innings ? `${innings.overs} overs` : side === "bowling" ? "Bowling" : "Waiting"}
        </p>
      </div>
    </div>
  );
}

function ContextStrip({ center }: { center: MatchCenter }) {
  return (
    <section className="grid gap-3 md:grid-cols-3">
      <InfoTile icon={<Shield />} label="Batting" value={center.state.batting_team.name} />
      <InfoTile icon={<Swords />} label="Bowling" value={center.state.bowling_team.name} />
      <InfoTile icon={<Clock3 />} label="Venue" value={center.match.venue || "Venue unavailable"} />
    </section>
  );
}

function RecentMatchSummary({ center }: { center: MatchCenter }) {
  const performers = topPerformers(center);

  return (
    <section className="rounded-xl border border-line bg-white p-5 shadow-panel">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-black">Last Completed Match</h2>
          <p className="mt-1 text-sm text-muted">{center.match.result_summary || center.status_line}</p>
        </div>
        <StatusPill status={center.match.status} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {center.innings.map((innings) => (
          <div className="rounded-xl border border-line p-4" key={`${innings.team.id}-${innings.overs}`}>
            <p className="font-black">{innings.team.name}</p>
            <p className="mt-1 text-3xl font-black tracking-tight">
              {innings.runs}/{innings.wickets}
            </p>
            <p className="text-sm text-muted">{innings.overs} overs</p>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {performers.map((performer) => (
          <div className="rounded-xl bg-gradient-to-br from-[#f7f9f6] to-emerald-50 p-4" key={performer.label}>
            <span className="flex items-center gap-2 text-xs font-black uppercase text-muted">
              <Award className="h-4 w-4" />
              {performer.label}
            </span>
            <strong className="mt-2 block">{performer.name}</strong>
            <p className="text-sm text-muted">{performer.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function UpcomingMatchSummary({ center }: { center: MatchCenter }) {
  const [teamA, teamB] = center.match.teams;

  return (
    <section className="rounded-xl border border-line bg-white p-5 shadow-panel">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-black">Upcoming Match</h2>
          <p className="mt-1 text-sm text-muted">{center.match.series || "Cricket"}</p>
        </div>
        <StatusPill status={center.match.status} />
      </div>

      <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-center">
        <UpcomingTeam team={teamA} />
        <span className="text-center text-sm font-black uppercase text-muted">vs</span>
        <UpcomingTeam alignRight team={teamB} />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoTile icon={<CalendarClock />} label="Date & Time" value={formatDate(center.match.start_time_utc)} />
        <InfoTile icon={<Clock3 />} label="Venue" value={center.match.venue || "Venue unavailable"} />
      </div>
    </section>
  );
}

function UpcomingTeam({ team, alignRight = false }: { team?: Team; alignRight?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-xl bg-gradient-to-br from-[#f7f9f6] to-brand-50 p-4 ${alignRight ? "md:justify-end md:text-right" : ""}`}
    >
      <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-brand-700 to-teal-800 font-black text-white text-sm shrink-0">
        {team?.short_name || initials(team?.name)}
      </div>
      <div>
        <p className="font-black">{team?.name || "Team TBD"}</p>
        <p className="text-sm text-muted">{team?.short_name || "Squad pending"}</p>
      </div>
    </div>
  );
}

function Tabs({
  selectedTab,
  onSelect,
}: {
  selectedTab: "commentary" | "scorecard" | "squads";
  onSelect: (tab: "commentary" | "scorecard" | "squads") => void;
}) {
  const tabs = [
    ["commentary", "Commentary"],
    ["scorecard", "Scorecard"],
    ["squads", "Squads"],
  ] as const;

  return (
    <div className="flex gap-2 overflow-x-auto">
      {tabs.map(([value, label]) => (
        <button
          className={`min-h-11 min-w-32 rounded-xl border px-4 font-black transition-all duration-200 ${
            selectedTab === value
              ? "border-brand-500 bg-gradient-to-br from-brand-50 to-emerald-50 text-brand-700 shadow-sm"
              : "border-line bg-white text-muted hover:border-brand-200 hover:bg-brand-50"
          }`}
          key={value}
          onClick={() => onSelect(value)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function CommentaryPanel({ center }: { center: MatchCenter }) {
  const listRef = useRef<HTMLDivElement>(null);

  return (
    <div className="p-4">
      <PanelHeader title="Ball By Ball" subtitle={center.state.last_event} />
      {center.commentary.length ? (
        <div ref={listRef} className="divide-y divide-line">
          {center.commentary.map((ball, index) => (
            <CommentaryRow ball={ball} key={`${ball.over_ball}-${index}`} />
          ))}
        </div>
      ) : (
        <EmptyPanel
          title="No commentary yet"
          body="The feed will populate automatically when the backend provider returns ball-by-ball events."
        />
      )}
    </div>
  );
}

function CommentaryRow({ ball }: { ball: CommentaryBall }) {
  const runLabel =
    ball.wicket ? "W" :
    ball.runs === 6 ? "6" :
    ball.runs === 4 ? "4" :
    String(ball.runs);

  return (
    <article className="grid grid-cols-[56px_minmax(0,1fr)] gap-3 py-3 md:grid-cols-[62px_minmax(0,1fr)] transition-colors hover:bg-slate-50 rounded-lg px-1">
      <span
        className={`grid h-9 w-9 place-items-center rounded-lg font-black text-sm ${
          ball.wicket
            ? "bg-red-50 text-red-700 border border-red-200"
            : ball.boundary
            ? "bg-amber-50 text-amber-700 border border-amber-200"
            : "bg-slate-100 text-slate-600"
        }`}
      >
        {runLabel}
      </span>
      <div>
        <p className="font-black text-sm">
          <span className="text-brand-700">{ball.over_ball}</span>
          {ball.over_ball && " · "}
          {ball.bowler && ball.striker
            ? `${ball.bowler} to ${ball.striker}`
            : ball.striker || ball.bowler || ""}
          {ball.wicket && (
            <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-black text-red-700">OUT</span>
          )}
          {ball.boundary && !ball.wicket && (
            <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-black text-amber-700">
              {ball.runs === 6 ? "SIX!" : "FOUR!"}
            </span>
          )}
        </p>
        {ball.text && !ball.text.startsWith("<") && (
          <p className="mt-0.5 leading-relaxed text-[#34413e] text-xs">{ball.text}</p>
        )}
      </div>
    </article>
  );
}

function ScorecardPanel({ innings }: { innings: InningsScore[] }) {
  return (
    <div className="space-y-4 p-4">
      <PanelHeader title="Scorecard" subtitle={innings.length ? "Live innings summary" : "Awaiting innings"} />
      {innings.length ? (
        innings.map((item) => <InningsBlock innings={item} key={`${item.team.id}-${item.overs}`} />)
      ) : (
        <EmptyPanel title="No scorecard yet" body="Scorecard tables appear once the live provider returns innings data." />
      )}
    </div>
  );
}

function InningsBlock({ innings }: { innings: InningsScore }) {
  return (
    <section className="overflow-hidden rounded-xl border border-line">
      <div className="flex items-center justify-between border-b border-line bg-gradient-to-r from-[#f7f9f6] to-brand-50 px-4 py-3">
        <h3 className="font-black">{innings.team.name}</h3>
        <p className="font-black text-brand-700">
          {innings.runs}/{innings.wickets} ({innings.overs})
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[580px] table-fixed text-sm">
          <thead className="text-left text-xs uppercase text-muted bg-slate-50">
            <tr>
              <th className="w-[40%] px-3 py-2">Batter</th>
              <th className="px-3 py-2 text-right">R</th>
              <th className="px-3 py-2 text-right">B</th>
              <th className="px-3 py-2 text-right">4s</th>
              <th className="px-3 py-2 text-right">6s</th>
              <th className="px-3 py-2 text-right">SR</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {innings.batting.map((row) => (
              <tr
                key={row.player.id}
                className={`transition-colors ${row.is_batting ? "bg-emerald-50/60" : "hover:bg-slate-50"}`}
              >
                <td className="px-3 py-2">
                  <span className="font-black">{row.player.name}</span>
                  {row.is_batting && (
                    <span className="ml-2 inline-flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[8px] font-black text-white">
                      ●
                    </span>
                  )}
                  <span className="block text-xs text-muted">{row.dismissal || (row.is_batting ? "batting" : "")}</span>
                </td>
                <td className="px-3 py-2 text-right font-black">{row.runs}</td>
                <td className="px-3 py-2 text-right">{row.balls}</td>
                <td className="px-3 py-2 text-right">{row.fours}</td>
                <td className="px-3 py-2 text-right">{row.sixes}</td>
                <td className="px-3 py-2 text-right">{row.strike_rate.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {innings.bowling.length > 0 && (
        <div className="overflow-x-auto border-t border-line">
          <table className="w-full min-w-[580px] table-fixed text-sm">
            <thead className="text-left text-xs uppercase text-muted bg-slate-50">
              <tr>
                <th className="w-[40%] px-3 py-2">Bowler</th>
                <th className="px-3 py-2 text-right">O</th>
                <th className="px-3 py-2 text-right">M</th>
                <th className="px-3 py-2 text-right">R</th>
                <th className="px-3 py-2 text-right">W</th>
                <th className="px-3 py-2 text-right">Econ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {innings.bowling.map((row) => (
                <tr key={row.player.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-3 py-2 font-black">{row.player.name}</td>
                  <td className="px-3 py-2 text-right">{row.overs}</td>
                  <td className="px-3 py-2 text-right">{row.maidens}</td>
                  <td className="px-3 py-2 text-right">{row.runs}</td>
                  <td className="px-3 py-2 text-right font-black">{row.wickets}</td>
                  <td className="px-3 py-2 text-right">{row.economy.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {innings.fall_of_wickets.length > 0 && (
        <div className="border-t border-line px-4 py-3">
          <p className="mb-2 text-xs font-black uppercase text-muted">Fall of Wickets</p>
          <div className="flex flex-wrap gap-2">
            {innings.fall_of_wickets.map((fow) => (
              <span className="bg-slate-100 text-sm px-2 py-1 rounded-lg" key={fow}>
                {fow}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function SquadsPanel({ center }: { center: MatchCenter }) {
  return (
    <div className="p-4">
      <PanelHeader title="Squads" subtitle="Provider team list" />
      {center.squads.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {center.squads.map((squad) => (
            <section className="overflow-hidden rounded-xl border border-line" key={squad.team.id}>
              <h3 className="border-b border-line bg-gradient-to-r from-[#f7f9f6] to-brand-50 px-4 py-3 font-black">
                {squad.team.name}
              </h3>
              <div className="divide-y divide-line">
                {squad.players.length ? (
                  squad.players.map((player) => (
                    <div className="flex items-center justify-between gap-3 px-4 py-2" key={player.id}>
                      <span className="font-semibold">{player.name}</span>
                      <span className="text-right text-sm text-muted">{player.role || "-"}</span>
                    </div>
                  ))
                ) : (
                  <p className="px-4 py-3 text-sm text-muted">Squad not returned by provider.</p>
                )}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <EmptyPanel title="No squads yet" body="Squads appear when the provider returns team/player data for this match." />
      )}
    </div>
  );
}

function PredictionPanel({ forecast }: { forecast: OverForecast }) {
  // Determine phase from factors list (e.g. "Phase: death")
  const phaseRaw = forecast.factors.find((f) => f.startsWith("Phase:"))?.split(":")[1]?.trim() ?? "";
  const phaseColor =
    phaseRaw === "powerplay"
      ? "bg-blue-100 text-blue-800"
      : phaseRaw === "death"
      ? "bg-red-100 text-red-800"
      : "bg-amber-100 text-amber-800";

  const momentumColor =
    forecast.momentum.includes("Strong") || forecast.momentum.includes("building")
      ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
      : forecast.momentum.includes("pressure") || forecast.momentum.includes("control")
      ? "bg-red-50 text-red-800 border border-red-200"
      : "bg-slate-100 text-slate-700";

  const confidencePct = Math.round((forecast.confidence ?? 0) * 100);

  return (
    <section className="rounded-xl border border-line bg-white shadow-panel overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-line bg-gradient-to-r from-slate-50 to-brand-50 px-4 py-3">
        <div className="flex items-center gap-2">
          {/* LIVE pulse */}
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </span>
          <h2 className="text-base font-black">Next Over</h2>
        </div>
        <div className="flex items-center gap-2">
          {phaseRaw && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-black uppercase ${phaseColor}`}>
              {phaseRaw}
            </span>
          )}
          <span className="text-xs text-muted">{forecast.next_over}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Expected runs hero */}
        <div className="rounded-xl border border-emerald-100 bg-gradient-to-br from-brand-50 to-teal-50 px-5 py-4">
          <span className="text-xs font-black uppercase tracking-wider text-muted">Expected runs</span>
          <div className="flex items-end justify-between gap-3 mt-1">
            <strong className="text-5xl font-black text-brand-700 tabular-nums">
              {forecast.expected_runs.toFixed(1)}
            </strong>
            <div className="pb-2 text-right">
              <p className="text-xs text-muted">Range</p>
              <p className="font-black text-brand-600">{forecast.run_range}</p>
            </div>
          </div>
        </div>

        {/* 2×2 probability grid */}
        <div className="grid grid-cols-2 gap-3">
          <Probability label="Wicket risk" value={forecast.wicket_probability} tone="red" />
          <Probability label="Boundary chance" value={forecast.boundary_probability} tone="amber" />
          <Probability label="Dot ball" value={forecast.dot_ball_probability} tone="teal" />
          <Probability label="Win probability" value={forecast.win_probability} tone="green" />
        </div>

        {/* Momentum + strategy */}
        <div className="rounded-xl border border-line bg-slate-50 p-4">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-black ${momentumColor}`}>
            {forecast.momentum}
          </span>
          <p className="mt-2 leading-relaxed text-[#34413e] text-sm">{forecast.suggested_strategy}</p>
        </div>

        {/* Factor chips — only non-phase ones */}
        {forecast.factors.filter((f) => !f.startsWith("Phase:")).length > 0 && (
          <div className="space-y-1.5">
            {forecast.factors.filter((f) => !f.startsWith("Phase:")).map((factor) => (
              <div
                key={factor}
                className="border-l-[3px] border-brand-400 bg-brand-50/60 px-3 py-1.5 text-xs text-[#34413e] rounded-r-lg font-medium"
              >
                {factor}
              </div>
            ))}
          </div>
        )}

        {/* Confidence meter */}
        {forecast.confidence != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="flex items-center gap-1.5 text-xs text-muted">
                <Gauge className="h-3.5 w-3.5" />
                Model confidence
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-black ${
                  confidencePct >= 80
                    ? "bg-emerald-100 text-emerald-800"
                    : confidencePct >= 60
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {confidencePct}%
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-emerald-500 transition-all duration-700"
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>
        )}

        {/* Feature importance (dynamic per phase) */}
        {forecast.feature_importance && Object.keys(forecast.feature_importance).length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-black uppercase tracking-wider text-muted">Feature importance</p>
            {Object.entries(forecast.feature_importance)
              .sort(([, a], [, b]) => b - a)
              .map(([feature, importance]) => (
                <div key={feature}>
                  <div className="flex items-center justify-between text-xs mb-0.5">
                    <span className="text-[#34413e] capitalize">{feature.replace(/_/g, " ")}</span>
                    <span className="font-black text-brand-700">{Math.round(importance * 100)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-brand-500 to-teal-400 transition-all duration-700"
                      style={{ width: `${Math.round(importance * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </section>
  );
}

function CurrentPlayers({ center }: { center: MatchCenter }) {
  return (
    <section className="rounded-xl border border-line bg-white p-5 shadow-panel">
      <PanelHeader title="Current Context" subtitle={center.forecast.momentum} />
      <div className="divide-y divide-line">
        <PlayerContext label="Striker" value={center.state.striker.name} highlight />
        <PlayerContext label="Non-striker" value={center.state.non_striker.name} />
        <PlayerContext label="Bowler" value={center.state.bowler.name} />
        <PlayerContext label="Projected score" value={String(center.state.projected_score || "-")} />
      </div>
    </section>
  );
}

function EmptyLiveState() {
  return (
    <section className="xl:col-span-2">
      <div className="rounded-xl border border-dashed border-line bg-white p-10 text-center shadow-panel">
        <Radio className="mx-auto h-10 w-10 text-muted" />
        <h2 className="mt-4 text-xl font-black">No matches available</h2>
        <p className="mx-auto mt-2 max-w-xl leading-relaxed text-muted">
          Check back shortly for live, recent, or upcoming cricket fixtures.
        </p>
      </div>
    </section>
  );
}

function InfoTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex min-h-20 items-center gap-3 rounded-xl border border-line bg-white p-4 shadow-panel hover:shadow-md transition-shadow">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-brand-50 to-emerald-50 text-brand-700">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-black uppercase text-muted">{label}</p>
        <p className="truncate font-semibold">{value}</p>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-white px-3 py-2 shadow-sm">
      <p className="text-xl font-black text-brand-900">{value}</p>
      <p className="text-xs text-muted">{label}</p>
    </div>
  );
}

function Probability({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "red" | "amber" | "teal" | "green";
}) {
  const width = pct(value);
  const barColor = {
    red: "bg-gradient-to-r from-red-400 to-red-600",
    amber: "bg-gradient-to-r from-amber-400 to-orange-500",
    teal: "bg-gradient-to-r from-cyan-500 to-teal-600",
    green: "bg-gradient-to-r from-emerald-400 to-brand-600",
  }[tone];

  return (
    <div className="rounded-xl border border-line p-3">
      <p className="text-xs text-muted font-semibold">{label}</p>
      <p className="mt-1 text-2xl font-black">{width}</p>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-700`}
          style={{ width }}
        />
      </div>
    </div>
  );
}

function PlayerContext({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <span className="text-muted text-sm">{label}</span>
      <strong className={`text-right ${highlight ? "text-brand-700" : ""}`}>{value}</strong>
    </div>
  );
}

function PanelHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <h2 className="text-lg font-black">{title}</h2>
      {subtitle ? <p className="max-w-[55%] text-right text-sm text-muted">{subtitle}</p> : null}
    </div>
  );
}

function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-line p-6 text-center">
      <p className="font-black">{title}</p>
      <p className="mt-1 text-sm leading-relaxed text-muted">{body}</p>
    </div>
  );
}

function StatusPill({
  status,
  isLiveGlow = false,
}: {
  status: string;
  isLiveGlow?: boolean;
}) {
  const isLive = status.toLowerCase().includes("live") || status.toLowerCase().includes("need");
  return (
    <span
      className={`inline-flex min-h-7 items-center gap-2 rounded-lg px-2.5 text-xs font-black uppercase ${
        isLive
          ? "bg-red-50 text-red-700 border border-red-200"
          : "bg-brand-50 text-brand-700 border border-brand-200"
      }`}
    >
      {isLive ? (
        <span className={`h-2 w-2 rounded-full bg-red-500 ${isLiveGlow ? "sim-pulse-dot" : ""}`} />
      ) : (
        <Gauge className="h-3.5 w-3.5" />
      )}
      {isLive ? "LIVE" : (status.length > 18 ? status.slice(0, 18) + "…" : status) || "unknown"}
    </span>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getDefaultKind(data: LiveMatchResponse): MatchKind {
  if (data.liveMatch) return "live";
  if (data.recentMatch) return "recent";
  if (data.upcomingMatch) return "upcoming";
  return "empty";
}

function getCenterFor(data: LiveMatchResponse, kind: MatchKind): MatchCenter | null {
  if (kind === "live") return data.liveMatch;
  if (kind === "recent") return data.recentMatch;
  if (kind === "upcoming") return data.upcomingMatch;
  return null;
}

function defaultTabForKind(kind: MatchKind): "commentary" | "scorecard" | "squads" {
  if (kind === "recent") return "scorecard";
  if (kind === "upcoming") return "squads";
  return "commentary";
}

function summaryFor(kind: MatchKind, center: MatchCenter) {
  if (kind === "live") return center.status_line;
  if (kind === "recent") return center.match.result_summary || center.status_line;
  if (kind === "upcoming") {
    return `${formatDate(center.match.start_time_utc)}${center.match.venue ? ` · ${center.match.venue}` : ""}`;
  }
  return "No matches available";
}

function topPerformers(center: MatchCenter) {
  const batters = center.innings.flatMap((innings) =>
    innings.batting.map((row) => ({
      label: "Top Batter",
      name: row.player.name,
      value: `${row.runs} (${row.balls}) · SR ${row.strike_rate.toFixed(1)}`,
      score: row.runs,
    }))
  );

  const bowlers = center.innings.flatMap((innings) =>
    innings.bowling.map((row) => ({
      label: "Top Bowler",
      name: row.player.name,
      value: `${row.wickets}/${row.runs} · Econ ${row.economy.toFixed(2)}`,
      score: row.wickets * 100 - row.runs,
    }))
  );

  const topBatter = batters.sort((a, b) => b.score - a.score)[0];
  const topBowler = bowlers.sort((a, b) => b.score - a.score)[0];
  return [topBatter, topBowler].filter(Boolean);
}

function heroTeams(center: MatchCenter) {
  const teamA = center.match.teams[0];
  const teamB = center.match.teams[1];
  const firstInnings = center.innings[0];
  const secondInnings = center.innings[1];

  if (secondInnings) {
    // 2nd innings: batting team is 2nd, bowling team is 1st
    return [
      { team: secondInnings.team, innings: secondInnings },
      { team: firstInnings?.team ?? teamB, innings: firstInnings },
    ];
  }

  if (firstInnings) {
    // 1st innings: batting team known from innings, bowling = the OTHER team
    const battingName = firstInnings.team.name;
    const bowlingTeam =
      teamA?.name === battingName ? teamB : teamA;
    return [
      { team: firstInnings.team, innings: firstInnings },
      { team: bowlingTeam ?? teamB, innings: undefined },
    ];
  }

  // Pre-match: no innings yet
  return [
    { team: teamA, innings: undefined },
    { team: teamB, innings: undefined },
  ];
}

function initials(name?: string | null) {
  if (!name) return "--";
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();
}

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:-- UTC";
  return `${date.toISOString().slice(11, 16)} UTC`;
}

function formatDate(value?: string | null) {
  if (!value) return "Time unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function formatShortDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

function formatShortTime(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}
