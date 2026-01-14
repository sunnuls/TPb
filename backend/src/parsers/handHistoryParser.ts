import { Card, Position, Street, PlayerAction } from '@tpb/shared';
import { logger } from '../utils/logger';

export interface ParsedHand {
  handId: string;
  site: 'pokerstars' | 'gg' | 'generic';
  gameType: 'holdem' | 'omaha';
  stakes: {
    smallBlind: number;
    bigBlind: number;
    ante?: number;
  };
  tableName: string;
  players: Array<{
    name: string;
    position: Position;
    stack: number;
    holeCards?: Card[];
  }>;
  buttonSeat: number;
  actions: PlayerAction[];
  board: {
    flop?: Card[];
    turn?: Card;
    river?: Card;
  };
  pot: number;
  rake?: number;
  timestamp: Date;
}

export class HandHistoryParser {
  /**
   * Parse hand history from text
   */
  parseHandHistory(text: string): ParsedHand {
    // Detect format
    if (text.includes('PokerStars')) {
      return this.parsePokerStars(text);
    } else if (text.includes('GGPoker') || text.includes('GG Poker')) {
      return this.parseGGPoker(text);
    } else {
      return this.parseGeneric(text);
    }
  }

  /**
   * Parse PokerStars hand history
   */
  private parsePokerStars(text: string): ParsedHand {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l);

    // Parse hand ID from first line
    // Example: "PokerStars Hand #123456789: Hold'em No Limit ($0.50/$1.00) - 2024/01/14 20:30:00"
    const handIdMatch = lines[0].match(/Hand #(\d+)/);
    const handId = handIdMatch ? handIdMatch[1] : 'unknown';

    // Parse game type
    const gameTypeMatch = lines[0].match(/(Hold'em|Omaha)/i);
    const gameType = gameTypeMatch?.[1].toLowerCase() === 'omaha' ? 'omaha' : 'holdem';

    // Parse stakes
    const stakesMatch = lines[0].match(/\$([0-9.]+)\/\$([0-9.]+)/);
    const smallBlind = stakesMatch ? parseFloat(stakesMatch[1]) : 0.5;
    const bigBlind = stakesMatch ? parseFloat(stakesMatch[2]) : 1.0;

    // Parse table name
    const tableMatch = lines[1]?.match(/Table '([^']+)'/);
    const tableName = tableMatch ? tableMatch[1] : 'Unknown';

    // Parse button seat
    const buttonMatch = lines[1]?.match(/Seat #(\d+) is the button/);
    const buttonSeat = buttonMatch ? parseInt(buttonMatch[1]) : 1;

    // Parse players
    const players: ParsedHand['players'] = [];
    for (const line of lines) {
      const playerMatch = line.match(/Seat (\d+): (.+) \(\$?([0-9.]+) in chips\)/);
      if (playerMatch) {
        const seat = parseInt(playerMatch[1]);
        const name = playerMatch[2];
        const stack = parseFloat(playerMatch[3]);
        
        // Determine position (simplified)
        const position = this.seatToPosition(seat, buttonSeat, players.length + 1);
        
        players.push({ name, position, stack });
      }
    }

    // Parse hole cards
    for (let i = 0; i < lines.length; i++) {
      const holeMatch = lines[i].match(/Dealt to (.+) \[(.+)\]/);
      if (holeMatch) {
        const playerName = holeMatch[1];
        const cards = holeMatch[2].split(' ').map(c => this.normalizeCard(c));
        const player = players.find(p => p.name === playerName);
        if (player) {
          player.holeCards = cards as Card[];
        }
      }
    }

    // Parse actions
    const actions: PlayerAction[] = [];
    let street: Street = 'preflop';
    let actionIdx = 0;

    for (const line of lines) {
      // Update street
      if (line.includes('*** FLOP ***')) street = 'flop';
      else if (line.includes('*** TURN ***')) street = 'turn';
      else if (line.includes('*** RIVER ***')) street = 'river';

      // Parse action
      const actionMatch = line.match(/^(.+?): (folds|checks|calls|bets|raises|all-in)(?:\s+\$?([0-9.]+))?/);
      if (actionMatch) {
        const playerName = actionMatch[1];
        const action = actionMatch[2] as any;
        const amount = actionMatch[3] ? parseFloat(actionMatch[3]) : 0;
        
        const playerIdx = players.findIndex(p => p.name === playerName);
        if (playerIdx >= 0) {
          actions.push({
            playerIdx,
            action,
            amount,
            timestamp: new Date(),
            street,
            potAtAction: 0,
            stackAtAction: players[playerIdx].stack,
          });
        }
      }
    }

    // Parse board
    const board: ParsedHand['board'] = {};
    
    const flopMatch = text.match(/\*\*\* FLOP \*\*\* \[([^\]]+)\]/);
    if (flopMatch) {
      board.flop = flopMatch[1].split(' ').map(c => this.normalizeCard(c)) as Card[];
    }

    const turnMatch = text.match(/\*\*\* TURN \*\*\* \[[^\]]+\] \[([^\]]+)\]/);
    if (turnMatch) {
      board.turn = this.normalizeCard(turnMatch[1]) as Card;
    }

