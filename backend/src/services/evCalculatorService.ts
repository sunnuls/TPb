import { Card, Equity } from '@tpb/shared';
import { EquityService } from './equityService';
import { logger } from '../utils/logger';

export interface EVCalculation {
  action: 'fold' | 'call' | 'raise' | 'bet' | 'check';
  ev: number; // Expected value in big blinds
  evDifference: number; // Difference from best action
  isBestAction: boolean;
  breakdown: {
    winEV?: number;
    loseEV?: number;
    tieEV?: number;
    foldEquity?: number;
  };
  explanation: string;
}

export interface EVAnalysis {
  actions: EVCalculation[];
  bestAction: EVCalculation;
  potOdds?: number;
  requiredEquity?: number;
}

export class EVCalculatorService {
  private equityService: EquityService;

  constructor() {
    this.equityService = new EquityService();
  }

  /**
   * Calculate EV for different actions
   */
  async calculateEV(
    heroCards: Card[],
    board: Card[],
    pot: number,
    betSize: number,
    heroStack: number,
    villainStack: number,
    equity?: Equity
  ): Promise<EVAnalysis> {
    logger.info('Calculating EV for decision point');

    // Calculate equity if not provided
    if (!equity) {
      const equityResults = await this.equityService.calculateEquity(
        [heroCards, ['As', 'Ah']], // Placeholder villain range
        board
      );
      equity = equityResults[0];
    }

    const actions: EVCalculation[] = [];

    // Calculate EV for fold
    actions.push(this.calculateFoldEV());

    // Calculate EV for call
    if (betSize > 0) {
      actions.push(this.calculateCallEV(equity, pot, betSize));
    }

    // Calculate EV for raise
    if (betSize > 0 && heroStack > betSize * 2) {
      const raiseSize = betSize * 3;
      actions.push(await this.calculateRaiseEV(equity, pot, betSize, raiseSize, heroStack, villainStack));
    }

    // Calculate EV for bet (if checking is available)
    if (betSize === 0 && heroStack > pot * 0.5) {
      const betAmount = pot * 0.75;
      actions.push(await this.calculateBetEV(equity, pot, betAmount, heroStack, villainStack));
    }

    // Calculate EV for check
    if (betSize === 0) {
      actions.push(this.calculateCheckEV(equity, pot));
    }

    // Find best action
    const bestAction = actions.reduce((best, curr) =>
      curr.ev > best.ev ? curr : best
    );

    // Calculate EV differences
    actions.forEach(action => {
      action.evDifference = action.ev - bestAction.ev;
      action.isBestAction = action.action === bestAction.action;
    });

    // Calculate pot odds if facing a bet
    const potOdds = betSize > 0 ? betSize / (pot + betSize) : undefined;
    const requiredEquity = potOdds;

    logger.info(`EV Analysis complete. Best action: ${bestAction.action} (EV: ${bestAction.ev.toFixed(2)})`);

    return {
      actions,
      bestAction,
      potOdds,
      requiredEquity,
    };
  }

  /**
   * Calculate EV for folding
   */
  private calculateFoldEV(): EVCalculation {
    return {
      action: 'fold',
      ev: 0,
      evDifference: 0,
      isBestAction: false,
      breakdown: {},
      explanation: 'Folding gives 0 EV (preserves remaining stack)',
    };
  }

  /**
   * Calculate EV for calling
   * EV(call) = (equity * (pot + call)) - call
   */
  private calculateCallEV(equity: Equity, pot: number, callAmount: number): EVCalculation {
    const totalPot = pot + callAmount * 2;
    const winEV = equity.equity * totalPot;
    const loseEV = callAmount;
    const ev = winEV - loseEV;

    const potOdds = callAmount / (pot + callAmount);
    const explanation = equity.equity >= potOdds
      ? `Profitable call: ${(equity.equity * 100).toFixed(1)}% equity > ${(potOdds * 100).toFixed(1)}% pot odds`
      : `Unprofitable call: ${(equity.equity * 100).toFixed(1)}% equity < ${(potOdds * 100).toFixed(1)}% pot odds`;

    return {
      action: 'call',
      ev: Number(ev.toFixed(2)),
      evDifference: 0,
      isBestAction: false,
      breakdown: {
        winEV: Number(winEV.toFixed(2)),
        loseEV: Number(loseEV.toFixed(2)),
      },
      explanation,
    };
  }

