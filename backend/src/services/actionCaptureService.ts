import { EventEmitter } from 'events';
import { Action, Street } from '@tpb/shared';
import { ActionParser, ActionContext } from '../parsers/actionParser';
import { logger } from '../utils/logger';

export interface CapturedAction {
  action: Action;
  amount: number;
  timestamp: Date;
  source: 'ocr' | 'keyboard' | 'manual' | 'stream';
  confidence: number;
  validated: boolean;
  errors?: string[];
}

export interface ActionDetectionConfig {
  enableKeyboardHotkeys: boolean;
  enableOCR: boolean;
  enableStreamParsing: boolean;
  confidenceThreshold: number;
  autoValidate: boolean;
}

/**
 * Action capture service - detects player actions from multiple sources
 */
export class ActionCaptureService extends EventEmitter {
  private actionParser: ActionParser;
  private config: ActionDetectionConfig;
  private lastAction?: CapturedAction;
  private actionHistory: CapturedAction[] = [];

  constructor(config?: Partial<ActionDetectionConfig>) {
    super();
    this.actionParser = new ActionParser();
    this.config = {
      enableKeyboardHotkeys: true,
      enableOCR: false, // Disabled by default (CPU intensive)
      enableStreamParsing: true,
      confidenceThreshold: 0.7,
      autoValidate: true,
      ...config,
    };
  }

  /**
   * Start action capture
   */
  start(): void {
    logger.info('Action capture service started');

    if (this.config.enableKeyboardHotkeys) {
      this.setupKeyboardHotkeys();
    }

    if (this.config.enableOCR) {
      this.setupOCRCapture();
    }

    if (this.config.enableStreamParsing) {
      this.setupStreamCapture();
    }
  }

  /**
   * Stop action capture
   */
  stop(): void {
    logger.info('Action capture service stopped');
    this.removeAllListeners();
  }

  /**
   * Manually capture action
   */
  captureAction(
    action: Action,
    amount: number = 0,
    context?: ActionContext
  ): CapturedAction {
    const captured: CapturedAction = {
      action,
      amount,
      timestamp: new Date(),
      source: 'manual',
      confidence: 1.0,
      validated: false,
    };

    // Validate if context provided
    if (context && this.config.autoValidate) {
      const validation = this.actionParser.validateAction(
        {
          playerIdx: 0,
          playerName: 'Hero',
          action,
          amount,
          street: context.street,
          timestamp: captured.timestamp,
          valid: false,
        },
        context
      );

      captured.validated = validation.valid;
      captured.errors = validation.errors;
    } else {
      captured.validated = true;
    }

    this.recordAction(captured);
    return captured;
  }

  /**
   * Setup keyboard hotkey listeners
   */
  private setupKeyboardHotkeys(): void {
    logger.info('Keyboard hotkeys enabled');

    // Placeholder for keyboard listener
    // In production, use:
    // - ioHook (cross-platform keyboard hook)
    // - robot-js
    // - Custom native addon

    // Common hotkeys:
    // F - Fold
    // X - Check
    // C - Call
    // R - Raise
    // B - Bet
    // A - All-in
  }

  /**
   * Setup OCR-based action capture
   */
  private setupOCRCapture(): void {
    logger.info('OCR action capture enabled');

    // Placeholder for OCR monitoring
    // In production:
    // 1. Monitor action button regions
    // 2. Detect button highlights/changes
    // 3. Capture action when buttons change
    // 4. Parse action from button text
  }

  /**
   * Setup stream-based action capture
   */
  private setupStreamCapture(): void {
    logger.info('Stream action capture enabled');

    // Placeholder for stream monitoring
    // In production:
    // 1. Monitor stream data feed
    // 2. Parse action events
    // 3. Validate and emit
  }

  /**
   * Record captured action
   */
  private recordAction(action: CapturedAction): void {
    this.lastAction = action;
    this.actionHistory.push(action);

    // Trim history
    if (this.actionHistory.length > 1000) {
      this.actionHistory = this.actionHistory.slice(-1000);
    }

    // Emit event
    this.emit('actionCaptured', action);

    logger.info(
      `Action captured: ${action.action} (${action.source}, confidence: ${action.confidence})`
    );
  }

  /**
   * Get last captured action
   */
  getLastAction(): CapturedAction | undefined {
    return this.lastAction;
  }

  /**
   * Get action history
   */
  getHistory(): CapturedAction[] {
    return [...this.actionHistory];
  }

  /**
   * Get actions by source
   */
  getActionsBySource(source: CapturedAction['source']): CapturedAction[] {
    return this.actionHistory.filter(a => a.source === source);
  }

  /**
   * Get configuration
   */
  getConfig(): ActionDetectionConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<ActionDetectionConfig>): void {
    this.config = { ...this.config, ...config };
    logger.info('Action capture config updated', this.config);
  }
}

