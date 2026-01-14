import { useState } from 'react';
import { useGameStore } from '../../stores/gameStore';
import { TableView } from '../TableView/TableView';
import { StatisticsPanel } from '../StatisticsPanel/StatisticsPanel';
import { StrategyPanel } from '../StrategyPanel/StrategyPanel';
import { SettingsPanel } from '../SettingsPanel/SettingsPanel';
import styles from './Overlay.module.css';

export function Overlay() {
  const { gameState } = useGameStore();
  const [activeTab, setActiveTab] = useState<'stats' | 'strategy' | 'settings'>('stats');

  if (!gameState) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-white">
          <p className="text-xl mb-4">No active game</p>
          <p className="text-gray-400">Waiting for game data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.container}>
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

