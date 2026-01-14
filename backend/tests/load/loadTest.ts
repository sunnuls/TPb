import axios from 'axios';
import { performance } from 'perf_hooks';

interface LoadTestConfig {
  baseURL: string;
  endpoints: TestEndpoint[];
  concurrency: number;
  duration: number; // seconds
  rampUp?: number; // seconds
}

interface TestEndpoint {
  method: 'GET' | 'POST';
  path: string;
  body?: any;
  weight: number; // 1-10, higher = more requests
}

interface LoadTestResults {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  avgResponseTime: number;
  minResponseTime: number;
  maxResponseTime: number;
  requestsPerSecond: number;
  errors: Map<string, number>;
  statusCodes: Map<number, number>;
}

/**
 * Load Testing Utility
 */
export class LoadTester {
  private config: LoadTestConfig;
  private results: LoadTestResults;
  private running: boolean = false;

  constructor(config: LoadTestConfig) {
    this.config = config;
    this.results = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      avgResponseTime: 0,
      minResponseTime: Infinity,
      maxResponseTime: 0,
      requestsPerSecond: 0,
      errors: new Map(),
      statusCodes: new Map(),
    };
  }

  /**
   * Run load test
   */
  async run(): Promise<LoadTestResults> {
    console.log('🚀 Starting Load Test...\n');
    console.log(`Base URL: ${this.config.baseURL}`);
    console.log(`Concurrency: ${this.config.concurrency}`);
    console.log(`Duration: ${this.config.duration}s`);
    console.log(`Endpoints: ${this.config.endpoints.length}\n`);

    this.running = true;
    const startTime = performance.now();
    const endTime = startTime + this.config.duration * 1000;

    const responseTimes: number[] = [];

    // Create worker promises
    const workers: Promise<void>[] = [];

    for (let i = 0; i < this.config.concurrency; i++) {
      workers.push(this.worker(endTime, responseTimes));

      // Ramp up
      if (this.config.rampUp) {
        const delay = (this.config.rampUp * 1000) / this.config.concurrency;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    // Wait for all workers
    await Promise.all(workers);

    this.running = false;
    const actualDuration = (performance.now() - startTime) / 1000;

    // Calculate final stats
    this.results.avgResponseTime =
      responseTimes.reduce((sum, t) => sum + t, 0) / responseTimes.length;
    this.results.requestsPerSecond = this.results.totalRequests / actualDuration;

    this.printResults();

    return this.results;
  }

  /**
   * Worker function
   */
  private async worker(endTime: number, responseTimes: number[]): Promise<void> {
    while (this.running && performance.now() < endTime) {
      const endpoint = this.selectEndpoint();

      try {
        const start = performance.now();

        const response = await axios({
          method: endpoint.method,
          url: `${this.config.baseURL}${endpoint.path}`,
          data: endpoint.body,
          timeout: 30000,
        });

        const responseTime = performance.now() - start;
        responseTimes.push(responseTime);

        this.results.totalRequests++;
        this.results.successfulRequests++;
        this.results.minResponseTime = Math.min(this.results.minResponseTime, responseTime);
        this.results.maxResponseTime = Math.max(this.results.maxResponseTime, responseTime);

        // Track status codes
        const count = this.results.statusCodes.get(response.status) || 0;
        this.results.statusCodes.set(response.status, count + 1);
      } catch (error: any) {
        this.results.totalRequests++;
        this.results.failedRequests++;

        // Track errors
        const errorMsg = error.message || 'Unknown error';
        const count = this.results.errors.get(errorMsg) || 0;
        this.results.errors.set(errorMsg, count + 1);

        // Track status codes
        if (error.response?.status) {
          const statusCount = this.results.statusCodes.get(error.response.status) || 0;
          this.results.statusCodes.set(error.response.status, statusCount + 1);
        }
      }

      // Small delay to prevent overwhelming
      await new Promise(resolve => setTimeout(resolve, 10));
    }
  }

  /**
   * Select random endpoint based on weight
   */
  private selectEndpoint(): TestEndpoint {
    const totalWeight = this.config.endpoints.reduce((sum, e) => sum + e.weight, 0);
    let random = Math.random() * totalWeight;

    for (const endpoint of this.config.endpoints) {
      random -= endpoint.weight;
      if (random <= 0) {
        return endpoint;
      }
    }

    return this.config.endpoints[0];
  }

  /**
   * Print results
   */
  private printResults(): void {
    console.log('\n┌─────────────────────────────────────────────────────────────────┐');
    console.log('│                      Load Test Results                          │');
    console.log('├─────────────────────────────────────────────────────────────────┤');
    console.log(`│ Total Requests:       ${this.results.totalRequests.toString().padStart(10)}                        │`);
    console.log(`│ Successful:           ${this.results.successfulRequests.toString().padStart(10)}                        │`);
    console.log(`│ Failed:               ${this.results.failedRequests.toString().padStart(10)}                        │`);
    console.log(`│ Success Rate:         ${((this.results.successfulRequests / this.results.totalRequests) * 100).toFixed(2).padStart(10)}%                       │`);
    console.log('├─────────────────────────────────────────────────────────────────┤');
    console.log(`│ Avg Response Time:    ${this.results.avgResponseTime.toFixed(2).padStart(10)} ms                      │`);
    console.log(`│ Min Response Time:    ${this.results.minResponseTime.toFixed(2).padStart(10)} ms                      │`);
    console.log(`│ Max Response Time:    ${this.results.maxResponseTime.toFixed(2).padStart(10)} ms                      │`);
    console.log(`│ Requests/sec:         ${this.results.requestsPerSecond.toFixed(2).padStart(10)}                        │`);
    console.log('├─────────────────────────────────────────────────────────────────┤');

    if (this.results.statusCodes.size > 0) {
      console.log('│ Status Codes:                                                   │');
      for (const [code, count] of this.results.statusCodes) {
        console.log(`│   ${code}: ${count.toString().padStart(10)} requests                                    │`);
      }
      console.log('├─────────────────────────────────────────────────────────────────┤');
    }

    if (this.results.errors.size > 0) {
      console.log('│ Errors:                                                         │');
      for (const [error, count] of this.results.errors) {
        const truncated = error.substring(0, 40);
        console.log(`│   ${truncated.padEnd(40)}: ${count.toString().padStart(5)}         │`);
      }
      console.log('├─────────────────────────────────────────────────────────────────┤');
    }

    console.log('└─────────────────────────────────────────────────────────────────┘\n');

    // Performance assessment
    const successRate = (this.results.successfulRequests / this.results.totalRequests) * 100;

    if (successRate < 95) {
      console.log('⚠️  WARNING: Success rate below 95%');
    }

    if (this.results.avgResponseTime > 500) {
      console.log('⚠️  WARNING: Average response time above 500ms');
    }

    if (this.results.maxResponseTime > 2000) {
      console.log('⚠️  WARNING: Max response time above 2000ms');
    }

    if (successRate >= 95 && this.results.avgResponseTime <= 500) {
      console.log('✅ Load test passed all thresholds!');
    }
  }
}

/**
 * Run default load test
 */
async function runDefaultLoadTest() {
  const config: LoadTestConfig = {
    baseURL: 'http://localhost:3001',
    concurrency: 10,
    duration: 30,
    rampUp: 5,
    endpoints: [
      {
        method: 'GET',
        path: '/health',
        weight: 2,
      },
      {
        method: 'POST',
        path: '/api/game/state',
        body: {
          players: [],
          board: [],
          pot: 0,
        },
        weight: 5,
      },
      {
        method: 'POST',
        path: '/api/analytics/session',
        body: {
          sessionId: 'test-session',
          hands: [],
          actions: [],
        },
        weight: 3,
      },
    ],
  };

  const tester = new LoadTester(config);

  try {
    await tester.run();
    process.exit(0);
  } catch (error) {
    console.error('Load test failed:', error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  console.log('⚠️  Make sure the server is running on http://localhost:3001\n');
  runDefaultLoadTest();
}

export { LoadTester, LoadTestConfig, LoadTestResults };

