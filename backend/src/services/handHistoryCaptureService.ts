import { EventEmitter } from 'events';
import { promises as fs } from 'fs';
import { join } from 'path';
import { GameState, PlayerAction, Card } from '@tpb/shared';
import { HandHistoryParser } from '../parsers/handHistoryParser';
import { logger } from '../utils/logger';

export interface CapturedHand {
  id: string;
  timestamp: Date;
  site: string;
  gameType: 'holdem' | 'omaha';
  stakes: string;
  heroName: string;
  heroPosition: string;
  heroCards: Card[];
  board: Card[];
  pot: number;
  actions: PlayerAction[];
  result?: {
    won: boolean;
    amount: number;
  };
  raw: string; // Raw hand history text
}

export interface CaptureConfig {
  autoCapture: boolean;
  captureFolder: string;
  includeRaw: boolean;
  autoExport: boolean;
  exportFormat: 'json' | 'csv' | 'txt';
}

/**
 * Hand history capture service
 */
export class HandHistoryCaptureService extends EventEmitter {
  private parser: HandHistoryParser;
  private config: CaptureConfig;
  private currentHand?: Partial<CapturedHand>;
  private capturedHands: CapturedHand[] = [];

  constructor(config?: Partial<CaptureConfig>) {
    super();
    this.parser = new HandHistoryParser();
    this.config = {
      autoCapture: true,
      captureFolder: './data/hand_history',
      includeRaw: true,
      autoExport: false,
      exportFormat: 'json',
      ...config,
    };
  }

  /**
   * Start hand capture
   */
  startHand(gameState: GameState): void {
    logger.info('Starting hand capture');

    // Find hero's cards from players
    const heroCards = gameState.players.find(p => p.holeCards)?.holeCards || [];

    this.currentHand = {
      id: this.generateHandId(),
      timestamp: new Date(),
      gameType: 'holdem',
      heroCards: heroCards,
      board: [],
      pot: 0,
      actions: [],
      raw: '',
    };

    this.emit('handStarted', this.currentHand);
  }

  /**
   * Record action during hand
   */
  recordAction(action: PlayerAction): void {
    if (!this.currentHand) {
      logger.warn('No active hand to record action');
      return;
    }

    if (!this.currentHand.actions) {
      this.currentHand.actions = [];
    }

    this.currentHand.actions.push(action);
    logger.debug(`Action recorded: ${action.action}`, action);
  }

  /**
   * Update board
   */
  updateBoard(board: Card[]): void {
    if (!this.currentHand) return;

    this.currentHand.board = board;
    logger.debug(`Board updated: ${board.join(',')}`);
  }

  /**
   * Update pot
   */
  updatePot(pot: number): void {
    if (!this.currentHand) return;

    this.currentHand.pot = pot;
  }

  /**
   * End hand and save
   */
  async endHand(result?: { won: boolean; amount: number }): Promise<CapturedHand | null> {
    if (!this.currentHand) {
      logger.warn('No active hand to end');
      return null;
    }

    // Complete hand data
    const completedHand: CapturedHand = {
      id: this.currentHand.id!,
      timestamp: this.currentHand.timestamp!,
      site: this.currentHand.site || 'unknown',
      gameType: this.currentHand.gameType!,
      stakes: this.currentHand.stakes || '0.5/1',
      heroName: this.currentHand.heroName || 'Hero',
      heroPosition: this.currentHand.heroPosition || 'BTN',
      heroCards: this.currentHand.heroCards || [],
      board: this.currentHand.board || [],
      pot: this.currentHand.pot || 0,
      actions: this.currentHand.actions || [],
      result,
      raw: this.currentHand.raw || this.generateRawHandHistory(this.currentHand),
    };

    // Store hand
    this.capturedHands.push(completedHand);

    // Auto-export if enabled
    if (this.config.autoExport) {
      await this.exportHand(completedHand);
    }

    // Emit event
    this.emit('handCompleted', completedHand);

    // Clear current hand
    this.currentHand = undefined;

    logger.info(`Hand completed: ${completedHand.id}`);

    return completedHand;
  }

  /**
   * Import hand from raw text
   */
  async importHand(rawText: string): Promise<CapturedHand | null> {
    try {
      const parsed = this.parser.parseHandHistory(rawText);

      if (!parsed) {
        logger.error('Failed to parse hand history');
        return null;
      }

      // Find hero in players
      const hero = parsed.players.find(p => p.holeCards);
      
      // Convert board object to array
      const boardCards: Card[] = [
        ...(parsed.board.flop || []),
        ...(parsed.board.turn ? [parsed.board.turn] : []),
        ...(parsed.board.river ? [parsed.board.river] : []),
      ];

      const hand: CapturedHand = {
        id: parsed.handId || this.generateHandId(),
        timestamp: parsed.timestamp,
        site: parsed.site,
        gameType: parsed.gameType,
        stakes: `${parsed.stakes.smallBlind}/${parsed.stakes.bigBlind}`,
        heroName: hero?.name || 'Hero',
        heroPosition: hero?.position || 'BTN',
        heroCards: hero?.holeCards || [],
        board: boardCards,
        pot: parsed.pot,
        actions: parsed.actions,
        raw: rawText,
      };

      this.capturedHands.push(hand);
      this.emit('handImported', hand);

      logger.info(`Hand imported: ${hand.id}`);

      return hand;
    } catch (error) {
      logger.error(`Failed to import hand: ${error}`);
      return null;
    }
  }

