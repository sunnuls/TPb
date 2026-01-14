import { Card, Position, Street } from '@tpb/shared';
import { parseCard } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface HandRange {
  hands: string[]; // e.g., ["AA", "KK", "AKs", "AKo"]
  frequency: number; // 0-1
  description: string;
}

export interface OpponentRange {
  position: Position;
  street: Street;
  action: string;
  ranges: HandRange[];
  totalCombos: number;
}

export class RangeConstructorService {
  /**
   * Build opponent range based on position and action
   */
  buildOpponentRange(
    position: Position,
    street: Street,
    action: 'raise' | 'call' | 'check' | 'bet' | 'fold',
    previousAction?: string
  ): OpponentRange {
    logger.info(`Building range for ${position} ${action} on ${street}`);

    let ranges: HandRange[] = [];

    if (street === 'preflop') {
      ranges = this.getPreflopRange(position, action, previousAction);
    } else {
      ranges = this.getPostflopRange(position, street, action);
    }

    const totalCombos = this.calculateTotalCombos(ranges);

    return {
      position,
      street,
      action,
      ranges,
      totalCombos,
    };
  }

  /**
   * Get preflop opening ranges by position
   */
  private getPreflopRange(
    position: Position,
    action: string,
    previousAction?: string
  ): HandRange[] {
    // Standard GTO-inspired preflop ranges
    const ranges: HandRange[] = [];

    if (action === 'raise' && !previousAction) {
      // Opening ranges
      switch (position) {
        case 'UTG':
          ranges.push({
            hands: this.expandRange('22+,A2s+,K9s+,QTs+,JTs,ATo+,KQo'),
            frequency: 1.0,
            description: 'UTG Open (tight, ~12%)',
          });
          break;
        case 'MP':
          ranges.push({
            hands: this.expandRange('22+,A2s+,K8s+,Q9s+,J9s+,T9s,ATo+,KJo+'),
            frequency: 1.0,
            description: 'MP Open (~15%)',
          });
          break;
        case 'CO':
          ranges.push({
            hands: this.expandRange('22+,A2s+,K5s+,Q8s+,J8s+,T8s+,97s+,87s,A9o+,KTo+,QJo'),
            frequency: 1.0,
            description: 'CO Open (~25%)',
          });
          break;
        case 'BTN':
          ranges.push({
            hands: this.expandRange('22+,A2s+,K2s+,Q5s+,J7s+,T7s+,97s+,87s,76s,A2o+,K9o+,QTo+,JTo'),
            frequency: 1.0,
            description: 'BTN Open (wide, ~45%)',
          });
          break;
        case 'SB':
          ranges.push({
            hands: this.expandRange('22+,A2s+,K4s+,Q6s+,J7s+,T7s+,97s+,86s+,76s,A5o+,K9o+,QTo+,JTo'),
            frequency: 1.0,
            description: 'SB Open (~35%)',
          });
          break;
        case 'BB':
          // BB typically doesn't open, but defends
          ranges.push({
            hands: this.expandRange('22+,A2s+,K2s+,Q2s+,J5s+,T6s+,96s+,86s+,76s,65s,A2o+,K5o+,Q8o+,J9o+,T9o'),
            frequency: 1.0,
            description: 'BB Defense vs BTN (~50%)',
          });
          break;
        default:
          ranges.push({
            hands: this.expandRange('77+,AJs+,KQs,AKo'),
            frequency: 1.0,
            description: 'Default tight range',
          });
      }
    } else if (action === 'call') {
      // 3-bet calling ranges
      ranges.push({
        hands: this.expandRange('JJ-99,AQs,AJs,KQs,AQo'),
        frequency: 1.0,
        description: 'Flat 3-bet range',
      });
    }

    return ranges;
  }

  /**
   * Get postflop ranges (simplified)
   */
  private getPostflopRange(
    position: Position,
    street: Street,
    action: string
  ): HandRange[] {
    // Postflop ranges are more complex and depend on board texture
    // This is a simplified placeholder
    const ranges: HandRange[] = [];

    if (action === 'bet' || action === 'raise') {
      ranges.push({
        hands: ['AA', 'KK', 'QQ', 'AK', 'Top Pair+', 'Strong Draws'],
        frequency: 1.0,
        description: `${street} value betting range`,
      });
    } else if (action === 'call') {
      ranges.push({
        hands: ['Middle Pair', 'Weak Top Pair', 'Draws'],
        frequency: 1.0,
        description: `${street} calling range`,
      });
    }

    return ranges;
  }

