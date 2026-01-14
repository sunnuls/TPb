import { TournamentStrategyService } from '../src/services/tournamentStrategyService';

describe('TournamentStrategyService', () => {
  let service: TournamentStrategyService;

  beforeEach(() => {
    service = new TournamentStrategyService();
  });

  describe('analyzeStackDepth', () => {
    it('should categorize deep stack correctly', () => {
      const depth = service.analyzeStackDepth(10000, 100);

      expect(depth.bigBlinds).toBe(100);
      expect(depth.category).toBe('deep');
      expect(depth.playStyle).toContain('standard');
    });

    it('should categorize medium stack correctly', () => {
      const depth = service.analyzeStackDepth(3000, 100);

      expect(depth.bigBlinds).toBe(30);
      expect(depth.category).toBe('medium');
      expect(depth.playStyle).toContain('Tighten');
    });

    it('should categorize short stack correctly', () => {
      const depth = service.analyzeStackDepth(1500, 100);

      expect(depth.bigBlinds).toBe(15);
      expect(depth.category).toBe('short');
      expect(depth.playStyle).toContain('Push/fold');
    });

    it('should categorize push-fold stack correctly', () => {
      const depth = service.analyzeStackDepth(800, 100);

      expect(depth.bigBlinds).toBe(8);
      expect(depth.category).toBe('push_fold');
      expect(depth.playStyle).toContain('Strict');
    });
  });

  describe('determineTournamentPhase', () => {
    it('should detect early phase', () => {
      const phase = service.determineTournamentPhase(150, 180, 18);

      expect(phase.phase).toBe('early');
      expect(phase.adjustments).toContain('Play solid poker');
    });

    it('should detect middle phase', () => {
      const phase = service.determineTournamentPhase(50, 180, 18);

      expect(phase.phase).toBe('middle');
      expect(phase.adjustments.length).toBeGreaterThan(0);
    });

    it('should detect bubble phase', () => {
      const phase = service.determineTournamentPhase(19, 180, 18);

      expect(phase.phase).toBe('bubble');
      expect(phase.adjustments).toContain('Extreme ICM pressure');
    });

    it('should detect ITM phase', () => {
      const phase = service.determineTournamentPhase(15, 180, 18);

      expect(phase.phase).toBe('ITM');
      expect(phase.adjustments).toContain('Focus on chip accumulation');
    });

    it('should detect final table', () => {
      const phase = service.determineTournamentPhase(9, 180, 18);

      expect(phase.phase).toBe('final_table');
      expect(phase.adjustments).toContain('ICM is critical - avoid marginal spots');
    });
  });

  describe('calculatePushFoldRange', () => {
    it('should provide wider range from BTN', () => {
      const btnRange = service.calculatePushFoldRange(10, 'BTN', 3);
      const utgRange = service.calculatePushFoldRange(10, 'UTG', 3);

      expect(btnRange.frequency).toBeGreaterThan(utgRange.frequency);
      expect(btnRange.range.length).toBeGreaterThan(utgRange.range.length);
    });

    it('should tighten range with more opponents', () => {
      const fewOpps = service.calculatePushFoldRange(10, 'BTN', 2);
      const manyOpps = service.calculatePushFoldRange(10, 'BTN', 8);

      expect(fewOpps.frequency).toBeGreaterThanOrEqual(manyOpps.frequency);
    });

    it('should tighten range with deeper stack', () => {
      const shortStack = service.calculatePushFoldRange(8, 'BTN', 3);
      const deeperStack = service.calculatePushFoldRange(20, 'BTN', 3);

      expect(shortStack.frequency).toBeGreaterThan(deeperStack.frequency);
    });

    it('should include premium hands in all ranges', () => {
      const range = service.calculatePushFoldRange(10, 'UTG', 8);

      expect(range.range).toContain('22+'); // Pairs
    });
  });

  describe('calculateCallVsShoveRange', () => {
    it('should widen range with good pot odds', () => {
      const goodOdds = service.calculateCallVsShoveRange(20, 5, 'BB');
      const badOdds = service.calculateCallVsShoveRange(20, 15, 'BB');

      expect(goodOdds.frequency).toBeGreaterThan(badOdds.frequency);
    });

    it('should call tighter when not getting odds', () => {
      const range = service.calculateCallVsShoveRange(15, 14, 'BB');

      expect(range.frequency).toBeLessThan(15);
      expect(range.range).toContain('99+'); // Premium hands
    });
  });

  describe('analyzeAnteImpact', () => {
    it('should recognize high ante value', () => {
      const analysis = service.analyzeAnteImpact(100, 500, 9);

      expect(analysis.anteRatio).toBeCloseTo(0.2, 2);
      expect(analysis.recommendation).toContain('High antes');
    });

    it('should calculate dead money correctly', () => {
      const analysis = service.analyzeAnteImpact(50, 200, 9);

      expect(analysis.deadMoney).toBe(50 * 9 + 1.5 * 200);
    });

    it('should show stealing is less valuable without antes', () => {
      const withAntes = service.analyzeAnteImpact(50, 200, 9);
      const noAntes = service.analyzeAnteImpact(0, 200, 9);

      expect(withAntes.stealingValue).toBeGreaterThan(noAntes.stealingValue);
    });
  });

  describe('generateRecommendations', () => {
    it('should recommend push/fold for critical stack', () => {
      const recommendations = service.generateRecommendations(
        800,
        100,
        'BTN',
        {
          players: [
            { name: 'Hero', stack: 800 },
            { name: 'V1', stack: 5000 },
          ],
          payoutStructure: { totalPrize: 1000, payouts: [600, 400] },
          remainingPlayers: 2,
          totalChips: 5800,
        }
      );

      const criticalRec = recommendations.find(r => r.priority === 'critical');
      expect(criticalRec).toBeDefined();
      expect(criticalRec!.recommendation).toContain('push/fold');
    });

    it('should warn about bubble', () => {
      const recommendations = service.generateRecommendations(
        3000,
        100,
        'CO',
        {
          players: [
            { name: 'Hero', stack: 3000 },
            { name: 'V1', stack: 3000 },
            { name: 'V2', stack: 3000 },
            { name: 'V3', stack: 3000 },
          ],
          payoutStructure: { totalPrize: 1000, payouts: [500, 300, 200] },
          remainingPlayers: 4,
          totalChips: 12000,
        }
      );

      const bubbleRec = recommendations.find(r => r.situation === 'Bubble');
      expect(bubbleRec).toBeDefined();
      expect(bubbleRec!.priority).toBe('critical');
    });

    it('should suggest stealing from late position', () => {
      const recommendations = service.generateRecommendations(
        5000,
        100,
        'BTN',
        {
          players: [
            { name: 'Hero', stack: 5000 },
            { name: 'V1', stack: 5000 },
          ],
          payoutStructure: { totalPrize: 1000, payouts: [600, 400] },
          remainingPlayers: 2,
          totalChips: 10000,
        }
      );

      const posRec = recommendations.find(r => r.situation === 'Late Position');
      expect(posRec).toBeDefined();
    });
  });
});

