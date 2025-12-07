# services/analysis_service.py

"""
Analysis Service for Spot-Futures Arbitrage Strategy
Calculates spreads, Z-scores, convergence indicators, and generates signals
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import deque

from models.trading_models import SpotFuturesSpread, ArbitrageSignal, LiveQuote
from config.settings import SignalType

logger = logging.getLogger(__name__)


class ArbitrageAnalysisService:
    """Analysis service for arbitrage strategy"""

    def __init__(self, websocket_service):
        self.websocket_service = websocket_service

        # Historical spread data for statistical analysis
        self.spread_history: Dict[str, deque] = {}
        self.max_history_length = 100  # Keep last 100 spread observations

        # Z-score parameters
        self.zscore_window = 20  # Window for Z-score calculation

    def calculate_spread_statistics(self, pair_name: str, current_spread: SpotFuturesSpread) -> Dict:
        """Calculate statistical measures for spread"""
        try:
            # Initialize history if needed
            if pair_name not in self.spread_history:
                self.spread_history[pair_name] = deque(maxlen=self.max_history_length)

            # Add current spread
            self.spread_history[pair_name].append(current_spread.spread_pct)

            # Get historical data
            history = list(self.spread_history[pair_name])

            if len(history) < 10:  # Need minimum data
                return {
                    'mean': current_spread.spread_pct,
                    'std': 0.0,
                    'zscore': 0.0,
                    'min': current_spread.spread_pct,
                    'max': current_spread.spread_pct
                }

            # Calculate statistics
            mean = np.mean(history[-self.zscore_window:])
            std = np.std(history[-self.zscore_window:])
            zscore = (current_spread.spread_pct - mean) / std if std > 0 else 0.0

            return {
                'mean': mean,
                'std': std,
                'zscore': zscore,
                'min': min(history),
                'max': max(history),
                'percentile_25': np.percentile(history, 25),
                'percentile_75': np.percentile(history, 75)
            }

        except Exception as e:
            logger.error(f"Error calculating spread statistics for {pair_name}: {e}")
            return {}

    def calculate_fair_value_premium(self, days_to_expiry: int, risk_free_rate: float = 0.05) -> float:
        """Calculate fair value premium based on cost of carry"""
        try:
            # Fair value premium = (Risk-free rate × Days to expiry) / 365
            # Expressed as percentage
            premium = (risk_free_rate * days_to_expiry) / 365 * 100
            return premium
        except Exception as e:
            logger.error(f"Error calculating fair value premium: {e}")
            return 0.0

    def detect_mispricing(self, current_spread: SpotFuturesSpread,
                          fair_value_premium: float,
                          stats: Dict,
                          min_zscore: float = 1.5) -> Tuple[bool, SignalType, float]:
        """
        Detect mispricing opportunity

        Returns:
            (is_mispriced, signal_type, confidence)
        """
        try:
            zscore = stats.get('zscore', 0.0)
            spread_pct = current_spread.spread_pct

            # Futures overpriced (spread too high) -> Long spot, Short futures
            if zscore > min_zscore and spread_pct > fair_value_premium:
                confidence = min(abs(zscore) / 3.0, 1.0)  # Normalize to 0-1
                return True, SignalType.LONG_SPOT_SHORT_FUTURES, confidence

            # Futures underpriced (spread too low) -> Short spot, Long futures
            elif zscore < -min_zscore and spread_pct < fair_value_premium:
                confidence = min(abs(zscore) / 3.0, 1.0)
                return True, SignalType.SHORT_SPOT_LONG_FUTURES, confidence

            return False, None, 0.0

        except Exception as e:
            logger.error(f"Error detecting mispricing: {e}")
            return False, None, 0.0

    def calculate_convergence_probability(self, spread_history: deque) -> float:
        """Calculate probability of spread convergence"""
        try:
            if len(spread_history) < 10:
                return 0.5  # Neutral

            recent_spreads = list(spread_history)[-10:]

            # Check if spread is narrowing
            first_half = np.mean(recent_spreads[:5])
            second_half = np.mean(recent_spreads[5:])

            if abs(second_half) < abs(first_half):
                # Spread is converging
                convergence_rate = (abs(first_half) - abs(second_half)) / abs(first_half) if first_half != 0 else 0
                return min(0.5 + convergence_rate, 1.0)
            else:
                # Spread is diverging
                divergence_rate = (abs(second_half) - abs(first_half)) / abs(first_half) if first_half != 0 else 0
                return max(0.5 - divergence_rate, 0.0)

        except Exception as e:
            logger.error(f"Error calculating convergence probability: {e}")
            return 0.5

    def generate_arbitrage_signal(self, pair_name: str, pair_info: Dict,
                                  min_confidence: float = 0.7) -> Optional[ArbitrageSignal]:
        """Generate arbitrage trading signal"""
        try:
            # Get current spread
            current_spread = self.websocket_service.get_spread(pair_name)
            if not current_spread:
                return None

            # Calculate statistics
            stats = self.calculate_spread_statistics(pair_name, current_spread)

            # Calculate fair value
            days_to_expiry = pair_info.get('days_to_expiry', 30)
            fair_value_premium = self.calculate_fair_value_premium(days_to_expiry)

            # Detect mispricing
            is_mispriced, signal_type, base_confidence = self.detect_mispricing(
                current_spread, fair_value_premium, stats
            )

            if not is_mispriced:
                return None

            # Calculate comprehensive confidence score
            confidence = self._calculate_signal_confidence(
                current_spread, stats, base_confidence
            )

            if confidence < min_confidence:
                return None

            # Create signal
            from models.trading_models import ArbitrageSignal

            signal = ArbitrageSignal(
                pair_name=pair_name,
                spot_symbol=current_spread.spot_symbol,
                futures_symbol=current_spread.futures_symbol,
                signal_type=signal_type,
                spot_price=current_spread.spot_price,
                futures_price=current_spread.futures_price,
                spread_value=current_spread.spread_value,
                spread_pct=current_spread.spread_pct,
                fair_value_premium=fair_value_premium,
                mispricing=current_spread.spread_pct - fair_value_premium,
                zscore=stats.get('zscore', 0.0),
                confidence=confidence,
                volume_ratio=current_spread.volume_ratio,
                timestamp=datetime.now()
            )

            logger.info(f"Arbitrage signal generated: {pair_name} {signal_type.value} "
                        f"Confidence: {confidence:.2f} Z-score: {stats.get('zscore', 0):.2f}")

            return signal

        except Exception as e:
            logger.error(f"Error generating arbitrage signal for {pair_name}: {e}")
            return None

    def _calculate_signal_confidence(self, spread: SpotFuturesSpread,
                                     stats: Dict, base_confidence: float) -> float:
        """Calculate comprehensive confidence score"""
        try:
            confidence_factors = []

            # 1. Z-score strength (30%)
            zscore = abs(stats.get('zscore', 0.0))
            zscore_score = min(zscore / 3.0, 1.0)
            confidence_factors.append(('zscore', zscore_score, 0.30))

            # 2. Volume ratio (25%)
            volume_score = min(spread.volume_ratio / 2.0, 1.0) if spread.volume_ratio > 0 else 0.0
            confidence_factors.append(('volume', volume_score, 0.25))

            # 3. Convergence trend (25%)
            if self.spread_history.get(spread.pair_name):
                convergence_prob = self.calculate_convergence_probability(
                    self.spread_history[spread.pair_name]
                )
                confidence_factors.append(('convergence', convergence_prob, 0.25))

            # 4. Historical stability (20%)
            std = stats.get('std', 0.0)
            stability_score = 1.0 - min(std / 2.0, 1.0)  # Lower std = higher stability
            confidence_factors.append(('stability', stability_score, 0.20))

            # Calculate weighted confidence
            total_confidence = sum(score * weight for _, score, weight in confidence_factors)

            return min(max(total_confidence, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating signal confidence: {e}")
            return base_confidence