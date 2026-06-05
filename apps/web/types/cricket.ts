export type Team = {
  id: string;
  name: string;
  short_name?: string | null;
};

export type Player = {
  id: string;
  name: string;
  role?: string | null;
};

export type Match = {
  id: string;
  name: string;
  status: string;
  series?: string | null;
  match_number?: string | null;
  venue?: string | null;
  start_time_utc?: string | null;
  teams: Team[];
  result_summary?: string | null;
};

export type BattingCard = {
  player: Player;
  runs: number;
  balls: number;
  fours: number;
  sixes: number;
  strike_rate: number;
  is_batting: boolean;
  dismissal?: string | null;
};

export type BowlingCard = {
  player: Player;
  overs: string;
  maidens: number;
  runs: number;
  wickets: number;
  economy: number;
};

export type InningsScore = {
  team: Team;
  runs: number;
  wickets: number;
  overs: string;
  run_rate: number;
  extras: number;
  target?: number | null;
  required_rate?: number | null;
  projected_score?: number | null;
  current_partnership?: string | null;
  batting: BattingCard[];
  bowling: BowlingCard[];
  fall_of_wickets: string[];
};

export type CommentaryBall = {
  over_ball: string;
  striker: string;
  bowler: string;
  runs: number;
  text: string;
  wicket: boolean;
  boundary: boolean;
  tags: string[];
};

export type MatchState = {
  batting_team: Team;
  bowling_team: Team;
  striker: Player;
  non_striker: Player;
  bowler: Player;
  required_runs?: number | null;
  balls_remaining?: number | null;
  current_run_rate: number;
  required_run_rate?: number | null;
  projected_score: number;
  last_event: string;
};

export type OverForecast = {
  match_id: string;
  next_over: string;
  batting_team: Team;
  bowling_team: Team;
  expected_runs: number;
  run_range: string;
  wicket_probability: number;
  boundary_probability: number;
  dot_ball_probability: number;
  win_probability: number;
  momentum: string;
  suggested_strategy: string;
  factors: string[];
  confidence: number;
  feature_importance: Record<string, number>;
};

export type Squad = {
  team: Team;
  players: Player[];
};

export type MatchCenter = {
  match: Match;
  status_line: string;
  state: MatchState;
  innings: InningsScore[];
  squads: Squad[];
  commentary: CommentaryBall[];
  forecast: OverForecast;
  data_mode?: string;
  source_note?: string | null;
};

export type LiveMatchResponse = {
  liveMatch: MatchCenter | null;
  recentMatch: MatchCenter | null;
  upcomingMatch: MatchCenter | null;
  fetchedAt: string;
};
