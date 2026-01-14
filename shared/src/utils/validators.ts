import { Card, Position, Action, Street } from '../types/poker';
import { parseCard } from './cardUtils';
import { POSITIONS } from '../constants/positions';
import { LIMITS } from '../constants/limits';

export function isValidCard(card: string): card is Card {
  return parseCard(card) !== null;
}

export function isValidPosition(position: string): position is Position {
  return POSITIONS.includes(position as Position);
}

export function isValidAction(action: string): action is Action {
  const validActions: Action[] = ['fold', 'check', 'call', 'raise', 'bet', 'all-in'];
  return validActions.includes(action as Action);
}

export function isValidStreet(street: string): street is Street {
  const validStreets: Street[] = ['preflop', 'flop', 'turn', 'river'];
  return validStreets.includes(street as Street);
}

export function validatePlayerCount(count: number): boolean {
  return count >= LIMITS.MIN_PLAYERS && count <= LIMITS.MAX_PLAYERS;
}

export function validateStack(stack: number, bigBlind: number): boolean {
  const stackInBB = stack / bigBlind;
  return stackInBB >= LIMITS.MIN_BUY_IN && stackInBB <= LIMITS.MAX_BUY_IN;
}

export function validateBet(bet: number, pot: number, stack: number): boolean {
  if (bet < 0) return false;
  if (bet > stack) return false;
  return true;
}

export function validateRaise(
  raiseAmount: number,
  previousBet: number,
  minRaise: number,
  stack: number
): { valid: boolean; reason?: string } {
  if (raiseAmount > stack) {
    return { valid: false, reason: 'Raise amount exceeds stack' };
  }
  
  if (raiseAmount < previousBet + minRaise) {
    return { valid: false, reason: 'Raise must be at least minimum raise' };
  }
  
  if (raiseAmount > previousBet * LIMITS.MAX_RAISE_FACTOR) {
    return { valid: false, reason: 'Raise exceeds maximum raise factor' };
  }
  
  return { valid: true };
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export function validateGameStateInput(data: any): ValidationError[] {
  const errors: ValidationError[] = [];
  
  if (!data.players || !Array.isArray(data.players)) {
    errors.push({
      field: 'players',
      message: 'Players must be an array',
      code: 'INVALID_TYPE',
    });
  } else {
    if (!validatePlayerCount(data.players.length)) {
      errors.push({
        field: 'players',
        message: `Player count must be between ${LIMITS.MIN_PLAYERS} and ${LIMITS.MAX_PLAYERS}`,
        code: 'INVALID_PLAYER_COUNT',
      });
    }
    
    data.players.forEach((player: any, idx: number) => {
      if (!player.name || typeof player.name !== 'string') {
        errors.push({
          field: `players[${idx}].name`,
          message: 'Player name is required',
          code: 'MISSING_FIELD',
        });
      }
      
      if (typeof player.stack !== 'number' || player.stack <= 0) {
        errors.push({
          field: `players[${idx}].stack`,
          message: 'Player stack must be a positive number',
          code: 'INVALID_VALUE',
        });
      }
      
      if (!isValidPosition(player.position)) {
        errors.push({
          field: `players[${idx}].position`,
          message: 'Invalid position',
          code: 'INVALID_POSITION',
        });
      }
    });
  }
  
  if (!isValidPosition(data.buttonPosition)) {
    errors.push({
      field: 'buttonPosition',
      message: 'Invalid button position',
      code: 'INVALID_POSITION',
    });
  }
  
  if (typeof data.smallBlind !== 'number' || data.smallBlind <= 0) {
    errors.push({
      field: 'smallBlind',
      message: 'Small blind must be a positive number',
      code: 'INVALID_VALUE',
    });
  }
  
  if (typeof data.bigBlind !== 'number' || data.bigBlind <= 0) {
    errors.push({
      field: 'bigBlind',
      message: 'Big blind must be a positive number',
      code: 'INVALID_VALUE',
    });
  }
  
  return errors;
}

