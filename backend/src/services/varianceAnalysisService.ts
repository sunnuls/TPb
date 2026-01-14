import { logger } from '../utils/logger';

export interface VarianceMetrics {
  standardDeviation: number;
  variance: number;
  coefficient: number; // Coefficient of Variation
  downswingRisk: number; // Probability of downswing
  requiredBankroll: number; // Recommended bankroll in BB
}

export interface DownswingAnalysis {
  currentDownswing: number; // in BB
  longestDownswing: number; // in BB
  averageDownswing: number;
  downswingFrequency: number; // % of time in downswing
  recoveryTime: number; // average hands to recover
}

export interface RunItTwice {
  actualResult: number;
  expectedResult: number;
  variance: number;
  luck: number; // -1 (unlucky) to 1 (lucky)
}

/**
 * Variance Analysis Service
 */
export class VarianceAnalysisService {
  /**
   * Calculate variance metrics
   */
  calculateVarianceMetrics(results: number[], winRate: number): VarianceMetrics {
    const n = results.length;

    if (n === 0) {
      return {
        standardDeviation: 0,
        variance: 0,
        coefficient: 0,
        downswingRisk: 0,
        requiredBankroll: 0,
      };
    }

    // Calculate standard deviation
    const mean = results.reduce((sum, val) => sum + val, 0) / n;
    const squaredDiffs = results.map(val => Math.pow(val - mean, 2));
    const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / n;
    const standardDeviation = Math.sqrt(variance);

    // Coefficient of Variation (CV = SD / Mean)
    const coefficient = mean !== 0 ? standardDeviation / Math.abs(mean) : 0;

    // Downswing risk (probability of being below EV)
    // Using normal distribution approximation
    const zScore = winRate / standardDeviation;
    const downswingRisk = this.normalCDF(-zScore);

    // Required bankroll (Kelly Criterion adjusted)
    // Bankroll = (SD^2) / (2 * WinRate)
    const requiredBankroll = winRate > 0
      ? Math.ceil((Math.pow(standardDeviation, 2)) / (2 * winRate))
      : 100; // Default minimum

    return {
      standardDeviation,
      variance,
      coefficient,
      downswingRisk,
      requiredBankroll,
    };
  }

  /**
   * Analyze downswings
   */
  analyzeDownswings(cumulativeResults: number[]): DownswingAnalysis {
    if (cumulativeResults.length === 0) {
      return {
        currentDownswing: 0,
        longestDownswing: 0,
        averageDownswing: 0,
        downswingFrequency: 0,
        recoveryTime: 0,
      };
    }

    let currentDownswing = 0;
    let longestDownswing = 0;
    let totalDownswing = 0;
    let downswingCount = 0;
    let inDownswing = false;
    let downswingStart = 0;
    let totalRecoveryTime = 0;

    let peak = cumulativeResults[0];

    for (let i = 1; i < cumulativeResults.length; i++) {
      const current = cumulativeResults[i];

      if (current > peak) {
        // New peak - end downswing if in one
        if (inDownswing) {
          const recoveryTime = i - downswingStart;
          totalRecoveryTime += recoveryTime;
          inDownswing = false;
        }
        peak = current;
        currentDownswing = 0;
      } else {
        // Below peak - in downswing
        const drawdown = peak - current;

        if (!inDownswing) {
          inDownswing = true;
          downswingStart = i;
          downswingCount++;
        }

        currentDownswing = drawdown;
        totalDownswing += drawdown;

        if (drawdown > longestDownswing) {
          longestDownswing = drawdown;
        }
      }
    }

    const averageDownswing = downswingCount > 0 ? totalDownswing / downswingCount : 0;
    const downswingFrequency = (downswingCount / cumulativeResults.length) * 100;
    const recoveryTime = downswingCount > 0 ? totalRecoveryTime / downswingCount : 0;

    return {
      currentDownswing,
      longestDownswing,
      averageDownswing,
      downswingFrequency,
      recoveryTime,
    };
  }

