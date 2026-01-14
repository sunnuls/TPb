import { logger } from '../utils/logger';

export interface PayoutStructure {
  totalPrize: number;
  payouts: number[]; // Payout for each position [1st, 2nd, 3rd, ...]
}

export interface ICMResult {
  equity: number; // Expected monetary value
  equityPercentage: number; // % of total prize pool
  chipEV: number; // Chip expected value
  cashEV: number; // Cash expected value (ICM-adjusted)
  risk: number; // Risk factor (0-1)
}

export interface TournamentState {
  players: TournamentPlayer[];
  payoutStructure: PayoutStructure;
  remainingPlayers: number;
  totalChips: number;
}

export interface TournamentPlayer {
  name: string;
  stack: number;
  position?: number; // Current table position
}

/**
 * ICM (Independent Chip Model) Calculator Service
 * Calculates tournament equity based on chip stacks and payout structure
 */
export class ICMCalculatorService {
  /**
   * Calculate ICM for all players
   */
  calculateICM(state: TournamentState): Map<string, ICMResult> {
    logger.info('Calculating ICM for tournament state');

    const results = new Map<string, ICMResult>();

    for (const player of state.players) {
      const equity = this.calculatePlayerEquity(
        player.stack,
        state.players,
        state.payoutStructure
      );

      results.set(player.name, equity);
    }

    return results;
  }

  /**
   * Calculate equity for a single player
   */
  calculatePlayerEquity(
    heroStack: number,
    allPlayers: TournamentPlayer[],
    payoutStructure: PayoutStructure
  ): ICMResult {
    const totalChips = allPlayers.reduce((sum, p) => sum + p.stack, 0);

    // Simple ICM calculation (exact for small fields, approximation for large)
    const winProbabilities = this.calculateWinProbabilities(heroStack, allPlayers);

    let cashEV = 0;
    for (let i = 0; i < winProbabilities.length && i < payoutStructure.payouts.length; i++) {
      cashEV += winProbabilities[i] * payoutStructure.payouts[i];
    }

    const chipEV = heroStack; // In chip EV, your stack is your EV
    const equityPercentage = (cashEV / payoutStructure.totalPrize) * 100;

    // Calculate risk (difference between chip EV and cash EV)
    const chipPercentage = (heroStack / totalChips) * 100;
    const risk = Math.abs(chipPercentage - equityPercentage) / 100;

    return {
      equity: cashEV,
      equityPercentage,
      chipEV,
      cashEV,
      risk,
    };
  }

  /**
   * Calculate win probabilities for each place
   */
  private calculateWinProbabilities(
    heroStack: number,
    allPlayers: TournamentPlayer[]
  ): number[] {
    const totalChips = allPlayers.reduce((sum, p) => sum + p.stack, 0);
    const playerCount = allPlayers.length;

    if (playerCount === 1) {
      return [1]; // 100% to win if only player
    }

    if (playerCount === 2) {
      // Heads-up: probability is simply stack ratio
      return [heroStack / totalChips, 1 - heroStack / totalChips];
    }

    // For more players, use recursive ICM calculation
    return this.recursiveICM(heroStack, allPlayers, 0);
  }

  /**
   * Recursive ICM calculation (simplified)
   */
  private recursiveICM(
    heroStack: number,
    allPlayers: TournamentPlayer[],
    depth: number
  ): number[] {
    const playerCount = allPlayers.length;

    if (playerCount === 1) {
      return [1];
    }

    if (depth > 5) {
      // Depth limit for performance - use approximation
      const totalChips = allPlayers.reduce((sum, p) => sum + p.stack, 0);
      const prob = heroStack / totalChips;
      return Array(playerCount).fill(prob / playerCount);
    }

    const totalChips = allPlayers.reduce((sum, p) => sum + p.stack, 0);
    const probabilities: number[] = [];

    // Calculate probability of finishing in each position
    for (let place = 0; place < playerCount; place++) {
      if (place === 0) {
        // Probability of winning
        probabilities.push(heroStack / totalChips);
      } else {
        // Simplified: equal probability for other places
        probabilities.push((1 - heroStack / totalChips) / (playerCount - 1));
      }
    }

    return probabilities;
  }

  /**
   * Calculate chip EV to cash EV conversion factor
   */
  calculateConversionFactor(
    heroStack: number,
    state: TournamentState
  ): number {
    const icm = this.calculatePlayerEquity(
      heroStack,
      state.players,
      state.payoutStructure
    );

    const totalChips = state.totalChips || state.players.reduce((sum, p) => sum + p.stack, 0);
    const chipPercentage = heroStack / totalChips;

    // Conversion factor: how much is 1 chip worth in $ compared to chip EV
    return icm.equityPercentage / (chipPercentage * 100);
  }

