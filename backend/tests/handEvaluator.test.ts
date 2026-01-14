import { HandEvaluator, HandRank } from '../src/engines/handEvaluator';
import { Card } from '@tpb/shared';

describe('HandEvaluator', () => {
  let evaluator: HandEvaluator;

  beforeEach(() => {
    evaluator = new HandEvaluator();
  });

  describe('Royal Flush', () => {
    it('should identify a royal flush', () => {
      const cards: Card[] = ['As', 'Ks', 'Qs', 'Js', 'Ts'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.ROYAL_FLUSH);
      expect(result.rankName).toBe('Royal Flush');
    });
  });

  describe('Straight Flush', () => {
    it('should identify a straight flush', () => {
      const cards: Card[] = ['9h', '8h', '7h', '6h', '5h'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.STRAIGHT_FLUSH);
      expect(result.description).toContain('Straight Flush');
    });
  });

  describe('Four of a Kind', () => {
    it('should identify four of a kind', () => {
      const cards: Card[] = ['Kc', 'Kd', 'Kh', 'Ks', 'Ah'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.FOUR_OF_A_KIND);
      expect(result.description).toContain('Four');
    });
  });

  describe('Full House', () => {
    it('should identify a full house', () => {
      const cards: Card[] = ['Qc', 'Qd', 'Qh', 'Jc', 'Jd'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.FULL_HOUSE);
      expect(result.description).toContain('full of');
    });
  });

  describe('Flush', () => {
    it('should identify a flush', () => {
      const cards: Card[] = ['Ad', 'Kd', 'Td', '7d', '3d'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.FLUSH);
      expect(result.rankName).toBe('Flush');
    });
  });

  describe('Straight', () => {
    it('should identify a straight', () => {
      const cards: Card[] = ['9c', '8d', '7h', '6s', '5c'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.STRAIGHT);
      expect(result.rankName).toBe('Straight');
    });

    it('should identify a wheel (A-2-3-4-5)', () => {
      const cards: Card[] = ['Ac', '2d', '3h', '4s', '5c'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.STRAIGHT);
      expect(result.description).toContain('5 high');
    });
  });

  describe('Three of a Kind', () => {
    it('should identify three of a kind', () => {
      const cards: Card[] = ['Jc', 'Jd', 'Jh', '9s', '4c'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.THREE_OF_A_KIND);
      expect(result.description).toContain('Three');
    });
  });

  describe('Two Pair', () => {
    it('should identify two pair', () => {
      const cards: Card[] = ['Tc', 'Td', '8h', '8s', 'Kc'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.TWO_PAIR);
      expect(result.rankName).toBe('Two Pair');
    });
  });

  describe('One Pair', () => {
    it('should identify one pair', () => {
      const cards: Card[] = ['7c', '7d', 'Ah', 'Ks', '4c'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.ONE_PAIR);
      expect(result.description).toContain('Pair');
    });
  });

  describe('High Card', () => {
    it('should identify high card', () => {
      const cards: Card[] = ['Ac', 'Kd', 'Qh', '9s', '4c'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      expect(result.rank).toBe(HandRank.HIGH_CARD);
      expect(result.description).toContain('high');
    });
  });

  describe('7-card evaluation', () => {
    it('should find best 5 cards from 7 cards', () => {
      // Board: As Kh Qd Jc Tc (royal flush possible)
      // Hand: 2c 3d
      const cards: Card[] = ['As', 'Kh', 'Qd', 'Jc', 'Tc', '2c', '3d'];
      const result = evaluator.evaluateBest5CardHand(cards);
      
      // Should find the straight (A-K-Q-J-T)
      expect(result.rank).toBe(HandRank.STRAIGHT);
    });
  });

  describe('Hand comparison', () => {
    it('should correctly compare two hands', () => {
      const cards1: Card[] = ['Ac', 'Ad', 'Ah', 'Ks', 'Kd']; // Full house
      const cards2: Card[] = ['Qc', 'Qd', 'Qh', 'Js', 'Jd']; // Full house (lower)
      
      const eval1 = evaluator.evaluateBest5CardHand(cards1);
      const eval2 = evaluator.evaluateBest5CardHand(cards2);
      
      const comparison = evaluator.compareHands(eval1, eval2);
      expect(comparison).toBe(1); // Hand1 should win
    });

    it('should identify a tie', () => {
      const cards1: Card[] = ['Ac', 'Kd', 'Qh', 'Js', 'Tc'];
      const cards2: Card[] = ['Ad', 'Kc', 'Qd', 'Jh', 'Ts'];
      
      const eval1 = evaluator.evaluateBest5CardHand(cards1);
      const eval2 = evaluator.evaluateBest5CardHand(cards2);
      
      const comparison = evaluator.compareHands(eval1, eval2);
      expect(comparison).toBe(0); // Should tie (same straight)
    });
  });

  describe('Omaha evaluation', () => {
    it('should evaluate Omaha hand correctly', () => {
      const holeCards: Card[] = ['As', 'Ad', 'Ks', 'Kd'];
      const board: Card[] = ['Ah', 'Kh', 'Qd', 'Jc', 'Tc'];
      
      const result = evaluator.evaluateOmahaHand(holeCards, board);
      
      // Best hand should be full house (AAA KK using As-Ad from hole and Ah-Kh-Qd from board)
      expect(result.rank).toBeGreaterThanOrEqual(HandRank.FULL_HOUSE);
    });

    it('should throw error for invalid Omaha hole cards', () => {
      const holeCards: Card[] = ['As', 'Ad', 'Ks']; // Only 3 cards
      const board: Card[] = ['Ah', 'Kh', 'Qd', 'Jc', 'Tc'];
      
      expect(() => evaluator.evaluateOmahaHand(holeCards, board)).toThrow();
    });
  });
});

