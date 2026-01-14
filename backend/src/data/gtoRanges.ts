import { Position } from '@tpb/shared';

/**
 * GTO Preflop Ranges Database
 * Based on modern solver solutions (simplified for v1)
 */

export interface GTORange {
  position: Position;
  action: 'open' | '3bet' | 'call' | 'cold_call' | '4bet';
  vsPosition?: Position;
  range: string; // Range notation
  frequency: number; // 0-1
  stackDepth?: 'shallow' | 'medium' | 'deep';
  description: string;
}

/**
 * Opening Ranges (RFI - Raise First In)
 */
export const OPENING_RANGES: Record<Position, GTORange> = {
  'UTG': {
    position: 'UTG',
    action: 'open',
    range: '22+,A2s+,K9s+,Q9s+,JTs,T9s,ATo+,KJo+,QJo',
    frequency: 1.0,
    description: 'UTG Open ~12%',
  },
  'UTG+1': {
    position: 'UTG+1',
    action: 'open',
    range: '22+,A2s+,K8s+,Q9s+,J9s+,T8s+,98s,ATo+,KTo+,QJo',
    frequency: 1.0,
    description: 'MP Open ~14%',
  },
  'MP': {
    position: 'MP',
    action: 'open',
    range: '22+,A2s+,K7s+,Q8s+,J8s+,T8s+,97s+,87s,A9o+,KTo+,QTo+,JTo',
    frequency: 1.0,
    description: 'MP Open ~17%',
  },
  'HJ': {
    position: 'HJ',
    action: 'open',
    range: '22+,A2s+,K6s+,Q7s+,J7s+,T7s+,97s+,86s+,76s,A8o+,K9o+,QTo+,JTo',
    frequency: 1.0,
    description: 'HJ Open ~22%',
  },
  'CO': {
    position: 'CO',
    action: 'open',
    range: '22+,A2s+,K4s+,Q5s+,J6s+,T6s+,96s+,86s+,75s+,65s,54s,A5o+,K9o+,Q9o+,JTo',
    frequency: 1.0,
    description: 'CO Open ~28%',
  },
  'BTN': {
    position: 'BTN',
    action: 'open',
    range: '22+,A2s+,K2s+,Q2s+,J4s+,T6s+,95s+,85s+,75s+,64s+,54s,43s,A2o+,K7o+,Q8o+,J9o+,T9o',
    frequency: 1.0,
    description: 'BTN Open ~48%',
  },
  'SB': {
    position: 'SB',
    action: 'open',
    range: '22+,A2s+,K2s+,Q3s+,J5s+,T6s+,96s+,85s+,75s+,64s+,54s,A2o+,K8o+,Q9o+,J9o+,T9o',
    frequency: 1.0,
    description: 'SB Open ~40%',
  },
  'BB': {
    position: 'BB',
    action: 'open',
    range: '22+,A2s+,K2s+,Q2s+,J2s+,T5s+,95s+,85s+,75s+,64s+,54s,A2o+,K5o+,Q7o+,J8o+,T8o+,98o',
    frequency: 1.0,
    description: 'BB vs SB Defense ~52%',
  },
};

/**
 * 3-Bet Ranges
 */
export const THREE_BET_RANGES: GTORange[] = [
  {
    position: 'BTN',
    action: '3bet',
    vsPosition: 'CO',
    range: 'QQ+,AKs,AKo,AQs,AJs,KQs,A5s-A2s,K5s,Q5s,J5s,T5s,95s,85s,76s,65s,54s',
    frequency: 0.11,
    description: 'BTN vs CO 3-bet ~11%',
  },
  {
    position: 'BTN',
    action: '3bet',
    vsPosition: 'HJ',
    range: 'TT+,AQs+,AQo+,KQs,A5s-A2s,K5s,Q5s,J5s',
    frequency: 0.09,
    description: 'BTN vs HJ 3-bet ~9%',
  },
  {
    position: 'SB',
    action: '3bet',
    vsPosition: 'BTN',
    range: '99+,ATs+,ATo+,KQs,A5s-A2s,K9s,Q9s,J9s,T9s',
    frequency: 0.12,
    description: 'SB vs BTN 3-bet ~12%',
  },
  {
    position: 'BB',
    action: '3bet',
    vsPosition: 'BTN',
    range: '88+,A9s+,A5s-A2s,AJo+,K9s+,KQo,Q9s+,J9s+,T9s',
    frequency: 0.14,
    description: 'BB vs BTN 3-bet ~14%',
  },
  {
    position: 'BB',
    action: '3bet',
    vsPosition: 'SB',
    range: '66+,A7s+,A5s-A2s,ATo+,K8s+,KJo+,Q9s+,J9s+,T8s+,98s',
    frequency: 0.15,
    description: 'BB vs SB 3-bet ~15%',
  },
];

/**
 * Cold Call Ranges
 */
export const COLD_CALL_RANGES: GTORange[] = [
  {
    position: 'BB',
    action: 'cold_call',
    vsPosition: 'BTN',
    range: '22-77,A2s-A8s,K2s-K8s,Q6s-Q8s,J7s-J8s,T7s-T8s,97s-98s,87s,76s,A2o-ATo,K9o,Q9o-QJo,J9o-JTo,T9o',
    frequency: 1.0,
    description: 'BB call vs BTN open ~38%',
  },
  {
    position: 'BB',
    action: 'cold_call',
    vsPosition: 'CO',
    range: '22-88,A2s-A9s,K6s-K9s,Q8s-Q9s,J8s-J9s,T8s-T9s,98s,A9o,KJo,QJo',
    frequency: 1.0,
    description: 'BB call vs CO open ~28%',
  },
];

/**
 * 4-Bet Ranges
 */
export const FOUR_BET_RANGES: GTORange[] = [
  {
    position: 'BTN',
    action: '4bet',
    vsPosition: 'BB',
    range: 'QQ+,AKs,AKo,A5s-A2s',
    frequency: 0.30,
    description: 'BTN 4-bet vs BB 3-bet (polarized)',
  },
  {
    position: 'BB',
    action: '4bet',
    vsPosition: 'BTN',
    range: 'KK+,AKs,A5s-A2s',
    frequency: 0.25,
    description: 'BB 4-bet vs BTN 3-bet',
  },
];

/**
 * Get opening range for position
 */
export function getOpeningRange(position: Position): GTORange {
  return OPENING_RANGES[position];
}

/**
 * Get 3-bet range for position vs opponent position
 */
export function get3BetRange(heroPosition: Position, villainPosition: Position): GTORange | null {
  return THREE_BET_RANGES.find(
    r => r.position === heroPosition && r.vsPosition === villainPosition
  ) || null;
}

/**
 * Get cold call range
 */
export function getColdCallRange(heroPosition: Position, villainPosition: Position): GTORange | null {
  return COLD_CALL_RANGES.find(
    r => r.position === heroPosition && r.vsPosition === villainPosition
  ) || null;
}

/**
 * Get 4-bet range
 */
export function get4BetRange(heroPosition: Position, villainPosition: Position): GTORange | null {
  return FOUR_BET_RANGES.find(
    r => r.position === heroPosition && r.vsPosition === villainPosition
  ) || null;
}

/**
 * Get all GTO ranges
 */
export function getAllGTORanges(): {
  opening: Record<Position, GTORange>;
  threeBet: GTORange[];
  coldCall: GTORange[];
  fourBet: GTORange[];
} {
  return {
    opening: OPENING_RANGES,
    threeBet: THREE_BET_RANGES,
    coldCall: COLD_CALL_RANGES,
    fourBet: FOUR_BET_RANGES,
  };
}

