import { GameState, Position, Street, Card } from '@tpb/shared';

/**
 * Generates demo game state for flop (default demo)
 */
export function generateDemoGameState(): GameState {
  return {
    id: 'demo-table-001',
    players: [
      {
        idx: 0,
        name: 'Hero (You)',
        position: 'BTN' as Position,
        stack: 9850,
        bet: 150,
        holeCards: ['Ah', 'Ks'] as Card[],
        folded: false,
        allIn: false,
        vpip: 25,
        pfr: 20,
        aggression: 2.5
      },
      {
        idx: 1,
        name: 'TightAggro88',
        position: 'SB' as Position,
        stack: 8500,
        bet: 50,
        holeCards: [],
        folded: false,
        allIn: false,
        vpip: 18,
        pfr: 15,
        aggression: 3.2
      },
      {
        idx: 2,
        name: 'FishyPlayer',
        position: 'BB' as Position,
        stack: 12300,
        bet: 100,
        holeCards: [],
        folded: false,
        allIn: false,
        vpip: 45,
        pfr: 8,
        aggression: 1.2
      },
      {
        idx: 3,
        name: 'RegularJoe',
        position: 'UTG' as Position,
        stack: 8000,
        bet: 0,
        holeCards: [],
        folded: true,
        allIn: false,
        vpip: 22,
        pfr: 18,
        aggression: 2.0
      },
      {
        idx: 4,
        name: 'LAGPlayer99',
        position: 'MP' as Position,
        stack: 15000,
        bet: 150,
        holeCards: [],
        folded: false,
        allIn: false,
        vpip: 38,
        pfr: 28,
        aggression: 4.5
      },
      {
        idx: 5,
        name: 'NittyRock',
        position: 'CO' as Position,
        stack: 9500,
        bet: 0,
        holeCards: [],
        folded: true,
        allIn: false,
        vpip: 12,
        pfr: 10,
        aggression: 1.8
      }
    ],
    board: ['Qh', 'Jd', 'Tc'] as Card[],
    pot: 600,
    street: 'flop' as Street,
    buttonPosition: 'BTN' as Position,
    blinds: {
      small: 50,
      big: 100
    },
    currentPlayerIdx: 1,
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  };
}

/**
 * Generates demo game state for turn street
 */
export function generateDemoGameStateTurn(): GameState {
  const state = generateDemoGameState();
  return {
    ...state,
    id: 'demo-table-turn',
    street: 'turn' as Street,
    board: ['Qh', 'Jd', 'Tc', '7s'] as Card[],
    pot: 1200,
    players: state.players.map((p, idx) => ({
      ...p,
      bet: idx === 0 || idx === 1 || idx === 4 ? 300 : p.bet,
      stack: idx === 0 ? 9550 : idx === 1 ? 8200 : idx === 4 ? 14700 : p.stack
    }))
  };
}

/**
 * Generates demo game state for river street
 */
export function generateDemoGameStateRiver(): GameState {
  const state = generateDemoGameStateTurn();
  return {
    ...state,
    id: 'demo-table-river',
    street: 'river' as Street,
    board: ['Qh', 'Jd', 'Tc', '7s', '3h'] as Card[],
    pot: 2400,
    players: state.players.map((p, idx) => ({
      ...p,
      bet: idx === 0 || idx === 1 ? 600 : p.bet,
      stack: idx === 0 ? 9250 : idx === 1 ? 7900 : p.stack
    }))
  };
}

/**
 * Generates demo game state for preflop
 */
export function generateDemoGameStatePreflop(): GameState {
  return {
    id: 'demo-table-preflop',
    players: [
      {
        idx: 0,
        name: 'Hero (You)',
        position: 'CO' as Position,
        stack: 10000,
        bet: 0,
        holeCards: ['As', 'Ah'] as Card[],
        folded: false,
        allIn: false,
        vpip: 25,
        pfr: 20,
        aggression: 2.5
      },
      {
        idx: 1,
        name: 'SmallBlind',
        position: 'SB' as Position,
        stack: 9950,
        bet: 50,
        holeCards: [],
        folded: false,
        allIn: false,
        vpip: 20,
        pfr: 16,
        aggression: 2.8
      },
      {
        idx: 2,
        name: 'BigBlind',
        position: 'BB' as Position,
        stack: 9900,
        bet: 100,
        holeCards: [],
        folded: false,
        allIn: false,
        vpip: 28,
        pfr: 12,
        aggression: 1.9
      }
    ],
    board: [] as Card[],
    pot: 150,
    street: 'preflop' as Street,
    buttonPosition: 'CO' as Position,
    blinds: {
      small: 50,
      big: 100
    },
    currentPlayerIdx: 0,
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  };
}
