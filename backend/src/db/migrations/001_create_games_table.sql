-- Create games table
CREATE TABLE IF NOT EXISTS games (
    id VARCHAR(255) PRIMARY KEY,
    button_position VARCHAR(10) NOT NULL,
    small_blind DECIMAL(10, 2) NOT NULL,
    big_blind DECIMAL(10, 2) NOT NULL,
    ante DECIMAL(10, 2),
    pot DECIMAL(10, 2) NOT NULL DEFAULT 0,
    street VARCHAR(10) NOT NULL DEFAULT 'preflop',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create players table
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(255) NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_idx INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    stack DECIMAL(10, 2) NOT NULL,
    position VARCHAR(10) NOT NULL,
    hole_card1 VARCHAR(3),
    hole_card2 VARCHAR(3),
    folded BOOLEAN NOT NULL DEFAULT false,
    all_in BOOLEAN NOT NULL DEFAULT false,
    bet DECIMAL(10, 2) NOT NULL DEFAULT 0,
    vpip DECIMAL(5, 2),
    pfr DECIMAL(5, 2),
    aggression DECIMAL(5, 2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, player_idx)
);

-- Create board_cards table
CREATE TABLE IF NOT EXISTS board_cards (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(255) NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    card VARCHAR(3) NOT NULL,
    card_order INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, card_order)
);

-- Create actions table
CREATE TABLE IF NOT EXISTS actions (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(255) NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_idx INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    amount DECIMAL(10, 2),
    street VARCHAR(10) NOT NULL,
    pot_at_action DECIMAL(10, 2) NOT NULL,
    stack_at_action DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_games_created_at ON games(created_at);
CREATE INDEX IF NOT EXISTS idx_players_game_id ON players(game_id);
CREATE INDEX IF NOT EXISTS idx_actions_game_id ON actions(game_id);
CREATE INDEX IF NOT EXISTS idx_actions_player_idx ON actions(player_idx);
CREATE INDEX IF NOT EXISTS idx_actions_street ON actions(street);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger to games table
CREATE TRIGGER update_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

