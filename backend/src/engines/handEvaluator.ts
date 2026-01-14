import { Card, Rank, Suit } from '@tpb/shared';
import { parseCard, RANK_VALUES } from '@tpb/shared';

/**
 * Hand ranks (higher is better)
 */
export enum HandRank {
  HIGH_CARD = 0,
  ONE_PAIR = 1,
  TWO_PAIR = 2,
  THREE_OF_A_KIND = 3,
  STRAIGHT = 4,
  FLUSH = 5,
  FULL_HOUSE = 6,
  FOUR_OF_A_KIND = 7,
  STRAIGHT_FLUSH = 8,
  ROYAL_FLUSH = 9,
}

export interface HandEvaluation {
  rank: HandRank;
  rankName: string;
  value: number; // Unique value for comparison (higher is better)
  cards: Card[]; // Best 5-card hand
  description: string;
  kickers: number[]; // Kicker ranks for tiebreaking
}

/**
 * Fast poker hand evaluator
 * Uses a simplified algorithm for speed
 */
export class HandEvaluator {
  /**
   * Evaluate the best 5-card hand from 7 cards (Hold'em/Omaha with board)
   */
  evaluateBest5CardHand(cards: Card[]): HandEvaluation {
    if (cards.length < 5) {
      throw new Error('Need at least 5 cards to evaluate');
    }

    // If exactly 5 cards, evaluate directly
    if (cards.length === 5) {
      return this.evaluate5Cards(cards);
    }

    // Find best 5-card combination from 6 or 7 cards
    const combinations = this.generate5CardCombinations(cards);
    let bestEval: HandEvaluation | null = null;

    for (const combo of combinations) {
      const eval = this.evaluate5Cards(combo);
      if (!bestEval || eval.value > bestEval.value) {
        bestEval = eval;
      }
    }

    return bestEval!;
  }

  /**
   * Evaluate exactly 5 cards
   */
  private evaluate5Cards(cards: Card[]): HandEvaluation {
    const parsed = cards.map(c => parseCard(c)!);
    const ranks = parsed.map(p => p.rank);
    const suits = parsed.map(p => p.suit);

    // Check for flush
    const isFlush = this.checkFlush(suits);

    // Check for straight
    const straightRank = this.checkStraight(ranks);
    const isStraight = straightRank !== null;

    // Count rank frequencies
    const rankCounts = this.countRanks(ranks);
    const counts = Array.from(rankCounts.values()).sort((a, b) => b - a);
    const uniqueRanks = Array.from(rankCounts.keys()).sort(
      (a, b) => RANK_VALUES[b] - RANK_VALUES[a]
    );

    // Determine hand rank
    let handRank: HandRank;
    let rankName: string;
    let description: string;
    let kickers: number[] = [];

    // Straight Flush / Royal Flush
    if (isFlush && isStraight) {
      if (straightRank === 'A') {
        handRank = HandRank.ROYAL_FLUSH;
        rankName = 'Royal Flush';
        description = 'Royal Flush';
      } else {
        handRank = HandRank.STRAIGHT_FLUSH;
        rankName = 'Straight Flush';
        description = `Straight Flush, ${straightRank} high`;
      }
      kickers = [RANK_VALUES[straightRank!]];
    }
    // Four of a Kind
    else if (counts[0] === 4) {
      handRank = HandRank.FOUR_OF_A_KIND;
      rankName = 'Four of a Kind';
      const quadRank = this.findRankWithCount(rankCounts, 4);
      const kickerRank = uniqueRanks.find(r => r !== quadRank)!;
      description = `Four ${quadRank}s`;
      kickers = [RANK_VALUES[quadRank], RANK_VALUES[kickerRank]];
    }
    // Full House
    else if (counts[0] === 3 && counts[1] === 2) {
      handRank = HandRank.FULL_HOUSE;
      rankName = 'Full House';
      const tripRank = this.findRankWithCount(rankCounts, 3);
      const pairRank = this.findRankWithCount(rankCounts, 2);
      description = `${tripRank}s full of ${pairRank}s`;
      kickers = [RANK_VALUES[tripRank], RANK_VALUES[pairRank]];
    }
    // Flush
    else if (isFlush) {
      handRank = HandRank.FLUSH;
      rankName = 'Flush';
      description = `Flush, ${uniqueRanks[0]} high`;
      kickers = uniqueRanks.map(r => RANK_VALUES[r]);
    }
    // Straight
    else if (isStraight) {
      handRank = HandRank.STRAIGHT;
      rankName = 'Straight';
      description = `Straight, ${straightRank} high`;
      kickers = [RANK_VALUES[straightRank!]];
    }
    // Three of a Kind
    else if (counts[0] === 3) {
      handRank = HandRank.THREE_OF_A_KIND;
      rankName = 'Three of a Kind';
      const tripRank = this.findRankWithCount(rankCounts, 3);
      const kickerRanks = uniqueRanks.filter(r => r !== tripRank);
      description = `Three ${tripRank}s`;
      kickers = [RANK_VALUES[tripRank], ...kickerRanks.map(r => RANK_VALUES[r])];
    }
    // Two Pair
    else if (counts[0] === 2 && counts[1] === 2) {
      handRank = HandRank.TWO_PAIR;
      rankName = 'Two Pair';
      const pairs = uniqueRanks.filter(r => rankCounts.get(r) === 2);
      const kickerRank = uniqueRanks.find(r => rankCounts.get(r) === 1)!;
      description = `${pairs[0]}s and ${pairs[1]}s`;
      kickers = [...pairs.map(r => RANK_VALUES[r]), RANK_VALUES[kickerRank]];
    }
    // One Pair
    else if (counts[0] === 2) {
      handRank = HandRank.ONE_PAIR;
      rankName = 'One Pair';
      const pairRank = this.findRankWithCount(rankCounts, 2);
      const kickerRanks = uniqueRanks.filter(r => r !== pairRank);
      description = `Pair of ${pairRank}s`;
      kickers = [RANK_VALUES[pairRank], ...kickerRanks.map(r => RANK_VALUES[r])];
    }
    // High Card
    else {
      handRank = HandRank.HIGH_CARD;
      rankName = 'High Card';
      description = `${uniqueRanks[0]} high`;
      kickers = uniqueRanks.map(r => RANK_VALUES[r]);
    }

    // Calculate unique value for comparison
    const value = this.calculateHandValue(handRank, kickers);

    return {
      rank: handRank,
      rankName,
      value,
      cards,
      description,
      kickers,
    };
  }

