import { useState } from 'react';
import styles from './RangeVisualizer.module.css';

interface RangeVisualizerGridProps {
  position?: string;
  street?: string;
}

// GTO ranges for different positions (simplified)
const GTORanges: Record<string, string[]> = {
  'BTN': [
    'AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'AKo', 'KK', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s',
    'AQo', 'KQo', 'QQ', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s',
    'AJo', 'KJo', 'QJo', 'JJ', 'JTs', 'J9s', 'J8s',
    'ATo', 'KTo', 'QTo', 'JTo', 'TT', 'T9s', 'T8s',
    'A9o', 'K9o', 'Q9o', 'J9o', 'T9o', '99', '98s', '97s',
    '88', '87s', '86s', '77', '76s', '75s', '66', '65s', '55', '54s', '44', '33', '22'
  ],
  'CO': [
    'AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'AKo', 'KK', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s',
    'AQo', 'KQo', 'QQ', 'QJs', 'QTs', 'Q9s', 'Q8s',
    'AJo', 'KJo', 'QJo', 'JJ', 'JTs', 'J9s',
    'ATo', 'KTo', 'QTo', 'JTo', 'TT', 'T9s', 'T8s',
    'A9o', '99', '98s', '88', '87s', '77', '76s', '66', '55', '44', '33', '22'
  ],
  'MP': [
    'AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
    'AKo', 'KK', 'KQs', 'KJs', 'KTs', 'K9s',
    'AQo', 'KQo', 'QQ', 'QJs', 'QTs', 'Q9s',
    'AJo', 'KJo', 'JJ', 'JTs', 'J9s',
    'ATo', 'TT', 'T9s', '99', '88', '77', '66', '55'
  ],
  'UTG': [
    'AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A5s', 'A4s',
    'AKo', 'KK', 'KQs', 'KJs', 'KTs',
    'AQo', 'KQo', 'QQ', 'QJs', 'QTs',
    'AJo', 'JJ', 'JTs', 'TT', '99', '88', '77', '66'
  ]
};

