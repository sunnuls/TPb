import { Card, Position } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface TableState {
  tableId: string;
  players: TablePlayer[];
  heroSeat?: number;
  buttonSeat: number;
  board: Card[];
  pot: number;
  activePlayers: number;
  timestamp: Date;
}

export interface TablePlayer {
  seat: number;
  name: string;
  stack: number;
  position: Position;
  isHero: boolean;
  isActive: boolean;
  currentBet: number;
}

/**
 * Table state parser - converts stream data to table state
 */
export class TableParser {
  /**
   * Parse table state from stream data
   */
  parseTableState(data: any): TableState {
    logger.info('Parsing table state');

    const players = this.parsePlayers(data.players || [], data.buttonSeat || 1);
    const heroSeat = players.find(p => p.isHero)?.seat;

    return {
      tableId: data.tableId || 'unknown',
      players,
      heroSeat,
      buttonSeat: data.buttonSeat || 1,
      board: this.parseBoard(data.board || []),
      pot: parseFloat(data.pot || 0),
      activePlayers: players.filter(p => p.isActive).length,
      timestamp: new Date(data.timestamp || Date.now()),
    };
  }

  /**
   * Parse players and assign positions
   */
  private parsePlayers(players: any[], buttonSeat: number): TablePlayer[] {
    const playerCount = players.length;

    return players.map((p: any) => {
      const seat = p.seat || p.seatNumber;
      const position = this.calculatePosition(seat, buttonSeat, playerCount);

      return {
        seat,
        name: p.name || `Player ${seat}`,
        stack: parseFloat(p.stack || 0),
        position,
        isHero: p.isHero === true || p.hero === true,
        isActive: p.isActive !== false && !p.folded,
        currentBet: parseFloat(p.currentBet || p.bet || 0),
      };
    });
  }

  /**
   * Calculate position based on seat and button
   */
  private calculatePosition(seat: number, buttonSeat: number, playerCount: number): Position {
    // Calculate offset from button
    let offset = seat - buttonSeat;
    if (offset < 0) offset += playerCount;

    // Map offset to position
    if (playerCount === 2) {
      // Heads-up
      return offset === 0 ? 'BTN' : 'BB';
    } else if (playerCount === 3) {
      // 3-handed
      if (offset === 0) return 'BTN';
      if (offset === 1) return 'SB';
      return 'BB';
    } else if (playerCount === 6) {
      // 6-max
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO'];
      return positions[offset];
    } else if (playerCount >= 9) {
      // Full ring (9-10 players)
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'];
      return positions[Math.min(offset, 7)];
    } else {
      // 4-5 handed or 7-8 handed (simplified)
      if (offset === 0) return 'BTN';
      if (offset === 1) return 'SB';
      if (offset === 2) return 'BB';
      if (offset === playerCount - 1) return 'CO';
      if (offset === playerCount - 2) return 'HJ';
      return 'MP';
    }
  }

  /**
   * Parse board cards
   */
  private parseBoard(board: any[]): Card[] {
    if (!Array.isArray(board)) return [];

    return board
      .map(card => this.normalizeCard(card))
      .filter((card): card is Card => card !== null);
  }

  /**
   * Normalize card notation
   */
  private normalizeCard(card: any): Card | null {
    let cardStr: string;

    if (typeof card === 'string') {
      cardStr = card;
    } else if (card.rank && card.suit) {
      cardStr = `${card.rank}${card.suit}`;
    } else {
      return null;
    }

    if (cardStr.length < 2) return null;

    const rank = cardStr[0].toUpperCase();
    const suit = cardStr[1].toLowerCase();

    if (!'AKQJT98765432'.includes(rank)) return null;
    if (!'shdc'.includes(suit)) return null;

    return `${rank}${suit}` as Card;
  }

  /**
   * Update table state with new action
   */
  updateTableState(
    state: TableState,
    action: {
      seat: number;
      action: string;
      amount?: number;
    }
  ): TableState {
    const player = state.players.find(p => p.seat === action.seat);
    if (!player) return state;

    // Update player based on action
    if (action.action === 'fold') {
      player.isActive = false;
      state.activePlayers--;
    } else if (action.action === 'bet' || action.action === 'raise' || action.action === 'call') {
      const amount = action.amount || 0;
      player.stack -= amount;
      player.currentBet += amount;
      state.pot += amount;
    } else if (action.action === 'all-in') {
      const amount = player.stack;
      player.stack = 0;
      player.currentBet += amount;
      state.pot += amount;
    }

    state.timestamp = new Date();

    return state;
  }

  /**
   * Get hero from table state
   */
  getHero(state: TableState): TablePlayer | null {
    return state.players.find(p => p.isHero) || null;
  }

  /**
   * Get active players
   */
  getActivePlayers(state: TableState): TablePlayer[] {
    return state.players.filter(p => p.isActive);
  }

  /**
   * Get player by seat
   */
  getPlayerBySeat(state: TableState, seat: number): TablePlayer | null {
    return state.players.find(p => p.seat === seat) || null;
  }

  /**
   * Get player by position
   */
  getPlayerByPosition(state: TableState, position: Position): TablePlayer | null {
    return state.players.find(p => p.position === position) || null;
  }
}

