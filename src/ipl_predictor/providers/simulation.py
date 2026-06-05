"""
SimulationProvider — a fully deterministic provider that returns realistic
IPL match data without any external credentials.

A new ball is bowled every BALL_INTERVAL_SECONDS seconds (real wall-clock time).
The 2nd innings is a 5-over (balls 91–120) CSK chase of RCB's 184/5.
Once the chase completes, it loops back to ball index 0.

Usage: set LIVE_PROVIDER=simulation (or leave CRICAPI_API_KEY blank).
"""

from __future__ import annotations

import time
from typing import Any

# ─── Configuration ────────────────────────────────────────────────────────────
BALL_INTERVAL_SECONDS = 15  # advance one ball every N wall-clock seconds

# ─── Fixed first-innings (RCB scored 184/5 in 20 overs) ─────────────────────
RCB_FIRST_INNINGS = {
    "inning": "Royal Challengers Bangalore Inning 1",
    "totals": {"R": 184, "W": 5, "O": 20.0, "RR": 9.2},
    "batting": [
        {"batsman": {"id": "virat", "name": "Virat Kohli"}, "r": 72, "b": 46, "4s": 7, "6s": 2, "sr": 156.52, "dismissal": "c Jadeja b Pathirana"},
        {"batsman": {"id": "rajat", "name": "Rajat Patidar"}, "r": 38, "b": 28, "4s": 4, "6s": 1, "sr": 135.71, "dismissal": "c Gaikwad b Jadeja"},
        {"batsman": {"id": "faf", "name": "Faf du Plessis"}, "r": 31, "b": 19, "4s": 3, "6s": 1, "sr": 163.16, "dismissal": "b Chahar"},
        {"batsman": {"id": "maxwell", "name": "Glenn Maxwell"}, "r": 24, "b": 15, "4s": 1, "6s": 2, "sr": 160.0, "dismissal": "run out"},
        {"batsman": {"id": "dhruv", "name": "Dhruv Jurel"}, "r": 11, "b": 9, "4s": 1, "6s": 0, "sr": 122.22, "dismissal": "not out"},
        {"batsman": {"id": "will", "name": "Will Jacks"}, "r": 8, "b": 6, "4s": 0, "6s": 1, "sr": 133.33, "dismissal": "not out"},
    ],
    "bowling": [
        {"bowler": {"id": "pathirana", "name": "Matheesha Pathirana"}, "o": 4.0, "m": 0, "r": 28, "w": 2, "eco": 7.0},
        {"bowler": {"id": "jadeja", "name": "Ravindra Jadeja"}, "o": 4.0, "m": 0, "r": 34, "w": 1, "eco": 8.5},
        {"bowler": {"id": "chahar", "name": "Deepak Chahar"}, "o": 4.0, "m": 0, "r": 38, "w": 1, "eco": 9.5},
        {"bowler": {"id": "mukesh", "name": "Mukesh Choudhary"}, "o": 4.0, "m": 0, "r": 45, "w": 0, "eco": 11.25},
        {"bowler": {"id": "moeen", "name": "Moeen Ali"}, "o": 4.0, "m": 0, "r": 39, "w": 1, "eco": 9.75},
    ],
}

