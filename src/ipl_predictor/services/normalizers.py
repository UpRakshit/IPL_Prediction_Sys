import re

from ipl_predictor.live.schemas import BattingCard, BowlingCard, InningsScore, Match, Player, Team


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def team_from_name(name: str | None) -> Team:
    display = name or "Unknown"
    words = [part for part in re.split(r"\s+", display) if part]
    short_name = "".join(part[0] for part in words[:3]).upper() or None
    return Team(id=slugify(display), name=display, short_name=short_name)


def player_from_provider(value: dict | str | None) -> Player:
    if isinstance(value, dict):
        name = value.get("name") or "Unknown"
        return Player(id=str(value.get("id") or slugify(name)), name=name)
    name = value or "Unknown"
    return Player(id=slugify(name), name=name)


def match_from_provider(raw: dict) -> Match:
    teams = [team_from_name(team) for team in raw.get("teams", []) if isinstance(team, str)]
    if not teams:
        name = raw.get("name", "")
        teams = [team_from_name(part.strip()) for part in re.split(r"\s+v(?:s)?\.?\s+", name) if part.strip()]

    return Match(
        id=str(raw.get("id") or raw.get("match_id") or slugify(raw.get("name", "match"))),
        name=raw.get("name") or "Cricket match",
        status=str(raw.get("status") or "unknown"),
        series=raw.get("series") or raw.get("series_name"),
        match_number=raw.get("matchType") or raw.get("match_number"),
        venue=raw.get("venue"),
        start_time_utc=raw.get("dateTimeGMT") or raw.get("date_start_utc"),
        teams=teams,
        toss_winner_id=slugify(raw["tossWinner"]) if raw.get("tossWinner") else None,
        batting_first_id=None,
        result_summary=raw.get("status"),
    )


def innings_from_scorecard(data: dict) -> list[InningsScore]:
    innings: list[InningsScore] = []
    for item in data.get("scorecard", []) or []:
        if not isinstance(item, dict):
            continue
        totals = item.get("totals") or {}
        inning_name = item.get("inning") or "Innings"
        team_name = inning_name.split(" Inning")[0].strip()
        team = team_from_name(team_name)
        runs = int(totals.get("R") or totals.get("r") or 0)
        wickets = int(totals.get("W") or totals.get("w") or 0)
        overs = str(totals.get("O") or totals.get("o") or "0")
        run_rate = float(totals.get("RR") or totals.get("rr") or 0)
        innings.append(
            InningsScore(
                team=team,
                runs=runs,
                wickets=wickets,
                overs=overs,
                run_rate=run_rate,
                extras=int((item.get("extras") or {}).get("r") or 0),
                batting=[_batting_card(row) for row in item.get("batting", []) if isinstance(row, dict)],
                bowling=[_bowling_card(row) for row in item.get("bowling", []) if isinstance(row, dict)],
                fall_of_wickets=[
                    str(row)
                    for row in item.get("fall_of_wickets", [])
                    if isinstance(row, str | int | float)
                ],
            )
        )
    return innings


def innings_from_scores(raw: dict) -> list[InningsScore]:
    innings: list[InningsScore] = []
    for score in raw.get("score", []) or []:
        if not isinstance(score, dict):
            continue
        inning_name = score.get("inning") or "Innings"
        team_name = inning_name.split(" Inning")[0].strip()
        overs = str(score.get("o") or "0")
        runs = int(score.get("r") or 0)
        innings.append(
            InningsScore(
                team=team_from_name(team_name),
                runs=runs,
                wickets=int(score.get("w") or 0),
                overs=overs,
                run_rate=_run_rate(runs, overs),
            )
        )
    return innings


def overs_to_float(overs: str | float | int | None) -> float:
    if overs is None:
        return 0.0
    text = str(overs)
    if "." not in text:
        return float(text)
    whole, balls = text.split(".", 1)
    return int(whole or 0) + int((balls or "0")[0]) / 6


def _run_rate(runs: int, overs: str) -> float:
    value = overs_to_float(overs)
    return round(runs / value, 2) if value else 0


def _batting_card(row: dict) -> BattingCard:
    runs = int(row.get("r") or 0)
    balls = int(row.get("b") or 0)
    return BattingCard(
        player=player_from_provider(row.get("batsman")),
        runs=runs,
        balls=balls,
        fours=int(row.get("4s") or 0),
        sixes=int(row.get("6s") or 0),
        strike_rate=float(row.get("sr") or (runs / balls * 100 if balls else 0)),
        dismissal=row.get("dismissal-text") or row.get("dismissal"),
        is_batting=row.get("is_batting") if "is_batting" in row else (row.get("dismissal") in {None, "not out", "batting*"}),
    )


def _bowling_card(row: dict) -> BowlingCard:
    return BowlingCard(
        player=player_from_provider(row.get("bowler")),
        overs=str(row.get("o") or "0"),
        maidens=int(row.get("m") or 0),
        runs=int(row.get("r") or 0),
        wickets=int(row.get("w") or 0),
        economy=float(row.get("eco") or 0),
    )
