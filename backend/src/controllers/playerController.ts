import { Router, Request, Response } from 'express';
import { GameStateService } from '../services/gameStateService';
import { GetPlayerStatsResponse } from '@tpb/shared';

const router = Router();
const gameStateService = new GameStateService();

// Get player action history
router.get('/:playerIdx/history', (req: Request, res: Response) => {
  const playerIdx = parseInt(req.params.playerIdx);

  if (isNaN(playerIdx)) {
    res.status(400).json({
      success: false,
      error: {
        message: 'Invalid player index',
        code: 'INVALID_PLAYER_INDEX',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  const history = gameStateService.getPlayerActionHistory(playerIdx);

  res.json({
    success: true,
    data: history,
    timestamp: new Date().toISOString(),
  });
});

// Get player statistics
router.get('/:playerIdx/stats', (req: Request, res: Response<GetPlayerStatsResponse>) => {
  const playerIdx = parseInt(req.params.playerIdx);

  if (isNaN(playerIdx)) {
    res.status(400).json({
      success: false,
      error: {
        message: 'Invalid player index',
        code: 'INVALID_PLAYER_INDEX',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  // Placeholder stats - in production, calculate from history
  res.json({
    success: true,
    data: {
      playerIdx,
      totalHands: 0,
      vpip: 0,
      pfr: 0,
      aggression: 0,
      wtsd: 0,
      wonAtShowdown: 0,
    },
    timestamp: new Date().toISOString(),
  });
});

export default router;

