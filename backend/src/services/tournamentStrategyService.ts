import { Position } from '@tpb/shared';
import { ICMCalculatorService, TournamentState } from './icmCalculatorService';
import { logger } from '../utils/logger';

export interface StackDepth {
  bigBlinds: number;
  category: 'deep' | 'medium' | 'short' | 'push_fold';
  playStyle: string;
}

export interface TournamentPhase {
  phase: 'early' | 'middle' | 'bubble' | 'ITM' | 'final_table';
  adjustments: string[];
}

export interface TournamentRecommendation {
  situation: string;
  recommendation: string;
  reasoning: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  icmConsideration?: string;
}

/**
 * Tournament Strategy Service
 * Provides strategy recommendations specific to tournament play
 */
export class TournamentStrategyService {
  private icmCalculator: ICMCalculatorService;

  constructor() {
    this.icmCalculator = new ICMCalculatorService();
  }

  /**
   * Analyze stack depth
   */
  analyzeStackDepth(stack: number, bigBlind: number): StackDepth {
    const bb = stack / bigBlind;

    let category: StackDepth['category'];
    let playStyle: string;

    if (bb > 50) {
      category = 'deep';
      playStyle = 'Play standard poker, focus on postflop skill';
    } else if (bb > 20) {
      category = 'medium';
      playStyle = 'Tighten preflop, avoid marginal spots';
    } else if (bb > 10) {
      category = 'short';
      playStyle = 'Push/fold strategy, look for spots to shove';
    } else {
      category = 'push_fold';
      playStyle = 'Strict push/fold, only shove or fold preflop';
    }

    return {
      bigBlinds: bb,
      category,
      playStyle,
    };
  }

  /**
   * Determine tournament phase
   */
  determineTournamentPhase(
    remainingPlayers: number,
    totalPlayers: number,
    paidPlaces: number
  ): TournamentPhase {
    const percentRemaining = (remainingPlayers / totalPlayers) * 100;

    let phase: TournamentPhase['phase'];
    let adjustments: string[] = [];

    if (remainingPlayers <= 9) {
      phase = 'final_table';
      adjustments = [
        'ICM is critical - avoid marginal spots',
        'Pay attention to big stacks',
        'Laddering considerations',
      ];
    } else if (remainingPlayers <= paidPlaces) {
      phase = 'ITM';
      adjustments = [
        'Focus on chip accumulation',
        'Pressure short stacks',
        'ICM still matters but less extreme',
      ];
    } else if (remainingPlayers <= paidPlaces + 5) {
      phase = 'bubble';
      adjustments = [
        'Extreme ICM pressure',
        'Very tight unless big stack',
        'Avoid confrontations',
        'Exploit scared players if deep',
      ];
    } else if (percentRemaining < 40) {
      phase = 'middle';
      adjustments = [
        'Accumulate chips for late stages',
        'Start considering ICM',
        'Avoid unnecessary risks',
      ];
    } else {
      phase = 'early';
      adjustments = [
        'Play solid poker',
        'Build a stack',
        'ICM not a factor yet',
      ];
    }

    return {
      phase,
      adjustments,
    };
  }

  /**
   * Generate tournament recommendations
   */
  generateRecommendations(
    heroStack: number,
    bigBlind: number,
    position: Position,
    tournamentState: TournamentState
  ): TournamentRecommendation[] {
    const recommendations: TournamentRecommendation[] = [];

    // Stack depth analysis
    const stackDepth = this.analyzeStackDepth(heroStack, bigBlind);

    if (stackDepth.category === 'push_fold') {
      recommendations.push({
        situation: 'Critical Stack Depth',
        recommendation: 'Enter push/fold mode - only shove or fold preflop',
        reasoning: `You have ${stackDepth.bigBlinds.toFixed(1)}BB - too short for postflop play`,
        priority: 'critical',
      });
    } else if (stackDepth.category === 'short') {
      recommendations.push({
        situation: 'Short Stack',
        recommendation: 'Look for shove spots with decent equity',
        reasoning: `${stackDepth.bigBlinds.toFixed(1)}BB - need to accumulate chips soon`,
        priority: 'high',
      });
    }

    // ICM analysis
    const icmPressure = this.icmCalculator.calculateICMPressure(
      heroStack,
      bigBlind * 3, // Example pot size
      tournamentState
    );

    if (icmPressure.pressure > 0.6) {
      recommendations.push({
        situation: 'High ICM Pressure',
        recommendation: icmPressure.recommendation,
        reasoning: 'Your tournament equity is at risk',
        priority: 'high',
        icmConsideration: `ICM Pressure: ${(icmPressure.pressure * 100).toFixed(0)}%`,
      });
    }

    // Bubble analysis
    const bubbleFactor = this.icmCalculator.calculateBubbleFactor(tournamentState);

    if (bubbleFactor.isBubble) {
      recommendations.push({
        situation: 'Bubble',
        recommendation: 'Extreme caution - one player from the money',
        reasoning: 'Making the money is worth significant $EV',
        priority: 'critical',
        icmConsideration: 'Bubble situation',
      });
    } else if (bubbleFactor.playersToMoney <= 3) {
      recommendations.push({
        situation: 'Near Bubble',
        recommendation: 'Tighten up - approaching the money',
        reasoning: `${bubbleFactor.playersToMoney} players from the money`,
        priority: 'high',
      });
    }

    // Position-based recommendations
    if (stackDepth.category !== 'push_fold') {
      if (position === 'BTN' || position === 'CO') {
        recommendations.push({
          situation: 'Late Position',
          recommendation: 'Widen your stealing range',
          reasoning: 'Good position to accumulate chips with minimal risk',
          priority: 'medium',
        });
      } else if (position === 'SB' || position === 'BB') {
        recommendations.push({
          situation: 'Blind Defense',
          recommendation: 'Defend appropriately but consider ICM',
          reasoning: 'Balance defending vs tournament life preservation',
          priority: 'medium',
        });
      }
    }

    return recommendations;
  }

