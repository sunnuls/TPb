export const MESSAGES = {
  ERRORS: {
    CONNECTION_FAILED: 'Failed to connect to server',
    NO_GAME_STATE: 'No active game found',
    INVALID_ACTION: 'Invalid action',
    NETWORK_ERROR: 'Network error occurred',
    TIMEOUT: 'Request timed out',
  },
  
  SUCCESS: {
    CONNECTED: 'Connected to server',
    GAME_STARTED: 'Game started successfully',
    ACTION_RECORDED: 'Action recorded',
    SETTINGS_SAVED: 'Settings saved',
  },
  
  WARNINGS: {
    LOW_EQUITY: 'Low equity in this spot',
    RISKY_PLAY: 'This play deviates from GTO',
    TILTED: 'Consider taking a break',
  },
  
  INFO: {
    WAITING_FOR_PLAYERS: 'Waiting for players...',
    YOUR_TURN: "It's your turn",
    HAND_COMPLETE: 'Hand complete',
  },
} as const;

export const TOOLTIPS = {
  VPIP: 'Voluntarily Put $ In Pot - percentage of hands played',
  PFR: 'Pre-Flop Raise - percentage of hands raised preflop',
  AGGRESSION: 'Aggression Factor - (Bet + Raise) / Call ratio',
  WTSD: 'Went To ShowDown - percentage of hands that reach showdown',
  EQUITY: 'Your chance of winning the pot',
  GTO: 'Game Theory Optimal - balanced unexploitable strategy',
  EV: 'Expected Value - average profit/loss of an action',
} as const;

