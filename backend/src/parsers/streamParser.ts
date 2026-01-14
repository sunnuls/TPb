import { Card, Position, Street, Action } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface StreamData {
  source: 'pokerstars' | 'gg' | 'generic';
  timestamp: Date;
  tableId: string;
  gameType: 'holdem' | 'omaha';
  stakes: {
    smallBlind: number;
    bigBlind: number;
    ante?: number;
  };
  players: StreamPlayer[];
  board: Card[];
  street: Street;
  pot: number;
  actions: StreamAction[];
}

export interface StreamPlayer {
  seatNumber: number;
  name: string;
  stack: number;
  position?: Position;
  holeCards?: Card[];
  isActive: boolean;
  hasFolded: boolean;
  currentBet: number;
}

export interface StreamAction {
  playerName: string;
  action: Action;
  amount?: number;
  timestamp: Date;
  street: Street;
}

/**
 * Generic stream parser for poker table data
 */
export class StreamParser {
  /**
   * Parse stream data from generic format
   */
  parseStreamData(data: any): StreamData {
    logger.info('Parsing stream data');

    try {
      // Detect source format
      if (data.source === 'pokerstars' || data.table?.includes('PokerStars')) {
        return this.parsePokerStarsStream(data);
      } else if (data.source === 'gg' || data.table?.includes('GG')) {
        return this.parseGGStream(data);
      } else {
        return this.parseGenericStream(data);
      }
    } catch (error) {
      logger.error(`Stream parsing failed: ${error}`);
      throw error;
    }
  }

  /**
   * Parse PokerStars stream format
   */
  private parsePokerStarsStream(data: any): StreamData {
    return {
      source: 'pokerstars',
      timestamp: new Date(data.timestamp || Date.now()),
      tableId: data.tableId || 'unknown',
      gameType: this.parseGameType(data.gameType || 'holdem'),
      stakes: {
        smallBlind: parseFloat(data.smallBlind || 0.5),
        bigBlind: parseFloat(data.bigBlind || 1.0),
        ante: data.ante ? parseFloat(data.ante) : undefined,
      },
      players: this.parsePlayers(data.players || []),
      board: this.parseBoard(data.board || []),
      street: this.parseStreet(data.street || 'preflop'),
      pot: parseFloat(data.pot || 0),
      actions: this.parseActions(data.actions || []),
    };
  }

  /**
   * Parse GGPoker stream format
   */
  private parseGGStream(data: any): StreamData {
    // GG format is similar to PokerStars with minor differences
    return this.parsePokerStarsStream(data);
  }

  /**
   * Parse generic stream format
   */
  private parseGenericStream(data: any): StreamData {
    logger.warn('Using generic stream parser - may have limited accuracy');

    return {
      source: 'generic',
      timestamp: new Date(),
      tableId: data.table_id || data.tableId || 'generic_table',
      gameType: 'holdem',
      stakes: {
        smallBlind: 0.5,
        bigBlind: 1.0,
      },
      players: [],
      board: [],
      street: 'preflop',
      pot: 0,
      actions: [],
    };
  }

  /**
   * Parse game type
   */
  private parseGameType(gameType: string): 'holdem' | 'omaha' {
    const normalized = gameType.toLowerCase();
    if (normalized.includes('omaha')) {
      return 'omaha';
    }
    return 'holdem';
  }

  /**
   * Parse players from stream data
   */
  private parsePlayers(players: any[]): StreamPlayer[] {
    return players.map((p, idx) => ({
      seatNumber: p.seat || p.seatNumber || idx + 1,
      name: p.name || p.playerName || `Player ${idx + 1}`,
      stack: parseFloat(p.stack || p.chips || 0),
      position: p.position as Position | undefined,
      holeCards: p.holeCards ? this.parseCards(p.holeCards) : undefined,
      isActive: p.isActive !== false,
      hasFolded: p.folded === true || p.hasFolded === true,
      currentBet: parseFloat(p.bet || p.currentBet || 0),
    }));
  }

  /**
   * Parse board cards
   */
  private parseBoard(board: any[]): Card[] {
    if (Array.isArray(board)) {
      return this.parseCards(board);
    }
    return [];
  }

  /**
   * Parse cards from various formats
   */
  private parseCards(cards: any[]): Card[] {
    return cards
      .map(card => {
        if (typeof card === 'string') {
          return this.normalizeCard(card);
        } else if (card.rank && card.suit) {
          return this.normalizeCard(`${card.rank}${card.suit}`);
        }
        return null;
      })
      .filter((card): card is Card => card !== null);
  }

  /**
   * Normalize card notation
   */
  private normalizeCard(card: string): Card | null {
    if (card.length < 2) return null;

    const rank = card[0].toUpperCase();
    const suit = card[1].toLowerCase();

    // Validate rank
    if (!'AKQJT98765432'.includes(rank)) return null;

    // Validate suit
    if (!'shdc'.includes(suit)) return null;

    return `${rank}${suit}` as Card;
  }

  /**
   * Parse street
   */
  private parseStreet(street: string): Street {
    const normalized = street.toLowerCase();

    if (normalized.includes('river')) return 'river';
    if (normalized.includes('turn')) return 'turn';
    if (normalized.includes('flop')) return 'flop';
    return 'preflop';
  }

  /**
   * Parse actions
   */
  private parseActions(actions: any[]): StreamAction[] {
    return actions.map(a => ({
      playerName: a.player || a.playerName || 'Unknown',
      action: this.normalizeAction(a.action),
      amount: a.amount ? parseFloat(a.amount) : undefined,
      timestamp: new Date(a.timestamp || Date.now()),
      street: this.parseStreet(a.street || 'preflop'),
    }));
  }

  /**
   * Normalize action
   */
  private normalizeAction(action: string): Action {
    const normalized = action.toLowerCase();

    if (normalized.includes('fold')) return 'fold';
    if (normalized.includes('check')) return 'check';
    if (normalized.includes('call')) return 'call';
    if (normalized.includes('raise')) return 'raise';
    if (normalized.includes('bet')) return 'bet';
    if (normalized.includes('all') && normalized.includes('in')) return 'all-in';

    return 'check'; // Default
  }

  /**
   * Validate stream data
   */
  validateStreamData(data: StreamData): {
    valid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate players
    if (data.players.length < 2) {
      errors.push('Need at least 2 players');
    }

    if (data.players.length > 10) {
      errors.push('Maximum 10 players supported');
    }

    // Validate board
    const boardCardCount = data.board.length;
    if (data.street === 'flop' && boardCardCount !== 3) {
      warnings.push(`Flop should have 3 cards, found ${boardCardCount}`);
    } else if (data.street === 'turn' && boardCardCount !== 4) {
      warnings.push(`Turn should have 4 cards, found ${boardCardCount}`);
    } else if (data.street === 'river' && boardCardCount !== 5) {
      warnings.push(`River should have 5 cards, found ${boardCardCount}`);
    }

    // Check for duplicate cards
    const allCards = [
      ...data.board,
      ...data.players.flatMap(p => p.holeCards || []),
    ];
    const uniqueCards = new Set(allCards);
    if (allCards.length !== uniqueCards.size) {
      errors.push('Duplicate cards detected');
    }

    // Validate stakes
    if (data.stakes.bigBlind <= data.stakes.smallBlind) {
      errors.push('Big blind must be greater than small blind');
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }
}

