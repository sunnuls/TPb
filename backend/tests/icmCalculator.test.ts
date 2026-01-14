import { ICMCalculatorService, TournamentState } from '../src/services/icmCalculatorService';

describe('ICMCalculatorService', () => {
  let icmService: ICMCalculatorService;

  beforeEach(() => {
    icmService = new ICMCalculatorService();
  });

  describe('calculateICM', () => {
    it('should calculate correct equity for heads-up', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 6000 },
          { name: 'Villain', stack: 4000 },
        ],
        payoutStructure: {
          totalPrize: 1000,
          payouts: [600, 400],
        },
        remainingPlayers: 2,
        totalChips: 10000,
      };

      const results = icmService.calculateICM(state);
      const heroICM = results.get('Hero');
      const villainICM = results.get('Villain');

      expect(heroICM).toBeDefined();
      expect(villainICM).toBeDefined();
      expect(heroICM!.equity).toBeGreaterThan(500);
      expect(heroICM!.equity).toBeLessThan(600);
      expect(villainICM!.equity).toBeGreaterThan(400);
      expect(villainICM!.equity).toBeLessThan(500);
      expect(heroICM!.equity + villainICM!.equity).toBeCloseTo(1000, 1);
    });

    it('should calculate correct equity for 3-way', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 5000 },
          { name: 'V1', stack: 5000 },
          { name: 'V2', stack: 5000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const results = icmService.calculateICM(state);
      const heroICM = results.get('Hero');

      expect(heroICM).toBeDefined();
      // Equal stacks should give equal equity
      expect(heroICM!.equity).toBeCloseTo(500, 0);
      expect(heroICM!.equityPercentage).toBeCloseTo(33.33, 1);
    });

    it('should show chip leader has less than proportional equity', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 9000 }, // 60% of chips
          { name: 'V1', stack: 3000 },
          { name: 'V2', stack: 3000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const results = icmService.calculateICM(state);
      const heroICM = results.get('Hero');

      expect(heroICM).toBeDefined();
      // 60% chips but less than 60% equity due to ICM
      expect(heroICM!.equityPercentage).toBeLessThan(60);
      expect(heroICM!.equityPercentage).toBeGreaterThan(50);
    });
  });

  describe('calculateConversionFactor', () => {
    it('should return factor close to 1 for equal stacks', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 5000 },
          { name: 'V1', stack: 5000 },
          { name: 'V2', stack: 5000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const factor = icmService.calculateConversionFactor(5000, state);

      expect(factor).toBeCloseTo(1, 1);
    });

    it('should return factor < 1 for chip leader (chips worth less)', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 9000 },
          { name: 'V1', stack: 3000 },
          { name: 'V2', stack: 3000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const factor = icmService.calculateConversionFactor(9000, state);

      expect(factor).toBeLessThan(1);
    });
  });

  describe('calculateICMPressure', () => {
    it('should show high pressure for short stack', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 2000 },
          { name: 'V1', stack: 8000 },
          { name: 'V2', stack: 5000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const pressure = icmService.calculateICMPressure(2000, 1000, state);

      expect(pressure.pressure).toBeGreaterThan(0.5);
      expect(pressure.recommendation).toContain('pressure');
    });

    it('should show low pressure for chip leader', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 8000 },
          { name: 'V1', stack: 4000 },
          { name: 'V2', stack: 3000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const pressure = icmService.calculateICMPressure(8000, 500, state);

      expect(pressure.pressure).toBeLessThan(0.5);
    });
  });

  describe('calculateBubbleFactor', () => {
    it('should detect bubble situation', () => {
      const state: TournamentState = {
        players: [
          { name: 'P1', stack: 5000 },
          { name: 'P2', stack: 4000 },
          { name: 'P3', stack: 3000 },
          { name: 'P4', stack: 3000 },
        ],
        payoutStructure: {
          totalPrize: 1000,
          payouts: [500, 300, 200],
        },
        remainingPlayers: 4,
        totalChips: 15000,
      };

      const bubble = icmService.calculateBubbleFactor(state);

      expect(bubble.isBubble).toBe(true);
      expect(bubble.playersToMoney).toBe(1);
      expect(bubble.factor).toBeGreaterThan(1);
    });

    it('should not be bubble when everyone is ITM', () => {
      const state: TournamentState = {
        players: [
          { name: 'P1', stack: 6000 },
          { name: 'P2', stack: 5000 },
          { name: 'P3', stack: 4000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const bubble = icmService.calculateBubbleFactor(state);

      expect(bubble.isBubble).toBe(false);
      expect(bubble.playersToMoney).toBe(0);
    });
  });

  describe('calculateDecisionEV', () => {
    it('should show positive EV for good call', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 5000 },
          { name: 'V1', stack: 5000 },
          { name: 'V2', stack: 5000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const decision = icmService.calculateDecisionEV(
        5000,  // heroStack
        3000,  // potSize
        1000,  // callAmount
        0.6,   // winProbability (60%)
        state
      );

      expect(decision.chipEV).toBeGreaterThan(0);
      expect(decision.shouldCall).toBe(true);
    });

    it('should show negative EV for bad call', () => {
      const state: TournamentState = {
        players: [
          { name: 'Hero', stack: 5000 },
          { name: 'V1', stack: 5000 },
          { name: 'V2', stack: 5000 },
        ],
        payoutStructure: {
          totalPrize: 1500,
          payouts: [750, 450, 300],
        },
        remainingPlayers: 3,
        totalChips: 15000,
      };

      const decision = icmService.calculateDecisionEV(
        5000,
        3000,
        1000,
        0.3,  // Only 30% to win
        state
      );

      expect(decision.chipEV).toBeLessThan(0);
      expect(decision.shouldCall).toBe(false);
    });
  });

  describe('generatePayoutStructure', () => {
    it('should generate standard structure', () => {
      const structure = icmService.generatePayoutStructure(1000, 100, 'standard');

      expect(structure.totalPrize).toBe(1000);
      expect(structure.payouts.length).toBeGreaterThan(0);
      expect(structure.payouts[0]).toBe(500); // 50% to 1st
      expect(structure.payouts[1]).toBe(300); // 30% to 2nd
      expect(structure.payouts[2]).toBe(200); // 20% to 3rd
    });

    it('should generate flat structure', () => {
      const structure = icmService.generatePayoutStructure(1000, 10, 'flat');

      const firstPayout = structure.payouts[0];
      const lastPayout = structure.payouts[structure.payouts.length - 1];

      expect(firstPayout).toBeCloseTo(lastPayout, 0);
    });

    it('should generate top-heavy structure', () => {
      const structure = icmService.generatePayoutStructure(1000, 100, 'top_heavy');

      expect(structure.payouts[0]).toBe(600); // 60% to 1st
      expect(structure.payouts[0]).toBeGreaterThan(structure.payouts[1] * 2);
    });
  });
});

