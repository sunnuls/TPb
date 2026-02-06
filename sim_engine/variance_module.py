"""
Variance and Adaptive Modeling Module.

This module provides behavioral variance and opponent profiling using
simple neural networks for game theory research (Фаза 3, Шаг 3.2).

Educational Use Only: Designed for studying behavioral adaptation and
opponent modeling in multi-agent research environments.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

# Try to import torch, but make it optional for testing
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Warning: torch not available. Opponent profiling will use fallback.")


class BehaviorType(str, Enum):
    """Agent behavior types for variance (Пункт 1)."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    RANDOM = "random"
    ADAPTIVE = "adaptive"


class AnomalySignal(str, Enum):
    """Anomaly signals in virtual environment (Подпункт 1.1)."""
    NORMAL = "normal"
    EXCESSIVE_ACTIVITY = "excessive_activity"
    PATTERN_DETECTED = "pattern_detected"
    RESOURCE_ANOMALY = "resource_anomaly"
    SESSION_TIMEOUT = "session_timeout"


@dataclass
class SessionState:
    """
    Session state tracking (Подпункт 1.1: session modeling).
    
    Educational Note:
        Sessions are limited to 1-2h cycles to simulate realistic
        research constraints and enable periodic resets.
    """
    session_id: str
    start_time: float = field(default_factory=time.time)
    hands_played: int = 0
    decisions_made: int = 0
    anomaly_count: int = 0
    
    # Session limits (Подпункт 1.1)
    max_duration_seconds: float = 3600.0  # 1 hour default
    max_hands: Optional[int] = None
    
    def elapsed_seconds(self) -> float:
        """Get elapsed session time."""
        return time.time() - self.start_time
    
    def should_reset(self) -> bool:
        """
        Check if session should reset (Подпункт 1.1: 1-2h cycles).
        
        Returns:
            True if session exceeded limits
        """
        # Time limit
        if self.elapsed_seconds() >= self.max_duration_seconds:
            return True
        
        # Hand limit
        if self.max_hands and self.hands_played >= self.max_hands:
            return True
        
        return False


