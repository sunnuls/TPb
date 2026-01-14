import { EventEmitter } from 'events';
import { PlayerAction, Street, Position } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface SessionMetrics {
  handsPlayed: number;
  totalWinnings: number;
  bigBlindsWon: number;
  vpip: number;
  pfr: number;
  aggressionFactor: number;
  wtsd: number; // Went To ShowDown
  wsd: number; // Won at ShowDown
  threeBetPct: number;
  foldToCBet: number;
  cBetFreq: number;
  winRate: number; // BB/100
  hourlyRate: number;
  roi: number;
}

export interface HandMetrics {
  handId: string;
  profit: number;
  expectedValue: number;
  equity: number;
  actualOutcome: number;
  skillFactor: number; // -1 to 1
  mistakes: number;
  optimalActions: number;
}

export interface TrendData {
  metric: string;
  values: number[];
  timestamps: Date[];
  trend: 'up' | 'down' | 'stable';
  changePercent: number;
}

/**
 * Advanced Analytics Service
 */
export class AdvancedAnalyticsService extends EventEmitter {
  private sessionData: Map<string, SessionMetrics> = new Map();
  private handMetrics: HandMetrics[] = [];

  /**
   * Calculate session metrics
   */
  calculateSessionMetrics(
    sessionId: string,
    hands: any[],
    actions: PlayerAction[]
  ): SessionMetrics {
    logger.info(`Calculating metrics for session ${sessionId}`);

    const totalHands = hands.length;
    const pfRaises = actions.filter(
      a => a.action === 'raise' && a.street === 'preflop'
    ).length;
    const vpipActions = actions.filter(
      a => (a.action === 'call' || a.action === 'raise' || a.action === 'bet') && a.street === 'preflop'
    ).length;
    const totalBets = actions.filter(a => a.action === 'bet').length;
    const totalRaises = actions.filter(a => a.action === 'raise').length;
    const totalCalls = actions.filter(a => a.action === 'call').length;

    const metrics: SessionMetrics = {
      handsPlayed: totalHands,
      totalWinnings: 0,
      bigBlindsWon: 0,
      vpip: totalHands > 0 ? (vpipActions / totalHands) * 100 : 0,
      pfr: totalHands > 0 ? (pfRaises / totalHands) * 100 : 0,
      aggressionFactor: totalCalls > 0 ? (totalBets + totalRaises) / totalCalls : 0,
      wtsd: 0,
      wsd: 0,
      threeBetPct: 0,
      foldToCBet: 0,
      cBetFreq: 0,
      winRate: 0,
      hourlyRate: 0,
      roi: 0,
    };

    this.sessionData.set(sessionId, metrics);
    this.emit('sessionAnalyzed', { sessionId, metrics });

    return metrics;
  }

  /**
   * Analyze hand performance
   */
  analyzeHand(
    handId: string,
    heroActions: PlayerAction[],
    result: { won: boolean; amount: number },
    equity: number,
    optimalStrategy?: any
  ): HandMetrics {
    const profit = result.won ? result.amount : -result.amount;
    const expectedValue = equity * result.amount;
    const actualOutcome = result.won ? 1 : 0;

    // Calculate skill factor (-1 = bad, 0 = neutral, 1 = good)
    const skillFactor = (profit - expectedValue) / Math.abs(expectedValue);

    // Count mistakes (simplified)
    const mistakes = heroActions.filter(a => {
      // This would compare against optimal strategy
      return false; // Placeholder
    }).length;

    const optimalActions = heroActions.length - mistakes;

    const metrics: HandMetrics = {
      handId,
      profit,
      expectedValue,
      equity,
      actualOutcome,
      skillFactor: Math.max(-1, Math.min(1, skillFactor)),
      mistakes,
      optimalActions,
    };

    this.handMetrics.push(metrics);

    // Trim history
    if (this.handMetrics.length > 10000) {
      this.handMetrics = this.handMetrics.slice(-10000);
    }

    return metrics;
  }

  /**
   * Calculate win rate (BB/100)
   */
  calculateWinRate(
    handsPlayed: number,
    totalWinnings: number,
    bigBlind: number
  ): number {
    if (handsPlayed === 0) return 0;
    const bigBlindsWon = totalWinnings / bigBlind;
    return (bigBlindsWon / handsPlayed) * 100;
  }