  /**
   * Check if all cards are the same suit
   */
  private checkFlush(suits: Suit[]): boolean {
    return suits.every(s => s === suits[0]);
  }

  /**
   * Check for straight and return high rank if found
   */
  private checkStraight(ranks: Rank[]): Rank | null {
    const values = ranks.map(r => RANK_VALUES[r]).sort((a, b) => b - a);

    // Check for A-2-3-4-5 (wheel)
    if (values[0] === 14 && values[1] === 5 && values[2] === 4 && values[3] === 3 && values[4] === 2) {
      return '5'; // In wheel straight, 5 is high
    }

    // Check for regular straight
    for (let i = 0; i < values.length - 1; i++) {
      if (values[i] - values[i + 1] !== 1) {
        return null;
      }
    }

    // Return high rank
    return ranks.find(r => RANK_VALUES[r] === values[0])!;
  }

  /**
   * Count occurrences of each rank
   */
  private countRanks(ranks: Rank[]): Map<Rank, number> {
    const counts = new Map<Rank, number>();
    for (const rank of ranks) {
      counts.set(rank, (counts.get(rank) || 0) + 1);
    }
    return counts;
  }

  /**
   * Find rank with specific count
   */
  private findRankWithCount(rankCounts: Map<Rank, number>, count: number): Rank {
    for (const [rank, cnt] of rankCounts.entries()) {
      if (cnt === count) {
        return rank;
      }
    }
    throw new Error(`No rank with count ${count}`);
  }

  /**
   * Calculate unique value for hand comparison
   * Higher value = better hand
   */
  private calculateHandValue(handRank: HandRank, kickers: number[]): number {
    // Base value from hand rank (multiply by large number to separate ranks)
    let value = handRank * 100000000;

    // Add kicker values (weighted by position)
    for (let i = 0; i < kickers.length && i < 5; i++) {
      value += kickers[i] * Math.pow(100, 4 - i);
    }

    return value;
  }

  /**
   * Generate all 5-card combinations from N cards
   */
  private generate5CardCombinations(cards: Card[]): Card[][] {
    const combinations: Card[][] = [];
    const n = cards.length;

    // Generate combinations recursively
    const generate = (start: number, combo: Card[]) => {
      if (combo.length === 5) {
        combinations.push([...combo]);
        return;
      }

      for (let i = start; i < n; i++) {
        combo.push(cards[i]);
        generate(i + 1, combo);
        combo.pop();
      }
    };

    generate(0, []);
    return combinations;
  }

  /**
   * Compare two hand evaluations
   * Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
   */
  compareHands(hand1: HandEvaluation, hand2: HandEvaluation): number {
    if (hand1.value > hand2.value) return 1;
    if (hand1.value < hand2.value) return -1;
    return 0;
  }

  /**
   * Evaluate Omaha hand (must use exactly 2 hole cards + 3 board cards)
   */
  evaluateOmahaHand(holeCards: Card[], board: Card[]): HandEvaluation {
    if (holeCards.length !== 4) {
      throw new Error('Omaha requires exactly 4 hole cards');
    }
    if (board.length !== 5) {
      throw new Error('Omaha requires exactly 5 board cards');
    }

    let bestEval: HandEvaluation | null = null;

    // Try all combinations of 2 hole cards + 3 board cards
    for (let h1 = 0; h1 < 4; h1++) {
      for (let h2 = h1 + 1; h2 < 4; h2++) {
        for (let b1 = 0; b1 < 5; b1++) {
          for (let b2 = b1 + 1; b2 < 5; b2++) {
            for (let b3 = b2 + 1; b3 < 5; b3++) {
              const hand = [
                holeCards[h1],
                holeCards[h2],
                board[b1],
                board[b2],
                board[b3],
              ];

              const eval = this.evaluate5Cards(hand);

              if (!bestEval || eval.value > bestEval.value) {
                bestEval = eval;
              }
            }
          }
        }
      }
    }

    return bestEval!;
  }

  /**
   * Get hand rank name
   */
  getHandRankName(rank: HandRank): string {
    const names: Record<HandRank, string> = {
      [HandRank.HIGH_CARD]: 'High Card',
      [HandRank.ONE_PAIR]: 'One Pair',
      [HandRank.TWO_PAIR]: 'Two Pair',
      [HandRank.THREE_OF_A_KIND]: 'Three of a Kind',
      [HandRank.STRAIGHT]: 'Straight',
      [HandRank.FLUSH]: 'Flush',
      [HandRank.FULL_HOUSE]: 'Full House',
      [HandRank.FOUR_OF_A_KIND]: 'Four of a Kind',
      [HandRank.STRAIGHT_FLUSH]: 'Straight Flush',
      [HandRank.ROYAL_FLUSH]: 'Royal Flush',
    };
    return names[rank];
  }
}

