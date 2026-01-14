import { Position, Street } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface Leak {
  id: string;
  category: 'preflop' | 'postflop' | 'positional' | 'sizing' | 'frequency' | 'mental';
  severity: 'minor' | 'moderate' | 'major' | 'critical';
  title: string;
  description: string;
  impact: string; // Estimated BB/100 cost
  recommendation: string;
  examples?: string[];
}

export interface LeakReport {
  playerName: string;
  totalLeaks: number;
  criticalLeaks: number;
  estimatedCost: number; // BB/100
  leaks: Leak[];
  priority: Leak[];
  timestamp: Date;
}

/**
 * Leak Finder Service - identifies common poker leaks
 */
export class LeakFinderService {
  private leakCounter = 0;

  /**
   * Analyze player for leaks
   */
  analyzeLeaks(
    playerName: string,
    stats: any,
    actions: any[],
    results: number[]
  ): LeakReport {
    logger.info(`Analyzing leaks for ${playerName}`);

    const leaks: Leak[] = [];

    // Preflop leaks
    leaks.push(...this.checkPreflopLeaks(stats));

    // Postflop leaks
    leaks.push(...this.checkPostflopLeaks(stats, actions));

    // Positional leaks
    leaks.push(...this.checkPositionalLeaks(stats));

    // Sizing leaks
    leaks.push(...this.checkSizingLeaks(actions));

    // Frequency leaks
    leaks.push(...this.checkFrequencyLeaks(stats));

    // Mental game leaks
    leaks.push(...this.checkMentalLeaks(results));

    // Sort by severity
    const severityOrder = { critical: 0, major: 1, moderate: 2, minor: 3 };
    leaks.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

    const criticalLeaks = leaks.filter(l => l.severity === 'critical').length;
    const estimatedCost = leaks.reduce((sum, leak) => {
      const cost = parseFloat(leak.impact) || 0;
      return sum + cost;
    }, 0);

    // Top 5 priority leaks
    const priority = leaks.slice(0, 5);

    return {
      playerName,
      totalLeaks: leaks.length,
      criticalLeaks,
      estimatedCost,
      leaks,
      priority,
      timestamp: new Date(),
    };
  }

  /**
   * Check preflop leaks
   */
  private checkPreflopLeaks(stats: any): Leak[] {
    const leaks: Leak[] = [];

    // VPIP too high
    if (stats.vpip > 30) {
      leaks.push({
        id: this.generateId(),
        category: 'preflop',
        severity: stats.vpip > 40 ? 'critical' : 'major',
        title: 'Playing Too Many Hands',
        description: `Your VPIP is ${stats.vpip.toFixed(1)}%, which is too high`,
        impact: `${((stats.vpip - 25) * 0.5).toFixed(1)} BB/100`,
        recommendation: 'Tighten your starting hand requirements, especially from early position',
        examples: ['Fold weak hands from UTG', 'Avoid calling with suited connectors OOP'],
      });
    }

    // VPIP too low
    if (stats.vpip < 15 && stats.handsPlayed > 100) {
      leaks.push({
        id: this.generateId(),
        category: 'preflop',
        severity: 'moderate',
        title: 'Playing Too Tight',
        description: `Your VPIP is ${stats.vpip.toFixed(1)}%, which is too tight`,
        impact: `${((20 - stats.vpip) * 0.3).toFixed(1)} BB/100`,
        recommendation: 'Loosen up your range, especially from late position',
        examples: ['Open more hands from BTN/CO', 'Defend BB more liberally'],
      });
    }

    // PFR too low relative to VPIP (limping too much)
    if (stats.vpip > 0 && (stats.pfr / stats.vpip) < 0.5) {
      leaks.push({
        id: this.generateId(),
        category: 'preflop',
        severity: 'major',
        title: 'Limping Too Often',
        description: `Your PFR/VPIP ratio is ${((stats.pfr / stats.vpip) * 100).toFixed(0)}%`,
        impact: '3.5 BB/100',
        recommendation: 'Raise instead of limping with your playable hands',
        examples: ['Raise 22-99 instead of limping', 'Raise suited connectors instead of limping'],
      });
    }

    // 3-bet too high
    if (stats.threeBet > 12) {
      leaks.push({
        id: this.generateId(),
        category: 'preflop',
        severity: 'moderate',
        title: '3-Betting Too Frequently',
        description: `Your 3-bet frequency is ${stats.threeBet.toFixed(1)}%`,
        impact: '2.0 BB/100',
        recommendation: 'Reduce your 3-bet frequency and improve your range selection',
      });
    }

    return leaks;
  }

