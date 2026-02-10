import { useState, useEffect } from 'react';
import { GameState, Card } from '@tpb/shared';
import styles from './EquityDisplay.module.css';

interface EquityDisplayProps {
  gameState: GameState;
}

interface EquityData {
  heroEquity: number;
  villainEquity: number;
  potOdds: number;
  requiredEquity: number;
  recommendation: 'call' | 'fold' | 'raise';
  outs: number;
}

/**
 * Calculate approximate equity based on hand strength and board texture
 */
function calculateEquity(gameState: GameState): EquityData {
  const hero = gameState.players.find((p, idx) => idx === 0);
  if (!hero || !hero.holeCards || hero.holeCards.length !== 2) {
    return {
      heroEquity: 50,
      villainEquity: 50,
      potOdds: 0,
      requiredEquity: 0,
      recommendation: 'fold',
      outs: 0
    };
  }

  // Count active opponents
  const activeOpponents = gameState.players.filter(p => !p.folded && p.idx !== 0).length;
  
  // Base equity calculations (simplified)
  let heroEquity = 50;
  let outs = 0;

  const heroCards = hero.holeCards;
  const board = gameState.board;

  // Check for pairs, draws, etc.
  const isPair = heroCards[0][0] === heroCards[1][0];
  const isSuited = heroCards[0][1] === heroCards[1][1];
  const hasAce = heroCards.some(c => c[0] === 'A');
  const hasKing = heroCards.some(c => c[0] === 'K');

  if (gameState.street === 'preflop') {
    // Preflop equity estimation
    if (isPair) {
      const rank = heroCards[0][0];
      if (rank === 'A') heroEquity = 85;
      else if (rank === 'K') heroEquity = 82;
      else if (rank === 'Q') heroEquity = 80;
      else if (rank === 'J' || rank === 'T') heroEquity = 75;
      else heroEquity = 70;
    } else if (hasAce && hasKing) {
      heroEquity = isSuited ? 67 : 65;
    } else if (hasAce) {
      heroEquity = isSuited ? 60 : 58;
    } else if (hasKing) {
      heroEquity = isSuited ? 57 : 55;
    } else if (isSuited) {
      heroEquity = 55;
    }
    
    // Adjust for number of opponents
    heroEquity = heroEquity / (1 + activeOpponents * 0.15);
  } else {
    // Postflop - check for draws
    const heroRanks = heroCards.map(c => c[0]);
    const heroSuits = heroCards.map(c => c[1]);
    const boardRanks = board.map(c => c[0]);
    const boardSuits = board.map(c => c[1]);
    
    // Count suits for flush draw
    const allSuits = [...heroSuits, ...boardSuits];
    const suitCounts = allSuits.reduce((acc, suit) => {
      acc[suit] = (acc[suit] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const maxSuitCount = Math.max(...Object.values(suitCounts));
    const hasFlushDraw = maxSuitCount === 4;
    const hasFlush = maxSuitCount >= 5;
    
    // Simple equity estimation for postflop
    if (hasFlush) {
      heroEquity = 80;
      outs = 0;
    } else if (hasFlushDraw) {
      heroEquity = 35;
      outs = 9; // 9 outs for flush
    } else if (isPair) {
      heroEquity = 55;
      outs = 2;
    } else {
      heroEquity = 30;
      outs = 6; // Assume some overcards
    }

    // Check for straight draws (simplified)
    const allRanks = [...heroRanks, ...boardRanks];
    const rankValues: Record<string, number> = {
      'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
      '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    };
    const sortedValues = allRanks.map(r => rankValues[r]).sort((a, b) => b - a);
    const uniqueValues = [...new Set(sortedValues)];
    
    // Check for potential straight
    if (uniqueValues.length >= 4) {
      let maxConsecutive = 1;
      let currentConsecutive = 1;
      for (let i = 1; i < uniqueValues.length; i++) {
        if (uniqueValues[i] === uniqueValues[i-1] - 1) {
          currentConsecutive++;
          maxConsecutive = Math.max(maxConsecutive, currentConsecutive);
        } else {
          currentConsecutive = 1;
        }
      }
      if (maxConsecutive === 4) {
        heroEquity += 10;
        outs += 8; // Open-ended straight draw
      }
    }

    // Adjust for street
    if (gameState.street === 'turn') {
      heroEquity = heroEquity * 1.1;
    } else if (gameState.street === 'river') {
      // On river, equity is fixed - no more cards
      heroEquity = heroEquity > 50 ? 100 : 0;
      outs = 0;
    }

    // Adjust for opponents
    heroEquity = Math.min(95, heroEquity / (1 + activeOpponents * 0.1));
  }

  // Calculate pot odds
  const totalPot = gameState.pot;
  const toCall = Math.max(...gameState.players.map(p => p.bet)) - hero.bet;
  const potOdds = toCall > 0 ? (toCall / (totalPot + toCall)) * 100 : 0;
  const requiredEquity = potOdds;

  // Recommendation
  let recommendation: 'call' | 'fold' | 'raise' = 'fold';
  if (heroEquity >= requiredEquity + 15) {
    recommendation = 'raise';
  } else if (heroEquity >= requiredEquity) {
    recommendation = 'call';
  }

  const villainEquity = 100 - heroEquity;

  return {
    heroEquity: Math.round(heroEquity * 10) / 10,
    villainEquity: Math.round(villainEquity * 10) / 10,
    potOdds: Math.round(potOdds * 10) / 10,
    requiredEquity: Math.round(requiredEquity * 10) / 10,
    recommendation,
    outs: Math.min(outs, 15)
  };
}

export function EquityDisplay({ gameState }: EquityDisplayProps) {
  const [equity, setEquity] = useState<EquityData | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  useEffect(() => {
    setIsCalculating(true);
    // Simulate calculation delay
    const timer = setTimeout(() => {
      const result = calculateEquity(gameState);
      setEquity(result);
      setIsCalculating(false);
    }, 500);

    return () => clearTimeout(timer);
  }, [gameState]);

  if (isCalculating || !equity) {
    return (
      <div className={styles.equityDisplay}>
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-gray-400 text-xs">Calculating...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.equityDisplay}>
      <h3 className="text-sm font-bold text-white mb-1.5">Equity Calculator</h3>
      
      {/* Equity Bar */}
      <div className="mb-2">
        <div className="flex justify-between text-[10px] mb-0.5">
          <span className="text-green-400 font-semibold">You: {equity.heroEquity}%</span>
          <span className="text-red-400 font-semibold">Opp: {equity.villainEquity}%</span>
        </div>
        <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden flex">
          <div 
            className="bg-gradient-to-r from-green-500 to-green-400 flex items-center justify-center text-[9px] font-bold text-white"
            style={{ width: `${equity.heroEquity}%` }}
          >
            {equity.heroEquity > 15 && `${equity.heroEquity}%`}
          </div>
          <div 
            className="bg-gradient-to-r from-red-400 to-red-500 flex items-center justify-center text-[9px] font-bold text-white"
            style={{ width: `${equity.villainEquity}%` }}
          >
            {equity.villainEquity > 15 && `${equity.villainEquity}%`}
          </div>
        </div>
      </div>

      {/* Stats Grid - Compact */}
      <div className="grid grid-cols-2 gap-1.5 mb-2">
        <div className="bg-gray-800 rounded p-1.5">
          <p className="text-gray-400 text-[9px]">Pot Odds</p>
          <p className="text-white font-bold text-xs">{equity.potOdds.toFixed(1)}%</p>
        </div>
        <div className="bg-gray-800 rounded p-1.5">
          <p className="text-gray-400 text-[9px]">Required</p>
          <p className="text-white font-bold text-xs">{equity.requiredEquity.toFixed(1)}%</p>
        </div>
        {equity.outs > 0 && (
          <>
            <div className="bg-gray-800 rounded p-1.5">
              <p className="text-gray-400 text-[9px]">Outs</p>
              <p className="text-white font-bold text-xs">{equity.outs}</p>
            </div>
            <div className="bg-gray-800 rounded p-1.5">
              <p className="text-gray-400 text-[9px]">Turn/River</p>
              <p className="text-white font-bold text-xs">{(equity.outs * 4).toFixed(0)}%</p>
            </div>
          </>
        )}
      </div>

      {/* Recommendation Badge - Compact */}
      <div className={`p-2 rounded-lg border ${
        equity.recommendation === 'raise' 
          ? 'bg-green-900 bg-opacity-30 border-green-500' 
          : equity.recommendation === 'call'
          ? 'bg-yellow-900 bg-opacity-30 border-yellow-500'
          : 'bg-red-900 bg-opacity-30 border-red-500'
      }`}>
        <p className={`font-bold text-sm ${
          equity.recommendation === 'raise' ? 'text-green-400' :
          equity.recommendation === 'call' ? 'text-yellow-400' :
          'text-red-400'
        }`}>
          {equity.recommendation === 'raise' && '📈 RAISE'}
          {equity.recommendation === 'call' && '✅ CALL'}
          {equity.recommendation === 'fold' && '❌ FOLD'}
        </p>
        <p className="text-[9px] text-gray-300 mt-0.5">
          {equity.recommendation === 'raise' && 'Strong equity - build pot'}
          {equity.recommendation === 'call' && 'Sufficient equity'}
          {equity.recommendation === 'fold' && 'Not enough equity'}
        </p>
      </div>
    </div>
  );
}
