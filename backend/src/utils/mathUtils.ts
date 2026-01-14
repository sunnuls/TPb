/**
 * Mathematical utility functions
 */

/**
 * Calculate standard deviation
 */
export function standardDeviation(values: number[]): number {
  if (values.length === 0) return 0;
  
  const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
  const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
  const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;
  
  return Math.sqrt(variance);
}

/**
 * Calculate percentile
 */
export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  
  const sorted = [...values].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;
  
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

/**
 * Clamp value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Linear interpolation
 */
export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

/**
 * Calculate moving average
 */
export function movingAverage(values: number[], windowSize: number): number[] {
  const result: number[] = [];
  
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1);
    const avg = window.reduce((sum, val) => sum + val, 0) / window.length;
    result.push(avg);
  }
  
  return result;
}

/**
 * Round to nearest step
 */
export function roundToNearest(value: number, step: number): number {
  return Math.round(value / step) * step;
}

/**
 * Calculate combinations (n choose k)
 */
export function combinations(n: number, k: number): number {
  if (k > n) return 0;
  if (k === 0 || k === n) return 1;
  
  let result = 1;
  for (let i = 1; i <= k; i++) {
    result *= (n - i + 1) / i;
  }
  
  return Math.round(result);
}

/**
 * Calculate factorial
 */
export function factorial(n: number): number {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}

/**
 * Convert BB to big blinds
 */
export function toBigBlinds(amount: number, bigBlind: number): number {
  return amount / bigBlind;
}

/**
 * Calculate pot odds
 */
export function calculatePotOdds(bet: number, pot: number): number {
  return bet / (pot + bet);
}

/**
 * Convert odds to percentage
 */
export function oddsToPercentage(numerator: number, denominator: number): number {
  return (numerator / (numerator + denominator)) * 100;
}

/**
 * Convert percentage to odds
 */
export function percentageToOdds(percentage: number): { numerator: number; denominator: number } {
  const decimal = percentage / 100;
  const numerator = decimal;
  const denominator = 1 - decimal;
  
  // Simplify ratio
  const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
  const divisor = gcd(Math.round(numerator * 100), Math.round(denominator * 100));
  
  return {
    numerator: Math.round((numerator * 100) / divisor),
    denominator: Math.round((denominator * 100) / divisor),
  };
}

