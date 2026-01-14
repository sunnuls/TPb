import { EventEmitter } from 'events';
import { Position } from '@tpb/shared';
import { logger } from '../utils/logger';

export type PlayerType = 'TAG' | 'LAG' | 'TP' | 'LP' | 'MANIAC' | 'ROCK' | 'FISH' | 'UNKNOWN';

export interface PlayerProfile {
  playerName: string;
  handsObserved: number;
  playerType: PlayerType;
  confidence: number; // 0-1
  stats: {
    vpip: number;
    pfr: number;
    aggressionFactor: number;
    wtsd: number;
    wsd: number;
    threeBet: number;
    foldTo3Bet: number;
    cBet: number;
    foldToCBet: number;
    checkRaise: number;
  };
  tendencies: {
    bluffsOften: boolean;
    valueHeavy: boolean;
    positionalAware: boolean;
    tiltProne: boolean;
    predictable: boolean;
  };
  rangeEstimates: {
    [key in Position]?: string[]; // Opening ranges by position
  };
  notes: string[];
  lastUpdated: Date;
}

export interface ExploitativeStrategy {
  playerName: string;
  playerType: PlayerType;
  recommendations: string[];
  adjustments: {
    tightenRange: boolean;
    loosenRange: boolean;
    increaseAggression: boolean;
    decreaseAggression: boolean;
    bluffMore: boolean;
    bluffLess: boolean;
    valueBetThin: boolean;
  };
}

/**
 * Player Profiler Service - builds detailed player profiles
 */
export class PlayerProfilerService extends EventEmitter {
  private profiles: Map<string, PlayerProfile> = new Map();

  /**
   * Create or update player profile
   */
  updateProfile(
    playerName: string,
    stats: Partial<PlayerProfile['stats']>,
    actions?: any[]
  ): PlayerProfile {
    const existing = this.profiles.get(playerName);

    const profile: PlayerProfile = {
      playerName,
      handsObserved: (existing?.handsObserved || 0) + 1,
      playerType: 'UNKNOWN',
      confidence: 0,
      stats: {
        vpip: stats.vpip || existing?.stats.vpip || 0,
        pfr: stats.pfr || existing?.stats.pfr || 0,
        aggressionFactor: stats.aggressionFactor || existing?.stats.aggressionFactor || 0,
        wtsd: stats.wtsd || existing?.stats.wtsd || 0,
        wsd: stats.wsd || existing?.stats.wsd || 0,
        threeBet: stats.threeBet || existing?.stats.threeBet || 0,
        foldTo3Bet: stats.foldTo3Bet || existing?.stats.foldTo3Bet || 0,
        cBet: stats.cBet || existing?.stats.cBet || 0,
        foldToCBet: stats.foldToCBet || existing?.stats.foldToCBet || 0,
        checkRaise: stats.checkRaise || existing?.stats.checkRaise || 0,
      },
      tendencies: existing?.tendencies || {
        bluffsOften: false,
        valueHeavy: false,
        positionalAware: false,
        tiltProne: false,
        predictable: false,
      },
      rangeEstimates: existing?.rangeEstimates || {},
      notes: existing?.notes || [],
      lastUpdated: new Date(),
    };

    // Classify player type
    profile.playerType = this.classifyPlayerType(profile.stats);
    profile.confidence = this.calculateConfidence(profile.handsObserved);

    // Analyze tendencies
    profile.tendencies = this.analyzeTendencies(profile.stats, actions);

    this.profiles.set(playerName, profile);
    this.emit('profileUpdated', profile);

    logger.debug(`Profile updated: ${playerName} - ${profile.playerType}`);

    return profile;
  }

  /**
   * Classify player type based on stats
   */
  private classifyPlayerType(stats: PlayerProfile['stats']): PlayerType {
    const { vpip, pfr, aggressionFactor } = stats;

    // TAG (Tight-Aggressive): Low VPIP, high PFR/VPIP ratio, high AF
    if (vpip < 20 && pfr / vpip > 0.6 && aggressionFactor > 2) {
      return 'TAG';
    }

    // LAG (Loose-Aggressive): High VPIP, high PFR, high AF
    if (vpip > 25 && pfr > 18 && aggressionFactor > 2) {
      return 'LAG';
    }

    // TP (Tight-Passive): Low VPIP, low AF
    if (vpip < 20 && aggressionFactor < 1.5) {
      return 'TP';
    }

    // LP (Loose-Passive): High VPIP, low AF
    if (vpip > 30 && aggressionFactor < 1.5) {
      return 'LP';
    }

    // MANIAC: Very high VPIP, very high AF
    if (vpip > 40 && aggressionFactor > 3) {
      return 'MANIAC';
    }

    // ROCK: Very tight
    if (vpip < 12 && pfr < 8) {
      return 'ROCK';
    }

    // FISH: Loose-passive with poor stats
    if (vpip > 35 && pfr < 10 && aggressionFactor < 1) {
      return 'FISH';
    }

    return 'UNKNOWN';
  }