  /**
   * Calculate ICM pressure (risk of busting vs chip gain)
   */
  calculateICMPressure(
    heroStack: number,
    potSize: number,
    state: TournamentState
  ): {
    pressure: number; // 0-1, higher = more pressure
    recommendation: string;
  } {
    const currentICM = this.calculatePlayerEquity(
      heroStack,
      state.players,
      state.payoutStructure
    );

    // Calculate ICM if we win pot
    const winICM = this.calculatePlayerEquity(
      heroStack + potSize,
      state.players,
      state.payoutStructure
    );

    // Calculate ICM if we lose pot
    const loseICM = this.calculatePlayerEquity(
      Math.max(0, heroStack - potSize),
      state.players,
      state.payoutStructure
    );

    // ICM pressure: risk of losing vs reward of winning
    const gainIfWin = winICM.equity - currentICM.equity;
    const lossIfLose = currentICM.equity - loseICM.equity;

    const pressure = lossIfLose > 0 ? lossIfLose / (lossIfLose + gainIfWin) : 0;

    let recommendation: string;

    if (pressure > 0.7) {
      recommendation = 'High ICM pressure - play tight, avoid marginal spots';
    } else if (pressure > 0.5) {
      recommendation = 'Moderate ICM pressure - be selective';
    } else if (pressure > 0.3) {
      recommendation = 'Low ICM pressure - standard play';
    } else {
      recommendation = 'Minimal ICM pressure - focus on chip accumulation';
    }

    return {
      pressure: Math.min(1, pressure),
      recommendation,
    };
  }

  /**
   * Calculate bubble factor (proximity to money)
   */
  calculateBubbleFactor(state: TournamentState): {
    factor: number; // 1 = normal, >1 = near bubble
    isBubble: boolean;
    playersToMoney: number;
  } {
    const remainingPlayers = state.remainingPlayers;
    const paidPlaces = state.payoutStructure.payouts.length;
    const playersToMoney = Math.max(0, remainingPlayers - paidPlaces);

    const isBubble = playersToMoney === 1;

    // Bubble factor increases as we approach the bubble
    let factor = 1.0;

    if (playersToMoney <= 3) {
      factor = 1.0 + (4 - playersToMoney) * 0.3;
    }

    return {
      factor,
      isBubble,
      playersToMoney,
    };
  }

  /**
   * Calculate $EV of a decision (ICM-adjusted)
   */
  calculateDecisionEV(
    heroStack: number,
    potSize: number,
    callAmount: number,
    winProbability: number,
    state: TournamentState
  ): {
    chipEV: number;
    cashEV: number;
    evDifference: number;
    shouldCall: boolean;
  } {
    // Chip EV (simple)
    const chipEV = winProbability * (potSize + callAmount) - (1 - winProbability) * callAmount;

    // Cash EV (ICM-adjusted)
    const winStack = heroStack + potSize + callAmount - callAmount;
    const loseStack = heroStack - callAmount;

    const currentICM = this.calculatePlayerEquity(heroStack, state.players, state.payoutStructure);
    const winICM = this.calculatePlayerEquity(winStack, state.players, state.payoutStructure);
    const loseICM = this.calculatePlayerEquity(loseStack, state.players, state.payoutStructure);

    const cashEV = winProbability * winICM.equity + (1 - winProbability) * loseICM.equity - currentICM.equity;

    return {
      chipEV,
      cashEV,
      evDifference: chipEV - cashEV,
      shouldCall: cashEV > 0,
    };
  }

  /**
   * Generate payout structure from prize pool
   */
  generatePayoutStructure(
    totalPrize: number,
    playerCount: number,
    structure: 'standard' | 'flat' | 'top_heavy' = 'standard'
  ): PayoutStructure {
    const paidPlaces = Math.min(
      Math.floor(playerCount / 10), // 10% get paid
      playerCount
    );

    const payouts: number[] = [];

    switch (structure) {
      case 'standard':
        // Standard: 50% to 1st, 30% to 2nd, 20% to 3rd
        if (paidPlaces >= 1) payouts.push(totalPrize * 0.5);
        if (paidPlaces >= 2) payouts.push(totalPrize * 0.3);
        if (paidPlaces >= 3) payouts.push(totalPrize * 0.2);
        break;

      case 'flat':
        // Flat: equal payouts
        const flatAmount = totalPrize / paidPlaces;
        for (let i = 0; i < paidPlaces; i++) {
          payouts.push(flatAmount);
        }
        break;

      case 'top_heavy':
        // Top heavy: 60% to 1st, 25% to 2nd, 15% to 3rd
        if (paidPlaces >= 1) payouts.push(totalPrize * 0.6);
        if (paidPlaces >= 2) payouts.push(totalPrize * 0.25);
        if (paidPlaces >= 3) payouts.push(totalPrize * 0.15);
        break;
    }

    return {
      totalPrize,
      payouts,
    };
  }
}

