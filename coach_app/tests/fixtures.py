"""
Test fixtures: hand histories for parser + API tests.
Keep these as close to real PokerStars format as possible.
"""

PS_CASH_6MAX_FLOP = """\
PokerStars Hand #1234567890:  Hold'em No Limit ($0.50/$1.00 USD) - 2025/12/16 12:00:00 ET
Table 'Alpha' 6-max Seat #3 is the button
Seat 1: Hero (100 in chips)
Seat 2: Villain1 (100 in chips)
Seat 3: Villain2 (100 in chips)
Seat 4: Villain3 (100 in chips)
Seat 5: Villain4 (100 in chips)
Seat 6: Villain5 (100 in chips)
Villain4: posts small blind $0.50
Villain5: posts big blind $1.00
*** HOLE CARDS ***
Dealt to Hero [Ah Ks]
Hero: raises $2.00 to $3.00
Villain2: folds
Villain3: calls $3.00
Villain4: folds
Villain5: folds
Villain1: folds
*** FLOP *** [Ad 7c 2s]
Hero: bets $4.00
Villain3: calls $4.00
*** TURN *** [Ad 7c 2s] [Td]
Hero: checks
Villain3: bets $8.00
Hero: calls $8.00
"""


PS_TOURNAMENT_ANTES_MULTI_STREETS = """\
PokerStars Hand #9876543210: Tournament #555555555, $10+$1 Hold'em No Limit - Level II (15/30) - 2025/12/16 13:00:00 ET
Table 'Beta' 6-max Seat #6 is the button
Seat 1: Hero (1500 in chips)
Seat 2: VillainA (1500 in chips)
Seat 3: VillainB (1500 in chips)
Seat 4: VillainC (1500 in chips)
Seat 5: VillainD (1500 in chips)
Seat 6: VillainE (1500 in chips)
Hero: posts the ante 5
VillainA: posts the ante 5
VillainB: posts the ante 5
VillainC: posts the ante 5
VillainD: posts the ante 5
VillainE: posts the ante 5
VillainD: posts small blind 15
VillainE: posts big blind 30
*** HOLE CARDS ***
Dealt to Hero [9h 9d]
Hero: raises 60 to 90
VillainA: calls 90
VillainB: folds
VillainC: folds
VillainD: folds
VillainE: calls 60
*** FLOP *** [2h 7h 9s]
VillainE: checks
Hero: bets 180
VillainA: calls 180
VillainE: folds
*** TURN *** [2h 7h 9s] [Kh]
Hero: bets 360
VillainA: calls 360
*** RIVER *** [2h 7h 9s Kh] [2d]
Hero: bets 720
VillainA: folds
Uncalled bet (720) returned to Hero
"""


# Minimal HH that has cards but no sizes -> pot_odds should be absent and explanation must not mention it.
MINIMAL_HH_NO_SIZES = """\
PokerStars Hand #111:  Hold'em No Limit ($0.50/$1.00 USD) - 2025/12/16 14:00:00 ET
Table 'Gamma' 6-max Seat #1 is the button
Seat 1: Hero (100 in chips)
Seat 2: Villain (100 in chips)
*** HOLE CARDS ***
Dealt to Hero [Qh Jh]
*** FLOP *** [Ah 7d 2c]
"""
