CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS teams (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  short_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
  id TEXT PRIMARY KEY,
  team_id TEXT REFERENCES teams(id),
  name TEXT NOT NULL,
  role TEXT,
  batting_style TEXT,
  bowling_style TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS matches (
  id TEXT PRIMARY KEY,
  series_id TEXT,
  name TEXT NOT NULL,
  match_type TEXT,
  status TEXT NOT NULL,
  venue TEXT,
  start_time_utc TIMESTAMPTZ,
  team_a_id TEXT REFERENCES teams(id),
  team_b_id TEXT REFERENCES teams(id),
  toss_winner_id TEXT REFERENCES teams(id),
  batting_first_id TEXT REFERENCES teams(id),
  winner_id TEXT REFERENCES teams(id),
  raw_provider_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS innings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  team_id TEXT NOT NULL REFERENCES teams(id),
  innings_number INT NOT NULL,
  runs INT NOT NULL DEFAULT 0,
  wickets INT NOT NULL DEFAULT 0,
  overs NUMERIC(4,1) NOT NULL DEFAULT 0,
  run_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
  UNIQUE (match_id, innings_number)
);

CREATE TABLE IF NOT EXISTS ball_by_ball (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  innings_number INT NOT NULL,
  over_number INT NOT NULL,
  ball_number INT NOT NULL,
  batting_team_id TEXT REFERENCES teams(id),
  bowling_team_id TEXT REFERENCES teams(id),
  striker_id TEXT REFERENCES players(id),
  non_striker_id TEXT REFERENCES players(id),
  bowler_id TEXT REFERENCES players(id),
  runs_batter INT NOT NULL DEFAULT 0,
  runs_extras INT NOT NULL DEFAULT 0,
  wicket_type TEXT,
  commentary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (match_id, innings_number, over_number, ball_number)
);

CREATE TABLE IF NOT EXISTS predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  ball_id UUID REFERENCES ball_by_ball(id),
  model_version TEXT NOT NULL,
  predicted_for_over INT,
  batting_team_id TEXT REFERENCES teams(id),
  bowling_team_id TEXT REFERENCES teams(id),
  expected_runs NUMERIC(5,2) NOT NULL,
  wicket_probability NUMERIC(5,4) NOT NULL,
  boundary_probability NUMERIC(5,4) NOT NULL,
  dot_ball_probability NUMERIC(5,4) NOT NULL,
  win_probability NUMERIC(5,4) NOT NULL,
  features JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS points_table (
  series_id TEXT NOT NULL,
  team_id TEXT NOT NULL REFERENCES teams(id),
  played INT NOT NULL DEFAULT 0,
  won INT NOT NULL DEFAULT 0,
  lost INT NOT NULL DEFAULT 0,
  no_result INT NOT NULL DEFAULT 0,
  points INT NOT NULL DEFAULT 0,
  net_run_rate NUMERIC(6,3) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (series_id, team_id)
);

CREATE TABLE IF NOT EXISTS player_statistics (
  series_id TEXT NOT NULL,
  player_id TEXT NOT NULL REFERENCES players(id),
  team_id TEXT REFERENCES teams(id),
  matches INT NOT NULL DEFAULT 0,
  runs INT NOT NULL DEFAULT 0,
  balls_faced INT NOT NULL DEFAULT 0,
  strike_rate NUMERIC(6,2) NOT NULL DEFAULT 0,
  batting_average NUMERIC(6,2) NOT NULL DEFAULT 0,
  wickets INT NOT NULL DEFAULT 0,
  balls_bowled INT NOT NULL DEFAULT 0,
  economy NUMERIC(6,2) NOT NULL DEFAULT 0,
  dot_ball_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
  boundary_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (series_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_status_start ON matches(status, start_time_utc);
CREATE INDEX IF NOT EXISTS idx_ball_by_ball_match ON ball_by_ball(match_id, innings_number, over_number, ball_number);
CREATE INDEX IF NOT EXISTS idx_predictions_match_created ON predictions(match_id, created_at DESC);
