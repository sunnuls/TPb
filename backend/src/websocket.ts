import { Server } from 'socket.io';
import { ServerToClientEvents, ClientToServerEvents, InterServerEvents, SocketData } from '@tpb/shared';
import { GameStateService } from './services/gameStateService';
import { EquityService } from './services/equityService';
import { GTOService } from './services/gtoService';
import { logger } from './utils/logger';

const gameStateService = new GameStateService();
const equityService = new EquityService();
const gtoService = new GTOService();

export function setupWebSocket(
  io: Server<ClientToServerEvents, ServerToClientEvents, InterServerEvents, SocketData>
): void {
  io.on('connection', (socket) => {
    const clientId = socket.id;
    socket.data.clientId = clientId;
    socket.data.connectedAt = new Date();

    logger.info(`Client connected: ${clientId}`);

    socket.emit('connected', {
      clientId,
      timestamp: socket.data.connectedAt,
    });

    // Initialize game
    socket.on('initGame', async (data) => {
      try {
        const gameState = gameStateService.initializeGame(
          data.players,
          data.buttonPosition,
          data.smallBlind,
          data.bigBlind,
          data.ante
        );

        socket.data.gameId = gameState.id;
        socket.emit('gameInitialized', gameState);
        socket.broadcast.emit('gameInitialized', gameState);

        logger.info(`Game initialized: ${gameState.id} by ${clientId}`);
      } catch (error) {
        logger.error(`Error initializing game: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to initialize game',
          code: 'INIT_GAME_ERROR',
        });
      }
    });

    // Record player action
    socket.on('recordAction', async (data) => {
      try {
        const action = gameStateService.recordAction(
          data.playerIdx,
          data.action,
          data.amount || 0
        );

        const gameState = gameStateService.getCurrentGame();
        if (gameState) {
          io.emit('actionRecorded', { action, gameState });
          logger.info(`Action recorded: ${data.action} by player ${data.playerIdx}`);
        }
      } catch (error) {
        logger.error(`Error recording action: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to record action',
          code: 'RECORD_ACTION_ERROR',
        });
      }
    });

    // Update board
    socket.on('updateBoard', async (data) => {
      try {
        gameStateService.updateBoard(data.cards, data.street);

        const gameState = gameStateService.getCurrentGame();
        if (!gameState) {
          throw new Error('No active game state');
        }

        // Calculate equity for active players
        const activePlayers = gameState.players.filter(p => !p.folded && p.holeCards);
        const hands = activePlayers.map(p => p.holeCards!);

        const equity = await equityService.calculateEquity(hands, gameState.board);

        // Get GTO recommendations
        const recommendations = await gtoService.getRecommendations(gameState);

        io.emit('boardUpdated', { gameState, equity, recommendations });
        logger.info(`Board updated: ${data.street} with ${data.cards.length} cards`);
      } catch (error) {
        logger.error(`Error updating board: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to update board',
          code: 'UPDATE_BOARD_ERROR',
        });
      }
    });

    // Update hole cards
    socket.on('updateHoleCards', async (data) => {
      try {
        gameStateService.updateHoleCards(data.playerIdx, data.cards);

        const gameState = gameStateService.getCurrentGame();
        if (gameState) {
          io.emit('playerUpdated', {
            playerIdx: data.playerIdx,
            updates: { holeCards: data.cards },
          });
          logger.info(`Hole cards updated for player ${data.playerIdx}`);
        }
      } catch (error) {
        logger.error(`Error updating hole cards: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to update hole cards',
          code: 'UPDATE_HOLE_CARDS_ERROR',
        });
      }
    });

    // Request equity calculation
    socket.on('requestEquity', async (data) => {
      try {
        const equity = await equityService.calculateEquity(
          data.hands,
          data.board,
          data.dead
        );

        socket.emit('boardUpdated', {
          gameState: gameStateService.getCurrentGame()!,
          equity,
          recommendations: await gtoService.getRecommendations(gameStateService.getCurrentGame()!),
        });
      } catch (error) {
        logger.error(`Error calculating equity: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to calculate equity',
          code: 'EQUITY_CALC_ERROR',
        });
      }
    });

    // Request GTO recommendation
    socket.on('requestRecommendation', async (data) => {
      try {
        const recommendations = await gtoService.getRecommendations(data.gameState);

        socket.emit('boardUpdated', {
          gameState: data.gameState,
          equity: [],
          recommendations,
        });
      } catch (error) {
        logger.error(`Error getting recommendation: ${error}`);
        socket.emit('error', {
          message: error instanceof Error ? error.message : 'Failed to get recommendation',
          code: 'RECOMMENDATION_ERROR',
        });
      }
    });

    // Ping/pong for connection health
    socket.on('ping', () => {
      socket.emit('heartbeat');
    });

    // Disconnect handler
    socket.on('disconnect', (reason) => {
      logger.info(`Client disconnected: ${clientId}, reason: ${reason}`);
    });
  });

  // Heartbeat mechanism
  setInterval(() => {
    io.emit('heartbeat');
  }, parseInt(process.env.WS_HEARTBEAT_INTERVAL || '30000'));
}

