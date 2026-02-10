"""
Tests for Card Sharing (Roadmap5 Phase 2).

⚠️ EDUCATIONAL RESEARCH ONLY - Tests COLLUSION functionality.
"""

import pytest

from hive.card_sharing import CardShare, CardSharingSystem, TeamCardKnowledge


class TestCardShare:
    """Test card share dataclass."""
    
    def test_creation(self):
        """Test card share creation."""
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        
        assert share.bot_id == "bot_1"
        assert share.team_id == "team_1"
        assert share.hole_cards == ["As", "Kh"]
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        
        data = share.to_dict()
        
        assert data['bot_id'] == "bot_1"
        assert data['hole_cards'] == ["As", "Kh"]
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'bot_id': "bot_1",
            'team_id': "team_1",
            'table_id': "table_1",
            'hole_cards': ["As", "Kh"],
            'hand_id': "hand_001"
        }
        
        share = CardShare.from_dict(data)
        
        assert share.bot_id == "bot_1"
        assert share.hole_cards == ["As", "Kh"]
    
    def test_get_hash(self):
        """Test hash generation."""
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        
        hash_val = share.get_hash()
        
        assert isinstance(hash_val, str)
        assert len(hash_val) == 16


class TestTeamCardKnowledge:
    """Test team card knowledge."""
    
    def test_creation(self):
        """Test knowledge creation."""
        knowledge = TeamCardKnowledge(
            team_id="team_1",
            table_id="table_1",
            hand_id="hand_001"
        )
        
        assert knowledge.team_id == "team_1"
        assert len(knowledge.shares) == 0
        assert len(knowledge.known_cards) == 0
    
    def test_add_share(self):
        """Test adding share."""
        knowledge = TeamCardKnowledge(
            team_id="team_1",
            table_id="table_1",
            hand_id="hand_001"
        )
        
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"]
        )
        
        added = knowledge.add_share(share)
        
        assert added is True
        assert len(knowledge.shares) == 1
        assert len(knowledge.known_cards) == 2
    
    def test_is_complete(self):
        """Test completion check."""
        knowledge = TeamCardKnowledge(
            team_id="team_1",
            table_id="table_1",
            hand_id="hand_001"
        )
        
        # Not complete initially
        assert knowledge.is_complete() is False
        
        # Add 3 shares
        for i in range(3):
            share = CardShare(
                bot_id=f"bot_{i}",
                team_id="team_1",
                table_id="table_1",
                hole_cards=[f"A{i}", f"K{i}"]
            )
            knowledge.add_share(share)
        
        # Now complete
        assert knowledge.is_complete() is True
    
    def test_get_bot_cards(self):
        """Test getting cards for specific bot."""
        knowledge = TeamCardKnowledge(
            team_id="team_1",
            table_id="table_1",
            hand_id="hand_001"
        )
        
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"]
        )
        knowledge.add_share(share)
        
        cards = knowledge.get_bot_cards("bot_1")
        
        assert cards == ["As", "Kh"]
        
        # Unknown bot
        assert knowledge.get_bot_cards("bot_999") is None


class TestCardSharingSystem:
    """Test card sharing system."""
    
    def test_initialization(self):
        """Test system initialization."""
        system = CardSharingSystem(enable_logging=True)
        
        assert system.enable_logging is True
        assert system.shares_received == 0
        assert system.shares_sent == 0
    
    def test_create_share(self):
        """Test share creation."""
        system = CardSharingSystem()
        
        share = system.create_share(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        
        assert share.bot_id == "bot_1"
        assert share.hole_cards == ["As", "Kh"]
        assert system.shares_sent == 1
    
    def test_receive_share(self):
        """Test receiving share."""
        system = CardSharingSystem()
        
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        
        received = system.receive_share(share)
        
        assert received is True
        assert system.shares_received == 1
        assert len(system.share_history) == 1
    
    def test_get_team_knowledge(self):
        """Test getting team knowledge."""
        system = CardSharingSystem()
        
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        system.receive_share(share)
        
        knowledge = system.get_team_knowledge("team_1", "table_1", "hand_001")
        
        assert knowledge is not None
        assert knowledge.team_id == "team_1"
    
    def test_get_known_cards(self):
        """Test getting known cards."""
        system = CardSharingSystem()
        
        # Add multiple shares
        for i in range(3):
            share = CardShare(
                bot_id=f"bot_{i}",
                team_id="team_1",
                table_id="table_1",
                hole_cards=[f"A{i}", f"K{i}"],
                hand_id="hand_001"
            )
            system.receive_share(share)
        
        known_cards = system.get_known_cards("team_1", "table_1", "hand_001")
        
        assert len(known_cards) == 6  # 3 bots * 2 cards
    
    def test_clear_hand(self):
        """Test clearing hand knowledge."""
        system = CardSharingSystem()
        
        share = CardShare(
            bot_id="bot_1",
            team_id="team_1",
            table_id="table_1",
            hole_cards=["As", "Kh"],
            hand_id="hand_001"
        )
        system.receive_share(share)
        
        # Clear
        system.clear_hand("team_1", "table_1", "hand_001")
        
        # Should be gone
        knowledge = system.get_team_knowledge("team_1", "table_1", "hand_001")
        assert knowledge is None
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        system = CardSharingSystem()
        
        # Add some shares
        for i in range(2):
            share = system.create_share(
                bot_id=f"bot_{i}",
                team_id="team_1",
                table_id="table_1",
                hole_cards=[f"A{i}", f"K{i}"],
                hand_id="hand_001"
            )
            system.receive_share(share)
        
        stats = system.get_statistics()
        
        assert stats['shares_sent'] == 2
        assert stats['shares_received'] == 2
        assert stats['active_teams'] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
