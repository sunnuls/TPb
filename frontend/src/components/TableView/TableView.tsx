import { GameState } from '@tpb/shared';
import { Card } from '../Common/Card';
import styles from './TableView.module.css';

interface TableViewProps {
  gameState: GameState;
}

export function TableView({ gameState }: TableViewProps) {
  const hero = gameState.players.find((p, idx) => idx === 0);
  const opponents = gameState.players.filter((p, idx) => idx !== 0);

  return (
    <div className={styles.tableView}>
      <div className="relative w-full h-full flex items-center justify-center">
        {/* Poker Table Background */}
        <div className={styles.pokerTable}>
          {/* Community Cards Section */}
          <div className={styles.boardArea}>
            <div className={styles.communityCards}>
              {gameState.board.length > 0 ? (
                <div className="flex gap-2">
                  {gameState.board.map((card, idx) => (
                    <div key={idx} className="transform hover:scale-105 transition-transform">
                      <Card card={card} size="md" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-sm font-semibold">
                  Waiting for flop...
                </div>
              )}
            </div>

            {/* Pot Display */}
            <div className={styles.potDisplay}>
              <div className="relative">
                {/* Poker Chips Icon */}
                <div className="absolute -top-6 left-1/2 transform -translate-x-1/2">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 border-3 border-yellow-300 flex items-center justify-center shadow-lg">
                    <span className="text-gray-900 font-bold text-xs">POT</span>
                  </div>
                </div>
                
                <div className="bg-gradient-to-br from-gray-800 to-gray-900 px-4 py-2 rounded-lg border-2 border-yellow-600 shadow-xl">
                  <p className="text-yellow-400 font-bold text-xl text-center">
                    ${gameState.pot}
                  </p>
                </div>
              </div>
            </div>

            {/* Street Indicator */}
            <div className={styles.streetBadge}>
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-3 py-1 rounded-full font-bold text-xs uppercase shadow-lg">
                {gameState.street}
              </span>
            </div>
          </div>

          {/* Opponents */}
          <div className={styles.opponentsArea}>
            {opponents.map((player, idx) => (
              <div
                key={player.idx}
                className={`${styles.opponentCard} ${
                  player.folded ? styles.foldedPlayer : ''
                } ${player.idx === gameState.currentPlayerIdx ? styles.activePlayer : ''}`}
              >
                <div className={`bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-2 border-2 ${
                  player.idx === gameState.currentPlayerIdx 
                    ? 'border-green-500 shadow-green-500/50' 
                    : 'border-gray-700'
                } shadow-lg transition-all`}>
                  {/* Player Info */}
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <p className="text-white font-bold text-xs">{player.name}</p>
                      <p className="text-yellow-400 text-xs">{player.position}</p>
                    </div>
                    {player.idx === gameState.currentPlayerIdx && (
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    )}
                  </div>

                  {/* Stack */}
                  <div className="bg-gray-950 rounded px-2 py-1 mb-1">
                    <p className="text-yellow-400 font-bold text-sm text-center">
                      ${player.stack}
                    </p>
                  </div>

                  {/* Bet */}
                  {player.bet > 0 && !player.folded && (
                    <div className="bg-blue-900 bg-opacity-50 rounded px-2 py-0.5">
                      <p className="text-blue-300 text-xs text-center">
                        Bet: ${player.bet}
                      </p>
                    </div>
                  )}

                  {/* Folded Status */}
                  {player.folded && (
                    <div className="bg-red-900 bg-opacity-50 rounded px-2 py-0.5">
                      <p className="text-red-400 text-xs font-bold text-center">
                        FOLDED
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Hero Section (Bottom) */}
        {hero && (
          <div className={styles.heroSection}>
            <div className="bg-gradient-to-br from-blue-900 to-blue-950 rounded-xl p-2 border-3 border-blue-500 shadow-2xl shadow-blue-500/30">
              {/* Hero Header & Stack */}
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-blue-300 text-xs font-semibold">{hero.name} ({hero.position})</p>
                <p className="text-yellow-400 font-bold text-lg">${hero.stack}</p>
              </div>

              {/* Hero Cards */}
              {hero.holeCards && hero.holeCards.length === 2 && (
                <div className="mb-1.5">
                  <div className="flex gap-2 justify-center">
                    {hero.holeCards.map((card, idx) => (
                      <div key={idx} className="transform hover:scale-105 transition-transform">
                        <Card card={card} size="md" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hero Bet */}
              {hero.bet > 0 && !hero.folded && (
                <div className="mb-1.5 bg-yellow-900 bg-opacity-30 rounded px-2 py-0.5 border border-yellow-600">
                  <p className="text-yellow-300 text-xs font-semibold text-center">
                    Bet: ${hero.bet}
                  </p>
                </div>
              )}

              {/* Action Buttons - Moved to top */}
              <div className="grid grid-cols-3 gap-1.5">
                <button className="bg-red-600 hover:bg-red-700 text-white py-2 px-2 rounded-lg font-bold text-sm transition-colors shadow-lg">
                  FOLD
                </button>
                <button className="bg-green-600 hover:bg-green-700 text-white py-2 px-2 rounded-lg font-bold text-sm transition-colors shadow-lg">
                  CALL
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-2 rounded-lg font-bold text-sm transition-colors shadow-lg">
                  RAISE
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
