import { performance } from 'perf_hooks';
import { HandEvaluator } from '../src/engines/handEvaluator';
import { EquityEngine } from '../src/engines/equityEngine';
import { ICMCalculatorService } from '../src/services/icmCalculatorService';
import { GTOService } from '../src/services/gtoService';

interface BenchmarkResult {
  name: string;
  iterations: number;
  totalTime: number;
  avgTime: number;
  minTime: number;
  maxTime: number;
  opsPerSecond: number;
}

/**
 * Performance Benchmarks
 */
export class PerformanceBenchmarks {
  /**
   * Run all benchmarks
   */
  static async runAll(): Promise<BenchmarkResult[]> {
    console.log('🚀 Starting Performance Benchmarks...\n');

    const results: BenchmarkResult[] = [];

    results.push(await this.benchmarkHandEvaluation());
    results.push(await this.benchmarkEquityCalculation());
    results.push(await this.benchmarkICMCalculation());
    results.push(await this.benchmarkGTOLookup());

    console.log('\n✅ All benchmarks complete!\n');
    this.printSummary(results);

    return results;
  }

  /**
   * Benchmark hand evaluation
   */
  static async benchmarkHandEvaluation(): Promise<BenchmarkResult> {
    console.log('Testing: Hand Evaluation...');

    const handEval = new HandEvaluator();
    const iterations = 10000;
    const times: number[] = [];

    // Test hands
    const testHands = [
      { hole: ['As', 'Kh'], board: ['Ks', 'Qd', 'Jc', 'Tc', '9h'] },
      { hole: ['2c', '3d'], board: ['4h', '5s', '6c', '7d', '8h'] },
      { hole: ['Ah', 'Ad'], board: ['Ac', 'As', 'Kh', 'Kd', 'Kc'] },
    ];

    for (let i = 0; i < iterations; i++) {
      const testHand = testHands[i % testHands.length];

      const start = performance.now();
      handEval.evaluateHand([...testHand.hole, ...testHand.board] as any);
      const end = performance.now();

      times.push(end - start);
    }

    return this.calculateStats('Hand Evaluation', times);
  }

  /**
   * Benchmark equity calculation
   */
  static async benchmarkEquityCalculation(): Promise<BenchmarkResult> {
    console.log('Testing: Equity Calculation...');

    const equityEngine = new EquityEngine();
    const iterations = 100;
    const times: number[] = [];

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();

      equityEngine.calculateEquity(
        ['As', 'Kh'] as any,
        ['Qs', 'Jd'] as any,
        ['Kd', 'Qc', '5h'] as any,
        'flop',
        10000 // 10k simulations
      );

      const end = performance.now();
      times.push(end - start);
    }

    return this.calculateStats('Equity Calculation (10k sims)', times);
  }

  /**
   * Benchmark ICM calculation
   */
  static async benchmarkICMCalculation(): Promise<BenchmarkResult> {
    console.log('Testing: ICM Calculation...');

    const icm = new ICMCalculatorService();
    const iterations = 1000;
    const times: number[] = [];

    const state = {
      players: [
        { name: 'P1', stack: 5000 },
        { name: 'P2', stack: 4000 },
        { name: 'P3', stack: 3000 },
        { name: 'P4', stack: 2000 },
        { name: 'P5', stack: 1000 },
      ],
      payoutStructure: {
        totalPrize: 1000,
        payouts: [400, 250, 200, 100, 50],
      },
      remainingPlayers: 5,
      totalChips: 15000,
    };

    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      icm.calculateICM(state);
      const end = performance.now();

      times.push(end - start);
    }

    return this.calculateStats('ICM Calculation (5 players)', times);
  }

  /**
   * Benchmark GTO lookup
   */
  static async benchmarkGTOLookup(): Promise<BenchmarkResult> {
    console.log('Testing: GTO Range Lookup...');

    const gto = new GTOService();
    const iterations = 10000;
    const times: number[] = [];

    const positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'];

    for (let i = 0; i < iterations; i++) {
      const position = positions[i % positions.length];

      const start = performance.now();
      gto.getPreflopRecommendation(position as any, [], 'raise');
      const end = performance.now();

      times.push(end - start);
    }

    return this.calculateStats('GTO Range Lookup', times);
  }

  /**
   * Calculate statistics
   */
  private static calculateStats(name: string, times: number[]): BenchmarkResult {
    const totalTime = times.reduce((sum, t) => sum + t, 0);
    const avgTime = totalTime / times.length;
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    const opsPerSecond = 1000 / avgTime;

    return {
      name,
      iterations: times.length,
      totalTime,
      avgTime,
      minTime,
      maxTime,
      opsPerSecond,
    };
  }

  /**
   * Print summary table
   */
  private static printSummary(results: BenchmarkResult[]): void {
    console.log('┌─────────────────────────────────────────────────────────────────┐');
    console.log('│                    Performance Summary                          │');
    console.log('├─────────────────────────────────────────────────────────────────┤');

    results.forEach(r => {
      console.log(`│ ${r.name.padEnd(30)} │`);
      console.log(`│   Iterations: ${r.iterations.toString().padStart(10)}                        │`);
      console.log(`│   Avg Time:   ${r.avgTime.toFixed(3).padStart(10)} ms                      │`);
      console.log(`│   Min Time:   ${r.minTime.toFixed(3).padStart(10)} ms                      │`);
      console.log(`│   Max Time:   ${r.maxTime.toFixed(3).padStart(10)} ms                      │`);
      console.log(`│   Ops/sec:    ${Math.floor(r.opsPerSecond).toString().padStart(10)}                        │`);
      console.log('├─────────────────────────────────────────────────────────────────┤');
    });

    console.log('└─────────────────────────────────────────────────────────────────┘');

    // Check if any benchmark failed targets
    const failures: string[] = [];

    if (results[0].avgTime > 1) failures.push('Hand Evaluation (target: <1ms)');
    if (results[1].avgTime > 100) failures.push('Equity Calculation (target: <100ms)');
    if (results[2].avgTime > 50) failures.push('ICM Calculation (target: <50ms)');
    if (results[3].avgTime > 10) failures.push('GTO Lookup (target: <10ms)');

    if (failures.length > 0) {
      console.log('\n⚠️  Performance Warnings:');
      failures.forEach(f => console.log(`   - ${f}`));
    } else {
      console.log('\n✅ All benchmarks passed performance targets!');
    }
  }
}

// Run benchmarks if executed directly
if (require.main === module) {
  PerformanceBenchmarks.runAll()
    .then(() => process.exit(0))
    .catch(err => {
      console.error('Benchmark failed:', err);
      process.exit(1);
    });
}

