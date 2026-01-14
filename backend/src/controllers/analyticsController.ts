import { Router, Request, Response } from 'express';
import { GameStateService } from '../services/gameStateService';
import { StatisticalAnalysisService } from '../services/statisticalAnalysisService';
import { RangeConstructorService } from '../services/rangeConstructorService';
import { EVCalculatorService } from '../services/evCalculatorService';
import { Card, Position, Street } from '@tpb/shared';

const router = Router();
const gameStateService = new GameStateService();
const statsService = new StatisticalAnalysisService();
const rangeService = new RangeConstructorService();
const evService = new EVCalculatorService();

// Get player statistics
router.get('/stats/:playerIdx', (req: Request, res: Response) => {
  try {
    const playerIdx = parseInt(req.params.playerIdx);

    if (isNaN(playerIdx)) {
      res.status(400).json({
        success: false,
        error: { message: 'Invalid player index', code: 'INVALID_PLAYER_INDEX' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const actions = gameStateService.getPlayerActionHistory(playerIdx);
    const stats = statsService.calculatePlayerStats(playerIdx, actions);

    res.json({
      success: true,
      data: stats,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to calculate stats',
        code: 'STATS_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

// Get all players statistics
router.get('/stats', (req: Request, res: Response) => {
  try {
    const gameState = gameStateService.getCurrentGame();

    if (!gameState) {
      res.status(404).json({
        success: false,
        error: { message: 'No active game', code: 'NO_ACTIVE_GAME' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const allActions = gameStateService.getFullHistory();
    const allStats = gameState.players.map(player =>
      statsService.calculatePlayerStats(player.idx, allActions)
    );

    res.json({
      success: true,
      data: allStats,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to calculate stats',
        code: 'STATS_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

// Build opponent range
router.post('/range', (req: Request, res: Response) => {
  try {
    const { position, street, action, previousAction } = req.body;

    if (!position || !street || !action) {
      res.status(400).json({
        success: false,
        error: { message: 'Missing required fields', code: 'MISSING_FIELDS' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const range = rangeService.buildOpponentRange(
      position as Position,
      street as Street,
      action,
      previousAction
    );

    res.json({
      success: true,
      data: range,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to build range',
        code: 'RANGE_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

// Calculate EV
router.post('/ev', async (req: Request, res: Response) => {
  try {
    const { heroCards, board, pot, betSize, heroStack, villainStack } = req.body;

    if (!heroCards || !board || pot === undefined || betSize === undefined) {
      res.status(400).json({
        success: false,
        error: { message: 'Missing required fields', code: 'MISSING_FIELDS' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const evAnalysis = await evService.calculateEV(
      heroCards as Card[],
      board as Card[],
      pot,
      betSize,
      heroStack || 1000,
      villainStack || 1000
    );

    res.json({
      success: true,
      data: evAnalysis,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to calculate EV',
        code: 'EV_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

export default router;

