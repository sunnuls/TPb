export const LIMITS = {
  MIN_PLAYERS: 2,
  MAX_PLAYERS: 10,
  MIN_BUY_IN: 20, // in BB
  MAX_BUY_IN: 200, // in BB
  MIN_BET: 1, // in BB
  MAX_RAISE_FACTOR: 4, // max raise can be 4x previous bet
} as const;

export const PERFORMANCE_TARGETS = {
  EQUITY_CALC_LATENCY_MS: 100,
  WS_MESSAGE_LATENCY_MS: 50,
  FRONTEND_RENDER_MS: 16.67, // 60 FPS
  BOARD_UPDATE_MS: 200,
  GTO_RECOMMENDATION_MS: 50,
} as const;

export const EQUITY_ENGINE_DEFAULTS = {
  ITERATIONS: 100000,
  PRECISION: 4,
  METHOD: 'monte-carlo' as 'monte-carlo' | 'exact',
} as const;

