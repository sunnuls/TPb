-- Create player_stats table for aggregated statistics
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    total_hands INTEGER NOT NULL DEFAULT 0,
    hands_won INTEGER NOT NULL DEFAULT 0,
    vpip DECIMAL(5, 2) NOT NULL DEFAULT 0,
    pfr DECIMAL(5, 2) NOT NULL DEFAULT 0,
    aggression DECIMAL(5, 2) NOT NULL DEFAULT 0,
    wtsd DECIMAL(5, 2) NOT NULL DEFAULT 0,
    won_at_showdown DECIMAL(5, 2) NOT NULL DEFAULT 0,
    total_winnings DECIMAL(12, 2) NOT NULL DEFAULT 0,
    last_played_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_name)
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    games_played INTEGER NOT NULL DEFAULT 0,
    total_hands INTEGER NOT NULL DEFAULT 0,
    net_result DECIMAL(12, 2) NOT NULL DEFAULT 0,
    buy_in DECIMAL(10, 2),
    cash_out DECIMAL(10, 2),
    duration_minutes INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_player_stats_name ON player_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_sessions_player_name ON sessions(player_name);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);

-- Add trigger to player_stats table
CREATE TRIGGER update_player_stats_updated_at
    BEFORE UPDATE ON player_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