  /**
   * Calculate confidence level based on sample size
   */
  private calculateConfidence(handsObserved: number): number {
    // Confidence increases with sample size, asymptotically approaching 1
    // 100 hands = ~0.7, 500 hands = ~0.9, 1000+ hands = ~0.95+
    return Math.min(0.95, 1 - Math.exp(-handsObserved / 300));
  }

  /**
   * Analyze player tendencies
   */
  private analyzeTendencies(
    stats: PlayerProfile['stats'],
    actions?: any[]
  ): PlayerProfile['tendencies'] {
    return {
      bluffsOften: stats.aggressionFactor > 2.5 && stats.wtsd < 20,
      valueHeavy: stats.aggressionFactor < 2 && stats.wsd > 55,
      positionalAware: true, // Would need positional stats
      tiltProne: false, // Would need variance analysis
      predictable: stats.cBet > 70 || stats.foldToCBet > 70,
    };
  }

  /**
   * Generate exploitative strategy
   */
  generateExploitativeStrategy(playerName: string): ExploitativeStrategy | null {
    const profile = this.profiles.get(playerName);

    if (!profile || profile.confidence < 0.5) {
      return null;
    }

    const recommendations: string[] = [];
    const adjustments = {
      tightenRange: false,
      loosenRange: false,
      increaseAggression: false,
      decreaseAggression: false,
      bluffMore: false,
      bluffLess: false,
      valueBetThin: false,
    };

    switch (profile.playerType) {
      case 'TAG':
        recommendations.push('Respect their raises - they have strong hands');
        recommendations.push('Avoid bluffing - they fold appropriately');
        recommendations.push('Value bet thinly - they pay off');
        adjustments.tightenRange = true;
        adjustments.valueBetThin = true;
        break;

      case 'LAG':
        recommendations.push('Widen your calling range - they bluff often');
        recommendations.push('Let them bet - trap with strong hands');
        recommendations.push('3-bet for value more liberally');
        adjustments.loosenRange = true;
        adjustments.decreaseAggression = true;
        break;

      case 'TP':
        recommendations.push('Bluff frequently - they fold too much');
        recommendations.push('Bet for value thinly - they call too wide');
        recommendations.push('Avoid slow-playing - they won\'t pay you off');
        adjustments.increaseAggression = true;
        adjustments.bluffMore = true;
        break;

      case 'LP':
      case 'FISH':
        recommendations.push('Value bet relentlessly - they call too much');
        recommendations.push('Avoid bluffing - they don\'t fold');
        recommendations.push('Play straightforward - they don\'t adjust');
        adjustments.bluffLess = true;
        adjustments.valueBetThin = true;
        break;

      case 'MANIAC':
        recommendations.push('Tighten up and wait for premiums');
        recommendations.push('Let them bluff - call down lighter');
        recommendations.push('Avoid bluffing back - they don\'t fold');
        adjustments.tightenRange = true;
        adjustments.bluffLess = true;
        break;

      case 'ROCK':
        recommendations.push('Steal their blinds aggressively');
        recommendations.push('Fold to their raises - they have it');
        recommendations.push('Avoid paying them off');
        adjustments.increaseAggression = true;
        adjustments.tightenRange = true;
        break;

      default:
        recommendations.push('Insufficient data - play standard strategy');
    }

    // Add specific tendency-based recommendations
    if (profile.tendencies.bluffsOften) {
      recommendations.push('Call down lighter - they bluff frequently');
    }

    if (profile.tendencies.predictable) {
      recommendations.push('Exploit their predictable patterns');
    }

    if (profile.stats.foldToCBet > 70) {
      recommendations.push('C-bet aggressively - they fold too much');
      adjustments.bluffMore = true;
    }

    if (profile.stats.threeBet > 10) {
      recommendations.push('Tighten your opening range - they 3-bet often');
    }

    return {
      playerName,
      playerType: profile.playerType,
      recommendations,
      adjustments,
    };
  }

  /**
   * Get player profile
   */
  getProfile(playerName: string): PlayerProfile | undefined {
    return this.profiles.get(playerName);
  }

  /**
   * Get all profiles
   */
  getAllProfiles(): PlayerProfile[] {
    return Array.from(this.profiles.values());
  }

  /**
   * Get profiles by type
   */
  getProfilesByType(type: PlayerType): PlayerProfile[] {
    return Array.from(this.profiles.values()).filter(p => p.playerType === type);
  }

  /**
   * Add note to profile
   */
  addNote(playerName: string, note: string): void {
    const profile = this.profiles.get(playerName);
    if (profile) {
      profile.notes.push(`[${new Date().toISOString()}] ${note}`);
      profile.lastUpdated = new Date();
      this.emit('noteAdded', { playerName, note });
    }
  }

  /**
   * Clear profile
   */
  clearProfile(playerName: string): void {
    this.profiles.delete(playerName);
    logger.info(`Profile cleared: ${playerName}`);
  }

  /**
   * Clear all profiles
   */
  clearAllProfiles(): void {
    this.profiles.clear();
    logger.info('All profiles cleared');
  }
}