# ─── 30-ball chase sequence: (runs_on_ball, is_wicket, is_boundary, striker, bowler, commentary) ─
# CSK needs 185. After 15 overs: 128/4. Need 57 from 30 balls.
# Striker at start: MS Dhoni (id=dhoni), Non-striker: Ravindra Jadeja (id=jadeja)
BALL_SEQUENCE: list[dict[str, Any]] = [
    # Over 15 — Siraj bowling (started fresh)
    {"r": 1,  "wkt": False, "bdry": False, "striker": "jadeja",    "bowler": "siraj",    "txt": "Jadeja taps it to mid-on and scampers through for a single. 56 needed off 29."},
    {"r": 6,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "siraj",    "txt": "MAXIMUM! Dhoni plants his back foot and sends it soaring over wide long-on! The stadium is electric!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Siraj gets one to nip back. Dhoni jabs it down to mid-wicket. Dot ball. 49 needed."},
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "siraj",    "txt": "FOUR! Short and wide — Dhoni cuts it with savage precision through backward point!"},
    {"r": 1,  "wkt": False, "bdry": False, "striker": "jadeja",    "bowler": "siraj",    "txt": "Jadeja clips it off his pads for a single. Good running between the wickets."},
    {"r": 2,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Driven firmly through mid-off. They come back for two. Dhoni is timing it beautifully!"},
    # Over 16 — Yash Dayal
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "jadeja",    "bowler": "dayal",    "txt": "FOUR! Jadeja flicks it off the back foot — races to the boundary at square leg!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "jadeja",    "bowler": "dayal",    "txt": "Dayal bangs it in short. Jadeja ducks under it. Wide signalled by the umpire."},
    {"r": 1,  "wkt": False, "bdry": False, "striker": "jadeja",    "bowler": "dayal",    "txt": "Glanced fine for one. Dayal looks frustrated."},
    {"r": 6,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "dayal",    "txt": "SIX! Inside out over long-off! Dhoni brings up the crowd with a helicopter follow-through!"},
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "dayal",    "txt": "FOUR! Dhoni drills a full-toss past the bowler. Back-to-back boundaries!"},
    {"r": 0,  "wkt": True,  "bdry": False, "striker": "jadeja",    "bowler": "dayal",    "txt": "WICKET! Jadeja goes for a big heave — gets a top edge and Kohli takes a clean catch at fine leg!"},
    # Over 17 — Siraj returns (Dhoni + Pathirana new)
    {"r": 1,  "wkt": False, "bdry": False, "striker": "pathirana",  "bowler": "siraj",   "txt": "Pathirana gets off the mark with a single to long-on. Dhoni keeps the strike next ball."},
    {"r": 6,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "siraj",    "txt": "ENORMOUS SIX! That's out of the park! Dhoni connects flush in the middle — 110 metres!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Good length delivery. Dhoni tries to slog but misses. Big shout for LBW — not out."},
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "siraj",    "txt": "FOUR! Dhoni uses the crease beautifully, sweeps it fine for a boundary!"},
    {"r": 2,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Two through cover. CSK need 17 off the last 3 overs! Siraj looks drained."},
    {"r": 1,  "wkt": False, "bdry": False, "striker": "pathirana",  "bowler": "siraj",   "txt": "Single to midwicket — Dhoni retains strike as Pathirana takes one."},
    # Over 18 — Dayal last over
    {"r": 6,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "dayal",    "txt": "SIX AGAIN! Dhoni charges down the track and launches it over long-on! He's UNSTOPPABLE!"},
    {"r": 1,  "wkt": False, "bdry": False, "striker": "pathirana",  "bowler": "dayal",   "txt": "Pathirana drills it to long-off and turns back for one. 9 needed off 12."},
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "dayal",    "txt": "FOUR! Full toss, Dhoni crunches it through midwicket! He's in the ZONE!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "dayal",    "txt": "Dayal gets his slower ball right. Dhoni miscues it to extra cover. 5 needed off 9."},
    {"r": 2,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "dayal",    "txt": "They push hard and get two. Brilliant running. 3 needed off 8 balls!"},
    {"r": 1,  "wkt": False, "bdry": False, "striker": "pathirana",  "bowler": "dayal",   "txt": "Pathirana squirts it to third man. They take one — 2 needed off 7. Dhoni on strike."},
    # Over 19 — Final over
    {"r": 4,  "wkt": False, "bdry": True,  "striker": "dhoni",     "bowler": "siraj",    "txt": "FOUR! Dhoni ends it in STYLE! Full and straight — Dhoni drives it for a boundary! CSK WIN AGAIN!!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "That's it! CSK have done it by 6 wickets! Dhoni finishes unbeaten — the Yellow Army erupts!"},
    # Loop buffer (ball 26-29 — celebration replays)
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "CSK vs RCB thrilling finish! Dhoni's 38*(22) seals the chase in dramatic fashion!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Man of the Match: MS Dhoni — 38* off 22 balls. Two sixes, two fours. Vintage Thala!"},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "IPL 2026 Qualifier drama! CSK march into the next round. Dhoni wins it with a ball to spare."},
    {"r": 0,  "wkt": False, "bdry": False, "striker": "dhoni",     "bowler": "siraj",    "txt": "Restarting highlights... The simulation reloops to ball 1 of the final-over chase."},
]

