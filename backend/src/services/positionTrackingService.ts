import { EventEmitter } from 'events';
import { Position } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface PlayerPosition {
  seat: number;
  name: string;
  position: Position;
  isActive: boolean;
  stack: number;
  vpip?: number; // Voluntarily Put money In Pot
  pfr?: number; // Pre-Flop Raise
  aggFactor?: number; // Aggression Factor
}

export interface PositionHistory {
  handId: string;
  timestamp: Date;
  positions: PlayerPosition[];
  buttonSeat: number;
}

/**
 * Player position tracking service
 */
export class PositionTrackingService extends EventEmitter {
  private currentPositions: Map<number, PlayerPosition> = new Map();
  private positionHistory: PositionHistory[] = [];
  private buttonSeat: number = 1;
  private playerCount: number = 6; // Default 6-max

  /**
   * Initialize table positions
   */
  initializeTable(playerCount: number, buttonSeat: number = 1): void {
    logger.info(`Initializing table: ${playerCount} players, button on seat ${buttonSeat}`);

    this.playerCount = playerCount;
    this.buttonSeat = buttonSeat;
    this.currentPositions.clear();

    this.emit('tableInitialized', { playerCount, buttonSeat });
  }

  /**
   * Update player position
   */
  updatePlayerPosition(seat: number, player: Partial<PlayerPosition>): void {
    const existing = this.currentPositions.get(seat);

    const updated: PlayerPosition = {
      seat,
      name: player.name || existing?.name || `Player ${seat}`,
      position: player.position || this.calculatePosition(seat),
      isActive: player.isActive !== undefined ? player.isActive : true,
      stack: player.stack || existing?.stack || 0,
      vpip: player.vpip || existing?.vpip,
      pfr: player.pfr || existing?.pfr,
      aggFactor: player.aggFactor || existing?.aggFactor,
    };

    this.currentPositions.set(seat, updated);

    this.emit('positionUpdated', updated);

    logger.debug(`Position updated: Seat ${seat} - ${updated.position}`);
  }

  /**
   * Calculate position based on seat and button
   */
  calculatePosition(seat: number): Position {
    // Calculate offset from button
    let offset = seat - this.buttonSeat;
    if (offset < 0) offset += this.playerCount;

    // Map offset to position based on player count
    if (this.playerCount === 2) {
      // Heads-up
      return offset === 0 ? 'BTN' : 'BB';
    } else if (this.playerCount === 3) {
      // 3-handed
      const positions: Position[] = ['BTN', 'SB', 'BB'];
      return positions[offset];
    } else if (this.playerCount === 6) {
      // 6-max
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO'];
      return positions[offset];
    } else if (this.playerCount >= 9) {
      // Full ring (9-10 players)
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'];
      if (this.playerCount === 10) {
        positions.splice(4, 0, 'UTG+2'); // Add UTG+2 for 10-handed
      }
      return positions[Math.min(offset, positions.length - 1)];
    } else {
      // 4-5 handed or 7-8 handed (simplified)
      if (offset === 0) return 'BTN';
      if (offset === 1) return 'SB';
      if (offset === 2) return 'BB';
      if (offset === this.playerCount - 1) return 'CO';
      if (offset === this.playerCount - 2) return 'HJ';
      return 'MP';
    }
  }

  /**
   * Move button to next seat
   */
  moveButton(): void {
    this.buttonSeat = (this.buttonSeat % this.playerCount) + 1;

    // Recalculate all positions
    for (const [seat, player] of this.currentPositions) {
      player.position = this.calculatePosition(seat);
    }

    this.emit('buttonMoved', this.buttonSeat);

    logger.info(`Button moved to seat ${this.buttonSeat}`);
  }

  /**
   * Get player by seat
   */
  getPlayerBySeat(seat: number): PlayerPosition | undefined {
    return this.currentPositions.get(seat);
  }

  /**
   * Get player by position
   */
  getPlayerByPosition(position: Position): PlayerPosition | undefined {
    for (const player of this.currentPositions.values()) {
      if (player.position === position) {
        return player;
      }
    }
    return undefined;
  }

  /**
   * Get all active players
   */
  getActivePlayers(): PlayerPosition[] {
    return Array.from(this.currentPositions.values()).filter(p => p.isActive);
  }

  /**
   * Get all players
   */
  getAllPlayers(): PlayerPosition[] {
    return Array.from(this.currentPositions.values());
  }

