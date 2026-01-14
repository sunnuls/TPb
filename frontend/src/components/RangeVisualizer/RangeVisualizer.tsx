import React, { useMemo } from 'react';
import styles from './RangeVisualizer.module.css';

interface RangeVisualizerProps {
  range: string[]; // Array of hand notations: ['AA', 'AKs', 'AKo', '22+', etc.]
  title?: string;
  showPercentage?: boolean;
  interactive?: boolean;
  onHandClick?: (hand: string) => void;
}

type HandType = 'pair' | 'suited' | 'offsuit';

interface HandCell {
  notation: string;
  inRange: boolean;
  type: HandType;
  frequency?: number; // 0-1 for mixed strategies
}

const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

/**
 * Range Visualizer - displays poker hand ranges in matrix format
 */
export const RangeVisualizer: React.FC<RangeVisualizerProps> = ({
  range,
  title = 'Range',
  showPercentage = true,
  interactive = false,
  onHandClick,
}) => {
  /**
   * Parse range notation and create matrix
   */
  const matrix = useMemo(() => {
    const grid: HandCell[][] = [];
    const rangeSet = new Set(expandRange(range));

    // Create 13x13 matrix
    for (let i = 0; i < 13; i++) {
      const row: HandCell[] = [];
      for (let j = 0; j < 13; j++) {
        const rank1 = RANKS[i];
        const rank2 = RANKS[j];

        let notation: string;
        let type: HandType;

        if (i === j) {
          // Pairs (diagonal)
          notation = `${rank1}${rank2}`;
          type = 'pair';
        } else if (i < j) {
          // Suited (upper triangle)
          notation = `${rank2}${rank1}s`;
          type = 'suited';
        } else {
          // Offsuit (lower triangle)
          notation = `${rank1}${rank2}o`;
          type = 'offsuit';
        }

        row.push({
          notation,
          inRange: rangeSet.has(notation),
          type,
        });
      }
      grid.push(row);
    }

    return grid;
  }, [range]);

  /**
   * Calculate range percentage
   */
  const rangePercentage = useMemo(() => {
    const totalHands = 169; // 13x13
    const handsInRange = matrix.flat().filter(cell => cell.inRange).length;
    return ((handsInRange / totalHands) * 100).toFixed(1);
  }, [matrix]);

  /**
   * Handle cell click
   */
  const handleCellClick = (hand: string) => {
    if (interactive && onHandClick) {
      onHandClick(hand);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {showPercentage && (
          <span className={styles.percentage}>{rangePercentage}%</span>
        )}
      </div>

      <div className={styles.matrix}>
        {matrix.map((row, i) => (
          <div key={i} className={styles.row}>
            {row.map((cell, j) => (
              <div
                key={j}
                className={`
                  ${styles.cell}
                  ${cell.inRange ? styles.inRange : ''}
                  ${styles[cell.type]}
                  ${interactive ? styles.interactive : ''}
                `}
                onClick={() => handleCellClick(cell.notation)}
                title={cell.notation}
              >
                <span className={styles.notation}>
                  {cell.notation.replace('s', '').replace('o', '')}
                </span>
                {cell.type === 'suited' && <span className={styles.suit}>s</span>}
                {cell.type === 'offsuit' && <span className={styles.suit}>o</span>}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className={styles.legend}>
        <div className={styles.legendItem}>
          <div className={`${styles.legendBox} ${styles.pair}`}></div>
          <span>Pairs</span>
        </div>
        <div className={styles.legendItem}>
          <div className={`${styles.legendBox} ${styles.suited}`}></div>
          <span>Suited</span>
        </div>
        <div className={styles.legendItem}>
          <div className={`${styles.legendBox} ${styles.offsuit}`}></div>
          <span>Offsuit</span>
        </div>
      </div>
    </div>
  );
};

/**
 * Expand range notation to individual hands
 */
function expandRange(range: string[]): string[] {
  const expanded = new Set<string>();

  for (const notation of range) {
    // Handle pairs with +: 22+, 77+, etc.
    if (notation.match(/^\d{2}\+$/) || notation.match(/^[AKQJT]\1\+$/)) {
      const rank = notation[0];
      const startIdx = RANKS.indexOf(rank);
      for (let i = startIdx; i >= 0; i--) {
        expanded.add(`${RANKS[i]}${RANKS[i]}`);
      }
      continue;
    }

    // Handle suited/offsuit ranges: AKs+, A5s+, etc.
    if (notation.match(/^[AKQJT\d]{2}[so]\+$/)) {
      const rank1 = notation[0];
      const rank2 = notation[1];
      const suitType = notation[2]; // 's' or 'o'
      const rank2Idx = RANKS.indexOf(rank2);

      for (let i = rank2Idx; i >= 0; i--) {
        expanded.add(`${rank1}${RANKS[i]}${suitType}`);
      }
      continue;
    }

    // Handle specific hands: AKs, AKo, 22, etc.
    expanded.add(notation);
  }

  return Array.from(expanded);
}