  /**
   * Calculate standard deviation
   */
  calculateStandardDeviation(values: number[]): number {
    if (values.length === 0) return 0;

    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
    const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;

    return Math.sqrt(variance);
  }

  /**
   * Identify statistical outliers
   */
  identifyOutliers(values: number[]): { outliers: number[]; threshold: number } {
    if (values.length < 3) return { outliers: [], threshold: 0 };

    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const sd = this.calculateStandardDeviation(values);
    const threshold = sd * 2; // 2 standard deviations

    const outliers = values.filter(val => Math.abs(val - mean) > threshold);

    return { outliers, threshold };
  }

  /**
   * Calculate percentile
   */
  calculatePercentile(values: number[], percentile: number): number {
    if (values.length === 0) return 0;

    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;

    return sorted[Math.max(0, index)];
  }

  /**
   * Calculate moving average
   */
  calculateMovingAverage(values: number[], window: number): number[] {
    if (values.length < window) return values;

    const movingAvg: number[] = [];

    for (let i = 0; i <= values.length - window; i++) {
      const windowValues = values.slice(i, i + window);
      const avg = windowValues.reduce((sum, val) => sum + val, 0) / window;
      movingAvg.push(avg);
    }

    return movingAvg;
  }

  /**
   * Detect performance trends
   */
  detectTrend(
    metric: string,
    values: number[],
    timestamps: Date[],
    window: number = 20
  ): TrendData {
    if (values.length < 2) {
      return {
        metric,
        values,
        timestamps,
        trend: 'stable',
        changePercent: 0,
      };
    }

    // Calculate moving average
    const movingAvg = this.calculateMovingAverage(values, Math.min(window, values.length));

    // Compare recent vs historical
    const recentAvg = movingAvg.slice(-Math.ceil(movingAvg.length / 4));
    const historicalAvg = movingAvg.slice(0, Math.ceil(movingAvg.length / 4));

    const recentMean = recentAvg.reduce((sum, v) => sum + v, 0) / recentAvg.length;
    const historicalMean = historicalAvg.reduce((sum, v) => sum + v, 0) / historicalAvg.length;

    const changePercent = ((recentMean - historicalMean) / Math.abs(historicalMean)) * 100;

    let trend: 'up' | 'down' | 'stable';
    if (changePercent > 5) {
      trend = 'up';
    } else if (changePercent < -5) {
      trend = 'down';
    } else {
      trend = 'stable';
    }

    return {
      metric,
      values,
      timestamps,
      trend,
      changePercent,
    };
  }

  /**
   * Generate performance report
   */
  generateReport(sessionId: string): {
    summary: SessionMetrics;
    trends: TrendData[];
    outliers: any;
    recommendations: string[];
  } {
    const metrics = this.sessionData.get(sessionId);

    if (!metrics) {
      throw new Error(`Session ${sessionId} not found`);
    }

    // Generate trends (placeholder)
    const trends: TrendData[] = [];

    // Identify outliers (placeholder)
    const outliers = {};

    // Generate recommendations
    const recommendations: string[] = [];

    if (metrics.vpip > 30) {
      recommendations.push('Your VPIP is high - consider tightening your range');
    }

    if (metrics.pfr < 10) {
      recommendations.push('Your PFR is low - consider raising more aggressively');
    }

    if (metrics.aggressionFactor < 2) {
      recommendations.push('Your aggression factor is low - bet and raise more often');
    }

    return {
      summary: metrics,
      trends,
      outliers,
      recommendations,
    };
  }

  /**
   * Get session metrics
   */
  getSessionMetrics(sessionId: string): SessionMetrics | undefined {
    return this.sessionData.get(sessionId);
  }

  /**
   * Get hand metrics
   */
  getHandMetrics(): HandMetrics[] {
    return [...this.handMetrics];
  }

  /**
   * Clear analytics data
   */
  clearData(): void {
    this.sessionData.clear();
    this.handMetrics = [];
    logger.info('Analytics data cleared');
  }
}

