"""
A/B Testing Framework — Phase 3 of settings.md.

Compares bot profiles by simulating sessions and collecting
performance metrics.  Answers questions like:
  "Does *shark* outperform *tag* over 500 hands?"

Features:
  - Run simulated sessions per profile
  - Collect key metrics (profit, win-rate, aggression factor, VPIP)
  - Statistical comparison (mean, std, confidence interval)
  - Multi-profile tournament (rank all profiles)
  - Human-readable report generation

Usage::

    ab = ABTestRunner()
    ab.add_profile("shark")
    ab.add_profile("tag")
    results = ab.run(hands_per_session=200, sessions=50)
    report = ab.report()

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from launcher.bot_profile_manager import BotProfileManager, BotProfile
from launcher.bot_settings import BotSettings

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class SessionMetrics:
    """Metrics from a single simulated session.

    Attributes:
        profile_name:     which profile ran
        hands_played:     number of hands
        net_profit_bb:    profit in big blinds
        vpip:             voluntarily put $ in pot (0–1)
        pfr:              preflop raise rate (0–1)
        aggression_factor: (bets+raises) / calls
        win_rate_bb100:   bb/100 hands
        showdown_wins:    fraction of showdowns won
        duration_s:       simulated session wall time (seconds)
    """
    profile_name: str = ""
    hands_played: int = 0
    net_profit_bb: float = 0.0
    vpip: float = 0.0
    pfr: float = 0.0
    aggression_factor: float = 0.0
    win_rate_bb100: float = 0.0
    showdown_wins: float = 0.0
    duration_s: float = 0.0


@dataclass
class ProfileStats:
    """Aggregated statistics for one profile across many sessions.

    Attributes:
        profile_name:   profile identifier
        sessions:       list of per-session metrics
        mean_profit:    mean net profit (bb)
        std_profit:     standard deviation of profit
        mean_wr:        mean win-rate (bb/100)
        std_wr:         std of win-rate
        mean_vpip:      mean VPIP
        mean_pfr:       mean PFR
        mean_af:        mean aggression factor
        ci_95_low:      95% confidence interval lower bound (profit)
        ci_95_high:     95% CI upper bound
    """
    profile_name: str = ""
    sessions: List[SessionMetrics] = field(default_factory=list)
    mean_profit: float = 0.0
    std_profit: float = 0.0
    mean_wr: float = 0.0
    std_wr: float = 0.0
    mean_vpip: float = 0.0
    mean_pfr: float = 0.0
    mean_af: float = 0.0
    ci_95_low: float = 0.0
    ci_95_high: float = 0.0


@dataclass
class ABTestResult:
    """Complete A/B test result.

    Attributes:
        profiles:       per-profile aggregated stats
        ranking:        profile names sorted best→worst by mean win-rate
        best_profile:   name of the top-ranked profile
        total_hands:    total hands simulated across all profiles
        total_sessions: total sessions run
        elapsed_s:      wall-clock time of the test
    """
    profiles: Dict[str, ProfileStats] = field(default_factory=dict)
    ranking: List[str] = field(default_factory=list)
    best_profile: str = ""
    total_hands: int = 0
    total_sessions: int = 0
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# Session simulator
# ---------------------------------------------------------------------------


class SessionSimulator:
    """Simulate a poker session for a given profile.

    Uses profile parameters to produce realistic (but synthetic)
    session outcomes.  This is NOT a full poker engine — it models
    the *distribution* of outcomes based on profile aggression,
    equity thresholds, and bet sizing.

    The simulation uses a simplified model:
      - Each hand: decide action based on equity thresholds + random equity
      - Profit/loss modelled as a function of action taken and bet sizing
      - VPIP/PFR/AF are derived from action frequencies
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def simulate(
        self,
        profile: BotProfile,
        hands: int = 200,
    ) -> SessionMetrics:
        """Run a single simulated session.

        Args:
            profile: the bot profile to simulate
            hands:   number of hands to play

        Returns:
            ``SessionMetrics`` with all stats filled.
        """
        t0 = time.monotonic()

        # Track action counters
        total_vpip = 0     # hands where we voluntarily put $ in
        total_pfr = 0      # hands where we raised preflop
        total_bets = 0
        total_raises = 0
        total_calls = 0
        total_folds = 0
        showdown_count = 0
        showdown_wins = 0
        net_profit = 0.0

        eq = profile.equity
        bs = profile.bet_sizing

        for _ in range(hands):
            # Random hand equity (0–1)
            hand_equity = self._rng.random()

            # --- Preflop decision ---
            if hand_equity >= eq.preflop_open:
                # Open raise
                total_vpip += 1
                total_pfr += 1
                total_raises += 1
                preflop_invested = bs.open_raise_bb
            elif hand_equity >= eq.preflop_call:
                # Call
                total_vpip += 1
                total_calls += 1
                preflop_invested = 1.0  # 1 BB call
            else:
                # Fold
                total_folds += 1
                continue  # next hand, no further action

            # --- Postflop (simplified) ---
            flop_equity = self._rng.random()
            postflop_invested = 0.0

            if flop_equity >= eq.postflop_bet:
                # Bet (c-bet)
                total_bets += 1
                pot_size = preflop_invested * 2 + 1  # rough pot
                postflop_invested += pot_size * bs.cbet_pot_fraction
            elif flop_equity >= eq.postflop_call:
                # Call opponent bet
                total_calls += 1
                pot_size = preflop_invested * 2 + 1
                postflop_invested += pot_size * 0.5  # facing half-pot bet
            else:
                # Fold postflop
                net_profit -= preflop_invested
                continue

            # --- Turn/River (simplified) ---
            river_equity = self._rng.random()
            total_invested = preflop_invested + postflop_invested

            if river_equity >= eq.postflop_bet:
                # Bet turn/river
                total_bets += 1
                pot_now = total_invested * 2
                total_invested += pot_now * bs.turn_pot_fraction
            elif river_equity >= eq.postflop_call:
                total_calls += 1
                pot_now = total_invested * 2
                total_invested += pot_now * 0.4

            # --- Showdown ---
            showdown_count += 1
            # Win probability influenced by equity + aggression bonus
            aggr_bonus = profile.aggression_level * 0.008  # slight edge
            win_prob = (hand_equity + flop_equity + river_equity) / 3 + aggr_bonus
            win_prob = max(0.0, min(1.0, win_prob))

            if self._rng.random() < win_prob:
                # Win: profit = opponent's investment (roughly matches ours)
                pot_total = total_invested * 2
                net_profit += pot_total - total_invested  # net = pot - our investment
                showdown_wins += 1
            else:
                # Lose
                net_profit -= total_invested

            # River bluff (occasionally, if equity was low but we got here)
            if river_equity < eq.river_bluff and self._rng.random() < 0.3:
                total_bets += 1  # bluff bet counted

        # --- Compute metrics ---
        total_actions = total_bets + total_raises + total_calls
        vpip = total_vpip / hands if hands > 0 else 0
        pfr = total_pfr / hands if hands > 0 else 0
        af = ((total_bets + total_raises) / max(1, total_calls))
        wr_bb100 = (net_profit / max(1, hands)) * 100
        sd_win_rate = showdown_wins / max(1, showdown_count)

        elapsed = time.monotonic() - t0

        return SessionMetrics(
            profile_name=profile.name,
            hands_played=hands,
            net_profit_bb=net_profit,
            vpip=vpip,
            pfr=pfr,
            aggression_factor=af,
            win_rate_bb100=wr_bb100,
            showdown_wins=sd_win_rate,
            duration_s=elapsed,
        )


