import { Action, Street, PlayerAction } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface ParsedAction {
  playerIdx: number;
  playerName: string;
  action: Action;
  amount: number;
  street: Street;
  timestamp: Date;
  valid: boolean;
  errors?: string[];
}

export interface ActionContext {
  pot: number;
  playerStack: number;
  currentBet: number;
  minimumRaise: number;
  bigBlind: number;
  street: Street;
  allowedActions: Action[];
}

/**
 * Action parser and validator
 */
export class ActionParser {
  /**
   * Parse action from text or object
   */
  parseAction(data: any, context: ActionContext): ParsedAction {
    logger.debug('Parsing action', data);

    const action: ParsedAction = {
      playerIdx: data.playerIdx || data.seat || 0,
      playerName: data.playerName || data.name || 'Unknown',
      action: this.normalizeAction(data.action),
      amount: parseFloat(data.amount || 0),
      street: data.street || context.street,
      timestamp: new Date(data.timestamp || Date.now()),
      valid: false,
    };

    // Validate action
    const validation = this.validateAction(action, context);
    action.valid = validation.valid;
    action.errors = validation.errors;

    return action;
  }

  /**
   * Normalize action string
   */
  private normalizeAction(action: string): Action {
    const normalized = action.toLowerCase().trim();

    if (normalized === 'f' || normalized.includes('fold')) return 'fold';
    if (normalized === 'x' || normalized === 'k' || normalized.includes('check')) return 'check';
    if (normalized === 'c' || normalized.includes('call')) return 'call';
    if (normalized === 'r' || normalized.includes('raise')) return 'raise';
    if (normalized === 'b' || normalized.includes('bet')) return 'bet';
    if (normalized.includes('all') && normalized.includes('in')) return 'all-in';

    return 'check'; // Default fallback
  }

  /**
   * Validate action against game context
   */
  validateAction(
    action: ParsedAction,
    context: ActionContext
  ): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check if action is allowed
    if (!context.allowedActions.includes(action.action)) {
      errors.push(`Action '${action.action}' is not allowed in this context`);
    }

    // Validate amounts
    switch (action.action) {
      case 'fold':
      case 'check':
        // No amount validation needed
        break;

      case 'call':
        const callAmount = context.currentBet;
        if (action.amount !== callAmount && action.amount > 0) {
          errors.push(`Call amount should be ${callAmount}, got ${action.amount}`);
        }
        if (callAmount > context.playerStack) {
          errors.push('Not enough chips to call (should be all-in)');
        }
        break;

      case 'bet':
        if (action.amount <= 0) {
          errors.push('Bet amount must be positive');
        }
        if (action.amount < context.bigBlind) {
          errors.push(`Minimum bet is ${context.bigBlind}`);
        }
        if (action.amount > context.playerStack) {
          errors.push('Bet exceeds player stack');
        }
        break;

      case 'raise':
        if (action.amount <= context.currentBet) {
          errors.push(`Raise must be more than current bet (${context.currentBet})`);
        }
        if (action.amount < context.currentBet + context.minimumRaise) {
          errors.push(
            `Minimum raise is ${context.currentBet + context.minimumRaise}`
          );
        }
        if (action.amount > context.playerStack) {
          errors.push('Raise exceeds player stack');
        }
        break;

      case 'all-in':
        if (action.amount !== context.playerStack) {
          errors.push(`All-in must be entire stack (${context.playerStack})`);
        }
        break;
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Parse action from text description
   */
  parseActionText(text: string): { action: Action; amount?: number } | null {
    const cleaned = text.toLowerCase().trim();

    // Pattern matching for common formats
    const patterns = [
      { regex: /^(fold|f)$/i, action: 'fold' as Action },
      { regex: /^(check|x|k)$/i, action: 'check' as Action },
      { regex: /^(call|c)(?:\s+(\d+(?:\.\d+)?))?/i, action: 'call' as Action },
      { regex: /^(bet|b)\s+(\d+(?:\.\d+)?)/i, action: 'bet' as Action },
      { regex: /^(raise|r)\s+(?:to\s+)?(\d+(?:\.\d+)?)/i, action: 'raise' as Action },
      { regex: /^(all[-\s]?in|allin|ai)/i, action: 'all-in' as Action },
    ];

    for (const pattern of patterns) {
      const match = cleaned.match(pattern.regex);
      if (match) {
        const amount = match[2] ? parseFloat(match[2]) : undefined;
        return { action: pattern.action, amount };
      }
    }

    return null;
  }

  /**
   * Get allowed actions based on context
   */
  getAllowedActions(context: {
    street: Street;
    currentBet: number;
    playerStack: number;
    canCheck: boolean;
  }): Action[] {
    const actions: Action[] = [];

    // Fold is always allowed (except when can check for free)
    if (context.currentBet > 0 || !context.canCheck) {
      actions.push('fold');
    }

    // Check if no bet to face
    if (context.currentBet === 0 && context.canCheck) {
      actions.push('check');
    }

    // Call if facing a bet
    if (context.currentBet > 0 && context.playerStack >= context.currentBet) {
      actions.push('call');
    }

    // Bet if no bet to face
    if (context.currentBet === 0 && context.playerStack > 0) {
      actions.push('bet');
    }

    // Raise if facing a bet
    if (context.currentBet > 0 && context.playerStack > context.currentBet) {
      actions.push('raise');
    }

    // All-in is always an option if not all-in already
    if (context.playerStack > 0) {
      actions.push('all-in');
    }

    return actions;
  }

  /**
   * Calculate minimum raise
   */
  calculateMinimumRaise(currentBet: number, lastRaiseSize: number, bigBlind: number): number {
    // Minimum raise is the size of the last raise, or big blind if no raises yet
    return Math.max(lastRaiseSize, bigBlind);
  }

  /**
   * Convert action to string description
   */
  actionToString(action: ParsedAction): string {
    switch (action.action) {
      case 'fold':
        return `${action.playerName} folds`;
      case 'check':
        return `${action.playerName} checks`;
      case 'call':
        return `${action.playerName} calls ${action.amount}`;
      case 'bet':
        return `${action.playerName} bets ${action.amount}`;
      case 'raise':
        return `${action.playerName} raises to ${action.amount}`;
      case 'all-in':
        return `${action.playerName} goes all-in for ${action.amount}`;
      default:
        return `${action.playerName} ${action.action}`;
    }
  }
}

