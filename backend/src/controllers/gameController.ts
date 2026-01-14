import { Router, Request, Response } from 'express';
import { GameStateService } from '../services/gameStateService';
import { ApiResponse, GetGameStateResponse, GetHistoryResponse } from '@tpb/shared';

const router = Router();
const gameStateService = new GameStateService();

// Get current game state
router.get('/current', (req: Request, res: Response<GetGameStateResponse>) => {
  const gameState = gameStateService.getCurrentGame();

  if (!gameState) {
    res.json({
      success: false,
      error: {
        message: 'No active game',
        code: 'NO_ACTIVE_GAME',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  res.json({
    success: true,
    data: gameState,
    timestamp: new Date().toISOString(),
  });
});

// Get action history
router.get('/history', (req: Request, res: Response<GetHistoryResponse>) => {
  const history = gameStateService.getFullHistory();

  res.json({
    success: true,
    data: history,
    timestamp: new Date().toISOString(),
  });
});

// Get street-specific history
router.get('/history/:street', (req: Request, res: Response<GetHistoryResponse>) => {
  const { street } = req.params;
  const history = gameStateService.getStreetActions(street as any);

  res.json({
    success: true,
    data: history,
    timestamp: new Date().toISOString(),
  });
});

export default router;