// All possible hands in standard grid format
const allHands = [
  ['AA', 'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s'],
  ['AKo', 'KK', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s'],
  ['AQo', 'KQo', 'QQ', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s'],
  ['AJo', 'KJo', 'QJo', 'JJ', 'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'J4s', 'J3s', 'J2s'],
  ['ATo', 'KTo', 'QTo', 'JTo', 'TT', 'T9s', 'T8s', 'T7s', 'T6s', 'T5s', 'T4s', 'T3s', 'T2s'],
  ['A9o', 'K9o', 'Q9o', 'J9o', 'T9o', '99', '98s', '97s', '96s', '95s', '94s', '93s', '92s'],
  ['A8o', 'K8o', 'Q8o', 'J8o', 'T8o', '98o', '88', '87s', '86s', '85s', '84s', '83s', '82s'],
  ['A7o', 'K7o', 'Q7o', 'J7o', 'T7o', '97o', '87o', '77', '76s', '75s', '74s', '73s', '72s'],
  ['A6o', 'K6o', 'Q6o', 'J6o', 'T6o', '96o', '86o', '76o', '66', '65s', '64s', '63s', '62s'],
  ['A5o', 'K5o', 'Q5o', 'J5o', 'T5o', '95o', '85o', '75o', '65o', '55', '54s', '53s', '52s'],
  ['A4o', 'K4o', 'Q4o', 'J4o', 'T4o', '94o', '84o', '74o', '64o', '54o', '44', '43s', '42s'],
  ['A3o', 'K3o', 'Q3o', 'J3o', 'T3o', '93o', '83o', '73o', '63o', '53o', '43o', '33', '32s'],
  ['A2o', 'K2o', 'Q2o', 'J2o', 'T2o', '92o', '82o', '72o', '62o', '52o', '42o', '32o', '22']
];

export function RangeVisualizerGrid({ position = 'BTN', street = 'preflop' }: RangeVisualizerGridProps) {
  const [selectedRange, setSelectedRange] = useState(position);
  const activeRange = GTORanges[selectedRange] || GTORanges['BTN'];

  const getHandColor = (hand: string): string => {
    if (activeRange.includes(hand)) {
      // Color based on hand strength
      if (hand.includes('AA') || hand.includes('KK') || hand.includes('QQ')) {
        return 'bg-red-600 hover:bg-red-700'; // Premium pairs
      } else if (hand.includes('JJ') || hand.includes('TT') || hand.includes('AKs') || hand.includes('AQs')) {
        return 'bg-orange-600 hover:bg-orange-700'; // Strong hands
      } else if (hand.includes('s') && !hand.includes('o')) {
        return 'bg-green-600 hover:bg-green-700'; // Suited hands
      } else if (hand.match(/^\d\d$/)) {
        return 'bg-yellow-600 hover:bg-yellow-700'; // Small pairs
      } else {
        return 'bg-blue-600 hover:bg-blue-700'; // Offsuit broadway
      }
    }
    return 'bg-gray-800 hover:bg-gray-700'; // Not in range
  };

  return (
    <div className={styles.rangeVisualizer}>
      <h3 className="text-sm font-bold text-white mb-1.5">Range Visualizer</h3>
      
      {/* Position Selector */}
      <div className="flex gap-1 mb-1.5 flex-wrap">
        {['BTN', 'CO', 'MP', 'UTG'].map((pos) => (
          <button
            key={pos}
            onClick={() => setSelectedRange(pos)}
            className={`px-2 py-0.5 rounded font-semibold text-[10px] transition-colors ${
              selectedRange === pos
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {pos}
          </button>
        ))}
      </div>

      {/* Stats - Compact */}
      <div className="mb-1.5 flex gap-2 text-[10px] justify-between bg-gray-800 rounded p-1">
        <span className="text-gray-400">Hands: <span className="text-white font-bold">{activeRange.length}</span></span>
        <span className="text-gray-400">Range: <span className="text-white font-bold">{((activeRange.length / 169) * 100).toFixed(1)}%</span></span>
        <span className="text-gray-400">Combos: <span className="text-white font-bold">{activeRange.length * 4}</span></span>
      </div>

      {/* Legend - Moved to top */}
      <div className="mb-1.5 grid grid-cols-3 gap-x-1 gap-y-0.5 text-[9px]">
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-red-600 rounded"></div>
          <span className="text-gray-300">Premium</span>
        </div>
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-orange-600 rounded"></div>
          <span className="text-gray-300">Strong</span>
        </div>
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-green-600 rounded"></div>
          <span className="text-gray-300">Suited</span>
        </div>
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-blue-600 rounded"></div>
          <span className="text-gray-300">Offsuit</span>
        </div>
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-yellow-600 rounded"></div>
          <span className="text-gray-300">Pairs</span>
        </div>
        <div className="flex items-center gap-0.5">
          <div className="w-2 h-2 bg-gray-800 rounded"></div>
          <span className="text-gray-300">Fold</span>
        </div>
      </div>

      {/* Range Grid - Split into columns for vertical display */}
      <div className="grid grid-cols-2 gap-1">
        {/* Left Column - First 7 rows */}
        <div className="inline-grid grid-cols-13 gap-0.5">
          {allHands.slice(0, 7).map((row, rowIdx) => (
            row.map((hand, colIdx) => (
              <div
                key={`${rowIdx}-${colIdx}`}
                className={`${getHandColor(hand)} rounded text-white font-bold flex items-center justify-center transition-all cursor-pointer`}
                style={{ 
                  width: '18px', 
                  height: '18px',
                  fontSize: '7px'
                }}
                title={hand}
              >
                {hand}
              </div>
            ))
          ))}
        </div>
        
        {/* Right Column - Last 6 rows */}
        <div className="inline-grid grid-cols-13 gap-0.5">
          {allHands.slice(7, 13).map((row, rowIdx) => (
            row.map((hand, colIdx) => (
              <div
                key={`${rowIdx + 7}-${colIdx}`}
                className={`${getHandColor(hand)} rounded text-white font-bold flex items-center justify-center transition-all cursor-pointer`}
                style={{ 
                  width: '18px', 
                  height: '18px',
                  fontSize: '7px'
                }}
                title={hand}
              >
                {hand}
              </div>
            ))
          ))}
        </div>
      </div>
    </div>
  );
}
