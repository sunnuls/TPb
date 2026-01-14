export type Card = `${Rank}${Suit}`;
export type Rank = 'A' | 'K' | 'Q' | 'J' | 'T' | '9' | '8' | '7' | '6' | '5' | '4' | '3' | '2';
export type Suit = 's' | 'h' | 'd' | 'c'; // spades, hearts, diamonds, clubs

export type Position = 'BTN' | 'SB' | 'BB' | 'UTG' | 'UTG+1' | 'MP' | 'HJ' | 'CO';

export type Street = 'preflop' | 'flop' | 'turn' | 'river';

export type Action = 'fold' | 'check' | 'call' | 'raise' | 'bet' | 'all-in';

export interface Hand {
  card1: Card;
  card2: Card;
}

export interface Equity {
  equity: number; // 0-1
  confidence: number; // 0-1
  wins: number;
  ties: number;
  losses: number;
}

export interface Range {
  [hand: string]: number; // hand -> percentage weight
}

export interface HandStrength {
  hand: Hand;
  strength: number; // 0-1 (strength ranking)
  rank: string; // e.g., "pair of aces"
  description: string;
}

export interface PlayerAction {
  playerIdx: number;
  action: Action;
  amount: number;
  timestamp: Date;
  street: Street;
  potAtAction: number;
  stackAtAction: number;
}

export interface PlayerState {
  idx: number;
  name: string;
  stack: number;
  position: Position;
  holeCards?: Card[];
  folded: boolean;
  allIn: boolean;
  bet: number;
  vpip?: number; // Voluntarily Put $ In Pot
  pfr?: number;  // Pre-flop Raise
  aggression?: number; // Aggression factor
}

export interface GameState {
  id: string;
  players: PlayerState[];
  buttonPosition: Position;
  blinds: {
    small: number;
    big: number;
    ante?: number;
  };
  pot: number;
  board: Card[];
  street: Street;
  currentPlayerIdx: number;
  createdAt: Date;
  updatedAt: Date;
  status: 'active' | 'completed' | 'paused';
}

export interface GTORecommendation {
  action: Action;
  frequency: number; // 0-1
  sizings?: number[]; // bet/raise sizings in BB
  reasoning: string;
  evDifference?: number; // EV compared to next best action
}

export interface StrategyRecommendation {
  primary: GTORecommendation;
  alternatives: GTORecommendation[];
  exploitative?: {
    recommendation: GTORecommendation;
    reason: string;
  };
}

