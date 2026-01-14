import { EventEmitter } from 'events';
import { GameState, PlayerState, PlayerAction, Card, Position, Street, Action } from '@tpb/shared';
import { logger } from '../utils/logger';

export class GameStateService extends EventEmitter {
  private gameState: GameState | null = null;
  private actionHistory: PlayerAction[] = [];
  private readonly maxHistorySize = 10000;

  /**
   * Initialize a new game
   */
  initializeGame(
    players: Array<{ name: string; stack: number; position: Position }>,
    buttonPosition: Position,
    smallBlind: number,
    bigBlind: number,
    ante?: number
  ): GameState {
    const playerStates: PlayerState[] = players.map((p, idx) => ({
      idx,
      name: p.name,
      stack: p.stack,
      position: p.position,
      folded: false,
      allIn: false,
      bet: 0,
    }));

    this.gameState = {
      id: this.generateGameId(),
      players: playerStates,
      buttonPosition,
      blinds: { small: smallBlind, big: bigBlind, ante },
      pot: 0,
      board: [],
      street: 'preflop',
      currentPlayerIdx: this.getUTGPosition(players.length),
      createdAt: new Date(),
      updatedAt: new Date(),
      status: 'active',
    };

    this.actionHistory = [];
    this.emit('gameInitialized', this.gameState);
    logger.info(`Game ${this.gameState.id} initialized with ${players.length} players`);
    return this.gameState;
  }

  /**
   * Record a player action
   */
  recordAction(playerIdx: number, action: Action, amount: number = 0): PlayerAction {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    if (playerIdx < 0 || playerIdx >= this.gameState.players.length) {
      throw new Error('Invalid player index');
    }

    const player = this.gameState.players[playerIdx];

    const newAction: PlayerAction = {
      playerIdx,
      action,
      amount,
      timestamp: new Date(),
      street: this.gameState.street,
      potAtAction: this.gameState.pot,
      stackAtAction: player.stack,
    };

    this.actionHistory.push(newAction);
    this.trimHistory();

    // Update player state
    if (action === 'fold') {
      player.folded = true;
    } else if (action === 'all-in') {
      this.gameState.pot += player.stack;
      player.stack = 0;
      player.allIn = true;
    } else if (action !== 'check') {
      player.stack -= amount;
      player.bet += amount;
      this.gameState.pot += amount;
    }

    this.gameState.updatedAt = new Date();
    this.emit('actionRecorded', newAction);

    logger.info(`Action recorded: Player ${playerIdx} ${action} ${amount > 0 ? amount : ''}`);
    return newAction;
  }

  /**
   * Update community cards (board)
   */
  updateBoard(cards: Card[], street: Street): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    this.gameState.board = cards;
    this.gameState.street = street;
    this.gameState.updatedAt = new Date();

    this.emit('boardUpdated', { cards, street });
    logger.info(`Board updated: ${street} - ${cards.join(', ')}`);
  }

  /**
   * Update hole cards for a player
   */
  updateHoleCards(playerIdx: number, cards: Card[]): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    if (playerIdx < 0 || playerIdx >= this.gameState.players.length) {
      throw new Error('Invalid player index');
    }

    this.gameState.players[playerIdx].holeCards = cards;
    this.gameState.updatedAt = new Date();

    this.emit('holeCardsUpdated', { playerIdx, cards });
    logger.info(`Hole cards updated for player ${playerIdx}`);
  }

  /**
   * Get current game state
   */
  getCurrentGame(): GameState | null {
    return this.gameState;
  }

  /**
   * Get action history for a specific player
   */
  getPlayerActionHistory(playerIdx: number): PlayerAction[] {
    return this.actionHistory.filter(action => action.playerIdx === playerIdx);
  }

  /**
   * Get actions on a specific street
   */
  getStreetActions(street: Street): PlayerAction[] {
    return this.actionHistory.filter(action => action.street === street);
  }

  /**
   * Get all actions in chronological order
   */
  getFullHistory(): PlayerAction[] {
    return [...this.actionHistory];
  }

  /**
   * End current game
   */
  endGame(winner: number, winAmount: number): void {
    if (!this.gameState) {
      throw new Error('No active game state');
    }

    this.gameState.status = 'completed';
    this.gameState.updatedAt = new Date();

    this.emit('gameEnded', {
      gameId: this.gameState.id,
      winner,
      winAmount,
    });

    logger.info(`Game ${this.gameState.id} ended. Winner: player ${winner}, amount: ${winAmount}`);
  }

  private getUTGPosition(playerCount: number): number {
    // In a typical game, UTG is 3 seats after button (BTN -> SB -> BB -> UTG)
    // For simplicity, return 0 (first player)
    return 0;
  }

  private generateGameId(): string {
    return `game_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private trimHistory(): void {
    if (this.actionHistory.length > this.maxHistorySize) {
      this.actionHistory = this.actionHistory.slice(-this.maxHistorySize);
    }
  }
}