  /**
   * Get players in position order (BTN -> BB)
   */
  getPlayersInOrder(): PlayerPosition[] {
    const players = this.getAllPlayers();

    return players.sort((a, b) => {
      const orderA = this.getPositionOrder(a.position);
      const orderB = this.getPositionOrder(b.position);
      return orderA - orderB;
    });
  }

  /**
   * Get position order for sorting
   */
  private getPositionOrder(position: Position): number {
    const order: Record<Position, number> = {
      'BTN': 0,
      'SB': 1,
      'BB': 2,
      'UTG': 3,
      'UTG+1': 4,
      'UTG+2': 5,
      'MP': 6,
      'HJ': 7,
      'CO': 8,
    };

    return order[position] || 99;
  }

  /**
   * Get position relative strength (early/middle/late)
   */
  getPositionStrength(position: Position): 'early' | 'middle' | 'late' {
    const earlyPositions: Position[] = ['UTG', 'UTG+1', 'UTG+2'];
    const middlePositions: Position[] = ['MP', 'HJ'];
    const latePositions: Position[] = ['CO', 'BTN', 'SB', 'BB'];

    if (earlyPositions.includes(position)) return 'early';
    if (middlePositions.includes(position)) return 'middle';
    return 'late';
  }

  /**
   * Check if position is in position relative to another
   */
  isInPosition(position1: Position, position2: Position): boolean {
    const order1 = this.getPositionOrder(position1);
    const order2 = this.getPositionOrder(position2);

    // Lower order number = acts later = in position
    return order1 < order2;
  }

  /**
   * Get distance between positions
   */
  getPositionDistance(position1: Position, position2: Position): number {
    const order1 = this.getPositionOrder(position1);
    const order2 = this.getPositionOrder(position2);

    return Math.abs(order1 - order2);
  }

  /**
   * Save current positions to history
   */
  saveToHistory(handId: string): void {
    const snapshot: PositionHistory = {
      handId,
      timestamp: new Date(),
      positions: Array.from(this.currentPositions.values()),
      buttonSeat: this.buttonSeat,
    };

    this.positionHistory.push(snapshot);

    // Trim history
    if (this.positionHistory.length > 1000) {
      this.positionHistory = this.positionHistory.slice(-1000);
    }

    logger.debug(`Position history saved for hand ${handId}`);
  }

  /**
   * Get position history
   */
  getHistory(): PositionHistory[] {
    return [...this.positionHistory];
  }

  /**
   * Get position statistics for a player
   */
  getPlayerPositionStats(playerName: string): {
    totalHands: number;
    positionDistribution: Record<Position, number>;
    vpipByPosition: Record<Position, number>;
    pfrByPosition: Record<Position, number>;
  } {
    const stats = {
      totalHands: 0,
      positionDistribution: {} as Record<Position, number>,
      vpipByPosition: {} as Record<Position, number>,
      pfrByPosition: {} as Record<Position, number>,
    };

    for (const history of this.positionHistory) {
      const player = history.positions.find(p => p.name === playerName);

      if (player) {
        stats.totalHands++;

        // Count position distribution
        stats.positionDistribution[player.position] =
          (stats.positionDistribution[player.position] || 0) + 1;

        // Track VPIP by position
        if (player.vpip !== undefined) {
          stats.vpipByPosition[player.position] = player.vpip;
        }

        // Track PFR by position
        if (player.pfr !== undefined) {
          stats.pfrByPosition[player.position] = player.pfr;
        }
      }
    }

    return stats;
  }

  /**
   * Clear position history
   */
  clearHistory(): void {
    this.positionHistory = [];
    logger.info('Position history cleared');
  }

  /**
   * Get button seat
   */
  getButtonSeat(): number {
    return this.buttonSeat;
  }

  /**
   * Get player count
   */
  getPlayerCount(): number {
    return this.playerCount;
  }

  /**
   * Remove player from table
   */
  removePlayer(seat: number): void {
    const player = this.currentPositions.get(seat);

    if (player) {
      this.currentPositions.delete(seat);
      this.emit('playerRemoved', player);
      logger.info(`Player removed from seat ${seat}: ${player.name}`);
    }
  }

  /**
   * Clear all positions
   */
  clearPositions(): void {
    this.currentPositions.clear();
    logger.info('All positions cleared');
  }
}