  /**
   * Run it twice analysis (compare actual vs expected)
   */
  runItTwiceAnalysis(
    actualResults: number[],
    expectedResults: number[]
  ): RunItTwice {
    if (actualResults.length !== expectedResults.length || actualResults.length === 0) {
      return {
        actualResult: 0,
        expectedResult: 0,
        variance: 0,
        luck: 0,
      };
    }

    const actualSum = actualResults.reduce((sum, val) => sum + val, 0);
    const expectedSum = expectedResults.reduce((sum, val) => sum + val, 0);

    const differences = actualResults.map((actual, i) => actual - expectedResults[i]);
    const variance = this.calculateVariance(differences);

    // Luck factor: (Actual - Expected) / SD
    const sd = Math.sqrt(variance);
    const luck = sd > 0 ? (actualSum - expectedSum) / sd : 0;

    // Normalize luck to -1 to 1
    const normalizedLuck = Math.max(-1, Math.min(1, luck / 3));

    return {
      actualResult: actualSum,
      expectedResult: expectedSum,
      variance,
      luck: normalizedLuck,
    };
  }

  /**
   * Calculate probability of ruin
   */
  calculateRuinProbability(
    bankroll: number,
    winRate: number,
    standardDeviation: number
  ): number {
    if (winRate <= 0) return 1; // Certain ruin if negative win rate

    // Simplified Risk of Ruin formula
    // RoR = exp(-2 * bankroll * winRate / SD^2)
    const exponent = (-2 * bankroll * winRate) / Math.pow(standardDeviation, 2);
    const ruinProbability = Math.exp(exponent);

    return Math.min(1, Math.max(0, ruinProbability));
  }

  /**
   * Calculate expected bankroll swings
   */
  calculateBankrollSwings(
    winRate: number,
    standardDeviation: number,
    hands: number
  ): {
    expected: number;
    worstCase5pct: number;
    worstCase1pct: number;
    bestCase5pct: number;
    bestCase1pct: number;
  } {
    const expected = winRate * hands;
    const totalSD = standardDeviation * Math.sqrt(hands);

    // Using z-scores for percentiles
    // 5th percentile: z = -1.645
    // 1st percentile: z = -2.326
    // 95th percentile: z = 1.645
    // 99th percentile: z = 2.326

    return {
      expected,
      worstCase5pct: expected - 1.645 * totalSD,
      worstCase1pct: expected - 2.326 * totalSD,
      bestCase5pct: expected + 1.645 * totalSD,
      bestCase1pct: expected + 2.326 * totalSD,
    };
  }

  /**
   * Detect if player is running bad/good
   */
  detectRunningBadGood(
    actualResults: number[],
    expectedResults: number[]
  ): {
    status: 'running_good' | 'running_bad' | 'normal';
    severity: number; // 0-1
    message: string;
  } {
    const analysis = this.runItTwiceAnalysis(actualResults, expectedResults);

    if (analysis.luck > 0.5) {
      return {
        status: 'running_good',
        severity: analysis.luck,
        message: `Running significantly above EV (${(analysis.luck * 100).toFixed(0)}% luck factor)`,
      };
    } else if (analysis.luck < -0.5) {
      return {
        status: 'running_bad',
        severity: Math.abs(analysis.luck),
        message: `Running significantly below EV (${(analysis.luck * 100).toFixed(0)}% luck factor)`,
      };
    } else {
      return {
        status: 'normal',
        severity: Math.abs(analysis.luck),
        message: 'Results are within expected variance',
      };
    }
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
   * Normal CDF (Cumulative Distribution Function)
   * Approximation using error function
   */
  private normalCDF(z: number): number {
    // Using approximation: CDF(z) ≈ 0.5 * (1 + erf(z / sqrt(2)))
    const erf = this.errorFunction(z / Math.sqrt(2));
    return 0.5 * (1 + erf);
  }

  /**
   * Error function approximation
   */
  private errorFunction(x: number): number {
    // Abramowitz and Stegun approximation
    const sign = x >= 0 ? 1 : -1;
    x = Math.abs(x);

    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;

    const t = 1 / (1 + p * x);
    const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

    return sign * y;
  }
}

