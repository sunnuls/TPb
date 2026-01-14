import { Router, Request, Response } from 'express';
import { HealthCheckResponse } from '@tpb/shared';

const router = Router();

// Health check
router.get('/health', (req: Request, res: Response<HealthCheckResponse>) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    version: '0.1.0',
    services: {
      database: true, // Placeholder - check actual DB connection
      redis: true,    // Placeholder - check actual Redis connection
    },
  });
});

// Get configuration
router.get('/', (req: Request, res: Response) => {
  res.json({
    success: true,
    data: {
      equityIterations: process.env.EQUITY_ITERATIONS || 100000,
      equityMethod: process.env.EQUITY_METHOD || 'monte-carlo',
      wsHeartbeatInterval: process.env.WS_HEARTBEAT_INTERVAL || 30000,
    },
    timestamp: new Date().toISOString(),
  });
});

export default router;

