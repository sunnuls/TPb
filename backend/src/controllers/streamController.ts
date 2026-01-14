import { Request, Response, NextFunction } from 'express';
import { StreamParser } from '../parsers/streamParser';
import { TableTrackingService } from '../services/tableTrackingService';
import { ActionCaptureService } from '../services/actionCaptureService';
import { HandHistoryCaptureService } from '../services/handHistoryCaptureService';
import { logger } from '../utils/logger';

/**
 * Stream Controller - handles stream integration endpoints
 */
export class StreamController {
  private streamParser: StreamParser;
  private tableTracking: TableTrackingService;
  private actionCapture: ActionCaptureService;
  private handCapture: HandHistoryCaptureService;

  constructor() {
    this.streamParser = new StreamParser();
    this.tableTracking = new TableTrackingService();
    this.actionCapture = new ActionCaptureService();
    this.handCapture = new HandHistoryCaptureService();
  }

  /**
   * Parse stream data
   */
  parseStream = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const streamData = req.body;

      logger.info('Parsing stream data');

      const parsed = this.streamParser.parseStreamData(streamData);
      const validation = this.streamParser.validateStreamData(parsed);

      res.json({
        success: true,
        data: parsed,
        validation,
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Start table tracking
   */
  startTracking = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { config } = req.body;

      if (config) {
        this.tableTracking.updateConfig(config);
      }

      await this.tableTracking.start();

      res.json({
        success: true,
        message: 'Table tracking started',
        config: this.tableTracking.getConfig(),
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Stop table tracking
   */
  stopTracking = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      this.tableTracking.stop();

      res.json({
        success: true,
        message: 'Table tracking stopped',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get table tracking status
   */
  getTrackingStatus = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const isActive = this.tableTracking.isActive();
      const currentState = this.tableTracking.getCurrentState();
      const changeHistory = this.tableTracking.getChangeHistory();

      res.json({
        success: true,
        data: {
          active: isActive,
          currentState,
          recentChanges: changeHistory.slice(-10),
          config: this.tableTracking.getConfig(),
        },
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Start action capture
   */
  startActionCapture = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { config } = req.body;

      if (config) {
        this.actionCapture.updateConfig(config);
      }

      this.actionCapture.start();

      res.json({
        success: true,
        message: 'Action capture started',
        config: this.actionCapture.getConfig(),
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Stop action capture
   */
  stopActionCapture = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      this.actionCapture.stop();

      res.json({
        success: true,
        message: 'Action capture stopped',
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get captured actions
   */
  getCapturedActions = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { source } = req.query;

      let actions;

      if (source) {
        actions = this.actionCapture.getActionsBySource(source as any);
      } else {
        actions = this.actionCapture.getHistory();
      }

      res.json({
        success: true,
        data: actions,
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Import hand history
   */
  importHandHistory = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { rawText, filePath } = req.body;

      let result;

      if (rawText) {
        result = await this.handCapture.importHand(rawText);
      } else if (filePath) {
        const count = await this.handCapture.importFromFile(filePath);
        result = { imported: count };
      } else {
        throw new Error('Provide rawText or filePath');
      }

      res.json({
        success: true,
        data: result,
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Export hand history
   */
  exportHandHistory = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      await this.handCapture.exportAll();

      res.json({
        success: true,
        message: 'Hand history exported',
        count: this.handCapture.getCapturedHands().length,
      });
    } catch (error) {
      next(error);
    }
  };

  /**
   * Get captured hands
   */
  getCapturedHands = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const { startDate, endDate, winningOnly } = req.query;

      let hands;

      if (winningOnly === 'true') {
        hands = this.handCapture.getWinningHands();
      } else if (startDate && endDate) {
        hands = this.handCapture.getHandsByDateRange(
          new Date(startDate as string),
          new Date(endDate as string)
        );
      } else {
        hands = this.handCapture.getCapturedHands();
      }

      res.json({
        success: true,
        data: hands,
        count: hands.length,
      });
    } catch (error) {
      next(error);
    }
  };
}