    const riverMatch = text.match(/\*\*\* RIVER \*\*\* \[[^\]]+\] \[([^\]]+)\]/);
    if (riverMatch) {
      board.river = this.normalizeCard(riverMatch[1]) as Card;
    }

    // Parse pot
    const potMatch = text.match(/Total pot \$?([0-9.]+)/);
    const pot = potMatch ? parseFloat(potMatch[1]) : 0;

    logger.info(`Parsed PokerStars hand ${handId}`);

    return {
      handId,
      site: 'pokerstars',
      gameType,
      stakes: { smallBlind, bigBlind },
      tableName,
      players,
      buttonSeat,
      actions,
      board,
      pot,
      timestamp: new Date(),
    };
  }

  /**
   * Parse GGPoker hand history (similar format to PokerStars)
   */
  private parseGGPoker(text: string): ParsedHand {
    // GGPoker format is similar to PokerStars with minor differences
    return this.parsePokerStars(text.replace('GGPoker', 'PokerStars'));
  }

  /**
   * Parse generic hand history format
   */
  private parseGeneric(text: string): ParsedHand {
    logger.warn('Parsing generic hand history format - results may be incomplete');
    
    // Minimal parsing for generic format
    return {
      handId: `generic_${Date.now()}`,
      site: 'generic',
      gameType: 'holdem',
      stakes: { smallBlind: 0.5, bigBlind: 1.0 },
      tableName: 'Unknown',
      players: [],
      buttonSeat: 1,
      actions: [],
      board: {},
      pot: 0,
      timestamp: new Date(),
    };
  }

  /**
   * Convert seat number to position
   */
  private seatToPosition(seat: number, buttonSeat: number, totalPlayers: number): Position {
    const offset = (seat - buttonSeat + totalPlayers) % totalPlayers;
    
    if (totalPlayers === 2) {
      return offset === 0 ? 'BTN' : 'BB';
    } else if (totalPlayers === 3) {
      if (offset === 0) return 'BTN';
      if (offset === 1) return 'SB';
      return 'BB';
    } else if (totalPlayers === 6) {
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO'];
      return positions[offset];
    } else if (totalPlayers >= 9) {
      const positions: Position[] = ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'];
      return positions[Math.min(offset, 7)];
    }

    return 'BTN';
  }

  /**
   * Normalize card notation (e.g., "Ah" or "AH" -> "Ah")
   */
  private normalizeCard(card: string): string {
    if (card.length !== 2) return card;
    
    const rank = card[0].toUpperCase();
    const suit = card[1].toLowerCase();
    
    return `${rank}${suit}`;
  }

  /**
   * Parse multiple hands from text
   */
  parseMultipleHands(text: string): ParsedHand[] {
    // Split by hand delimiter
    const handTexts = text.split(/(?=PokerStars Hand #|GGPoker Hand #)/);
    
    return handTexts
      .filter(ht => ht.trim().length > 0)
      .map(ht => this.parseHandHistory(ht));
  }

  /**
   * Export hand to JSON
   */
  exportToJSON(hand: ParsedHand): string {
    return JSON.stringify(hand, null, 2);
  }

  /**
   * Import hand from JSON
   */
  importFromJSON(json: string): ParsedHand {
    return JSON.parse(json);
  }
}

