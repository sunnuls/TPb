import { StreamParser } from '../src/parsers/streamParser';
import { Card } from '@tpb/shared';

describe('StreamParser', () => {
  let parser: StreamParser;

  beforeEach(() => {
    parser = new StreamParser();
  });

  describe('parseStreamData', () => {
    it('should parse PokerStars stream data', () => {
      const data = {
        source: 'pokerstars',
        tableId: 'PS-12345',
        gameType: 'holdem',
        smallBlind: 0.5,
        bigBlind: 1.0,
        players: [
          { seat: 1, name: 'Player1', stack: 100 },
          { seat: 2, name: 'Player2', stack: 150 },
        ],
        board: ['As', 'Kh', 'Qd'],
        street: 'flop',
        pot: 15,
        actions: [],
      };

      const result = parser.parseStreamData(data);

      expect(result.source).toBe('pokerstars');
      expect(result.tableId).toBe('PS-12345');
      expect(result.players).toHaveLength(2);
      expect(result.board).toEqual(['As', 'Kh', 'Qd']);
      expect(result.street).toBe('flop');
    });

    it('should normalize card notation', () => {
      const data = {
        source: 'generic',
        tableId: 'test',
        players: [],
        board: ['as', 'KH', '2d', 'tc'],
        actions: [],
      };

      const result = parser.parseStreamData(data);

      expect(result.board).toEqual(['As', 'Kh', '2d', 'Tc']);
    });
  });

  describe('validateStreamData', () => {
    it('should validate correct stream data', () => {
      const data = {
        source: 'pokerstars' as const,
        timestamp: new Date(),
        tableId: 'test',
        gameType: 'holdem' as const,
        stakes: { smallBlind: 0.5, bigBlind: 1.0 },
        players: [
          { seatNumber: 1, name: 'P1', stack: 100, isActive: true, hasFolded: false, currentBet: 0 },
          { seatNumber: 2, name: 'P2', stack: 100, isActive: true, hasFolded: false, currentBet: 0 },
        ],
        board: ['As', 'Kh', 'Qd'] as Card[],
        street: 'flop' as const,
        pot: 10,
        actions: [],
      };

      const validation = parser.validateStreamData(data);

      expect(validation.valid).toBe(true);
      expect(validation.errors).toHaveLength(0);
    });

    it('should detect invalid player count', () => {
      const data = {
        source: 'pokerstars' as const,
        timestamp: new Date(),
        tableId: 'test',
        gameType: 'holdem' as const,
        stakes: { smallBlind: 0.5, bigBlind: 1.0 },
        players: [
          { seatNumber: 1, name: 'P1', stack: 100, isActive: true, hasFolded: false, currentBet: 0 },
        ],
        board: [] as Card[],
        street: 'preflop' as const,
        pot: 0,
        actions: [],
      };

      const validation = parser.validateStreamData(data);

      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain('Need at least 2 players');
    });

    it('should detect duplicate cards', () => {
      const data = {
        source: 'pokerstars' as const,
        timestamp: new Date(),
        tableId: 'test',
        gameType: 'holdem' as const,
        stakes: { smallBlind: 0.5, bigBlind: 1.0 },
        players: [
          { seatNumber: 1, name: 'P1', stack: 100, isActive: true, hasFolded: false, currentBet: 0, holeCards: ['As', 'Kh'] as Card[] },
          { seatNumber: 2, name: 'P2', stack: 100, isActive: true, hasFolded: false, currentBet: 0 },
        ],
        board: ['As', 'Qd', 'Jc'] as Card[], // As is duplicate
        street: 'flop' as const,
        pot: 10,
        actions: [],
      };

      const validation = parser.validateStreamData(data);

      expect(validation.valid).toBe(false);
      expect(validation.errors).toContain('Duplicate cards detected');
    });
  });
});

