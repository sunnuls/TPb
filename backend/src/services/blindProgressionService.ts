import { EventEmitter } from 'events';
import { logger } from '../utils/logger';

export interface BlindLevel {
  level: number;
  smallBlind: number;
  bigBlind: number;
  ante?: number;
  duration: number; // minutes
}

export interface BlindStructure {
  name: string;
  levels: BlindLevel[];
  startingChips: number;
}

export interface BlindProgressionState {
  currentLevel: number;
  currentBlinds: BlindLevel;
  nextBlinds?: BlindLevel;
  timeRemaining: number; // seconds until next level
  averageStack: number;
  heroStack: number;
  avgStackInBB: number;
  heroStackInBB: number;
  projection: {
    levelsUntilCritical: number; // Levels until <10BB
    estimatedTime: string;
  };
}

/**
 * Blind Progression Service
 * Tracks and projects blind increases in tournaments
 */
export class BlindProgressionService extends EventEmitter {
  private structure?: BlindStructure;
  private currentLevel: number = 0;
  private startTime?: Date;
  private pausedTime?: Date;
  private isPaused: boolean = false;

  /**
   * Set blind structure
   */
  setStructure(structure: BlindStructure): void {
    this.structure = structure;
    this.currentLevel = 0;
    logger.info(`Blind structure set: ${structure.name}`);
  }

  /**
   * Start blind progression
   */
  start(): void {
    if (!this.structure) {
      throw new Error('Blind structure not set');
    }

    this.startTime = new Date();
    this.isPaused = false;
    logger.info('Blind progression started');

    this.emit('started');
  }

  /**
   * Pause blind progression
   */
  pause(): void {
    if (!this.isPaused) {
      this.pausedTime = new Date();
      this.isPaused = true;
      logger.info('Blind progression paused');
      this.emit('paused');
    }
  }

  /**
   * Resume blind progression
   */
  resume(): void {
    if (this.isPaused && this.pausedTime && this.startTime) {
      const pauseDuration = Date.now() - this.pausedTime.getTime();
      this.startTime = new Date(this.startTime.getTime() + pauseDuration);
      this.isPaused = false;
      this.pausedTime = undefined;
      logger.info('Blind progression resumed');
      this.emit('resumed');
    }
  }

  /**
   * Get current blind progression state
   */
  getState(heroStack: number, totalChips: number, playersRemaining: number): BlindProgressionState {
    if (!this.structure) {
      throw new Error('Blind structure not set');
    }

    const currentBlinds = this.structure.levels[this.currentLevel];
    const nextBlinds = this.structure.levels[this.currentLevel + 1];

    const averageStack = totalChips / playersRemaining;
    const avgStackInBB = averageStack / currentBlinds.bigBlind;
    const heroStackInBB = heroStack / currentBlinds.bigBlind;

    const timeRemaining = this.getTimeRemaining();

    // Project when hero will be critical (<10BB)
    const projection = this.projectCriticalLevel(
      heroStack,
      currentBlinds.bigBlind,
      this.currentLevel
    );

    return {
      currentLevel: this.currentLevel,
      currentBlinds,
      nextBlinds,
      timeRemaining,
      averageStack,
      heroStack,
      avgStackInBB,
      heroStackInBB,
      projection,
    };
  }

  /**
   * Get time remaining in current level
   */
  private getTimeRemaining(): number {
    if (!this.structure || !this.startTime) return 0;

    const currentBlinds = this.structure.levels[this.currentLevel];
    const levelDuration = currentBlinds.duration * 60 * 1000; // Convert to ms

    const elapsed = this.isPaused && this.pausedTime
      ? this.pausedTime.getTime() - this.startTime.getTime()
      : Date.now() - this.startTime.getTime();

    const timeRemainingMs = Math.max(0, levelDuration - elapsed);

    return Math.floor(timeRemainingMs / 1000); // Return in seconds
  }

  /**
   * Advance to next blind level
   */
  advanceLevel(): void {
    if (!this.structure) return;

    if (this.currentLevel < this.structure.levels.length - 1) {
      this.currentLevel++;
      this.startTime = new Date(); // Reset timer for new level

      const newBlinds = this.structure.levels[this.currentLevel];

      logger.info(
        `Blinds increased to ${newBlinds.smallBlind}/${newBlinds.bigBlind}`
      );

      this.emit('levelAdvanced', newBlinds);
    }
  }