  /**
   * Expand range notation to individual hands
   * Example: "AA,KK,AKs" -> ["AA", "KK", "AKs"]
   */
  private expandRange(rangeString: string): string[] {
    const hands: string[] = [];
    const parts = rangeString.split(',');

    for (const part of parts) {
      const trimmed = part.trim();

      // Handle pairs (e.g., "AA", "22+")
      if (trimmed.match(/^\d{2}\+?$/) || trimmed.match(/^[AKQJT]{2}\+?$/)) {
        hands.push(...this.expandPairs(trimmed));
      }
      // Handle suited (e.g., "AKs", "A2s+")
      else if (trimmed.includes('s')) {
        hands.push(...this.expandSuited(trimmed));
      }
      // Handle offsuit (e.g., "AKo", "A9o+")
      else if (trimmed.includes('o')) {
        hands.push(...this.expandOffsuit(trimmed));
      }
      // Single hand
      else {
        hands.push(trimmed);
      }
    }

    return hands;
  }

  /**
   * Expand pair notation
   */
  private expandPairs(notation: string): string[] {
    const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    const hasPlus = notation.includes('+');
    const rank = notation.replace('+', '')[0];

    if (!hasPlus) {
      return [notation.replace('+', '')];
    }

    const startIdx = ranks.indexOf(rank);
    const pairs: string[] = [];

    for (let i = startIdx; i < ranks.length; i++) {
      pairs.push(`${ranks[i]}${ranks[i]}`);
    }

    return pairs;
  }

  /**
   * Expand suited notation
   */
  private expandSuited(notation: string): string[] {
    const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    const hasPlus = notation.includes('+');
    const clean = notation.replace('s', '').replace('+', '');
    const [rank1, rank2] = clean.split('');

    if (!hasPlus) {
      return [notation.replace('+', '')];
    }

    const hands: string[] = [];
    const rank1Idx = ranks.indexOf(rank1);
    const rank2Idx = ranks.indexOf(rank2);

    for (let i = rank2Idx; i < ranks.length; i++) {
      if (i !== rank1Idx) {
        hands.push(`${rank1}${ranks[i]}s`);
      }
    }

    return hands;
  }

  /**
   * Expand offsuit notation
   */
  private expandOffsuit(notation: string): string[] {
    const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    const hasPlus = notation.includes('+');
    const clean = notation.replace('o', '').replace('+', '');
    const [rank1, rank2] = clean.split('');

    if (!hasPlus) {
      return [notation.replace('+', '')];
    }

    const hands: string[] = [];
    const rank1Idx = ranks.indexOf(rank1);
    const rank2Idx = ranks.indexOf(rank2);

    for (let i = rank2Idx; i < ranks.length; i++) {
      if (i !== rank1Idx) {
        hands.push(`${rank1}${ranks[i]}o`);
      }
    }

    return hands;
  }

  /**
   * Calculate total combinations in ranges
   */
  private calculateTotalCombos(ranges: HandRange[]): number {
    let total = 0;

    for (const range of ranges) {
      for (const hand of range.hands) {
        total += this.getHandCombos(hand);
      }
    }

    return total;
  }

  /**
   * Get number of combinations for a hand
   */
  private getHandCombos(hand: string): number {
    if (hand.length === 2 && hand[0] === hand[1]) {
      return 6; // Pairs: 6 combos
    } else if (hand.includes('s')) {
      return 4; // Suited: 4 combos
    } else if (hand.includes('o')) {
      return 12; // Offsuit: 12 combos
    } else {
      return 16; // Both suited and offsuit
    }
  }

  /**
   * Remove dead cards from range
   */
  removeDeadCards(range: OpponentRange, deadCards: Card[]): OpponentRange {
    const deadRanks = new Set(deadCards.map(c => parseCard(c)?.rank).filter(Boolean));

    const filteredRanges = range.ranges.map(r => ({
      ...r,
      hands: r.hands.filter(hand => {
        const ranks = hand.replace(/[so+]/, '').split('');
        return !ranks.some(rank => deadRanks.has(rank as any));
      }),
    }));

    return {
      ...range,
      ranges: filteredRanges,
      totalCombos: this.calculateTotalCombos(filteredRanges),
    };
  }
}

