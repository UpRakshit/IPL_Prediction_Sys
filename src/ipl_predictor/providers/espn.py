"""
ESPNProvider — fetches real IPL match data from ESPN's public API (no key required).

Live matches:  scoreboard (live scores) + play-by-play ALL pages (full batting/bowling/commentary)
Past matches:  summary matchcards (complete batting/bowling tables)
Pre-match:     summary squads
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

from ipl_predictor.cache.base import Cache

log = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/cricket/8048"
_TIMEOUT = 14
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CricketAI/1.0)"}

def _seq_to_over_ball(seq: int) -> str:
    """Decode ESPN sequence number → cricket over.ball notation.

    ESPN encodes sequence as: 100000 + (over_index * 100) + ball_number
    where over_index is 0-indexed (first over = 0) and ball_number is 1-6+.
    Cricket display convention: over 0 = "0.x", over 1 = "1.x", etc.
    (ESPN's over 0 = the 1st over; cricket shows "0.1" not "1.1")
    """
    if seq < 100000:
        return ""
    offset = seq - 100000
    over_idx = offset // 100     # 0-based over index
    ball_num = offset % 100      # 1-based ball number within over
    return f"{over_idx}.{ball_num}"


class ESPNProvider:
    """CricketDataProvider backed by ESPN Cricinfo free public API."""

    def __init__(self, cache: Cache) -> None:
        self.cache = cache

    @property
    def configured(self) -> bool:
        return True

    # ── Protocol surface ──────────────────────────────────────────────────────

    async def current_matches(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        date_strs = [
            (now - timedelta(days=2)).strftime("%Y%m%d"),
            (now - timedelta(days=1)).strftime("%Y%m%d"),
            now.strftime("%Y%m%d"),
            (now + timedelta(days=1)).strftime("%Y%m%d"),
            (now + timedelta(days=2)).strftime("%Y%m%d"),
        ]

        raw_lists = await asyncio.gather(
            *[self._fetch_scoreboard(d) for d in date_strs], return_exceptions=True
        )

        seen: set[str] = set()
        matches: list[dict] = []
        for events in raw_lists:
            if isinstance(events, Exception) or not isinstance(events, list):
                continue
            for ev in events:
                eid = str(ev.get("id", ""))
                if eid and eid not in seen:
                    seen.add(eid)
                    m = self._normalize_event(ev)
                    if m:
                        matches.append(m)

        # Sort: live first, then by date
        order = {"in": 0, "post": 1, "pre": 2}
        matches.sort(key=lambda m: (order.get(m.get("_espn_state", "pre"), 2), m.get("dateTimeGMT", "")))

        log.info("[ESPN] current_matches → %d matches: %s",
                 len(matches), [f"{m['name']} [{m['_espn_state']}]" for m in matches])
        return matches

    async def match_info(self, match_id: str) -> dict | None:
        return next((m for m in await self.current_matches() if m["id"] == match_id), None)

    async def match_scorecard(self, match_id: str) -> dict | None:
        if not match_id.startswith("espn-"):
            return None
        espn_id = match_id.removeprefix("espn-")
        info = await self.match_info(match_id)
        state = (info or {}).get("_espn_state", "pre")

        log.info("[ESPN] match_scorecard %s  state=%s", match_id, state)

        if state == "in":
            return await self._live_scorecard(espn_id, info or {})
        elif state == "post":
            return await self._completed_scorecard(espn_id, info or {})
        else:
            return await self._pre_match_data(espn_id)

    async def series_matches(self, series_id: str | None = None) -> list[dict]:
        return await self.current_matches()

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        return []

    # ── Live: scoreboard + ALL play-by-play pages ─────────────────────────────

    async def _live_scorecard(self, espn_id: str, info: dict) -> dict:
        cache_key = f"espn:live:{espn_id}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict):
            return cached

        pbp, summary = await asyncio.gather(
            self._fetch_pbp_all_pages(espn_id),
            self._fetch_summary_raw(espn_id),
            return_exceptions=True,
        )
        if isinstance(pbp, Exception):
            log.warning("[ESPN] PBP fetch failed: %s", pbp)
            pbp = {}
        if isinstance(summary, Exception):
            summary = {}

        result = self._build_live_scorecard(espn_id, info, pbp, summary)
        log.info("[ESPN] live scorecard built: innings=%d commentary=%d",
                 len(result.get("scorecard", [])),
                 len(result.get("commentary", [])))
        await self.cache.set_json(cache_key, result, 20)
        return result

    def _build_live_scorecard(self, espn_id: str, info: dict, pbp: dict, summary: dict) -> dict:
        """Build a rich live scorecard from linescores + full play-by-play."""
        # ── Parse all play-by-play balls ──────────────────────────────────────
        all_items = pbp.get("commentary", {}).get("items", [])
        ball_items = [i for i in all_items if i.get("batsman", {}).get("athlete", {}).get("id")]

        # ── Build per-batsman stats (latest stats per batsman ID) ─────────────
        # Items are sorted chronologically (oldest first), so iterate in order
        # and always overwrite — the last entry per player is their LATEST stats.
        batsman_order: list[str] = []          # insertion order
        batsman_stats: dict[str, dict] = {}
        dismissed_ids: set[str] = set()
        bowler_deliveries: dict[str, dict] = {}

        for item in ball_items:
            bat_obj = item.get("batsman", {})
            bat_ath = bat_obj.get("athlete", {})
            bat_id = bat_ath.get("id", "")
            if bat_id:
                if bat_id not in batsman_stats:
                    batsman_order.append(bat_id)
                batsman_stats[bat_id] = {
                    "id": bat_id,
                    "name": bat_ath.get("displayName") or bat_ath.get("name", "Unknown"),
                    "runs": int(bat_obj.get("totalRuns", 0) or 0),
                    "balls": int(bat_obj.get("faced", 0) or 0),
                    "fours": int(bat_obj.get("fours", 0) or 0),
                    "sixes": int(bat_obj.get("sixes", 0) or 0),
                }

            bowl_obj = item.get("bowler", {})
            bowl_ath = bowl_obj.get("athlete", {})
            bwid = bowl_ath.get("id", "")
            if bwid:
                if bwid not in bowler_deliveries:
                    bowler_deliveries[bwid] = {
                        "id": bwid,
                        "name": bowl_ath.get("displayName") or bowl_ath.get("name", "Unknown"),
                        "balls": 0, "runs": 0, "wickets": 0, "maidens": 0,
                    }
                score_val = int(item.get("scoreValue") or 0)
                bowler_deliveries[bwid]["balls"] += 1
                bowler_deliveries[bwid]["runs"] += score_val

            # Detect dismissals
            short_text = (item.get("shortText") or "").lower()
            if "out" in short_text and bat_id:
                dismissed_ids.add(bat_id)

        # ── Current batting players: last two non-dismissed batsmen ───────────
        # (last by batting order = most recently arrived at crease)
        non_dismissed = [bid for bid in batsman_order if bid not in dismissed_ids]
        currently_batting = set(non_dismissed[-2:]) if non_dismissed else set()

        # ── Batting rows ──────────────────────────────────────────────────────
        batting_rows = []
        for bid in batsman_order:
            s = batsman_stats[bid]
            is_bat = bid in currently_batting
            sr = round(s["runs"] / s["balls"] * 100, 2) if s["balls"] else 0.0
            batting_rows.append({
                "batsman": {"id": bid, "name": s["name"]},
                "r": s["runs"], "b": s["balls"],
                "4s": s["fours"], "6s": s["sixes"], "sr": sr,
                "dismissal": "batting*" if is_bat else "out",
                "is_batting": is_bat,
            })

        # ── Bowling rows ──────────────────────────────────────────────────────
        bowling_rows = []
        for bwid, bw in bowler_deliveries.items():
            full_ov = bw["balls"] // 6
            extra = bw["balls"] % 6
            overs_val = float(f"{full_ov}.{extra}")
            eco = round(bw["runs"] / max(full_ov + extra / 6, 0.1), 2)
            bowling_rows.append({
                "bowler": {"id": bwid, "name": bw["name"]},
                "o": overs_val, "m": 0, "r": bw["runs"], "w": bw["wickets"], "eco": eco,
            })

        # ── Live score from linescores ────────────────────────────────────────
        ls_list = info.get("_linescores", [])
        batting_ls = next((ls for ls in ls_list if ls.get("isBatting")), None)
        if not batting_ls and ls_list:
            batting_ls = ls_list[0]

        if batting_ls:
            runs = int(batting_ls.get("runs", 0))
            wickets = int(batting_ls.get("wickets", 0))
            overs_raw = float(batting_ls.get("overs", 0))
            overs_str = self._fmt_overs(overs_raw)
            rr = round(runs / max(self._overs_to_float(overs_str), 0.01), 2)
            team_name = batting_ls.get("team_name", "Batting Team")
            innings_list = [{
                "inning": f"{team_name} Inning 1",
                "totals": {"R": runs, "W": wickets, "O": overs_str, "RR": rr},
                "batting": batting_rows,
                "bowling": bowling_rows,
                "fall_of_wickets": [],
            }]
        else:
            innings_list = []

        # ── Commentary: newest first, with real over.ball format ──────────────
        commentary = []
        for item in reversed(ball_items):
            short_text = item.get("shortText", "") or ""
            pre_text = item.get("preText", "") or ""
            seq = int(item.get("sequence", 0) or 0)

            # Derive over.ball from ESPN sequence number (most reliable)
            over_ball = _seq_to_over_ball(seq)

            # Clean up text: prefer preText (full commentary) else shortText
            text = pre_text.strip() if pre_text.strip() else short_text

            bat_ath = item.get("batsman", {}).get("athlete", {})
            bowl_ath = item.get("bowler", {}).get("athlete", {})
            runs_val = int(item.get("scoreValue") or 0)
            is_wicket = "out" in short_text.lower()
            is_boundary = runs_val in (4, 6)

            if short_text:
                commentary.append({
                    "over_ball": over_ball,
                    "runs": runs_val,
                    "wicket": is_wicket,
                    "boundary": is_boundary,
                    "striker": bat_ath.get("displayName", ""),
                    "bowler": bowl_ath.get("displayName", ""),
                    "text": text,
                    "tags": [],
                })

        squads = self._squads_from_summary(summary)
        toss_info = (info.get("_espn_summary") or "")

        log.info("[ESPN] live scorecard: %s | batting=%d dismissed=%d commentary=%d",
                 batting_ls and f"{batting_ls.get('runs')}/{batting_ls.get('wickets')} ({overs_str}ov)" if batting_ls else "N/A",
                 len(batting_rows), len(dismissed_ids), len(commentary))

        return {
            "id": f"espn-{espn_id}",
            "scorecard": innings_list,
            "commentary": commentary[:30],
            "squads_data": squads,
            "result_summary": toss_info,
        }

    # ── Fetch ALL PBP pages ───────────────────────────────────────────────────

    async def _fetch_pbp_all_pages(self, espn_id: str) -> dict:
        """Fetch ALL play-by-play pages and merge into one combined response."""
        cache_key = f"espn:pbp:{espn_id}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict) and cached.get("commentary", {}).get("items"):
            return cached

        # Fetch page 1 to learn total page count
        page1 = await self._fetch_pbp_page(espn_id, 1)
        meta = page1.get("commentary", {})
        page_count = int(meta.get("pageCount", 1))

        log.info("[ESPN] PBP: event=%s pageCount=%d count=%s", espn_id, page_count, meta.get("count"))

        if page_count <= 1:
            await self.cache.set_json(cache_key, page1, 15)
            return page1

        # Fetch all remaining pages concurrently
        other_pages = await asyncio.gather(
            *[self._fetch_pbp_page(espn_id, p) for p in range(2, page_count + 1)],
            return_exceptions=True,
        )

        all_items = list(meta.get("items", []))
        for pg in other_pages:
            if isinstance(pg, dict):
                all_items.extend(pg.get("commentary", {}).get("items", []))

        # Sort by sequence ascending (chronological)
        all_items.sort(key=lambda x: int(x.get("sequence", 0) or 0))
        log.info("[ESPN] PBP combined: %d items from %d pages", len(all_items), page_count)

        result = {"commentary": {"items": all_items, "pageCount": page_count, "count": len(all_items)}}
        await self.cache.set_json(cache_key, result, 15)
        return result

    async def _fetch_pbp_page(self, espn_id: str, page: int) -> dict:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(
                    f"{ESPN_BASE}/playbyplay",
                    params={"event": espn_id, "page": page},
                    headers=_HEADERS,
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            log.warning("[ESPN] PBP page %d fetch error: %s", page, exc)
            return {}

    # ── Completed match ───────────────────────────────────────────────────────

    async def _completed_scorecard(self, espn_id: str, info: dict) -> dict:
        cache_key = f"espn:completed:{espn_id}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict):
            return cached

        summary = await self._fetch_summary_raw(espn_id)
        result = self._parse_summary_scorecard(espn_id, info, summary or {})
        await self.cache.set_json(cache_key, result, 300)
        return result

    def _parse_summary_scorecard(self, espn_id: str, info: dict, summary: dict) -> dict:
        matchcards = summary.get("matchcards", [])
        squads = summary.get("squads", [])
        header = summary.get("header", {})
        game_info = summary.get("gameInfo", {})

        comps = header.get("competitions", [{}])
        c = comps[0] if comps else {}
        result_summary = c.get("status", {}).get("summary", "")

        batting_cards = {mc["inningsNumber"]: mc for mc in matchcards if mc.get("typeID") == "11"}
        bowling_cards = {mc["inningsNumber"]: mc for mc in matchcards if mc.get("typeID") == "12"}
        innings_numbers = sorted(set(list(batting_cards) + list(bowling_cards)))

        innings_list = []
        for inn_num in innings_numbers:
            bat = batting_cards.get(inn_num, {})
            bowl = bowling_cards.get(inn_num, {})
            team_abbr = bat.get("teamName") or bowl.get("teamName", "")
            runs = int(bat.get("runs", 0) or 0)
            total_str = bat.get("total", "")
            overs_str = self._extract_overs_from_total(total_str)
            wickets = self._extract_wickets_from_total(total_str)
            rr = round(runs / max(self._overs_to_float(overs_str), 0.01), 2)

            batting_rows = []
            for p in bat.get("playerDetails", []):
                r = int(p.get("runs", 0) or 0)
                b = int(p.get("ballsFaced", 0) or 0)
                batting_rows.append({
                    "batsman": {"id": str(p.get("playerID", "")), "name": p.get("playerName", "Unknown")},
                    "r": r, "b": b,
                    "4s": int(p.get("fours", 0) or 0),
                    "6s": int(p.get("sixes", 0) or 0),
                    "sr": round(r / b * 100, 2) if b else 0.0,
                    "dismissal": p.get("dismissal") or "not out",
                    "is_batting": False,
                })

            bowling_rows = []
            for p in bowl.get("playerDetails", []):
                o_str = str(p.get("overs", "0"))
                o_val = float(o_str) if o_str else 0.0
                r = int(p.get("conceded", 0) or 0)
                bowling_rows.append({
                    "bowler": {"id": str(p.get("playerID", "")), "name": p.get("playerName", "Unknown")},
                    "o": o_val, "m": int(p.get("maidens", 0) or 0),
                    "r": r, "w": int(p.get("wickets", 0) or 0),
                    "eco": float(p.get("economyRate", 0) or 0),
                })

            squad = next((s for s in squads if s.get("team", {}).get("abbreviation") == team_abbr), None)
            team_name = squad.get("team", {}).get("displayName", team_abbr) if squad else team_abbr

            innings_list.append({
                "inning": f"{team_name} Inning {inn_num}",
                "totals": {"R": runs, "W": wickets, "O": overs_str, "RR": rr},
                "batting": batting_rows,
                "bowling": bowling_rows,
                "fall_of_wickets": [],
            })

        return {
            "id": f"espn-{espn_id}",
            "scorecard": innings_list,
            "commentary": [],
            "squads_data": self._squads_from_summary(summary),
            "result_summary": result_summary,
            "venue": game_info.get("venue", {}).get("fullName", "") if game_info else "",
        }

    # ── Pre-match ─────────────────────────────────────────────────────────────

    async def _pre_match_data(self, espn_id: str) -> dict:
        cache_key = f"espn:pre:{espn_id}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, dict):
            return cached

        summary = await self._fetch_summary_raw(espn_id)
        result = {
            "id": f"espn-{espn_id}",
            "scorecard": [],
            "commentary": [],
            "squads_data": self._squads_from_summary(summary or {}),
            "result_summary": "",
        }
        await self.cache.set_json(cache_key, result, 120)
        return result

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _fetch_scoreboard(self, date_str: str) -> list[dict]:
        cache_key = f"espn:sb:{date_str}"
        cached = await self.cache.get_json(cache_key)
        if isinstance(cached, list):
            return cached
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(
                    f"{ESPN_BASE}/scoreboard", params={"dates": date_str}, headers=_HEADERS
                )
                r.raise_for_status()
                events = r.json().get("events", [])
        except Exception as exc:
            log.warning("[ESPN] scoreboard fetch failed for %s: %s", date_str, exc)
            return []
        ttl = 20 if date_str == datetime.now(timezone.utc).strftime("%Y%m%d") else 300
        await self.cache.set_json(cache_key, events, ttl)
        return events

    async def _fetch_summary_raw(self, espn_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(
                    f"{ESPN_BASE}/summary", params={"event": espn_id}, headers=_HEADERS
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            log.warning("[ESPN] summary fetch failed for %s: %s", espn_id, exc)
            return {}

    # ── Event normalization ───────────────────────────────────────────────────

    def _normalize_event(self, event: dict) -> dict | None:
        comps = event.get("competitions", [])
        if not comps:
            return None
        c = comps[0]

        competitors = c.get("competitors", [])
        team_names = [comp.get("team", {}).get("displayName", "TBD") for comp in competitors]
        team_abbrs = [comp.get("team", {}).get("abbreviation", "") for comp in competitors]

        status_obj = c.get("status", {})
        status_type = status_obj.get("type", {})
        state = status_type.get("state", "pre")
        espn_summary = status_obj.get("summary", "")

        if state == "in":
            status_str = f"Live – {espn_summary}" if espn_summary else "Live"
        elif state == "post":
            status_str = espn_summary or "Match completed"
        else:
            status_str = espn_summary or "Upcoming"

        # Extract live score from linescores (authoritative for live)
        linescores_data: list[dict] = []
        scores: list[dict] = []
        for comp in competitors:
            abbr = comp.get("team", {}).get("abbreviation", "")
            name = comp.get("team", {}).get("displayName", "")
            score_str = comp.get("score", "") or ""
            for ls in comp.get("linescores", []):
                runs = ls.get("runs", 0)
                wickets = ls.get("wickets", 0)
                overs = ls.get("overs", 0.0)
                is_batting = bool(ls.get("isBatting", False))
                linescores_data.append({
                    "team_abbr": abbr,
                    "team_name": name,
                    "runs": runs,
                    "wickets": wickets,
                    "overs": overs,
                    "isBatting": is_batting,
                })
                if runs or is_batting:
                    scores.append({
                        "inning": f"{name} Inning 1",
                        "r": runs, "w": wickets,
                        "o": self._fmt_overs(overs),
                        "raw_score": score_str,
                    })

        venue = c.get("venue", {})
        venue_name = venue.get("fullName", "") if isinstance(venue, dict) else ""
        description = event.get("name", " vs ".join(team_names))

        return {
            "id": f"espn-{event['id']}",
            "name": " vs ".join(team_names),
            "matchType": "t20",
            "status": status_str,
            "venue": venue_name,
            "dateTimeGMT": c.get("date", ""),
            "teams": team_names,
            "score": scores,
            "series": self._series_label(description),
            "series_name": self._series_label(description),
            "team_abbrs": team_abbrs,
            "_espn_state": state,
            "_espn_summary": espn_summary,
            "_linescores": linescores_data,
        }

    # ── Squads ────────────────────────────────────────────────────────────────

    def _squads_from_summary(self, summary: dict) -> list[dict]:
        result = []
        for sq in summary.get("squads", []):
            team_name = sq.get("team", {}).get("displayName", "")
            players = [
                {
                    "id": str(a.get("id", "")),
                    "name": a.get("displayName") or a.get("fullName") or a.get("lastName") or "Unknown",
                    "role": a.get("position", {}).get("displayName")
                    if isinstance(a.get("position"), dict) else None,
                }
                for a in sq.get("athletes", [])
                if a.get("displayName") or a.get("fullName")
            ]
            if team_name:
                result.append({"team": team_name, "players": players})
        return result

    # ── Parsers / formatters ──────────────────────────────────────────────────

    @staticmethod
    def _fmt_overs(overs: float) -> str:
        return str(round(float(overs or 0), 1))

    @staticmethod
    def _overs_to_float(overs: str) -> float:
        try:
            parts = str(overs).split(".")
            return int(parts[0]) + (int(parts[1][0]) / 6 if len(parts) > 1 and parts[1] else 0)
        except Exception:
            return 0.0

    @staticmethod
    def _extract_overs_from_total(total_str: str) -> str:
        m = re.search(r"([\d.]+)\s+ovs?", total_str or "")
        return m.group(1) if m else "20.0"

    @staticmethod
    def _extract_wickets_from_total(total_str: str) -> int:
        if "all out" in (total_str or "").lower():
            return 10
        m = re.search(r"(\d+)\s+wkt", total_str or "")
        return int(m.group(1)) if m else 10

    @staticmethod
    def _series_label(description: str) -> str:
        m = re.match(r"^([^,]+),", description or "")
        if m:
            label = re.sub(r"\s*\([^)]*\)", "", m.group(1)).strip()
            return f"IPL 2026 – {label}"
        return "IPL 2026"