  /**
   * Check postflop leaks
   */
  private checkPostflopLeaks(stats: any, actions: any[]): Leak[] {
    const leaks: Leak[] = [];

    // C-bet too high
    if (stats.cBet > 75) {
      leaks.push({
        id: this.generateId(),
        category: 'postflop',
        severity: 'major',
        title: 'C-Betting Too Often',
        description: `Your c-bet frequency is ${stats.cBet.toFixed(1)}%`,
        impact: '2.5 BB/100',
        recommendation: 'Be more selective with your c-bets based on board texture',
        examples: ['Check more on wet boards', 'Check when out of position with weak hands'],
      });
    }

    // Fold to c-bet too high
    if (stats.foldToCBet > 70) {
      leaks.push({
        id: this.generateId(),
        category: 'postflop',
        severity: 'critical',
        title: 'Folding to C-Bets Too Much',
        description: `You fold to c-bets ${stats.foldToCBet.toFixed(1)}% of the time`,
        impact: '4.0 BB/100',
        recommendation: 'Defend more by calling or raising against c-bets',
        examples: ['Float more in position', 'Check-raise bluff occasionally'],
      });
    }

    // WTSD too low (giving up too easily)
    if (stats.wtsd < 20) {
      leaks.push({
        id: this.generateId(),
        category: 'postflop',
        severity: 'major',
        title: 'Giving Up Too Easily',
        description: `Your WTSD is ${stats.wtsd.toFixed(1)}%, indicating you fold too often`,
        impact: '3.0 BB/100',
        recommendation: 'Call down more with marginal hands when you have good pot odds',
      });
    }

    // Aggression factor too low
    if (stats.aggressionFactor < 1.5) {
      leaks.push({
        id: this.generateId(),
        category: 'postflop',
        severity: 'major',
        title: 'Not Aggressive Enough',
        description: `Your aggression factor is ${stats.aggressionFactor.toFixed(2)}`,
        impact: '3.5 BB/100',
        recommendation: 'Bet and raise more, call less',
        examples: ['Turn more draws into semi-bluffs', 'Value bet thinner'],
      });
    }

    return leaks;
  }

  /**
   * Check positional leaks
   */
  private checkPositionalLeaks(stats: any): Leak[] {
    const leaks: Leak[] = [];

    // Not exploiting position
    if (stats.positionAwareness && stats.positionAwareness < 0.5) {
      leaks.push({
        id: this.generateId(),
        category: 'positional',
        severity: 'major',
        title: 'Not Exploiting Position',
        description: 'You play similarly from all positions',
        impact: '2.5 BB/100',
        recommendation: 'Play tighter from early position and looser from late position',
        examples: ['Open 40%+ from BTN', 'Fold weak hands from UTG'],
      });
    }

    return leaks;
  }

  /**
   * Check sizing leaks
   */
  private checkSizingLeaks(actions: any[]): Leak[] {
    const leaks: Leak[] = [];

    // Analyze bet sizing patterns
    const bets = actions.filter(a => a.action === 'bet' || a.action === 'raise');

    if (bets.length > 10) {
      const sizes = bets.map(b => b.amount / (b.pot || 1));
      const avgSize = sizes.reduce((sum, s) => sum + s, 0) / sizes.length;

      // Betting too small
      if (avgSize < 0.4) {
        leaks.push({
          id: this.generateId(),
          category: 'sizing',
          severity: 'moderate',
          title: 'Betting Too Small',
          description: `Your average bet size is ${(avgSize * 100).toFixed(0)}% of pot`,
          impact: '1.5 BB/100',
          recommendation: 'Increase your bet sizes to 50-75% of pot',
        });
      }

      // Betting too large
      if (avgSize > 1.2) {
        leaks.push({
          id: this.generateId(),
          category: 'sizing',
          severity: 'moderate',
          title: 'Betting Too Large',
          description: `Your average bet size is ${(avgSize * 100).toFixed(0)}% of pot`,
          impact: '1.8 BB/100',
          recommendation: 'Reduce your bet sizes to 50-75% of pot',
        });
      }
    }

    return leaks;
  }

  /**
   * Check frequency leaks
   */
  private checkFrequencyLeaks(stats: any): Leak[] {
    const leaks: Leak[] = [];

    // Check-raise too rare
    if (stats.checkRaise < 5 && stats.handsPlayed > 100) {
      leaks.push({
        id: this.generateId(),
        category: 'frequency',
        severity: 'minor',
        title: 'Never Check-Raising',
        description: 'You check-raise very rarely',
        impact: '1.0 BB/100',
        recommendation: 'Incorporate check-raises into your strategy for balance',
      });
    }

    return leaks;
  }

  /**
   * Check mental game leaks
   */
  private checkMentalLeaks(results: number[]): Leak[] {
    const leaks: Leak[] = [];

    if (results.length < 10) return leaks;

    // Check for tilt patterns (high variance in recent results)
    const recentResults = results.slice(-20);
    const variance = this.calculateVariance(recentResults);
    const mean = recentResults.reduce((sum, v) => sum + v, 0) / recentResults.length;

    if (variance > Math.abs(mean) * 3) {
      leaks.push({
        id: this.generateId(),
        category: 'mental',
        severity: 'major',
        title: 'Possible Tilt Issues',
        description: 'High variance in recent results suggests inconsistent play',
        impact: '3.0 BB/100',
        recommendation: 'Take breaks after big losses, review your mental game',
        examples: ['Stop playing after 3 buy-ins down', 'Practice mindfulness'],
      });
    }

    return leaks;
  }

  /**
   * Calculate variance
   */
  private calculateVariance(values: number[]): number {
    if (values.length === 0) return 0;

    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const squaredDiffs = values.map(val => Math.pow(val - mean, 2));

    return squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `leak-${Date.now()}-${++this.leakCounter}`;
  }
}

