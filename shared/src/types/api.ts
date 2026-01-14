import { GameState, PlayerAction, Equity, StrategyRecommendation, Card } from './poker';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    code: string;
    details?: any;
  };
  timestamp: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  uptime: number;
  version: string;
  services: {
    database: boolean;
    redis: boolean;
  };
}

export interface GetGameStateResponse extends ApiResponse<GameState> {}

export interface GetHistoryResponse extends ApiResponse<PlayerAction[]> {}

export interface CalculateEquityRequest {
  hands: Card[][];
  board: Card[];
  dead?: Card[];
  iterations?: number;
}

export interface CalculateEquityResponse extends ApiResponse<Equity[]> {}

export interface GetRecommendationRequest {
  gameState: GameState;
  heroIdx: number;
}

export interface GetRecommendationResponse extends ApiResponse<StrategyRecommendation> {}

export interface GetPlayerStatsResponse extends ApiResponse<{
  playerIdx: number;
  totalHands: number;
  vpip: number;
  pfr: number;
  aggression: number;
  wtsd: number; // Went to showdown
  wonAtShowdown: number;
}> {}

