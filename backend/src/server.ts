import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { ServerToClientEvents, ClientToServerEvents, InterServerEvents, SocketData } from '@tpb/shared';
import { errorHandler } from './middleware/errorHandler';
import { rateLimiter } from './middleware/rateLimiter';
import { setupWebSocket } from './websocket';
import { logger } from './utils/logger';

// Routes
import gameRoutes from './controllers/gameController';
import playerRoutes from './controllers/playerController';
import configRoutes from './controllers/configController';
import analyticsRoutes from './controllers/analyticsController';
import handHistoryRoutes from './controllers/handHistoryController';
import { StreamController } from './controllers/streamController';

const app = express();
const httpServer = createServer(app);

// Socket.io setup with type safety
const io = new Server<ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData>(httpServer, {
  cors: {
    origin: process.env.CORS_ORIGIN || '*',
    methods: ['GET', 'POST'],
  },
  transports: ['websocket', 'polling'],
  pingInterval: 10000,
  pingTimeout: 5000,
});

// Middleware
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
app.use('/api/', rateLimiter);

// Request logging
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    version: '0.1.0',
  });
});

// API Routes
app.use('/api/game', gameRoutes);
app.use('/api/player', playerRoutes);
app.use('/api/config', configRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/handhistory', handHistoryRoutes);

// Stream integration routes
const streamController = new StreamController();
app.post('/api/stream/parse', streamController.parseStream);
app.post('/api/stream/tracking/start', streamController.startTracking);
app.post('/api/stream/tracking/stop', streamController.stopTracking);
app.get('/api/stream/tracking/status', streamController.getTrackingStatus);
app.post('/api/stream/action-capture/start', streamController.startActionCapture);
app.post('/api/stream/action-capture/stop', streamController.stopActionCapture);
app.get('/api/stream/actions', streamController.getCapturedActions);
app.post('/api/stream/hand-history/import', streamController.importHandHistory);
app.post('/api/stream/hand-history/export', streamController.exportHandHistory);
app.get('/api/stream/hands', streamController.getCapturedHands);

// WebSocket setup
setupWebSocket(io);

// Error handling middleware (must be last)
app.use(errorHandler);

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: {
      message: 'Endpoint not found',
      code: 'NOT_FOUND',
    },
    timestamp: new Date().toISOString(),
  });
});

export { app, httpServer, io };