class BehaviorVariance:
    """
    Agent behavior variance generator (Пункт 1).
    
    Educational Note:
        Behavioral variance enables research into heterogeneous multi-agent
        systems and the effects of strategy diversity on outcomes.
    """
    
    def __init__(self, base_behavior: BehaviorType = BehaviorType.BALANCED):
        """
        Initialize behavior variance.
        
        Args:
            base_behavior: Base behavior type
        """
        self.base_behavior = base_behavior
        
        # Variance parameters
        self.aggression_variance = 0.15
        self.risk_tolerance_variance = 0.20
        self.adaptivity_rate = 0.10
    
    def apply_behavioral_variance(
        self,
        base_equity: float,
        context: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Apply behavioral variance to decision (Пункт 1: vary behaviors).
        
        Args:
            base_equity: Base equity estimate
            context: Decision context
        
        Returns:
            (adjusted_equity, metadata) tuple
            
        Educational Note:
            Variance simulates realistic human behavioral diversity,
            crucial for multi-agent game theory research.
        """
        adjusted_equity = base_equity
        metadata = {"variance_applied": self.base_behavior.value}
        
        if self.base_behavior == BehaviorType.CONSERVATIVE:
            # Conservative: underestimate equity, avoid risk
            adjustment = random.uniform(-0.10, -0.02)
            adjusted_equity = max(0.0, base_equity + adjustment)
            metadata["adjustment"] = adjustment
            metadata["risk_factor"] = "low"
        
        elif self.base_behavior == BehaviorType.AGGRESSIVE:
            # Aggressive: overestimate equity, take risks
            adjustment = random.uniform(0.02, 0.15)
            adjusted_equity = min(1.0, base_equity + adjustment)
            metadata["adjustment"] = adjustment
            metadata["risk_factor"] = "high"
        
        elif self.base_behavior == BehaviorType.RANDOM:
            # Random: high variance
            adjustment = random.uniform(-0.15, 0.15)
            adjusted_equity = max(0.0, min(1.0, base_equity + adjustment))
            metadata["adjustment"] = adjustment
            metadata["risk_factor"] = "random"
        
        elif self.base_behavior == BehaviorType.ADAPTIVE:
            # Adaptive: adjust based on context
            opponent_count = context.get("opponent_count", 1)
            pot_odds = context.get("pot_odds", 0.5)
            
            # More opponents = more conservative
            # Better pot odds = more aggressive
            adjustment = (pot_odds - 0.5) * 0.1 - (opponent_count - 2) * 0.05
            adjusted_equity = max(0.0, min(1.0, base_equity + adjustment))
            metadata["adjustment"] = adjustment
            metadata["risk_factor"] = "adaptive"
        
        else:  # BALANCED
            # Balanced: minimal variance
            adjustment = random.uniform(-0.05, 0.05)
            adjusted_equity = max(0.0, min(1.0, base_equity + adjustment))
            metadata["adjustment"] = adjustment
            metadata["risk_factor"] = "balanced"
        
        return adjusted_equity, metadata


class OpponentProfiler:
    """
    Simple NN-based opponent profiler (Пункт 1: simple NN for opponent profiling).
    
    Educational Note:
        Neural network opponent modeling enables research into adaptive
        strategies and learning in multi-agent environments.
    """
    
    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 16,
        output_size: int = 3
    ):
        """
        Initialize opponent profiler.
        
        Args:
            input_size: Number of input features
            hidden_size: Hidden layer size
            output_size: Number of output classes (conservative/balanced/aggressive)
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Create simple neural network if torch available
        if TORCH_AVAILABLE:
            self.model = self._create_model()
            self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            self.criterion = nn.CrossEntropyLoss()
        else:
            self.model = None
            self.optimizer = None
            self.criterion = None
        
        # Fallback: simple heuristics
        self.fallback_profiles: Dict[str, Dict[str, float]] = {}
    
    def _create_model(self) -> Optional[nn.Module]:
        """
        Create simple neural network (Пункт 1).
        
        Returns:
            PyTorch model or None
            
        Educational Note:
            Simple 2-layer network is sufficient for basic opponent
            classification in research simulations.
        """
        if not TORCH_AVAILABLE:
            return None
        
        class SimpleOpponentNet(nn.Module):
            def __init__(self, input_size, hidden_size, output_size):
                super(SimpleOpponentNet, self).__init__()
                self.fc1 = nn.Linear(input_size, hidden_size)
                self.relu = nn.ReLU()
                self.fc2 = nn.Linear(hidden_size, output_size)
            
            def forward(self, x):
                x = self.fc1(x)
                x = self.relu(x)
                x = self.fc2(x)
                return x
        
        return SimpleOpponentNet(self.input_size, self.hidden_size, self.output_size)
    
    def extract_features(
        self,
        opponent_id: str,
        observations: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Extract features from opponent observations.
        
        Args:
            opponent_id: Opponent identifier
            observations: List of observed actions/states
        
        Returns:
            Feature vector (numpy array)
            
        Educational Note:
            Feature extraction converts raw observations into format
            suitable for neural network processing.
        """
        if not observations:
            # Default features
            return np.zeros(self.input_size)
        
        # Calculate statistics from observations
        vpip = sum(1 for obs in observations if obs.get("action") != "fold") / len(observations)
        pfr = sum(1 for obs in observations if obs.get("action") == "raise") / len(observations)
        
        aggression_actions = sum(1 for obs in observations if obs.get("action") in ["bet", "raise"])
        aggression_factor = aggression_actions / max(1, len(observations))
        
        # Average bet sizing
        bet_sizes = [obs.get("sizing", 0.5) for obs in observations if obs.get("sizing")]
        avg_bet_size = np.mean(bet_sizes) if bet_sizes else 0.5
        
        # Build feature vector
        features = np.array([
            vpip,
            pfr,
            aggression_factor,
            avg_bet_size,
            len(observations) / 100.0,  # Normalized sample size
            # Padding to input_size
            *[0.0] * (self.input_size - 5)
        ], dtype=np.float32)
        
        return features[:self.input_size]
    
    def predict_opponent_type(
        self,
        opponent_id: str,
        observations: List[Dict[str, Any]]
    ) -> Tuple[BehaviorType, float]:
        """
        Predict opponent behavior type (Пункт 1: opponent profiling).
        
        Args:
            opponent_id: Opponent identifier
            observations: Observed actions
        
        Returns:
            (behavior_type, confidence) tuple
            
        Educational Note:
            Opponent classification enables adaptive strategy selection
            in multi-agent research simulations.
        """
        # Extract features
        features = self.extract_features(opponent_id, observations)
        
        if self.model is not None and TORCH_AVAILABLE:
            # NN prediction
            self.model.eval()
            with torch.no_grad():
                # Ensure float32 dtype for PyTorch
                features_tensor = torch.from_numpy(features.astype(np.float32)).unsqueeze(0)
                outputs = self.model(features_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_class].item()
            
            # Map to behavior type
            behavior_map = {
                0: BehaviorType.CONSERVATIVE,
                1: BehaviorType.BALANCED,
                2: BehaviorType.AGGRESSIVE
            }
            
            return behavior_map.get(predicted_class, BehaviorType.BALANCED), confidence
        
        else:
            # Fallback: heuristic-based classification
            vpip = features[0]
            aggression = features[2]
            
            if vpip < 0.25 and aggression < 0.3:
                return BehaviorType.CONSERVATIVE, 0.7
            elif vpip > 0.45 or aggression > 0.6:
                return BehaviorType.AGGRESSIVE, 0.7
            else:
                return BehaviorType.BALANCED, 0.6
    
    def train_on_batch(
        self,
        features_batch: np.ndarray,
        labels_batch: np.ndarray
    ) -> float:
        """
        Train on batch of data (Подпункт 1.2: train NN on generated data).
        
        Args:
            features_batch: Feature vectors (N x input_size)
            labels_batch: Labels (N,)
        
        Returns:
            Training loss
            
        Educational Note:
            Online learning from generated data enables adaptive opponent
            modeling during research simulations.
        """
        if self.model is None or not TORCH_AVAILABLE:
            return 0.0
        
        self.model.train()
        
        # Convert to tensors (ensure correct dtypes)
        features_tensor = torch.from_numpy(features_batch.astype(np.float32))
        labels_tensor = torch.from_numpy(labels_batch.astype(np.int64)).long()
        
        # Forward pass
        outputs = self.model(features_tensor)
        loss = self.criterion(outputs, labels_tensor)
        
        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()


class AnomalyDetector:
    """
    Anomaly detection in virtual environment (Подпункт 1.1).
    
    Educational Note:
        Anomaly detection ensures research simulations remain within
        realistic bounds and detects unusual patterns for analysis.
    """
    
    def __init__(self):
        """Initialize anomaly detector."""
        self.activity_threshold = 100  # Actions per hour
        self.pattern_window = 20  # Observations for pattern detection
        self.resource_variance_threshold = 0.3
    
    def detect_anomalies(
        self,
        session: SessionState,
        recent_actions: List[Dict[str, Any]]
    ) -> List[AnomalySignal]:
        """
        Detect anomaly signals (Подпункт 1.1: detect anomaly signals).
        
        Args:
            session: Current session state
            recent_actions: Recent actions for analysis
        
        Returns:
            List of detected anomalies
            
        Educational Note:
            Multi-level anomaly detection ensures research quality by
            identifying unrealistic or problematic agent behaviors.
        """
        anomalies = []
        
        # Check session timeout
        if session.should_reset():
            anomalies.append(AnomalySignal.SESSION_TIMEOUT)
        
        # Check excessive activity
        elapsed_hours = session.elapsed_seconds() / 3600.0
        if elapsed_hours > 0:
            activity_rate = session.decisions_made / elapsed_hours
            
            if activity_rate > self.activity_threshold:
                anomalies.append(AnomalySignal.EXCESSIVE_ACTIVITY)
        
        # Check for repetitive patterns
        if len(recent_actions) >= self.pattern_window:
            action_types = [a.get("action") for a in recent_actions[-self.pattern_window:]]
            
            # Check for excessive repetition
            most_common = max(set(action_types), key=action_types.count)
            repetition_rate = action_types.count(most_common) / len(action_types)
            
            if repetition_rate > 0.8:  # 80% same action
                anomalies.append(AnomalySignal.PATTERN_DETECTED)
        
        # Check resource anomalies
        if recent_actions:
            resource_values = [
                a.get("resource_level", 0.5)
                for a in recent_actions
                if "resource_level" in a
            ]
            
            if resource_values:
                variance = np.var(resource_values)
                if variance > self.resource_variance_threshold:
                    anomalies.append(AnomalySignal.RESOURCE_ANOMALY)
        
        return anomalies if anomalies else [AnomalySignal.NORMAL]


def generate_training_data(
    num_samples: int = 1000,
    validation_split: float = 0.2
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic training data (Подпункт 1.2: train NN on generated data).
    
    Args:
        num_samples: Number of samples to generate
        validation_split: Fraction for validation set
    
    Returns:
        (train_features, train_labels, val_features, val_labels)
        
    Educational Note:
        Synthetic data generation enables training opponent profiling models
        without requiring large amounts of real gameplay data.
    """
    features_list = []
    labels_list = []
    
    for _ in range(num_samples):
        # Generate random behavior type
        behavior_class = random.randint(0, 2)
        
        if behavior_class == 0:  # Conservative
            vpip = random.uniform(0.10, 0.25)
            pfr = random.uniform(0.08, 0.18)
            aggression = random.uniform(0.1, 0.3)
        elif behavior_class == 1:  # Balanced
            vpip = random.uniform(0.20, 0.35)
            pfr = random.uniform(0.15, 0.28)
            aggression = random.uniform(0.3, 0.6)
        else:  # Aggressive
            vpip = random.uniform(0.35, 0.60)
            pfr = random.uniform(0.28, 0.50)
            aggression = random.uniform(0.6, 0.9)
        
        avg_bet_size = random.uniform(0.3, 1.0)
        sample_size = random.uniform(0.1, 1.0)
        
        features = np.array([
            vpip, pfr, aggression, avg_bet_size, sample_size,
            *[random.random() * 0.1 for _ in range(5)]  # Padding
        ], dtype=np.float32)
        
        features_list.append(features)
        labels_list.append(behavior_class)
    
    # Convert to arrays
    all_features = np.array(features_list)
    all_labels = np.array(labels_list)
    
    # Split into train/validation (Подпункт 1.2: add validation sets)
    split_idx = int(num_samples * (1 - validation_split))
    
    # Shuffle
    indices = np.random.permutation(num_samples)
    all_features = all_features[indices]
    all_labels = all_labels[indices]
    
    train_features = all_features[:split_idx]
    train_labels = all_labels[:split_idx]
    val_features = all_features[split_idx:]
    val_labels = all_labels[split_idx:]
    
    return train_features, train_labels, val_features, val_labels


def train_opponent_profiler(
    profiler: OpponentProfiler,
    epochs: int = 10,
    batch_size: int = 32
) -> Dict[str, List[float]]:
    """
    Train opponent profiler (Подпункт 1.2).
    
    Args:
        profiler: OpponentProfiler instance
        epochs: Training epochs
        batch_size: Batch size
    
    Returns:
        Training history (losses)
        
    Educational Note:
        Training loop with validation enables monitoring of model
        performance and prevents overfitting in research simulations.
    """
    if not TORCH_AVAILABLE or profiler.model is None:
        print("Warning: Training skipped (torch not available)")
        return {"train_loss": [], "val_loss": []}
    
    # Generate data
    train_X, train_y, val_X, val_y = generate_training_data(
        num_samples=1000,
        validation_split=0.2
    )
    
    history = {"train_loss": [], "val_loss": []}
    
    for epoch in range(epochs):
        # Training
        epoch_losses = []
        
        for i in range(0, len(train_X), batch_size):
            batch_X = train_X[i:i+batch_size]
            batch_y = train_y[i:i+batch_size]
            
            loss = profiler.train_on_batch(batch_X, batch_y)
            epoch_losses.append(loss)
        
        avg_train_loss = np.mean(epoch_losses)
        history["train_loss"].append(avg_train_loss)
        
        # Validation
        profiler.model.eval()
        with torch.no_grad():
            val_X_tensor = torch.from_numpy(val_X)
            val_y_tensor = torch.from_numpy(val_y).long()
            
            outputs = profiler.model(val_X_tensor)
            val_loss = profiler.criterion(outputs, val_y_tensor).item()
            history["val_loss"].append(val_loss)
        
        print(f"Epoch {epoch+1}/{epochs}: train_loss={avg_train_loss:.4f}, val_loss={val_loss:.4f}")
    
    return history
