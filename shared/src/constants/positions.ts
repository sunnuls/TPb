import { Position } from '../types/poker';

export const POSITIONS: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'];

export const POSITION_NAMES: Record<Position, string> = {
  'BTN': 'Button',
  'SB': 'Small Blind',
  'BB': 'Big Blind',
  'UTG': 'Under the Gun',
  'UTG+1': 'UTG+1',
  'MP': 'Middle Position',
  'HJ': 'Hijack',
  'CO': 'Cutoff',
};

export const POSITION_ORDER: Record<Position, number> = {
  'UTG': 0,
  'UTG+1': 1,
  'MP': 2,
  'HJ': 3,
  'CO': 4,
  'BTN': 5,
  'SB': 6,
  'BB': 7,
};

export function isInPosition(heroPosition: Position, villainPosition: Position): boolean {
  return POSITION_ORDER[heroPosition] > POSITION_ORDER[villainPosition];
}

export function getNextPosition(current: Position, playerCount: number): Position {
  const currentIdx = POSITIONS.indexOf(current);
  const nextIdx = (currentIdx + 1) % playerCount;
  return POSITIONS[nextIdx];
}

