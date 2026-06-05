"""
RuleBasedPredictionEngine — fully dynamic per-ball prediction.

Every field is computed from LIVE match state:
  - last_over_runs / last_3_overs_runs  → extracted from commentary
  - batsman_strike_rate                 → striker's current stats
  - bowler_economy                      → current bowler's economy
  - wickets_in_hand, phase, CRR        → from InningsScore

All inputs change every poll cycle → predictions change every over.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ipl_predictor.live.schemas import Match, OverForecast, Team


@dataclass(frozen=True)
class PredictionContext:
    match: Match
    runs: int = 0
    wickets: int = 0
    overs: float = 0.0
    target: int | None = None
    batting_team: Team | None = None
    bowling_team: Team | None = None

    # ── Live features extracted from commentary & batting card ──
    recent_runs: int = 0           # runs in LAST completed over
    recent_wickets: int = 0        # wickets in last over
    last_3_overs_runs: int = 0     # runs in last 3 overs (momentum window)
    last_3_overs_wickets: int = 0  # wickets in last 3 overs

    batsman_strike_rate: float = 0.0   # current striker's live SR
    bowler_economy: float = 0.0        # current bowler's live economy
    partnership_runs: int = 0          # runs in current partnership
    partnership_balls: int = 0         # balls in current partnership

    par_score: int = 170               # venue par (could be enriched later)


class RuleBasedPredictionEngine:
    """Fully dynamic prediction engine.  Inputs change every over → outputs change every over."""

    def predict(self, ctx: PredictionContext) -> OverForecast:
        batting_team = ctx.batting_team or self._team_at(ctx.match, 0)
        bowling_team = ctx.bowling_team or self._team_at(ctx.match, 1)

        phase = self._phase(ctx.overs)
        current_rr = ctx.runs / max(ctx.overs, 0.1)
        balls_bowled = int(ctx.overs * 6 + round((ctx.overs % 1) * 6))
        next_over_number = int(ctx.overs) + 1

        # ── Wickets-in-hand factor (more wickets remaining = more aggressive) ──
        wickets_in_hand = 10 - ctx.wickets
        wickets_factor = max(0.60, min(1.15, 0.60 + wickets_in_hand * 0.055))

        # ── Momentum from recent overs ──────────────────────────────────────────
        # last_over_runs compared to CRR: positive momentum if above CRR
        last_over_vs_crr = (ctx.recent_runs - current_rr) / max(current_rr, 1)
        last_3_rr = ctx.last_3_overs_runs / 3 if ctx.last_3_overs_runs else current_rr
        momentum_score = (
            last_over_vs_crr * 0.5
            + (last_3_rr - current_rr) / max(current_rr, 1) * 0.3
            - ctx.recent_wickets * 0.25
            - ctx.last_3_overs_wickets * 0.08
        )
        momentum_score = max(-1.0, min(1.0, momentum_score))

        # ── Batsman aggression factor ───────────────────────────────────────────
        # SR 150 = very aggressive; SR 60 = defensive
        effective_sr = ctx.batsman_strike_rate if ctx.batsman_strike_rate > 0 else (current_rr * 100 / 6)
        aggression = (effective_sr - 100) / 300  # normalised: 0 at SR 100, 0.17 at SR 150

        # ── Bowler pressure factor ──────────────────────────────────────────────
        # Lower economy bowler suppresses runs
        effective_eco = ctx.bowler_economy if ctx.bowler_economy > 0 else current_rr
        bowler_pressure = (current_rr - effective_eco) / max(current_rr, 1) * 0.4  # positive = bowler doing well

        # ── Phase multiplier ────────────────────────────────────────────────────
        phase_mult = {"powerplay": 1.10, "middle": 0.96, "death": 1.32}[phase]

        # ── Expected runs formula ────────────────────────────────────────────────
        # Blend: 50% CRR, 30% last-over-pace, 20% momentum adjustment
        last_over_rr = ctx.recent_runs if ctx.recent_runs > 0 else current_rr
        expected_runs = (
            current_rr * 0.50
            + last_over_rr * 0.30
            + current_rr * 0.20  # baseline
        ) * phase_mult * wickets_factor
        expected_runs += aggression * current_rr * 0.4   # batsman aggression lifts it
        expected_runs -= bowler_pressure * current_rr * 0.3  # good bowler suppresses
        expected_runs += momentum_score * 0.8
        expected_runs = round(max(2.5, min(22.0, expected_runs)), 1)

        # ── Wicket probability ──────────────────────────────────────────────────
        # Higher risk if: death overs, weak wickets, poor strike-rate match, bad momentum
        base_wkt_risk = {"powerplay": 0.10, "middle": 0.13, "death": 0.18}[phase]
        wicket_probability = (
            base_wkt_risk
            + (ctx.wickets - 3) * 0.008        # more wickets fallen = more nervous batsmen
            + ctx.recent_wickets * 0.06         # wicket this over → pressure
            + (100 - min(effective_sr, 200)) / 2000  # low-SR batsman more at risk
            - momentum_score * 0.04             # good momentum protects batsmen
            + (effective_eco - current_rr) / 100  # economy bowler raises risk slightly
        )
        wicket_probability = round(min(0.55, max(0.06, wicket_probability)), 2)

        # ── Boundary probability ────────────────────────────────────────────────
        boundary_probability = (
            0.22
            + effective_sr / 1000               # higher SR → more boundaries
            + (0.08 if phase == "death" else 0)
            + momentum_score * 0.05
            - wicket_probability * 0.10         # wicket pressure reduces boundary risk
        )
        boundary_probability = round(min(0.72, max(0.12, boundary_probability)), 2)

        # ── Dot ball probability ────────────────────────────────────────────────
        dot_ball_probability = (
            0.38
            - expected_runs / 60
            + wicket_probability * 0.15
            + (effective_eco - current_rr) / 30 * 0.05  # economy bowler dots
        )
        dot_ball_probability = round(min(0.62, max(0.12, dot_ball_probability)), 2)

        # ── Win probability ─────────────────────────────────────────────────────
        win_probability = self._win_probability(ctx, current_rr, momentum_score)

        # ── Confidence: higher when more balls bowled + real data present ───────
        data_richness = min(1.0, (
            (0.3 if ctx.batsman_strike_rate > 0 else 0)
            + (0.3 if ctx.bowler_economy > 0 else 0)
            + (0.2 if ctx.recent_runs > 0 else 0)
            + (0.2 if ctx.last_3_overs_runs > 0 else 0)
        ))
        overs_progress = min(1.0, ctx.overs / 20)
        confidence = round(0.35 + data_richness * 0.35 + overs_progress * 0.30, 2)

        # ── Feature importance (dynamic by phase) ──────────────────────────────
        if phase == "powerplay":
            feature_importance = {
                "phase_of_innings": 0.30,
                "wickets_in_hand": 0.25,
                "batsman_strike_rate": 0.20,
                "current_run_rate": 0.15,
                "recent_events": 0.10,
            }
        elif phase == "middle":
            feature_importance = {
                "recent_momentum": 0.28,
                "match_state": 0.25,
                "bowler_economy": 0.20,
                "wickets_in_hand": 0.18,
                "batsman_strike_rate": 0.09,
            }
        else:  # death
            feature_importance = {
                "wickets_in_hand": 0.30,
                "batsman_strike_rate": 0.28,
                "bowler_economy": 0.22,
                "recent_momentum": 0.12,
                "match_state": 0.08,
            }

        # ── Factors (human-readable feature audit) ──────────────────────────────
        factors = [
            f"Phase: {phase}",
            f"CRR: {current_rr:.2f}  |  Last over: {ctx.recent_runs}r {ctx.recent_wickets}w",
            f"Last 3 overs: {ctx.last_3_overs_runs}r {ctx.last_3_overs_wickets}w",
            f"Striker SR: {ctx.batsman_strike_rate:.1f}"
            if ctx.batsman_strike_rate else "Striker SR: —",
            f"Bowler eco: {ctx.bowler_economy:.2f}"
            if ctx.bowler_economy else "Bowler eco: —",
            f"Wickets lost: {ctx.wickets}  ({wickets_in_hand} in hand)",
            f"Momentum: {momentum_score:+.2f}",
        ]

        return OverForecast(
            match_id=ctx.match.id,
            next_over=f"Over {next_over_number} projection",
            batting_team=batting_team,
            bowling_team=bowling_team,
            expected_runs=expected_runs,
            run_range=f"{max(0, int(expected_runs - 3.5))}-{int(expected_runs + 4.5)}",
            wicket_probability=wicket_probability,
            boundary_probability=boundary_probability,
            dot_ball_probability=dot_ball_probability,
            win_probability=win_probability,
            momentum=self._momentum_label(momentum_score),
            suggested_strategy=self._strategy(
                phase, expected_runs, wicket_probability,
                momentum_score, wickets_in_hand, next_over_number
            ),
            factors=factors,
            confidence=confidence,
            feature_importance=feature_importance,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _team_at(match: Match, index: int) -> Team:
        return match.teams[index] if len(match.teams) > index else Team(id="unknown", name="Unknown")

    @staticmethod
    def _phase(overs: float) -> str:
        if overs < 6:
            return "powerplay"
        if overs < 16:
            return "middle"
        return "death"

    @staticmethod
    def _momentum_label(momentum: float) -> str:
        if momentum > 0.40:
            return "Strong batting momentum 🔥"
        if momentum > 0.15:
            return "Batting side building"
        if momentum < -0.30:
            return "Bowling side in control"
        if momentum < -0.10:
            return "Bowlers applying pressure"
        return "Balanced"

    @staticmethod
    def _strategy(
        phase: str,
        expected_runs: float,
        wicket_probability: float,
        momentum: float,
        wickets_in_hand: int,
        next_over: int,
    ) -> str:
        if wickets_in_hand <= 2:
            return "Protect wickets — tailenders in. Push only on full balls."
        if wicket_probability > 0.30:
            return "Settle first two balls, then target the slot. Wicket risk is high."
        if phase == "death":
            if wickets_in_hand >= 4 and expected_runs > 10:
                return "Go big! Maximize boundaries — the field is up, target long-on / long-off."
            return "Placement over power. Find the gap, run hard between wickets."
        if phase == "powerplay":
            return "Attack the field restrictions — target extra cover and square leg boundaries."
        if momentum > 0.30:
            return "Momentum is with you. Back the current striker to continue the onslaught."
        if momentum < -0.20:
            return "Reset. Rotate strike for two balls, then target the boundary by over end."
        return f"Build a {int(expected_runs)}+ run over — rotate & wait for the bad ball."

    @staticmethod
    def _win_probability(ctx: PredictionContext, current_rr: float, momentum: float) -> float:
        if ctx.target:
            # Chasing: DLS-style factor
            balls_used = int(ctx.overs * 6)
            balls_left = max(1, 120 - balls_used)
            runs_left = max(0, ctx.target - ctx.runs)
            required_rr = runs_left / (balls_left / 6)
            rr_advantage = (current_rr - required_rr) * 0.06
            wickets_advantage = (10 - ctx.wickets) * 0.025
            prob = 0.50 + rr_advantage + wickets_advantage + momentum * 0.04
        else:
            # Batting first: compare to par trajectory
            par_at_this_stage = ctx.par_score * min(ctx.overs, 20) / 20
            run_advantage = (ctx.runs - par_at_this_stage) / 200
            wickets_advantage = (10 - ctx.wickets) * 0.012
            prob = 0.50 + run_advantage + wickets_advantage + momentum * 0.04

        return round(min(0.94, max(0.06, prob)), 2)
