from pydantic import BaseModel, Field


class Team(BaseModel):
    id: str
    name: str
    short_name: str | None = None


class Player(BaseModel):
    id: str
    name: str
    role: str | None = None
    batting_style: str | None = None
    bowling_style: str | None = None


class Squad(BaseModel):
    team: Team
    players: list[Player] = Field(default_factory=list)


class Match(BaseModel):
    id: str
    name: str
    status: str
    series: str | None = None
    match_number: str | None = None
    venue: str | None = None
    start_time_utc: str | None = None
    teams: list[Team]
    toss_winner_id: str | None = None
    batting_first_id: str | None = None
    result_summary: str | None = None


class BattingCard(BaseModel):
    player: Player
    runs: int
    balls: int
    fours: int = 0
    sixes: int = 0
    strike_rate: float
    is_batting: bool = False
    dismissal: str | None = None


class BowlingCard(BaseModel):
    player: Player
    overs: str
    maidens: int = 0
    runs: int
    wickets: int
    economy: float


class InningsScore(BaseModel):
    team: Team
    runs: int
    wickets: int
    overs: str
    run_rate: float
    extras: int = 0
    target: int | None = None
    required_rate: float | None = None
    projected_score: int | None = None
    current_partnership: str | None = None
    batting: list[BattingCard] = Field(default_factory=list)
    bowling: list[BowlingCard] = Field(default_factory=list)
    fall_of_wickets: list[str] = Field(default_factory=list)


class CommentaryBall(BaseModel):
    over_ball: str
    batting_team_id: str
    striker: str
    bowler: str
    runs: int
    text: str
    wicket: bool = False
    boundary: bool = False
    tags: list[str] = Field(default_factory=list)


class MatchState(BaseModel):
    batting_team: Team
    bowling_team: Team
    striker: Player
    non_striker: Player
    bowler: Player
    required_runs: int | None = None
    balls_remaining: int | None = None
    current_run_rate: float
    required_run_rate: float | None = None
    projected_score: int
    last_event: str


class OverForecast(BaseModel):
    match_id: str
    next_over: str
    batting_team: Team
    bowling_team: Team
    expected_runs: float
    run_range: str
    wicket_probability: float
    boundary_probability: float
    dot_ball_probability: float
    win_probability: float
    momentum: str
    suggested_strategy: str
    factors: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    feature_importance: dict[str, float] = Field(default_factory=dict)


class PitchReport(BaseModel):
    venue: str
    surface: str
    par_score: int
    batting_first_avg: int
    chasing_avg: int
    pace_assist: float
    spin_assist: float
    dew_factor: float
    boundary_size: str
    notes: list[str] = Field(default_factory=list)


class PlayerForm(BaseModel):
    player: Player
    team: Team
    matches: int
    runs: int = 0
    strike_rate: float = 0
    batting_average: float = 0
    wickets: int = 0
    economy: float = 0
    dot_ball_pct: float = 0
    boundary_pct: float = 0
    recent_trend: str


class MatchupInsight(BaseModel):
    title: str
    value: str
    detail: str
    edge: str


class OverProjection(BaseModel):
    over: str
    phase: str
    expected_runs: float
    wicket_probability: float
    boundary_probability: float
    key_batter: str
    key_bowler: str
    note: str


class MatchCenter(BaseModel):
    match: Match
    status_line: str
    state: MatchState
    innings: list[InningsScore]
    squads: list[Squad]
    commentary: list[CommentaryBall]
    forecast: OverForecast
    pitch: PitchReport | None = None
    player_form: list[PlayerForm] = Field(default_factory=list)
    matchups: list[MatchupInsight] = Field(default_factory=list)
    over_projections: list[OverProjection] = Field(default_factory=list)
    data_mode: str = "mock"
    source_note: str | None = None
