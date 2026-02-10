"""
Configuration Manager - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Save/load accounts
- Save/load ROI configurations
- Persistent storage (JSON)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict

from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig, ROIZone

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration persistence manager.
    
    Features:
    - Save/load accounts to JSON
    - Save/load ROI configs per account
    - Auto-create config directory
    
    ⚠️ EDUCATIONAL NOTE:
        Manages bot configuration persistence.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_dir: Configuration directory (default: config/)
        """
        if config_dir is None:
            config_dir = Path("config")
        
        self.config_dir = Path(config_dir)
        self.accounts_file = self.config_dir / "accounts.json"
        self.roi_dir = self.config_dir / "roi"
        
        # Create directories
        self.config_dir.mkdir(exist_ok=True)
        self.roi_dir.mkdir(exist_ok=True)
        
        logger.info(f"Config manager initialized: {self.config_dir}")
    
    def save_accounts(self, accounts: List[Account]) -> bool:
        """
        Save accounts to file.
        
        Args:
            accounts: List of accounts
        
        Returns:
            True if successful
        """
        try:
            data = {
                'accounts': [acc.to_dict() for acc in accounts],
                'count': len(accounts)
            }
            
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(accounts)} accounts to {self.accounts_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
            return False
    
    def load_accounts(self) -> List[Account]:
        """
        Load accounts from file.
        
        Returns:
            List of accounts (empty if file doesn't exist)
        """
        if not self.accounts_file.exists():
            logger.info("No accounts file found")
            return []
        
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            accounts = [
                Account.from_dict(acc_data)
                for acc_data in data.get('accounts', [])
            ]
            
            logger.info(f"Loaded {len(accounts)} accounts from {self.accounts_file}")
            return accounts
        
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            return []
    
    def save_roi_config(self, account_id: str, roi_config: ROIConfig) -> bool:
        """
        Save ROI configuration for account.
        
        Args:
            account_id: Account ID
            roi_config: ROI configuration
        
        Returns:
            True if successful
        """
        try:
            roi_file = self.roi_dir / f"roi_{account_id}.json"
            
            with open(roi_file, 'w', encoding='utf-8') as f:
                json.dump(roi_config.to_dict(), f, indent=2)
            
            logger.info(f"Saved ROI config for {account_id} to {roi_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save ROI config: {e}")
            return False
    
    def load_roi_config(self, account_id: str) -> Optional[ROIConfig]:
        """
        Load ROI configuration for account.
        
        Args:
            account_id: Account ID
        
        Returns:
            ROI configuration if exists
        """
        roi_file = self.roi_dir / f"roi_{account_id}.json"
        
        if not roi_file.exists():
            logger.info(f"No ROI config found for {account_id}")
            return None
        
        try:
            with open(roi_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            roi_config = ROIConfig.from_dict(data)
            
            logger.info(f"Loaded ROI config for {account_id} from {roi_file}")
            return roi_config
        
        except Exception as e:
            logger.error(f"Failed to load ROI config: {e}")
            return None
    
    def delete_roi_config(self, account_id: str) -> bool:
        """
        Delete ROI configuration for account.
        
        Args:
            account_id: Account ID
        
        Returns:
            True if successful
        """
        roi_file = self.roi_dir / f"roi_{account_id}.json"
        
        if not roi_file.exists():
            return True
        
        try:
            roi_file.unlink()
            logger.info(f"Deleted ROI config for {account_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete ROI config: {e}")
            return False
    
    def get_all_roi_configs(self) -> Dict[str, ROIConfig]:
        """
        Get all ROI configurations.
        
        Returns:
            Dict of account_id -> ROIConfig
        """
        configs = {}
        
        for roi_file in self.roi_dir.glob("roi_*.json"):
            # Extract account_id from filename
            account_id = roi_file.stem.replace("roi_", "")
            
            roi_config = self.load_roi_config(account_id)
            if roi_config:
                configs[account_id] = roi_config
        
        logger.info(f"Loaded {len(configs)} ROI configs")
        return configs


# Educational example
if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("Config Manager - Educational Research")
    print("=" * 60)
    print()
    
    # Create manager
    manager = ConfigManager(Path("config_test"))
    
    print(f"Config manager:")
    print(f"  Config dir: {manager.config_dir}")
    print(f"  Accounts file: {manager.accounts_file}")
    print(f"  ROI dir: {manager.roi_dir}")
    print()
    
    # Create test accounts
    accounts = [
        Account(nickname="TestBot001", room="pokerstars"),
        Account(nickname="TestBot002", room="ignition")
    ]
    
    print(f"Saving {len(accounts)} accounts...")
    success = manager.save_accounts(accounts)
    print(f"  Success: {success}")
    print()
    
    # Load accounts
    print("Loading accounts...")
    loaded = manager.load_accounts()
    print(f"  Loaded: {len(loaded)} accounts")
    for acc in loaded:
        print(f"    - {acc.nickname} ({acc.room})")
    print()
    
    # Create ROI config
    from launcher.models.roi_config import ROIZone
    
    roi_config = ROIConfig(account_id=accounts[0].account_id)
    roi_config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
    roi_config.configured_at = time.time()
    
    print(f"Saving ROI config for {accounts[0].nickname}...")
    success = manager.save_roi_config(accounts[0].account_id, roi_config)
    print(f"  Success: {success}")
    print()
    
    # Load ROI config
    print("Loading ROI config...")
    loaded_roi = manager.load_roi_config(accounts[0].account_id)
    print(f"  Loaded: {len(loaded_roi.zones) if loaded_roi else 0} zones")
    if loaded_roi:
        for name, zone in loaded_roi.zones.items():
            print(f"    - {name}: {zone.to_tuple()}")
    print()
    
    # Cleanup
    print("Cleaning up test files...")
    manager.delete_roi_config(accounts[0].account_id)
    manager.accounts_file.unlink(missing_ok=True)
    manager.roi_dir.rmdir()
    manager.config_dir.rmdir()
    print("  Done")
    print()
    
    print("=" * 60)
    print("Config manager demonstration complete")
    print("=" * 60)