  /**
   * Calculate push/fold range (Nash equilibrium)
   */
  calculatePushFoldRange(
    stackBB: number,
    position: Position,
    opponents: number
  ): { range: string[]; frequency: number } {
    // Simplified push/fold ranges based on stack size
    let range: string[] = [];
    let frequency = 0;

    if (stackBB <= 10) {
      // Very short stack - wide push range
      if (position === 'BTN') {
        range = ['22+', 'A2+', 'K2+', 'Q2+', 'J7+', 'T7+', '97+'];
        frequency = 45;
      } else if (position === 'SB') {
        range = ['22+', 'A2+', 'K2+', 'Q5+', 'J8+', 'T8+'];
        frequency = 40;
      } else if (position === 'CO') {
        range = ['22+', 'A2+', 'K5+', 'Q8+', 'JT'];
        frequency = 35;
      } else {
        range = ['22+', 'A7+', 'K9+', 'QTs+'];
        frequency = 20;
      }
    } else if (stackBB <= 15) {
      // Short stack - selective push
      if (position === 'BTN') {
        range = ['22+', 'A2+', 'K5+', 'Q9+', 'JTs'];
        frequency = 35;
      } else if (position === 'SB') {
        range = ['33+', 'A5+', 'K9+', 'QJs'];
        frequency = 30;
      } else {
        range = ['66+', 'AT+', 'KQ'];
        frequency = 15;
      }
    } else if (stackBB <= 20) {
      // Medium-short - standard push
      if (position === 'BTN') {
        range = ['55+', 'A7+', 'KT+', 'QJ'];
        frequency = 25;
      } else {
        range = ['77+', 'AJ+', 'KQ'];
        frequency = 12;
      }
    } else {
      // Not push/fold territory
      range = ['TT+', 'AQ+'];
      frequency = 8;
    }

    return { range, frequency };
  }

  /**
   * Calculate calling range vs shove (Nash)
   */
  calculateCallVsShoveRange(
    stackBB: number,
    oppStackBB: number,
    position: Position
  ): { range: string[]; frequency: number } {
    let range: string[] = [];
    let frequency = 0;

    const potOdds = stackBB / (stackBB + oppStackBB);

    if (potOdds > 0.4) {
      // Getting good odds
      range = ['66+', 'A9+', 'KQ'];
      frequency = 15;
    } else if (potOdds > 0.35) {
      range = ['77+', 'AT+', 'KQ'];
      frequency = 12;
    } else {
      // Not getting good odds
      range = ['99+', 'AJ+'];
      frequency = 8;
    }

    return { range, frequency };
  }

  /**
   * Ante impact analysis
   */
  analyzeAnteImpact(
    ante: number,
    bigBlind: number,
    players: number
  ): {
    deadMoney: number;
    stealingValue: number;
    recommendation: string;
  } {
    const anteRatio = ante / bigBlind;
    const deadMoney = ante * players + 1.5 * bigBlind; // Antes + blinds

    const stealingValue = deadMoney / bigBlind;

    let recommendation: string;

    if (anteRatio >= 0.2) {
      recommendation = 'High antes - stealing is very profitable, widen your ranges';
    } else if (anteRatio >= 0.1) {
      recommendation = 'Moderate antes - stealing is important';
    } else {
      recommendation = 'No/low antes - standard play';
    }

    return {
      deadMoney,
      stealingValue,
      recommendation,
    };
  }
}