  /**
   * Project when stack will be critical
   */
  private projectCriticalLevel(
    heroStack: number,
    currentBB: number,
    currentLevel: number
  ): { levelsUntilCritical: number; estimatedTime: string } {
    if (!this.structure) {
      return { levelsUntilCritical: 0, estimatedTime: 'Unknown' };
    }

    const criticalThreshold = 10; // 10BB is critical

    let stackInBB = heroStack / currentBB;

    if (stackInBB <= criticalThreshold) {
      return { levelsUntilCritical: 0, estimatedTime: 'Now' };
    }

    let levelsUntilCritical = 0;
    let totalTime = 0;

    for (let i = currentLevel + 1; i < this.structure.levels.length; i++) {
      const level = this.structure.levels[i];
      stackInBB = heroStack / level.bigBlind;

      levelsUntilCritical++;
      totalTime += level.duration;

      if (stackInBB <= criticalThreshold) {
        break;
      }
    }

    const hours = Math.floor(totalTime / 60);
    const minutes = totalTime % 60;
    const estimatedTime = hours > 0
      ? `${hours}h ${minutes}m`
      : `${minutes}m`;

    return { levelsUntilCritical, estimatedTime };
  }

  /**
   * Get recommended action timing
   */
  getActionTiming(heroStackBB: number): {
    urgency: 'none' | 'low' | 'medium' | 'high' | 'critical';
    message: string;
  } {
    const timeRemaining = this.getTimeRemaining();
    const minutesRemaining = Math.floor(timeRemaining / 60);

    let urgency: 'none' | 'low' | 'medium' | 'high' | 'critical';
    let message: string;

    if (heroStackBB < 10) {
      urgency = 'critical';
      message = 'Push/fold mode - need chips immediately';
    } else if (heroStackBB < 15 && minutesRemaining < 3) {
      urgency = 'high';
      message = 'Blinds increasing soon, look for spots now';
    } else if (heroStackBB < 20) {
      urgency = 'medium';
      message = 'Build stack before next blind level';
    } else if (heroStackBB < 30 && minutesRemaining < 2) {
      urgency = 'low';
      message = 'Consider stealing blinds before increase';
    } else {
      urgency = 'none';
      message = 'Comfortable stack depth';
    }

    return { urgency, message };
  }

  /**
   * Create standard tournament structure
   */
  static createStandardStructure(
    startingChips: number = 10000,
    levelDuration: number = 15
  ): BlindStructure {
    const levels: BlindLevel[] = [
      { level: 1, smallBlind: 25, bigBlind: 50, ante: 0, duration: levelDuration },
      { level: 2, smallBlind: 50, bigBlind: 100, ante: 0, duration: levelDuration },
      { level: 3, smallBlind: 75, bigBlind: 150, ante: 0, duration: levelDuration },
      { level: 4, smallBlind: 100, bigBlind: 200, ante: 25, duration: levelDuration },
      { level: 5, smallBlind: 150, bigBlind: 300, ante: 25, duration: levelDuration },
      { level: 6, smallBlind: 200, bigBlind: 400, ante: 50, duration: levelDuration },
      { level: 7, smallBlind: 300, bigBlind: 600, ante: 75, duration: levelDuration },
      { level: 8, smallBlind: 400, bigBlind: 800, ante: 100, duration: levelDuration },
      { level: 9, smallBlind: 600, bigBlind: 1200, ante: 150, duration: levelDuration },
      { level: 10, smallBlind: 800, bigBlind: 1600, ante: 200, duration: levelDuration },
      { level: 11, smallBlind: 1000, bigBlind: 2000, ante: 250, duration: levelDuration },
      { level: 12, smallBlind: 1500, bigBlind: 3000, ante: 400, duration: levelDuration },
      { level: 13, smallBlind: 2000, bigBlind: 4000, ante: 500, duration: levelDuration },
      { level: 14, smallBlind: 3000, bigBlind: 6000, ante: 750, duration: levelDuration },
      { level: 15, smallBlind: 4000, bigBlind: 8000, ante: 1000, duration: levelDuration },
    ];

    return {
      name: 'Standard Tournament',
      levels,
      startingChips,
    };
  }

  /**
   * Create turbo structure
   */
  static createTurboStructure(startingChips: number = 5000): BlindStructure {
    const structure = this.createStandardStructure(startingChips, 8);
    structure.name = 'Turbo Tournament';
    return structure;
  }
}