# Initial CSK batting position (ball index 0, 128/4 after 15 overs)
_BATTERS: list[dict[str, Any]] = [
    {"batsman": {"id": "gaikwad",  "name": "Ruturaj Gaikwad"},  "r": 48, "b": 36, "4s": 4, "6s": 1, "sr": 133.3,  "dismissal": "c Kohli b Siraj"},
    {"batsman": {"id": "conway",   "name": "Devon Conway"},      "r": 22, "b": 18, "4s": 2, "6s": 0, "sr": 122.2,  "dismissal": "b Maxwell"},
    {"batsman": {"id": "ajinkya",  "name": "Ajinkya Rahane"},    "r": 15, "b": 14, "4s": 1, "6s": 0, "sr": 107.1,  "dismissal": "lbw b Dayal"},
    {"batsman": {"id": "shivam",   "name": "Shivam Dube"},       "r": 31, "b": 17, "4s": 1, "6s": 3, "sr": 182.4,  "dismissal": "c Rajat b Hasaranga"},
    {"batsman": {"id": "dhoni",    "name": "MS Dhoni"},          "r": 0,  "b": 0,  "4s": 0, "6s": 0, "sr": 0.0,    "dismissal": None},
    {"batsman": {"id": "jadeja",   "name": "Ravindra Jadeja"},   "r": 0,  "b": 0,  "4s": 0, "6s": 0, "sr": 0.0,    "dismissal": None},
    {"batsman": {"id": "pathirana","name": "Matheesha Pathirana"},"r": 0,  "b": 0,  "4s": 0, "6s": 0, "sr": 0.0,    "dismissal": None},
]

_BOWLERS_INIT: list[dict[str, Any]] = [
    {"bowler": {"id": "siraj",   "name": "Mohammed Siraj"},    "o": 3.0, "m": 0, "r": 28, "w": 1, "eco": 9.3},
    {"bowler": {"id": "dayal",   "name": "Yash Dayal"},        "o": 3.0, "m": 0, "r": 36, "w": 1, "eco": 12.0},
    {"bowler": {"id": "maxwell", "name": "Glenn Maxwell"},     "o": 3.0, "m": 0, "r": 22, "w": 1, "eco": 7.3},
    {"bowler": {"id": "hasa",    "name": "Wanindu Hasaranga"}, "o": 3.0, "m": 0, "r": 27, "w": 1, "eco": 9.0},
    {"bowler": {"id": "will",    "name": "Will Jacks"},        "o": 3.0, "m": 0, "r": 33, "w": 0, "eco": 11.0},
]

_SERIES_ID = "ipl-2026-qualifier"

# ─── Helper ──────────────────────────────────────────────────────────────────