  /**
   * Import hands from file
   */
  async importFromFile(filePath: string): Promise<number> {
    logger.info(`Importing hands from file: ${filePath}`);

    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const hands = this.parser.parseMultipleHands(content);

      let imported = 0;

      for (const parsed of hands) {
        // Find hero in players
        const hero = parsed.players.find(p => p.holeCards);
        
        // Convert board object to array
        const boardCards: Card[] = [
          ...(parsed.board.flop || []),
          ...(parsed.board.turn ? [parsed.board.turn] : []),
          ...(parsed.board.river ? [parsed.board.river] : []),
        ];

        const hand: CapturedHand = {
          id: parsed.handId || this.generateHandId(),
          timestamp: parsed.timestamp,
          site: parsed.site,
          gameType: parsed.gameType,
          stakes: `${parsed.stakes.smallBlind}/${parsed.stakes.bigBlind}`,
          heroName: hero?.name || 'Hero',
          heroPosition: hero?.position || 'BTN',
          heroCards: hero?.holeCards || [],
          board: boardCards,
          pot: parsed.pot,
          actions: parsed.actions,
          raw: '',
        };

        this.capturedHands.push(hand);
        imported++;
      }

      logger.info(`Imported ${imported} hands from file`);
      this.emit('handsImported', imported);

      return imported;
    } catch (error) {
      logger.error(`Failed to import from file: ${error}`);
      return 0;
    }
  }

  /**
   * Export hand to file
   */
  async exportHand(hand: CapturedHand): Promise<void> {
    try {
      // Ensure folder exists
      await fs.mkdir(this.config.captureFolder, { recursive: true });

      const filename = `hand_${hand.id}_${hand.timestamp.getTime()}.${this.config.exportFormat}`;
      const filepath = join(this.config.captureFolder, filename);

      let content: string;

      switch (this.config.exportFormat) {
        case 'json':
          content = JSON.stringify(hand, null, 2);
          break;
        case 'txt':
          content = hand.raw;
          break;
        case 'csv':
          content = this.convertToCSV(hand);
          break;
        default:
          content = JSON.stringify(hand);
      }

      await fs.writeFile(filepath, content, 'utf-8');
      logger.info(`Hand exported: ${filepath}`);
    } catch (error) {
      logger.error(`Failed to export hand: ${error}`);
    }
  }

  /**
   * Export all hands
   */
  async exportAll(): Promise<void> {
    logger.info(`Exporting ${this.capturedHands.length} hands`);

    for (const hand of this.capturedHands) {
      await this.exportHand(hand);
    }
  }

  /**
   * Get all captured hands
   */
  getCapturedHands(): CapturedHand[] {
    return [...this.capturedHands];
  }

  /**
   * Get hands by date range
   */
  getHandsByDateRange(start: Date, end: Date): CapturedHand[] {
    return this.capturedHands.filter(
      h => h.timestamp >= start && h.timestamp <= end
    );
  }

  /**
   * Get winning hands
   */
  getWinningHands(): CapturedHand[] {
    return this.capturedHands.filter(h => h.result?.won === true);
  }

  /**
   * Clear captured hands
   */
  clearCapturedHands(): void {
    this.capturedHands = [];
    logger.info('Captured hands cleared');
  }

  /**
   * Generate unique hand ID
   */
  private generateHandId(): string {
    return `hand-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Generate raw hand history text
   */
  private generateRawHandHistory(hand: Partial<CapturedHand>): string {
    const lines: string[] = [];

    lines.push(`Hand #${hand.id}`);
    lines.push(`Date: ${hand.timestamp?.toISOString()}`);
    lines.push(`Game: ${hand.gameType} ${hand.stakes}`);
    lines.push('');
    lines.push('*** HOLE CARDS ***');
    lines.push(`Hero: ${hand.heroCards?.join(' ')}`);
    lines.push('');

    if (hand.actions && hand.actions.length > 0) {
      lines.push('*** ACTIONS ***');
      hand.actions.forEach(a => {
        lines.push(`${a.playerIdx}: ${a.action} ${a.amount || ''}`);
      });
      lines.push('');
    }

    if (hand.board && hand.board.length > 0) {
      lines.push('*** BOARD ***');
      lines.push(hand.board.join(' '));
      lines.push('');
    }

    lines.push(`Pot: ${hand.pot}`);

    if (hand.result) {
      lines.push(`Result: ${hand.result.won ? 'WON' : 'LOST'} ${hand.result.amount}`);
    }

    return lines.join('\n');
  }

  /**
   * Convert hand to CSV format
   */
  private convertToCSV(hand: CapturedHand): string {
    const header = 'ID,Timestamp,Site,Game,Stakes,HeroCards,Board,Pot,Result,Won,Amount';
    const row = [
      hand.id,
      hand.timestamp.toISOString(),
      hand.site,
      hand.gameType,
      hand.stakes,
      hand.heroCards.join('-'),
      hand.board.join('-'),
      hand.pot,
      hand.result ? 'Yes' : 'No',
      hand.result?.won ? 'Yes' : 'No',
      hand.result?.amount || 0,
    ].join(',');

    return `${header}\n${row}`;
  }

  /**
   * Get configuration
   */
  getConfig(): CaptureConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<CaptureConfig>): void {
    this.config = { ...this.config, ...config };
    logger.info('Hand capture config updated', this.config);
  }
}