  /**
   * Calculate EV for raising
   * EV(raise) = (foldEquity * pot) + ((1 - foldEquity) * equity * totalPot) - raise
   */
  private async calculateRaiseEV(
    equity: Equity,
    pot: number,
    facingBet: number,
    raiseSize: number,
    heroStack: number,
    villainStack: number
  ): Promise<EVCalculation> {
    // Estimate fold equity (simplified)
    const foldEquity = this.estimateFoldEquity(raiseSize, pot + facingBet, villainStack);

    const foldEV = foldEquity * pot;
    const totalPot = pot + facingBet + raiseSize * 2;
    const callEV = (1 - foldEquity) * equity.equity * totalPot;
    const cost = raiseSize;
    const ev = foldEV + callEV - cost;

    const explanation = `Raise with ${(foldEquity * 100).toFixed(1)}% fold equity and ${(equity.equity * 100).toFixed(1)}% equity when called`;

    return {
      action: 'raise',
      ev: Number(ev.toFixed(2)),
      evDifference: 0,
      isBestAction: false,
      breakdown: {
        foldEquity: Number((foldEquity * 100).toFixed(1)),
        winEV: Number(callEV.toFixed(2)),
        loseEV: Number(cost.toFixed(2)),
      },
      explanation,
    };
  }

  /**
   * Calculate EV for betting
   */
  private async calculateBetEV(
    equity: Equity,
    pot: number,
    betSize: number,
    heroStack: number,
    villainStack: number
  ): Promise<EVCalculation> {
    // Estimate fold equity
    const foldEquity = this.estimateFoldEquity(betSize, pot, villainStack);

    const foldEV = foldEquity * pot;
    const totalPot = pot + betSize * 2;
    const callEV = (1 - foldEquity) * equity.equity * totalPot;
    const cost = betSize;
    const ev = foldEV + callEV - cost;

    const explanation = `Bet ${betSize} into ${pot} with ${(foldEquity * 100).toFixed(1)}% fold equity`;

    return {
      action: 'bet',
      ev: Number(ev.toFixed(2)),
      evDifference: 0,
      isBestAction: false,
      breakdown: {
        foldEquity: Number((foldEquity * 100).toFixed(1)),
        winEV: Number(callEV.toFixed(2)),
        loseEV: Number(cost.toFixed(2)),
      },
      explanation,
    };
  }

  /**
   * Calculate EV for checking
   * EV(check) = equity * pot
   */
  private calculateCheckEV(equity: Equity, pot: number): EVCalculation {
    const ev = equity.equity * pot;

    return {
      action: 'check',
      ev: Number(ev.toFixed(2)),
      evDifference: 0,
      isBestAction: false,
      breakdown: {
        winEV: Number(ev.toFixed(2)),
      },
      explanation: `Check and realize ${(equity.equity * 100).toFixed(1)}% equity`,
    };
  }

  /**
   * Estimate opponent fold equity (simplified model)
   */
  private estimateFoldEquity(betSize: number, pot: number, villainStack: number): number {
    // Simple fold equity model based on bet-to-pot ratio
    const betToPotRatio = betSize / pot;

    // Base fold equity
    let foldEquity = 0.3; // 30% baseline

    // Increase fold equity with larger bets
    if (betToPotRatio > 1.0) {
      foldEquity += 0.2; // 50% for overbet
    } else if (betToPotRatio > 0.75) {
      foldEquity += 0.15; // 45% for 75%+ pot bet
    } else if (betToPotRatio > 0.5) {
      foldEquity += 0.1; // 40% for 50%+ pot bet
    }

    // Adjust for stack sizes
    if (villainStack < pot * 2) {
      foldEquity *= 0.8; // Reduce fold equity when villain is committed
    }

    return Math.min(0.8, foldEquity); // Cap at 80%
  }

  /**
   * Calculate pot odds required to call
   */
  calculatePotOdds(pot: number, callAmount: number): number {
    return callAmount / (pot + callAmount);
  }

  /**
   * Calculate implied odds
   */
  calculateImpliedOdds(
    pot: number,
    callAmount: number,
    potentialWinnings: number
  ): number {
    return callAmount / (pot + callAmount + potentialWinnings);
  }
}

