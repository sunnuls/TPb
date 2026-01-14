import { GameState, PlayerAction, Card, Street, Position, Equity, StrategyRecommendation } from './poker';

export interface ServerToClientEvents {
  gameInitialized: (data: GameState) => void;
  actionRecorded: (data: { action: PlayerAction; gameState: GameState }) => void;
  boardUpdated: (data: { gameState: GameState; equity: Equity[]; recommendations: StrategyRecommendation }) => void;
  playerUpdated: (data: { playerIdx: number; updates: Partial<GameState['players'][0]> }) => void;
  error: (data: { message: string; code?: string }) => void;
  connected: (data: { clientId: string; timestamp: Date }) => void;
  heartbeat: () => void;
}

export interface ClientToServerEvents {
  initGame: (data: {
    players: Array<{ name: string; stack: number; position: Position }>;
    buttonPosition: Position;
    smallBlind: number;
    bigBlind: number;
    ante?: number;
  }) => void;
  recordAction: (data: {
    playerIdx: number;
    action: 'fold' | 'check' | 'call' | 'raise' | 'bet' | 'all-in';
    amount?: number;
  }) => void;
  updateBoard: (data: {
    cards: Card[];
    street: Street;
  }) => void;
  updateHoleCards: (data: {
    playerIdx: number;
    cards: Card[];
  }) => void;
  requestEquity: (data: {
    hands: Card[][];
    board: Card[];
    dead?: Card[];
  }) => void;
  requestRecommendation: (data: {
    gameState: GameState;
  }) => void;
  ping: () => void;
}

export interface InterServerEvents {
  broadcast: (event: string, data: any) => void;
}

export interface SocketData {
  clientId: string;
  connectedAt: Date;
  gameId?: string;
}

