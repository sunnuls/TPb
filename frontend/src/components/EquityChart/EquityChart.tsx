import React, { useMemo } from 'react';
import styles from './EquityChart.module.css';

interface EquityChartProps {
  equity: number; // 0-1
  potOdds?: number; // 0-1
  title?: string;
  showPotOdds?: boolean;
  showRecommendation?: boolean;
  size?: 'small' | 'medium' | 'large';
}

/**
 * Equity Chart - visual representation of equity vs pot odds
 */
export const EquityChart: React.FC<EquityChartProps> = ({
  equity,
  potOdds,
  title = 'Equity',
  showPotOdds = true,
  showRecommendation = true,
  size = 'medium',
}) => {
  const equityPercent = (equity * 100).toFixed(1);
  const potOddsPercent = potOdds ? (potOdds * 100).toFixed(1) : null;

  /**
   * Get recommendation based on equity vs pot odds
   */
  const recommendation = useMemo(() => {
    if (!potOdds) return null;

    const diff = equity - potOdds;
    const absDiff = Math.abs(diff);

    if (diff > 0.1) {
      return { text: 'Strong Call', color: '#10b981', icon: '✓✓' };
    } else if (diff > 0.05) {
      return { text: 'Call', color: '#3b82f6', icon: '✓' };
    } else if (absDiff <= 0.05) {
      return { text: 'Marginal', color: '#f59e0b', icon: '~' };
    } else if (diff > -0.1) {
      return { text: 'Fold', color: '#ef4444', icon: '✗' };
    } else {
      return { text: 'Strong Fold', color: '#dc2626', icon: '✗✗' };
    }
  }, [equity, potOdds]);

  /**
   * Get color based on equity
   */
  const getEquityColor = (eq: number): string => {
    if (eq >= 0.7) return '#10b981'; // Green
    if (eq >= 0.5) return '#3b82f6'; // Blue
    if (eq >= 0.3) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const equityColor = getEquityColor(equity);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const equityOffset = circumference - equity * circumference;
  const potOddsOffset = potOdds ? circumference - potOdds * circumference : 0;

  return (
    <div className={`${styles.container} ${styles[size]}`}>
      {title && <h4 className={styles.title}>{title}</h4>}

      <div className={styles.chartWrapper}>
        <svg
          className={styles.svg}
          viewBox="0 0 100 100"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Background circle */}
          <circle
            className={styles.bgCircle}
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="var(--bg-tertiary, #334155)"
            strokeWidth="10"
          />

          {/* Pot odds circle (if shown) */}
          {showPotOdds && potOdds && (
            <circle
              className={styles.potOddsCircle}
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="rgba(148, 163, 184, 0.3)"
              strokeWidth="10"
              strokeDasharray={circumference}
              strokeDashoffset={potOddsOffset}
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
            />
          )}

          {/* Equity circle */}
          <circle
            className={styles.equityCircle}
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={equityColor}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={equityOffset}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
          />

          {/* Center text */}
          <text
            x="50"
            y="50"
            textAnchor="middle"
            dominantBaseline="middle"
            className={styles.equityText}
            fill={equityColor}
          >
            {equityPercent}%
          </text>
        </svg>
      </div>

      {showPotOdds && potOdds && (
        <div className={styles.info}>
          <div className={styles.infoRow}>
            <span className={styles.label}>Equity:</span>
            <span className={styles.value} style={{ color: equityColor }}>
              {equityPercent}%
            </span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.label}>Pot Odds:</span>
            <span className={styles.value}>{potOddsPercent}%</span>
          </div>
        </div>
      )}

      {showRecommendation && recommendation && (
        <div
          className={styles.recommendation}
          style={{ borderColor: recommendation.color }}
        >
          <span className={styles.icon} style={{ color: recommendation.color }}>
            {recommendation.icon}
          </span>
          <span className={styles.recText} style={{ color: recommendation.color }}>
            {recommendation.text}
          </span>
        </div>
      )}
    </div>
  );
};

