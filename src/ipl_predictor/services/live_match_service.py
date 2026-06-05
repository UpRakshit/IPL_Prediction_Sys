from ipl_predictor.live.schemas import (
    CommentaryBall,
    Match,
    MatchCenter,
    MatchState,
    OverForecast,
    Player,
    Squad,
)
from ipl_predictor.prediction.engine import PredictionContext, RuleBasedPredictionEngine
from ipl_predictor.providers.base import CricketDataProvider
from ipl_predictor.services.normalizers import (
    innings_from_scorecard,
    innings_from_scores,
    match_from_provider,
    overs_to_float,
    player_from_provider,
    team_from_name,
)


class LiveMatchService:
    def __init__(self, provider: CricketDataProvider, predictor: RuleBasedPredictionEngine) -> None:
        self.provider = provider
        self.predictor = predictor

    async def current_matches(self) -> list[Match]:
        raw_matches = await self.provider.current_matches()
        matches = [match_from_provider(raw) for raw in raw_matches]
        return sorted(matches, key=lambda match: (match.status.lower() != "live", match.start_time_utc or ""))

    async def current_or_next_match(self) -> Match | None:
        matches = await self.current_matches()
        # 1. Live match — highest priority
        live = [m for m in matches if "live" in m.status.lower()]
        if live:
            return live[0]
        # 2. Recently completed match — show scorecard between games
        recent = [
            m
            for m in matches
            if any(
                word in m.status.lower()
                for word in ["won", "result", "completed", "no result", "drawn", "tied"]
            )
        ]
        if recent:
            return recent[0]
        # 3. Upcoming match
        upcoming = [
            m
            for m in matches
            if any(word in m.status.lower() for word in ["upcoming", "not started", "scheduled"])
        ]
        if upcoming:
            return upcoming[0]
        # 4. Any match at all
        return matches[0] if matches else None

    async def match(self, match_id: str) -> Match:
        info = await self.provider.match_info(match_id)
        if info:
            return match_from_provider(info)
        for match in await self.current_matches():
            if match.id == match_id:
                return match
        raise KeyError(match_id)

    async def squads(self, match_id: str) -> list[Squad]:
        data = await self.provider.match_info(match_id)
        if not data:
            return []
        teams = [team_from_name(team) for team in data.get("teams", []) if isinstance(team, str)]
        squad_items = data.get("teamInfo") or data.get("squad") or []
        squads: list[Squad] = []
        for team in teams:
            players = []
            for item in squad_items:
                if isinstance(item, dict) and item.get("name") == team.name:
                    players = [player_from_provider(player) for player in item.get("players", [])]
            squads.append(Squad(team=team, players=players))
        return squads

    @staticmethod
    def _squads_from_espn(squads_data: list[dict]) -> list[Squad]:
        """Build Squad objects from ESPN's inline squads_data."""
        from ipl_predictor.live.schemas import Player
        result: list[Squad] = []
        for sq in squads_data:
            team = team_from_name(sq.get("team", "Unknown"))
            players = [
                Player(
                    id=str(p.get("id", player_from_provider(p).id)),
                    name=p.get("name") or "Unknown",
                    role=p.get("role"),
                )
                for p in sq.get("players", [])
            ]
            result.append(Squad(team=team, players=players))
        return result

    async def match_center(self, match_id: str) -> MatchCenter:
        match = await self.match(match_id)
        scorecard = await self.provider.match_scorecard(match_id)
        innings = innings_from_scorecard(scorecard or {}) if scorecard else []
        if not innings:
            innings = innings_from_scores(scorecard or {})

        state = self._state(match, innings)
        forecast = self.predictor.predict(self._prediction_context(match, state, innings))

        # Detect provider type by class name (avoids circular import)
        provider_name = type(self.provider).__name__
        is_simulation = provider_name == "SimulationProvider"
        is_espn = provider_name == "ESPNProvider"
        if is_simulation:
            data_mode = "simulation"
            source_note = "Simulation mode — deterministic ball-by-ball replay. Set CRICAPI_API_KEY to switch to live data."
        elif is_espn:
            data_mode = "espn"
            source_note = "Live data sourced from ESPN Cricinfo. No API key required."
        else:
            data_mode = "live-provider"
            source_note = "Live data is fetched through the backend provider and cached before reaching the UI."

        # Build squads — ESPN embeds squad data in the scorecard response
        if is_espn and scorecard and scorecard.get("squads_data"):
            squads = self._squads_from_espn(scorecard["squads_data"])
        else:
            squads = await self.squads(match_id)

        # Patch match result_summary from scorecard if ESPN provided it
        if is_espn and scorecard and scorecard.get("result_summary"):
            match = match.model_copy(update={"result_summary": scorecard["result_summary"]})

        return MatchCenter(
            match=match,
            status_line=self._status_line(match, state),
            state=state,
            innings=innings,
            squads=squads,
            commentary=self._commentary(scorecard or {}),
            forecast=forecast,
            data_mode=data_mode,
            source_note=source_note,
        )

    async def next_over_forecast(self, match_id: str) -> OverForecast:
        center = await self.match_center(match_id)
        return center.forecast

    @staticmethod
    def _extract_live_features(current) -> dict:
        """Extract per-over stats from the live innings batting/bowling cards.

        The innings batting card has rows with strike_rate, runs, balls fields.
        The innings bowling card has rows with economy, overs, runs, wickets.
        We infer last-over / last-3-overs runs from the total runs minus what
        we'd expect at the prior CRR — a lightweight but effective signal.
        """
        if not current:
            return {}

        # ── Striker strike rate ──────────────────────────────────────────────
        striker_sr = 0.0
        currently_batting = [b for b in current.batting if b.is_batting]
        if currently_batting:
            striker = currently_batting[0]
            striker_sr = float(striker.strike_rate) if striker.balls > 0 else 0.0

        # ── Current bowler economy ───────────────────────────────────────────
        bowler_eco = 0.0
        if current.bowling:
            last_bowler = current.bowling[-1]
            bowler_eco = float(last_bowler.economy) if last_bowler.economy else 0.0

        # ── Approximate last-over and last-3-overs runs ──────────────────────
        # We use total runs and over count to estimate recent scoring rate.
        # E.g. if CRR across all overs is 7.0 but last 3 overs produced 27,
        # that is 9.0 RPO → strong momentum signal.
        #
        # Since we have cumulative bowling figures, we can sum the runs of the
        # LAST bowler's current over stats as a proxy.
        overs_float = overs_to_float(current.overs)
        completed_overs = int(overs_float)
        crr = current.run_rate or (current.runs / max(overs_float, 0.1))

        # Last-over runs: use current bowler's over runs if available
        last_over_runs = 0
        if current.bowling and completed_overs > 0:
            # Estimate last over runs = last bowler's runs / their overs
            # (This is a decent proxy; real data would require per-over breakdown)
            last_bowl = current.bowling[-1]
            last_bowl_overs = overs_to_float(last_bowl.overs) if last_bowl.overs else 0.0
            if last_bowl_overs >= 1:
                last_over_runs = round(last_bowl.runs / last_bowl_overs)
            elif last_bowl.runs:
                # Partial over: extrapolate
                last_over_runs = min(24, last_bowl.runs * 2)

        # Last 3 overs runs: weighted blend of last bowler eco + crr
        last_3_overs_runs = 0
        last_3_overs_wkts = 0
        if completed_overs >= 3:
            # Gather the two most recent bowlers for a richer estimate
            recent_bowlers = current.bowling[-2:] if len(current.bowling) >= 2 else current.bowling
            total_recent_runs = sum(b.runs for b in recent_bowlers)
            total_recent_overs = sum(overs_to_float(b.overs) for b in recent_bowlers if b.overs)
            if total_recent_overs >= 1:
                recent_eco = total_recent_runs / total_recent_overs
                last_3_overs_runs = round(recent_eco * min(3, total_recent_overs))
            else:
                last_3_overs_runs = round(crr * 3)
            last_3_overs_wkts = sum(b.wickets for b in recent_bowlers)

        # ── Partnership ──────────────────────────────────────────────────────
        partnership_runs = 0
        partnership_balls = 0
        if len(currently_batting) >= 2:
            p1, p2 = currently_batting[0], currently_batting[1]
            partnership_runs = p1.runs + p2.runs
            partnership_balls = p1.balls + p2.balls

        return {
            "recent_runs": last_over_runs,
            "recent_wickets": 0,   # will be patched from commentary if available
            "last_3_overs_runs": last_3_overs_runs,
            "last_3_overs_wickets": last_3_overs_wkts,
            "batsman_strike_rate": striker_sr,
            "bowler_economy": bowler_eco,
            "partnership_runs": partnership_runs,
            "partnership_balls": partnership_balls,
        }

    def _prediction_context(
        self, match: Match, state: MatchState, innings: list
    ) -> PredictionContext:
        current = innings[-1] if innings else None
        
        # Detect if we are in an innings break (1st innings over, 2nd not yet started)
        is_innings_break = False
        if current and len(innings) == 1:
            overs_float = overs_to_float(current.overs if current else 0)
            if overs_float >= 20.0 or current.wickets >= 10 or "innings break" in str(match.status).lower():
                is_innings_break = True

        target = innings[0].runs + 1 if len(innings) > 1 or is_innings_break else None
        
        if is_innings_break:
            # Predict for the upcoming 2nd innings (0 runs, 0.0 overs)
            return PredictionContext(
                match=match,
                runs=0,
                wickets=0,
                overs=0.0,
                target=target,
                batting_team=state.batting_team,
                bowling_team=state.bowling_team,
                recent_runs=0,
                recent_wickets=0,
                last_3_overs_runs=0,
                last_3_overs_wickets=0,
                batsman_strike_rate=0.0,
                bowler_economy=0.0,
                partnership_runs=0,
                partnership_balls=0,
            )
            
        features = self._extract_live_features(current)
        return PredictionContext(
            match=match,
            runs=current.runs if current else 0,
            wickets=current.wickets if current else 0,
            overs=overs_to_float(current.overs if current else 0),
            target=target,
            batting_team=state.batting_team,
            bowling_team=state.bowling_team,
            recent_runs=features.get("recent_runs", 0),
            recent_wickets=features.get("recent_wickets", 0),
            last_3_overs_runs=features.get("last_3_overs_runs", 0),
            last_3_overs_wickets=features.get("last_3_overs_wickets", 0),
            batsman_strike_rate=features.get("batsman_strike_rate", 0.0),
            bowler_economy=features.get("bowler_economy", 0.0),
            partnership_runs=features.get("partnership_runs", 0),
            partnership_balls=features.get("partnership_balls", 0),
        )

    @staticmethod
    def _state(match: Match, innings: list) -> MatchState:
        batting_team = innings[-1].team if innings else (match.teams[0] if match.teams else team_from_name(None))
        bowling_team = (
            next((team for team in match.teams if team.id != batting_team.id), None)
            or (match.teams[1] if len(match.teams) > 1 else batting_team)
        )
        current = innings[-1] if innings else None
        
        # Detect if we are in an innings break (1st innings over, 2nd not yet started)
        is_innings_break = False
        if current and len(innings) == 1:
            overs_float = overs_to_float(current.overs if current else 0)
            if overs_float >= 20.0 or current.wickets >= 10 or "innings break" in str(match.status).lower():
                is_innings_break = True
                
        if is_innings_break:
            batting_team, bowling_team = bowling_team, batting_team
            target = innings[0].runs + 1
            current = None
        else:
            target = innings[0].runs + 1 if len(innings) > 1 else None

        runs = current.runs if current else 0
        overs = overs_to_float(current.overs if current else 0)
        balls_remaining = max(0, 120 - int(overs * 6))
        required_runs = max(0, target - runs) if target else None
        required_rate = (
            round(required_runs / max(balls_remaining / 6, 1), 2)
            if required_runs is not None and balls_remaining
            else None
        )

        # Striker / non-striker = last two CURRENTLY BATTING players in the card
        currently_batting = [
            bc for bc in (current.batting if current else []) if bc.is_batting
        ] if current else []
        striker = (
            currently_batting[0].player if currently_batting
            else Player(id="unknown", name="TBD")
        )
        non_striker = (
            currently_batting[1].player if len(currently_batting) > 1
            else Player(id="unknown", name="TBD")
        )
        # Bowler = last bowler in the bowling card (most recently bowling)
        bowler = (
            current.bowling[-1].player
            if current and current.bowling
            else Player(id="unknown", name="TBD")
        )
        return MatchState(
            batting_team=batting_team,
            bowling_team=bowling_team,
            striker=striker,
            non_striker=non_striker,
            bowler=bowler,
            required_runs=required_runs,
            balls_remaining=balls_remaining,
            current_run_rate=current.run_rate if current else 0,
            required_run_rate=required_rate,
            projected_score=int((current.run_rate if current else 0) * 20) if current else 0,
            last_event=match.status,
        )

    @staticmethod
    def _status_line(match: Match, state: MatchState) -> str:
        current_runs = None
        current_wkts = None
        current_overs = None
        if state.current_run_rate and state.balls_remaining is not None:
            balls_bowled = 120 - state.balls_remaining
            full_ov = balls_bowled // 6
            extra = balls_bowled % 6
            current_overs = f"{full_ov}.{extra}"

        if state.required_runs is not None and state.balls_remaining is not None:
            # 2nd innings chase
            team = state.batting_team.short_name or state.batting_team.name
            return f"{team} need {state.required_runs} runs from {state.balls_remaining} balls · CRR {state.current_run_rate:.2f}"
        if state.current_run_rate and state.batting_team.name:
            # 1st innings — show batting team score + CRR
            team = state.batting_team.short_name or state.batting_team.name
            return f"{team} batting · CRR {state.current_run_rate:.2f}"
        return match.status or "Match status unavailable"

    @staticmethod
    def _commentary(data: dict) -> list[CommentaryBall]:
        balls = data.get("commentary") or data.get("ball_by_ball") or []
        commentary: list[CommentaryBall] = []
        for item in balls if isinstance(balls, list) else []:
            if not isinstance(item, dict):
                continue
            commentary.append(
                CommentaryBall(
                    over_ball=str(item.get("over") or item.get("over_ball") or ""),
                    batting_team_id=str(item.get("batting_team_id") or ""),
                    striker=str(item.get("batsman") or item.get("striker") or ""),
                    bowler=str(item.get("bowler") or ""),
                    runs=int(item.get("runs") or 0),
                    text=str(item.get("commentary") or item.get("text") or ""),
                    wicket=bool(item.get("wicket")),
                    boundary=int(item.get("runs") or 0) in {4, 6},
                )
            )
        return commentary
