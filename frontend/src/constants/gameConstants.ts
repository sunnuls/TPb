export const GAME_CONSTANTS = {
  MIN_PLAYERS: 2,
  MAX_PLAYERS: 10,
  MIN_BUY_IN_BB: 20,
  MAX_BUY_IN_BB: 200,
  
  STREETS: ['preflop', 'flop', 'turn', 'river'] as const,
  ACTIONS: ['fold', 'check', 'call', 'raise', 'bet', 'all-in'] as const,
  
  POSITIONS: ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'] as const,
  
  DEFAULT_STAKES: {
    smallBlind: 0.5,
    bigBlind: 1.0,
    ante: 0,
  },
} as const;

export const HAND_RANKS = [
  'High Card',
  'One Pair',
  'Two Pair',
  'Three of a Kind',
  'Straight',
  'Flush',
  'Full House',
  'Four of a Kind',
  'Straight Flush',
  'Royal Flush',
] as const;

export const SUITS = {
  s: '♠',
  h: '♥',
  d: '♦',
  c: '♣',
} as const;

export const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'] as const;

