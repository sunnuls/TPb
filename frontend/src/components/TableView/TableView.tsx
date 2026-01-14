import { GameState } from '@tpb/shared';
import { Card } from '../Common/Card';
import styles from './TableView.module.css';

interface TableViewProps {
  gameState: GameState;
}

export function TableView({ gameState }: TableViewProps) {
  return (
    <div className={styles.tableView}>
      <div className="poker-table rounded-[200px] p-8 relative">
        {/* Pot */}
        <div className={styles.pot}>
          <div className="bg-gray-800 px-4 py-2 rounded-lg">
            <p className="text-poker-gold font-bold text-xl">
              ${gameState.pot}
            </p>
            <p className="text-gray-400 text-sm">Pot</p>
          </div>
        </div>

        {/* Community Cards */}
        <div className={styles.communityCards}>
          {gameState.board.length > 0 ? (
            <div className="flex gap-2">
              {gameState.board.map((card, idx) => (
                <Card key={idx} card={card} />
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Waiting for cards...</p>
          )}
        </div>

        {/* Street Indicator */}
        <div className={styles.streetIndicator}>
          <span className="bg-poker-gold text-gray-900 px-3 py-1 rounded-full font-bold text-sm uppercase">
            {gameState.street}
          </span>
        </div>

        {/* Players */}
        <div className={styles.players}>
          {gameState.players.map((player, idx) => (
            <div
              key={idx}
              className={`${styles.playerSlot} ${
                player.folded ? styles.folded : ''
              } ${idx === gameState.currentPlayerIdx ? styles.active : ''}`}
            >
              <div className="bg-gray-800 rounded-lg p-3 border-2 border-gray-700">
                <p className="text-white font-semibold">{player.name}</p>
                <p className="text-poker-gold text-sm">${player.stack}</p>
                <p className="text-gray-400 text-xs">{player.position}</p>
                {player.folded && (
                  <p className="text-red-500 text-xs mt-1">FOLDED</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

