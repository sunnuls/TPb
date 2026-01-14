import { EventEmitter } from 'events';
import { GameState, Card, Position } from '@tpb/shared';
import { ScreenCaptureService } from './screenCaptureService';
import { OCRService } from './ocrService';
import { TableParser } from '../parsers/tableParser';
import { logger } from '../utils/logger';

export interface TableTrackingConfig {
  captureInterval: number; // ms
  ocrEnabled: boolean;
  autoDetectChanges: boolean;
  site: 'pokerstars' | 'gg' | 'generic';
}

export interface TableChange {
  type: 'board' | 'pot' | 'player' | 'action';
  previous: any;
  current: any;
  timestamp: Date;
}

/**
 * Real-time table state tracking service
 */
export class TableTrackingService extends EventEmitter {
  private screenCapture: ScreenCaptureService;
  private ocr: OCRService;
  private tableParser: TableParser;
  private config: TableTrackingConfig;
  private isTracking = false;
  private currentState?: GameState;
  private changeHistory: TableChange[] = [];

  constructor(config?: Partial<TableTrackingConfig>) {
    super();
    this.screenCapture = new ScreenCaptureService();
    this.ocr = new OCRService();
    this.tableParser = new TableParser();
    this.config = {
      captureInterval: 1000,
      ocrEnabled: false, // Disabled by default (resource intensive)
      autoDetectChanges: true,
      site: 'generic',
      ...config,
    };
  }

  /**
   * Start table tracking
   */
  async start(): Promise<void> {
    if (this.isTracking) {
      logger.warn('Table tracking already active');
      return;
    }

    logger.info('Starting table tracking', this.config);
    this.isTracking = true;

    // Detect poker table window
    const tableWindow = await this.screenCapture.detectPokerTable();

    if (!tableWindow.found) {
      logger.warn('No poker table detected - using manual mode');
    } else {
      logger.info(`Poker table detected: ${tableWindow.site} - ${tableWindow.windowTitle}`);
      if (tableWindow.site) {
        this.config.site = tableWindow.site;
      }
    }

    // Start screen capture loop
    if (this.config.ocrEnabled) {
      this.startCaptureLoop();
    }

    this.emit('trackingStarted');
  }

  /**
   * Stop table tracking
   */
  stop(): void {
    if (!this.isTracking) return;

    logger.info('Stopping table tracking');
    this.isTracking = false;
    this.screenCapture.stopCapture();
    this.emit('trackingStopped');
  }

  /**
   * Start capture loop
   */
  private startCaptureLoop(): void {
    this.screenCapture.startCapture(this.config.captureInterval, async (capture) => {
      await this.processCapture(capture);
    });
  }

  /**
   * Process captured screen
   */
  private async processCapture(capture: any): Promise<void> {
    try {
      // Run OCR on capture
      const ocrResult = await this.ocr.recognizeTableState(capture.buffer);

      // Validate OCR result
      const validation = this.ocr.validateOCRResult(ocrResult);

      if (!validation.valid) {
        logger.warn('OCR validation failed', validation.warnings);
      }

      // Detect changes
      if (this.config.autoDetectChanges) {
        this.detectChanges(ocrResult);
      }

      // Emit table state update
      this.emit('tableStateUpdated', ocrResult);
    } catch (error) {
      logger.error(`Failed to process capture: ${error}`);
    }
  }

  /**
   * Detect changes in table state
   */
  private detectChanges(newState: any): void {
    if (!this.currentState) {
      logger.info('Initial table state captured');
      return;
    }

    const changes: TableChange[] = [];

    // Detect board changes
    const newBoard = newState.cards?.board || [];
    const oldBoard = this.currentState.board || [];

    if (JSON.stringify(newBoard) !== JSON.stringify(oldBoard)) {
      changes.push({
        type: 'board',
        previous: oldBoard,
        current: newBoard,
        timestamp: new Date(),
      });

      logger.info(`Board changed: ${oldBoard.join(',')} -> ${newBoard.join(',')}`);
      this.emit('boardChanged', { old: oldBoard, new: newBoard });
    }

    // Detect pot changes
    const newPot = newState.pot?.amount || 0;
    const oldPot = this.currentState.pot || 0;

    if (Math.abs(newPot - oldPot) > 0.01) {
      changes.push({
        type: 'pot',
        previous: oldPot,
        current: newPot,
        timestamp: new Date(),
      });

      logger.info(`Pot changed: ${oldPot} -> ${newPot}`);
      this.emit('potChanged', { old: oldPot, new: newPot });
    }

    // Store changes
    this.changeHistory.push(...changes);
    this.trimChangeHistory();
  }

  /**
   * Manually update table state
   */
  updateTableState(state: Partial<GameState>): void {
    if (!this.currentState && state as GameState) {
      this.currentState = state as GameState;
    } else if (this.currentState) {
      this.currentState = { ...this.currentState, ...state };
    }

    this.emit('tableStateUpdated', this.currentState);
    logger.info('Table state manually updated');
  }

  /**
   * Get current table state
   */
  getCurrentState(): GameState | undefined {
    return this.currentState;
  }

  /**
   * Get change history
   */
  getChangeHistory(): TableChange[] {
    return [...this.changeHistory];
  }

  /**
   * Clear change history
   */
  clearChangeHistory(): void {
    this.changeHistory = [];
    logger.info('Change history cleared');
  }

  /**
   * Trim change history
   */
  private trimChangeHistory(): void {
    if (this.changeHistory.length > 500) {
      this.changeHistory = this.changeHistory.slice(-500);
    }
  }

  /**
   * Check if tracking is active
   */
  isActive(): boolean {
    return this.isTracking;
  }

  /**
   * Get configuration
   */
  getConfig(): TableTrackingConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<TableTrackingConfig>): void {
    const wasTracking = this.isTracking;

    // Stop if running
    if (wasTracking) {
      this.stop();
    }

    // Update config
    this.config = { ...this.config, ...config };
    logger.info('Table tracking config updated', this.config);

    // Restart if was running
    if (wasTracking) {
      this.start();
    }
  }
}

