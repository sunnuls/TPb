import { useState } from 'react';
import { useGameStore } from '../../stores/gameStore';
import { TableView } from '../TableView/TableView';
import { StatisticsPanel } from '../StatisticsPanel/StatisticsPanel';
import { StrategyPanel } from '../StrategyPanel/StrategyPanel';
import { SettingsPanel } from '../SettingsPanel/SettingsPanel';
import { 
  generateDemoGameState, 
  generateDemoGameStatePreflop,
  generateDemoGameStateTurn,
  generateDemoGameStateRiver 
} from '../../utils/demoData';
import styles from './Overlay.module.css';

export function Overlay() {
  const { gameState, setGameState, clearGame } = useGameStore();
  const [activeTab, setActiveTab] = useState<'stats' | 'strategy' | 'settings'>('stats');
  const [showDemoMenu, setShowDemoMenu] = useState(false);

  const handleDemoMode = (mode: 'preflop' | 'flop' | 'turn' | 'river') => {
    let demoState;
    switch (mode) {
      case 'preflop':
        demoState = generateDemoGameStatePreflop();
        break;
      case 'flop':
        demoState = generateDemoGameState();
        break;
      case 'turn':
        demoState = generateDemoGameStateTurn();
        break;
      case 'river':
        demoState = generateDemoGameStateRiver();
        break;
    }
    setGameState(demoState);
    setShowDemoMenu(false);
  };

  if (!gameState) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="text-center text-white">
          <div className="mb-8">
            <p className="text-2xl font-bold mb-2">No active game</p>
            <p className="text-gray-400">Waiting for game data...</p>
          </div>
          
          {/* Demo Mode Section */}
          <div className="relative inline-block">
            <button
              onClick={() => setShowDemoMenu(!showDemoMenu)}
              className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold rounded-lg shadow-lg transition-all transform hover:scale-105"
            >
              🎰 Start Demo Mode
            </button>

            {/* Demo Menu Dropdown */}
            {showDemoMenu && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-800 rounded-lg shadow-2xl border border-gray-700 overflow-hidden z-10 min-w-[200px]">
                <div className="p-2">
                  <p className="text-xs text-gray-400 px-3 py-2 font-semibold">Choose Street:</p>
                  <button
                    onClick={() => handleDemoMode('preflop')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-700 transition-colors rounded text-white"
                  >
                    <span className="font-semibold">🃏 Preflop</span>
                    <span className="block text-xs text-gray-400 mt-1">Pocket Aces - Decision time</span>
                  </button>
                  <button
                    onClick={() => handleDemoMode('flop')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-700 transition-colors rounded text-white"
                  >
                    <span className="font-semibold">🎴 Flop</span>
                    <span className="block text-xs text-gray-400 mt-1">AK on Q-J-T board</span>
                  </button>
                  <button
                    onClick={() => handleDemoMode('turn')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-700 transition-colors rounded text-white"
                  >
                    <span className="font-semibold">🎯 Turn</span>
                    <span className="block text-xs text-gray-400 mt-1">Straight on the board</span>
                  </button>
                  <button
                    onClick={() => handleDemoMode('river')}
                    className="w-full text-left px-4 py-3 hover:bg-gray-700 transition-colors rounded text-white"
                  >
                    <span className="font-semibold">💎 River</span>
                    <span className="block text-xs text-gray-400 mt-1">Final decision point</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          <p className="mt-6 text-sm text-gray-500">
            Or connect to a real poker table to get live assistance
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.container}>
        {/* Demo Mode Header */}
        {gameState.id.startsWith('demo-') && (
          <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
            <span className="px-4 py-2 bg-yellow-600 text-white rounded-lg font-bold text-sm shadow-lg animate-pulse">
              🎰 DEMO MODE
            </span>
            <button
              onClick={() => clearGame()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold text-sm shadow-lg transition-colors"
            >
              Exit Demo
            </button>
          </div>
        )}

        {/* Main Table View */}
        <div className={styles.mainPanel}>
          <TableView gameState={gameState} />
        </div>

        {/* Side Panels */}
        <div className={styles.sidePanels}>
          {/* Tab Buttons */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setActiveTab('stats')}
              className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-colors ${
                activeTab === 'stats'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Stats
            </button>
            <button
              onClick={() => setActiveTab('strategy')}
              className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-colors ${
                activeTab === 'strategy'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Strategy
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-colors ${
                activeTab === 'settings'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              ⚙️
            </button>
          </div>

          {/* Panel Content */}
          {activeTab === 'stats' && <StatisticsPanel gameState={gameState} />}
          {activeTab === 'strategy' && <StrategyPanel gameState={gameState} />}
          {activeTab === 'settings' && <SettingsPanel />}
        </div>
      </div>
    </div>
  );
}