def _current_ball_index() -> int:
    """Return the 0-indexed ball position based on wall-clock time."""
    return int(time.time() // BALL_INTERVAL_SECONDS) % len(BALL_SEQUENCE)


def _build_live_scorecard(ball_idx: int) -> dict:
    """
    Build the live scorecard for ball at ball_idx (0-based within BALL_SEQUENCE).
    The 2nd innings starts at 128/4 after 15 overs and advances ball by ball.
    """
    import copy
    balls_played = ball_idx + 1  # balls 1..30 in the over 15-20 window

    # Derive live stats by replaying events up to ball_idx
    runs = 128
    wickets = 4
    overs_played = 15.0
    balls_this_over = 0
    batting_stats: dict[str, dict] = {}  # id → {r, b, 4s, 6s}
    bowling_stats: dict[str, dict] = {}  # id → {r, w, balls}
    commentary_list: list[dict] = []
    wickets_fallen: list[str] = []

    striker_id = "dhoni"
    non_striker_id = "jadeja"

    def _batter_init(batter_id: str) -> dict:
        return {"r": 0, "b": 0, "4s": 0, "6s": 0, "out": False, "dismissal": None}

    def _bowler_init() -> dict:
        return {"r": 0, "w": 0, "balls": 0}

    for i in range(balls_played):
        ev = BALL_SEQUENCE[i]
        bid = ev["bowler"]
        sid = ev["striker"]

        striker_id = sid
        if sid not in batting_stats:
            batting_stats[sid] = _batter_init(sid)
        if bid not in bowling_stats:
            bowling_stats[bid] = _bowler_init()

        # Runs
        r = ev["r"]
        runs += r
        batting_stats[sid]["r"] += r
        batting_stats[sid]["b"] += 1
        bowling_stats[bid]["r"] += r
        bowling_stats[bid]["balls"] += 1

        if ev.get("bdry") and r == 4:
            batting_stats[sid]["4s"] += 1
        if ev.get("bdry") and r == 6:
            batting_stats[sid]["6s"] += 1

        # Wicket
        if ev["wkt"] and wickets < 10:
            wickets += 1
            batting_stats[sid]["out"] = True
            batting_stats[sid]["dismissal"] = "c Kohli b Siraj"
            wickets_fallen.append(f"{runs}/{wickets} ({_ball_number(i)})")

        balls_this_over += 1
        if balls_this_over == 6:
            overs_played += 1.0
            balls_this_over = 0
            # swap striker after over
            striker_id, non_striker_id = non_striker_id, striker_id

        commentary_list.append({
            "over": _ball_number(i),
            "batting_team_id": "csk",
            "batsman": _batter_name(sid),
            "bowler": _bowler_name(bid),
            "runs": r,
            "commentary": ev["txt"],
            "wicket": ev["wkt"],
        })

    overs_str = f"{int(overs_played)}.{balls_this_over}"
    run_rate = round(runs / max(float(overs_played) + balls_this_over / 6, 0.01), 2)

    # Build batting cards: first the 4 dismissed batters, then live batters
    batting_cards = list(copy.deepcopy(_BATTERS[:4]))  # already dismissed
    for batter_id in ["dhoni", "jadeja", "pathirana"]:
        binfo = next(b for b in _BATTERS if b["batsman"]["id"] == batter_id)
        bc = copy.deepcopy(binfo)
        if batter_id in batting_stats:
            st = batting_stats[batter_id]
            bc["r"] = st["r"]
            bc["b"] = st["b"]
            bc["4s"] = st["4s"]
            bc["6s"] = st["6s"]
            if st["out"]:
                bc["dismissal"] = st["dismissal"]
            else:
                bc["dismissal"] = "batting" if batter_id == striker_id else None
            bc["sr"] = round(bc["r"] / max(bc["b"], 1) * 100, 2)
        batting_cards.append(bc)

    # Build bowling cards: initial 5 overs each + live additions
    bowling_cards = copy.deepcopy(_BOWLERS_INIT)
    for bc in bowling_cards:
        bid = bc["bowler"]["id"]
        if bid in bowling_stats:
            extra = bowling_stats[bid]
            bc["r"] += extra["r"]
            bc["w"] += extra["w"]
            extra_overs = extra["balls"] // 6
            extra_balls = extra["balls"] % 6
            bc["o"] = bc["o"] + extra_overs + (extra_balls / 10)
            bc["eco"] = round(bc["r"] / max(float(bc["o"]) + (extra_balls / 6), 0.01), 2)

    return {
        "id": "simulated-match",
        "scorecard": [
            RCB_FIRST_INNINGS,
            {
                "inning": "Chennai Super Kings Inning 2",
                "totals": {
                    "R": runs,
                    "W": wickets,
                    "O": overs_str,
                    "RR": run_rate,
                },
                "batting": batting_cards,
                "bowling": bowling_cards,
                "fall_of_wickets": wickets_fallen,
            },
        ],
        "commentary": list(reversed(commentary_list)),
    }


def _ball_number(ball_idx: int) -> str:
    """Convert 0-based sequence index to over.ball label (ball 0 = 15.1)."""
    base_over = 15
    absolute_ball = base_over * 6 + ball_idx
    ov = absolute_ball // 6
    b = (absolute_ball % 6) + 1
    return f"{ov}.{b}"


def _batter_name(batter_id: str) -> str:
    _map = {
        "dhoni": "MS Dhoni",
        "jadeja": "Ravindra Jadeja",
        "pathirana": "Matheesha Pathirana",
    }
    return _map.get(batter_id, batter_id)


def _bowler_name(bowler_id: str) -> str:
    _map = {
        "siraj": "Mohammed Siraj",
        "dayal": "Yash Dayal",
    }
    return _map.get(bowler_id, bowler_id)


# ─── Live score summary (used by currentMatches) ─────────────────────────────

def _live_score_summary(ball_idx: int) -> list[dict]:
    """Compact score summary for currentMatches response."""
    runs = 128
    wickets = 4
    balls = 0
    for i in range(ball_idx + 1):
        ev = BALL_SEQUENCE[i]
        runs += ev["r"]
        if ev["wkt"]:
            wickets += 1
        balls += 1
    total_balls = 15 * 6 + balls
    overs = total_balls // 6 + (total_balls % 6) / 10
    return [
        {"r": 184, "w": 5, "o": 20.0, "inning": "Royal Challengers Bangalore Inning 1"},
        {"r": runs, "w": wickets, "o": overs, "inning": "Chennai Super Kings Inning 2"},
    ]


# ─── Provider ────────────────────────────────────────────────────────────────

class SimulationProvider:
    """
    Returns deterministic live IPL match data without any credentials.
    Implements the CricketDataProvider protocol.
    """

    @property
    def configured(self) -> bool:
        return True

    async def current_matches(self) -> list[dict]:
        ball_idx = _current_ball_index()
        score_summary = _live_score_summary(ball_idx)
        live_status = "Live - Chennai Super Kings need {} more from {} balls".format(
            max(0, 185 - score_summary[1]["r"]),
            max(0, 120 - (15 * 6 + ball_idx + 1)),
        )

        return [
            {
                "id": "simulated-match",
                "name": "Chennai Super Kings vs Royal Challengers Bangalore",
                "matchType": "t20",
                "status": live_status,
                "venue": "M. A. Chidambaram Stadium, Chennai",
                "dateTimeGMT": "2026-05-29T15:30:00",
                "teams": ["Chennai Super Kings", "Royal Challengers Bangalore"],
                "score": score_summary,
                "series": "IPL 2026 Qualifier 2",
                "series_name": "IPL 2026 Qualifier 2",
            },
            {
                "id": "simulated-recent",
                "name": "Kolkata Knight Riders vs Sunrisers Hyderabad",
                "matchType": "t20",
                "status": "Kolkata Knight Riders won by 34 runs",
                "venue": "Eden Gardens, Kolkata",
                "dateTimeGMT": "2026-05-28T14:00:00",
                "teams": ["Kolkata Knight Riders", "Sunrisers Hyderabad"],
                "score": [
                    {"r": 196, "w": 4, "o": 20.0, "inning": "Kolkata Knight Riders Inning 1"},
                    {"r": 162, "w": 8, "o": 20.0, "inning": "Sunrisers Hyderabad Inning 2"},
                ],
                "series": "IPL 2026 Eliminator",
                "series_name": "IPL 2026 Eliminator",
            },
            {
                "id": "simulated-upcoming",
                "name": "Rajasthan Royals vs Mumbai Indians",
                "matchType": "t20",
                "status": "Match starts at 19:30 IST",
                "venue": "Sawai Mansingh Stadium, Jaipur",
                "dateTimeGMT": "2026-05-30T14:00:00",
                "teams": ["Rajasthan Royals", "Mumbai Indians"],
                "score": [],
                "series": "IPL 2026 Qualifier 1",
                "series_name": "IPL 2026 Qualifier 1",
            },
        ]

    async def match_info(self, match_id: str) -> dict | None:
        matches = await self.current_matches()
        return next((m for m in matches if m["id"] == match_id), None)

    async def match_scorecard(self, match_id: str) -> dict | None:
        if match_id == "simulated-match":
            ball_idx = _current_ball_index()
            return _build_live_scorecard(ball_idx)
        if match_id == "simulated-recent":
            return {
                "id": "simulated-recent",
                "scorecard": [
                    {
                        "inning": "Kolkata Knight Riders Inning 1",
                        "totals": {"R": 196, "W": 4, "O": 20.0, "RR": 9.8},
                        "batting": [
                            {"batsman": {"id": "salt", "name": "Phil Salt"}, "r": 88, "b": 50, "4s": 9, "6s": 4, "sr": 176.0, "dismissal": "c Abhishek b Cummins"},
                            {"batsman": {"id": "narine", "name": "Sunil Narine"}, "r": 51, "b": 32, "4s": 5, "6s": 3, "sr": 159.4, "dismissal": "b Shahbaz"},
                            {"batsman": {"id": "iyer", "name": "Shreyas Iyer"}, "r": 37, "b": 25, "4s": 3, "6s": 2, "sr": 148.0, "dismissal": "not out"},
                            {"batsman": {"id": "russell", "name": "Andre Russell"}, "r": 20, "b": 10, "4s": 1, "6s": 2, "sr": 200.0, "dismissal": "not out"},
                        ],
                        "bowling": [
                            {"bowler": {"id": "cummins", "name": "Pat Cummins"}, "o": 4.0, "m": 0, "r": 38, "w": 1, "eco": 9.5},
                            {"bowler": {"id": "natarajan", "name": "T Natarajan"}, "o": 4.0, "m": 0, "r": 46, "w": 0, "eco": 11.5},
                            {"bowler": {"id": "shahbaz", "name": "Shahbaz Ahmed"}, "o": 4.0, "m": 0, "r": 29, "w": 1, "eco": 7.25},
                            {"bowler": {"id": "bhuvneshwar", "name": "Bhuvneshwar Kumar"}, "o": 4.0, "m": 0, "r": 42, "w": 1, "eco": 10.5},
                            {"bowler": {"id": "abhishek", "name": "Abhishek Sharma"}, "o": 4.0, "m": 0, "r": 41, "w": 1, "eco": 10.25},
                        ],
                        "fall_of_wickets": ["74/1 (8.2)", "163/2 (16.4)", "188/3 (18.5)", "196/4 (20.0)"],
                    },
                    {
                        "inning": "Sunrisers Hyderabad Inning 2",
                        "totals": {"R": 162, "W": 8, "O": 20.0, "RR": 8.1},
                        "batting": [
                            {"batsman": {"id": "abhishek2", "name": "Abhishek Sharma"}, "r": 34, "b": 28, "4s": 3, "6s": 2, "sr": 121.4, "dismissal": "b Narine"},
                            {"batsman": {"id": "cummins2", "name": "Travis Head"}, "r": 48, "b": 30, "4s": 4, "6s": 3, "sr": 160.0, "dismissal": "c Salt b Russell"},
                            {"batsman": {"id": "heinrich", "name": "Heinrich Klaasen"}, "r": 41, "b": 31, "4s": 3, "6s": 2, "sr": 132.3, "dismissal": "c Narine b Starc"},
                        ],
                        "bowling": [
                            {"bowler": {"id": "narine2", "name": "Sunil Narine"}, "o": 4.0, "m": 0, "r": 24, "w": 2, "eco": 6.0},
                            {"bowler": {"id": "russell2", "name": "Andre Russell"}, "o": 4.0, "m": 0, "r": 38, "w": 3, "eco": 9.5},
                            {"bowler": {"id": "starc", "name": "Mitchell Starc"}, "o": 4.0, "m": 0, "r": 30, "w": 2, "eco": 7.5},
                            {"bowler": {"id": "harshit", "name": "Harshit Rana"}, "o": 4.0, "m": 0, "r": 36, "w": 1, "eco": 9.0},
                            {"bowler": {"id": "chakravarthy", "name": "Varun Chakravarthy"}, "o": 4.0, "m": 0, "r": 34, "w": 0, "eco": 8.5},
                        ],
                        "fall_of_wickets": ["44/1 (5.3)", "93/2 (11.1)", "134/3 (16.0)", "162/8 (20.0)"],
                    },
                ],
                "commentary": [],
            }
        return None

    async def series_matches(self, series_id: str | None = None) -> list[dict]:
        return await self.current_matches()

    async def player_stats(self, player_id: str | None = None) -> list[dict]:
        stats = [
            {"player_id": "dhoni",    "name": "MS Dhoni",          "runs": 312, "matches": 14, "avg": 56.7, "sr": 171.4},
            {"player_id": "gaikwad",  "name": "Ruturaj Gaikwad",   "runs": 498, "matches": 14, "avg": 41.5, "sr": 138.6},
            {"player_id": "virat",    "name": "Virat Kohli",        "runs": 512, "matches": 14, "avg": 42.7, "sr": 148.1},
            {"player_id": "salt",     "name": "Phil Salt",          "runs": 478, "matches": 14, "avg": 36.8, "sr": 162.4},
        ]
        if player_id:
            return [s for s in stats if s["player_id"] == player_id]
        return stats