# ---------------------------------------------------------------------------
# A/B Test Runner
# ---------------------------------------------------------------------------


class ABTestRunner:
    """Run A/B tests comparing bot profiles.

    Parameters:
        profile_manager:  profile source
        seed:             RNG seed for reproducibility
    """

    def __init__(
        self,
        profile_manager: Optional[BotProfileManager] = None,
        seed: Optional[int] = None,
    ):
        self._pm = profile_manager or BotProfileManager()
        self._seed = seed
        self._profiles: List[str] = []
        self._result: Optional[ABTestResult] = None

    def add_profile(self, name: str) -> bool:
        """Add a profile to the test."""
        if self._pm.get_profile(name) is None:
            return False
        if name not in self._profiles:
            self._profiles.append(name)
        return True

    def add_all_profiles(self) -> int:
        """Add all available profiles."""
        added = 0
        for name in self._pm.list_profiles():
            if self.add_profile(name):
                added += 1
        return added

    @property
    def profile_names(self) -> List[str]:
        return list(self._profiles)

    def run(
        self,
        hands_per_session: int = 200,
        sessions_per_profile: int = 50,
    ) -> ABTestResult:
        """Execute the A/B test.

        Args:
            hands_per_session:     hands per simulated session
            sessions_per_profile:  number of sessions per profile

        Returns:
            ``ABTestResult`` with all metrics and ranking.
        """
        t0 = time.monotonic()
        sim = SessionSimulator(seed=self._seed)

        all_stats: Dict[str, ProfileStats] = {}
        total_hands = 0
        total_sessions = 0

        for name in self._profiles:
            profile = self._pm.get_profile(name)
            if profile is None:
                continue

            sessions: List[SessionMetrics] = []
            for i in range(sessions_per_profile):
                # Vary seed per session for diversity
                if self._seed is not None:
                    sim = SessionSimulator(seed=self._seed + i + hash(name) % 10000)
                m = sim.simulate(profile, hands=hands_per_session)
                sessions.append(m)
                total_hands += m.hands_played
                total_sessions += 1

            stats = self._aggregate(name, sessions)
            all_stats[name] = stats

        # Rank by mean win-rate (descending)
        ranking = sorted(
            all_stats.keys(),
            key=lambda n: all_stats[n].mean_wr,
            reverse=True,
        )

        elapsed = time.monotonic() - t0

        self._result = ABTestResult(
            profiles=all_stats,
            ranking=ranking,
            best_profile=ranking[0] if ranking else "",
            total_hands=total_hands,
            total_sessions=total_sessions,
            elapsed_s=elapsed,
        )
        return self._result

    @property
    def result(self) -> Optional[ABTestResult]:
        return self._result

    # -- Report generation ---------------------------------------------------

    def report(self) -> str:
        """Generate a human-readable text report of the last run."""
        r = self._result
        if r is None:
            return "No test has been run yet."

        lines = [
            "=" * 65,
            "  A/B TEST REPORT — Profile Comparison",
            "=" * 65,
            f"  Profiles tested: {len(r.profiles)}",
            f"  Sessions/profile: {r.total_sessions // max(1, len(r.profiles))}",
            f"  Total hands:     {r.total_hands:,}",
            f"  Elapsed:         {r.elapsed_s:.2f}s",
            "",
            "-" * 65,
            f"  {'Rank':<5} {'Profile':<12} {'WR bb/100':>10} {'±95%CI':>10} "
            f"{'VPIP':>7} {'PFR':>7} {'AF':>6}",
            "-" * 65,
        ]

        for rank, name in enumerate(r.ranking, 1):
            s = r.profiles[name]
            ci_half = (s.ci_95_high - s.ci_95_low) / 2
            lines.append(
                f"  {rank:<5} {name:<12} {s.mean_wr:>+10.2f} {ci_half:>10.2f} "
                f"{s.mean_vpip:>6.1%} {s.mean_pfr:>6.1%} {s.mean_af:>6.2f}"
            )

        lines.append("-" * 65)

        # Best profile detail
        if r.best_profile:
            best = r.profiles[r.best_profile]
            lines.extend([
                "",
                f"  BEST: {r.best_profile}",
                f"    Mean profit/session: {best.mean_profit:+.1f} bb",
                f"    Std profit:          {best.std_profit:.1f} bb",
                f"    Win-rate:            {best.mean_wr:+.2f} bb/100",
                f"    95% CI:              [{best.ci_95_low:+.2f}, {best.ci_95_high:+.2f}]",
                f"    Showdown win:        {best.sessions[0].showdown_wins:.1%}"
                if best.sessions else "",
            ])

        lines.extend(["", "=" * 65])
        return "\n".join(lines)

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _aggregate(name: str, sessions: List[SessionMetrics]) -> ProfileStats:
        """Compute aggregated stats from session list."""
        if not sessions:
            return ProfileStats(profile_name=name)

        profits = [s.net_profit_bb for s in sessions]
        wrs = [s.win_rate_bb100 for s in sessions]
        vpips = [s.vpip for s in sessions]
        pfrs = [s.pfr for s in sessions]
        afs = [s.aggression_factor for s in sessions]

        mean_p = statistics.mean(profits)
        std_p = statistics.stdev(profits) if len(profits) > 1 else 0.0
        mean_wr = statistics.mean(wrs)
        std_wr = statistics.stdev(wrs) if len(wrs) > 1 else 0.0

        # 95% confidence interval (t ≈ 1.96 for large n)
        n = len(sessions)
        se = std_p / math.sqrt(n) if n > 0 else 0
        ci_low = mean_p - 1.96 * se
        ci_high = mean_p + 1.96 * se

        return ProfileStats(
            profile_name=name,
            sessions=sessions,
            mean_profit=mean_p,
            std_profit=std_p,
            mean_wr=mean_wr,
            std_wr=std_wr,
            mean_vpip=statistics.mean(vpips),
            mean_pfr=statistics.mean(pfrs),
            mean_af=statistics.mean(afs),
            ci_95_low=ci_low,
            ci_95_high=ci_high,
        )
