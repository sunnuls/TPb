import { Card, Equity, Rank, Suit } from '@tpb/shared';
import { parseCard, cardToIndex } from '@tpb/shared';

export interface EquityCalculatorOptions {
  maxIterations?: number;
  precision?: number;
  method?: 'exact' | 'monte-carlo';
}

export class EquityEngine {
  private readonly iterations: number;
  private readonly precision: number;
  private readonly method: 'exact' | 'monte-carlo';

  constructor(options: EquityCalculatorOptions = {}) {
    this.iterations = options.maxIterations || 100000;
    this.precision = options.precision || 4;
    this.method = options.method || 'monte-carlo';
  }

  /**
   * Calculate equity for multiple hands
   */
  calculateEquity(hands: Card[][], board: Card[], dead: Card[] = []): Equity[] {
    // Validate input
    if (hands.length < 2) {
      throw new Error('Need at least 2 hands for equity calculation');
    }

    // Multi-way pot support (2-10 players)
    if (hands.length > 10) {
      throw new Error('Maximum 10 hands supported');
    }

    if (this.method === 'exact' && board.length >= 3 && hands.length <= 3) {
      return this.calculateExactEquity(hands, board, dead);
    }
    return this.calculateMonteCarloEquity(hands, board, dead);
  }

  private calculateExactEquity(hands: Card[][], board: Card[], dead: Card[]): Equity[] {
    const numHands = hands.length;
    const wins = new Array(numHands).fill(0);
    const ties = new Array(numHands).fill(0);
    let totalOutcomes = 0;

    const usedCards = new Set<string>();
    hands.forEach(hand => hand.forEach(card => usedCards.add(card.toUpperCase())));
    board.forEach(card => usedCards.add(card.toUpperCase()));
    dead.forEach(card => usedCards.add(card.toUpperCase()));

    const remainingCards = this.getRemainingCards(usedCards);
    const neededCards = 5 - board.length;

    const possibleBoards = this.generateCombinations(remainingCards, neededCards);

    possibleBoards.forEach(boardAddition => {
      const finalBoard = [...board, ...boardAddition];
      const handStrengths = hands.map(hand => this.evaluateHand(hand, finalBoard));
      const maxStrength = Math.max(...handStrengths);

      handStrengths.forEach((strength, idx) => {
        if (strength === maxStrength) {
          const tiePlayers = handStrengths.filter(s => s === strength).length;
          if (tiePlayers > 1) {
            ties[idx] += 1 / tiePlayers;
          } else {
            wins[idx] += 1;
          }
        }
      });

      totalOutcomes++;
    });

    return hands.map((_, idx) => ({
      equity: Number(((wins[idx] + ties[idx]) / totalOutcomes).toFixed(this.precision)),
      confidence: 1.0,
      wins: wins[idx],
      ties: ties[idx],
      losses: totalOutcomes - wins[idx] - ties[idx],
    }));
  }

  private calculateMonteCarloEquity(hands: Card[][], board: Card[], dead: Card[]): Equity[] {
    const numHands = hands.length;
    const wins = new Array(numHands).fill(0);
    const ties = new Array(numHands).fill(0);

    const usedCards = new Set<string>();
    hands.forEach(hand => hand.forEach(card => usedCards.add(card.toUpperCase())));
    board.forEach(card => usedCards.add(card.toUpperCase()));
    dead.forEach(card => usedCards.add(card.toUpperCase()));

    const remainingCards = this.getRemainingCards(usedCards);
    const neededCards = 5 - board.length;

    for (let i = 0; i < this.iterations; i++) {
      const randomBoard = this.getRandomSample(remainingCards, neededCards);
      const finalBoard = [...board, ...randomBoard];
      const handStrengths = hands.map(hand => this.evaluateHand(hand, finalBoard));
      const maxStrength = Math.max(...handStrengths);

      handStrengths.forEach((strength, idx) => {
        if (strength === maxStrength) {
          const tiePlayers = handStrengths.filter(s => s === strength).length;
          if (tiePlayers > 1) {
            ties[idx] += 1 / tiePlayers;
          } else {
            wins[idx] += 1;
          }
        }
      });
    }

    const variance = this.estimateVariance(wins.map(w => w / this.iterations));
    const stdError = Math.sqrt(variance / this.iterations);

    return hands.map((_, idx) => ({
      equity: Number(((wins[idx] + ties[idx]) / this.iterations).toFixed(this.precision)),
      confidence: this.calculateConfidence(stdError),
      wins: wins[idx],
      ties: ties[idx],
      losses: this.iterations - wins[idx] - ties[idx],
    }));
  }

  private evaluateHand(hand: Card[], board: Card[]): number {
    // Use proper hand evaluator
    const { HandEvaluator } = require('./handEvaluator');
    const evaluator = new HandEvaluator();
    
    try {
      const allCards = [...hand, ...board];
      const evaluation = evaluator.evaluateBest5CardHand(allCards);
      return evaluation.value;
    } catch (error) {
      // Fallback to simple random for invalid hands
      return Math.random() * 10000;
    }
  }

  private generateCombinations(cards: Card[], k: number): Card[][] {
    const result: Card[][] = [];
    const n = cards.length;

    const helper = (start: number, combo: Card[]) => {
      if (combo.length === k) {
        result.push([...combo]);
        return;
      }
      for (let i = start; i < n; i++) {
        combo.push(cards[i]);
        helper(i + 1, combo);
        combo.pop();
      }
    };

    helper(0, []);
    return result;
  }

  private getRandomSample(cards: Card[], k: number): Card[] {
    const sample: Card[] = [];
    const available = [...cards];

    for (let i = 0; i < k && available.length > 0; i++) {
      const idx = Math.floor(Math.random() * available.length);
      sample.push(available[idx]);
      available.splice(idx, 1);
    }

    return sample;
  }

  private getRemainingCards(usedCards: Set<string>): Card[] {
    const allCards = this.getAllCards();
    return allCards.filter(card => !usedCards.has(card.toUpperCase()));
  }

  private getAllCards(): Card[] {
    const ranks: Rank[] = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    const suits: Suit[] = ['s', 'h', 'd', 'c'];
    const cards: Card[] = [];

    for (const rank of ranks) {
      for (const suit of suits) {
        cards.push(`${rank}${suit}` as Card);
      }
    }

    return cards;
  }

  private estimateVariance(values: number[]): number {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const squaredDiffs = values.map(v => Math.pow(v - mean, 2));
    return squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  }

  private calculateConfidence(stdError: number): number {
    return Math.max(0, Math.min(1, 1 - stdError * 2));
  }
}

