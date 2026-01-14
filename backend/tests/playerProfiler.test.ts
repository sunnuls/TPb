import { PlayerProfilerService } from '../src/services/playerProfilerService';

describe('PlayerProfilerService', () => {
  let profiler: PlayerProfilerService;

  beforeEach(() => {
    profiler = new PlayerProfilerService();
  });

  describe('updateProfile', () => {
    it('should create new player profile', () => {
      profiler.updateProfile('Villain1', {
        vpip: 25,
        pfr: 20,
        aggressionFactor: 2.5,
      });

      const profile = profiler.getProfile('Villain1');

      expect(profile).toBeDefined();
      expect(profile!.playerName).toBe('Villain1');
      expect(profile!.stats.vpip).toBe(25);
    });

    it('should update existing profile', () => {
      profiler.updateProfile('Villain1', { vpip: 25 });
      profiler.updateProfile('Villain1', { vpip: 30 });

      const profile = profiler.getProfile('Villain1');

      expect(profile!.handsObserved).toBe(2);
      expect(profile!.stats.vpip).toBe(30);
    });
  });

  describe('classifyPlayerType', () => {
    it('should classify TAG correctly', () => {
      profiler.updateProfile('TAG_Player', {
        vpip: 18,
        pfr: 15,
        aggressionFactor: 2.8,
      });

      const profile = profiler.getProfile('TAG_Player');

      expect(profile!.playerType).toBe('TAG');
    });

    it('should classify LAG correctly', () => {
      profiler.updateProfile('LAG_Player', {
        vpip: 35,
        pfr: 28,
        aggressionFactor: 3.2,
      });

      const profile = profiler.getProfile('LAG_Player');

      expect(profile!.playerType).toBe('LAG');
    });

    it('should classify TP correctly', () => {
      profiler.updateProfile('TP_Player', {
        vpip: 15,
        pfr: 8,
        aggressionFactor: 1.2,
      });

      const profile = profiler.getProfile('TP_Player');

      expect(profile!.playerType).toBe('TP');
    });

    it('should classify LP/FISH correctly', () => {
      profiler.updateProfile('Fish_Player', {
        vpip: 45,
        pfr: 8,
        aggressionFactor: 0.8,
      });

      const profile = profiler.getProfile('Fish_Player');

      expect(profile!.playerType).toMatch(/LP|FISH/);
    });

    it('should classify ROCK correctly', () => {
      profiler.updateProfile('Rock_Player', {
        vpip: 10,
        pfr: 7,
        aggressionFactor: 1.5,
      });

      const profile = profiler.getProfile('Rock_Player');

      expect(profile!.playerType).toBe('ROCK');
    });

    it('should classify MANIAC correctly', () => {
      profiler.updateProfile('Maniac_Player', {
        vpip: 55,
        pfr: 40,
        aggressionFactor: 4.5,
      });

      const profile = profiler.getProfile('Maniac_Player');

      expect(profile!.playerType).toBe('MANIAC');
    });
  });

  describe('calculateConfidence', () => {
    it('should have low confidence with few hands', () => {
      profiler.updateProfile('New_Player', { vpip: 25 });

      const profile = profiler.getProfile('New_Player');

      expect(profile!.confidence).toBeLessThan(0.5);
    });

    it('should have high confidence with many hands', () => {
      const player = 'Veteran_Player';

      for (let i = 0; i < 500; i++) {
        profiler.updateProfile(player, { vpip: 25 });
      }

      const profile = profiler.getProfile(player);

      expect(profile!.confidence).toBeGreaterThan(0.8);
    });
  });

  describe('generateExploitativeStrategy', () => {
    it('should return null for low confidence', () => {
      profiler.updateProfile('Unknown', { vpip: 25 });

      const strategy = profiler.generateExploitativeStrategy('Unknown');

      expect(strategy).toBeNull();
    });

    it('should generate strategy for TAG', () => {
      for (let i = 0; i < 200; i++) {
        profiler.updateProfile('TAG_Villain', {
          vpip: 18,
          pfr: 15,
          aggressionFactor: 2.8,
        });
      }

      const strategy = profiler.generateExploitativeStrategy('TAG_Villain');

      expect(strategy).toBeDefined();
      expect(strategy!.playerType).toBe('TAG');
      expect(strategy!.recommendations.length).toBeGreaterThan(0);
      expect(strategy!.adjustments.valueBetThin).toBe(true);
    });

    it('should generate strategy for LAG', () => {
      for (let i = 0; i < 200; i++) {
        profiler.updateProfile('LAG_Villain', {
          vpip: 35,
          pfr: 28,
          aggressionFactor: 3.5,
        });
      }

      const strategy = profiler.generateExploitativeStrategy('LAG_Villain');

      expect(strategy).toBeDefined();
      expect(strategy!.adjustments.loosenRange).toBe(true);
      expect(strategy!.recommendations).toContain('Widen your calling range - they bluff often');
    });

    it('should generate strategy for FISH', () => {
      for (let i = 0; i < 200; i++) {
        profiler.updateProfile('Fish_Villain', {
          vpip: 45,
          pfr: 8,
          aggressionFactor: 0.8,
        });
      }

      const strategy = profiler.generateExploitativeStrategy('Fish_Villain');

      expect(strategy).toBeDefined();
      expect(strategy!.adjustments.bluffLess).toBe(true);
      expect(strategy!.adjustments.valueBetThin).toBe(true);
    });
  });

  describe('notes', () => {
    beforeEach(() => {
      profiler.updateProfile('Player1', { vpip: 25 });
    });

    it('should add note to profile', () => {
      profiler.addNote('Player1', '3-bet bluffed on river');

      const profile = profiler.getProfile('Player1');

      expect(profile!.notes.length).toBe(1);
      expect(profile!.notes[0]).toContain('3-bet bluffed');
    });

    it('should include timestamp in notes', () => {
      profiler.addNote('Player1', 'Test note');

      const profile = profiler.getProfile('Player1');

      expect(profile!.notes[0]).toMatch(/\[\d{4}-\d{2}-\d{2}/);
    });
  });

  describe('getProfilesByType', () => {
    beforeEach(() => {
      for (let i = 0; i < 100; i++) {
        profiler.updateProfile('TAG1', {
          vpip: 18,
          pfr: 15,
          aggressionFactor: 2.8,
        });

        profiler.updateProfile('TAG2', {
          vpip: 17,
          pfr: 14,
          aggressionFactor: 3.0,
        });

        profiler.updateProfile('LAG1', {
          vpip: 35,
          pfr: 28,
          aggressionFactor: 3.5,
        });
      }
    });

    it('should filter profiles by type', () => {
      const tags = profiler.getProfilesByType('TAG');
      const lags = profiler.getProfilesByType('LAG');

      expect(tags.length).toBe(2);
      expect(lags.length).toBe(1);
    });
  });

  describe('clearProfile', () => {
    it('should clear specific profile', () => {
      profiler.updateProfile('Player1', { vpip: 25 });
      profiler.updateProfile('Player2', { vpip: 30 });

      profiler.clearProfile('Player1');

      expect(profiler.getProfile('Player1')).toBeUndefined();
      expect(profiler.getProfile('Player2')).toBeDefined();
    });
  });

  describe('clearAllProfiles', () => {
    it('should clear all profiles', () => {
      profiler.updateProfile('Player1', { vpip: 25 });
      profiler.updateProfile('Player2', { vpip: 30 });

      profiler.clearAllProfiles();

      expect(profiler.getAllProfiles().length).toBe(0);
    });
  });
});

