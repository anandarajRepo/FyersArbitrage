# services/analysis_service.py

"""
Analysis Service for Spot-Futures Arbitrage Strategy
Z-Score Based Logic - Matching Arbitrage.py Backtest

Key Logic:
- Basis = Futures Price - Spot Price
- Basis % = (Basis / Spot Price) * 100
- Rolling Mean & Std of Basis % (window = basis_lookback)
- Z-Score = (Current Basis % - Mean) / Std

Entry Signals:
- Long Futures + Short Spot: z-score < -entry_threshold (futures underpriced)
- Short Futures + Long Spot: z-score > +entry_threshold (futures overpriced)

Exit Signals:
- Basis Convergence: |z-score| < exit_threshold
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Deque
from datetime import datetime
from collections import deque

from models.trading_models import SpotFuturesSpread, ArbitrageSignal, LiveQuote
from config.settings import SignalType, ArbitrageStrategyConfig

logger = logging.getLogger(__name__)


class ZScoreArbitrageAnalyzer:
    """
    Z-Score based arbitrage analyzer
    Implements the exact logic from Arbitrage.py backtest
    """

    def __init__(self, config: ArbitrageStrategyConfig):
        self.config = config

        # Historical basis data for each symbol
        # Stores basis_pct values for rolling statistics
        self.basis_history: Dict[str, Deque[float]] = {}

        # Track number of data points
        self.data_point_count: Dict[str, int] = {}

        # Max history length (keep more for better statistics)
        self.max_history_length = max(config.basis_lookback * 3, 200)

        logger.info(f"Z-Score Analyzer initialized:")
        logger.info(f"  Basis Lookback: {config.basis_lookback}")
        logger.info(f"  Entry Z-Score: ±{config.entry_zscore_threshold}")
        logger.info(f"  Exit Z-Score: ±{config.exit_zscore_threshold}")

    def update_basis_history(self, symbol: str, basis_pct: float):
        """Update basis history for a symbol"""
        if symbol not in self.basis_history:
            self.basis_history[symbol] = deque(maxlen=self.max_history_length)
            self.data_point_count[symbol] = 0

        self.basis_history[symbol].append(basis_pct)
        self.data_point_count[symbol] += 1

    def calculate_basis_statistics(self, symbol: str, current_basis_pct: float) -> Dict:
        """
        Calculate basis statistics using rolling window
        Matches the logic from Arbitrage.py backtest
        """
        try:
            # Update history
            self.update_basis_history(symbol, current_basis_pct)

            # Get historical data
            history = list(self.basis_history.get(symbol, []))

            # Need minimum data points
            if len(history) < self.config.basis_lookback:
                return {
                    'has_sufficient_data': False,
                    'data_points': len(history),
                    'mean': 0.0,
                    'std': 0.0,
                    'z_score': 0.0,
                    'min': current_basis_pct,
                    'max': current_basis_pct
                }

            # Calculate rolling statistics using the lookback window
            window_data = history[-self.config.basis_lookback:]

            basis_mean = np.mean(window_data)
            basis_std = np.std(window_data)

            # Calculate Z-score
            if basis_std > self.config.min_basis_std:
                z_score = (current_basis_pct - basis_mean) / basis_std
            else:
                # Basis not volatile enough - no signal
                z_score = 0.0

            return {
                'has_sufficient_data': True,
                'data_points': len(history),
                'mean': basis_mean,
                'std': basis_std,
                'z_score': z_score,
                'min': min(history),
                'max': max(history),
                'current_basis_pct': current_basis_pct
            }

        except Exception as e:
            logger.error(f"Error calculating basis statistics for {symbol}: {e}")
            return {
                'has_sufficient_data': False,
                'data_points': 0,
                'mean': 0.0,
                'std': 0.0,
                'z_score': 0.0
            }

    def generate_entry_signal(
            self,
            symbol: str,
            spread: SpotFuturesSpread,
            stats: Dict
    ) -> Optional[ArbitrageSignal]:
        """
        Generate entry signal based on z-score thresholds
        Exact logic from Arbitrage.py backtest
        """
        try:
            # Must have sufficient data
            if not stats.get('has_sufficient_data'):
                return None

            z_score = stats['z_score']
            basis_std = stats['std']

            # Check if basis has enough volatility
            if basis_std <= self.config.min_basis_std:
                logger.debug(f"{symbol}: Basis std too low ({basis_std:.4f})")
                return None

            # Check volume filters
            if spread.volume_ratio < self.config.min_volume_ratio:
                logger.debug(f"{symbol}: Volume ratio too low ({spread.volume_ratio:.2f})")
                return None

            total_volume = spread.spot_volume + spread.futures_volume
            if total_volume < self.config.min_total_volume:
                logger.debug(f"{symbol}: Total volume too low ({total_volume})")
                return None

            # ENTRY LOGIC (matching backtest)
            signal_type = None

            # Long Futures + Short Spot: When futures are underpriced (z-score < -threshold)
            if z_score < -self.config.entry_zscore_threshold:
                signal_type = SignalType.LONG_FUTURES_SHORT_SPOT
                logger.info(f"SIGNAL: {symbol} - LONG FUTURES + SHORT SPOT | "
                            f"Z-Score: {z_score:.2f} (Futures UNDERPRICED)")

            # Short Futures + Long Spot: When futures are overpriced (z-score > +threshold)
            elif z_score > self.config.entry_zscore_threshold:
                signal_type = SignalType.SHORT_FUTURES_LONG_SPOT
                logger.info(f"SIGNAL: {symbol} - SHORT FUTURES + LONG SPOT | "
                            f"Z-Score: {z_score:.2f} (Futures OVERPRICED)")

            if not signal_type:
                return None

            # Calculate position size (matching backtest)
            quantity = self._calculate_position_size(
                symbol,
                spread.spot_price,
                spread.futures_price
            )

            if quantity == 0:
                return None

            # Calculate targets
            target_spread = self._calculate_target_spread(spread, signal_type)
            stop_loss_spread = self._calculate_stop_loss_spread(spread, signal_type)

            # Create signal
            from config.symbols import symbol_manager
            lot_size = symbol_manager.get_lot_size(symbol) or 1

            signal = ArbitrageSignal(
                symbol=symbol,
                signal_type=signal_type,
                spot_price=spread.spot_price,
                futures_price=spread.futures_price,
                spread_pct=spread.spread_pct,
                mispricing=spread.spread_pct - stats['mean'],  # Deviation from mean
                entry_spot_price=spread.spot_price,
                entry_futures_price=spread.futures_price,
                target_spread=target_spread,
                stop_loss_spread=stop_loss_spread,
                lot_size=lot_size,
                quantity=quantity,
                capital_required=quantity * lot_size * spread.spot_price * 2,  # Both legs
                confidence=self._calculate_confidence_from_zscore(abs(z_score)),
                z_score=z_score,
                volume_ratio=spread.volume_ratio,
                convergence_rate=0.0,  # Not used in z-score strategy
                timestamp=datetime.now(),
                days_to_expiry=spread.days_to_expiry,
                risk_amount=0.0,  # Will be calculated
                reward_amount=0.0,  # Will be calculated
                sector=symbol_manager.get_sector(symbol) or "GENERAL"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating entry signal for {symbol}: {e}")
            return None

    def check_exit_signal(self, symbol: str, position, current_spread: SpotFuturesSpread) -> Tuple[bool, str]:
        """
        Check if position should be exited based on z-score

        Returns:
            (should_exit, exit_reason)
        """
        try:
            # Calculate current basis statistics
            stats = self.calculate_basis_statistics(symbol, current_spread.spread_pct)

            if not stats.get('has_sufficient_data'):
                return False, ""

            z_score = stats['z_score']

            # EXIT CONDITION: Basis convergence (|z-score| < exit_threshold)
            if abs(z_score) < self.config.exit_zscore_threshold:
                logger.info(f"EXIT SIGNAL: {symbol} - BASIS CONVERGENCE | "
                            f"Z-Score: {z_score:.2f} < {self.config.exit_zscore_threshold}")
                return True, "BASIS_CONVERGENCE"

            # Check stop loss
            if self._check_stop_loss(position, current_spread):
                logger.warning(f"EXIT SIGNAL: {symbol} - STOP LOSS HIT | "
                               f"Loss: {position.unrealized_pnl:.2f}")
                return True, "STOP_LOSS"

            return False, ""

        except Exception as e:
            logger.error(f"Error checking exit signal for {symbol}: {e}")
            return False, ""

    def _calculate_position_size(self, symbol: str, spot_price: float, futures_price: float) -> int:
        """
        Calculate position size (number of lots)
        Matches backtest logic: quantity = (capital * 0.5) / spot_price
        """
        try:
            from config.symbols import symbol_manager
            lot_size = symbol_manager.get_lot_size(symbol) or 1

            # Capital per leg (50% each for spot and futures)
            capital_per_leg = self.config.portfolio_value * (self.config.capital_per_leg_pct / 100)

            # Quantity in units
            quantity_units = int(capital_per_leg / spot_price)

            # Convert to lots
            quantity_lots = max(1, quantity_units // lot_size)

            return quantity_lots

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def _calculate_target_spread(self, spread: SpotFuturesSpread, signal_type: SignalType) -> float:
        """Calculate target spread (when z-score converges to near zero)"""
        # Target is mean basis (z-score = 0)
        if self.basis_history.get(spread.symbol):
            history = list(self.basis_history[spread.symbol])
            if len(history) >= self.config.basis_lookback:
                mean_basis_pct = np.mean(history[-self.config.basis_lookback:])
                # Convert back to spread value
                target_spread = (mean_basis_pct / 100) * spread.spot_price
                return target_spread

        # Fallback: current spread with small convergence
        return spread.spread * 0.5

    def _calculate_stop_loss_spread(self, spread: SpotFuturesSpread, signal_type: SignalType) -> float:
        """Calculate stop loss spread"""
        # Stop loss if spread widens beyond entry + stop_loss_pct
        if signal_type == SignalType.LONG_FUTURES_SHORT_SPOT:
            # Entered when futures underpriced, loss if spread widens more
            stop_spread = spread.spread * (1 - self.config.stop_loss_pct / 100)
        else:
            # Entered when futures overpriced, loss if spread narrows too much
            stop_spread = spread.spread * (1 + self.config.stop_loss_pct / 100)

        return stop_spread

    def _check_stop_loss(self, position, current_spread: SpotFuturesSpread) -> bool:
        """Check if stop loss is hit based on unrealized P&L"""
        if position.unrealized_pnl == 0:
            return False

        # Calculate total position value
        total_position_value = abs(position.entry_spot_price * position.spot_quantity * 2)

        # Check if loss exceeds threshold
        loss_pct = abs(position.unrealized_pnl / total_position_value) * 100

        return position.unrealized_pnl < 0 and loss_pct >= self.config.stop_loss_pct

    def _calculate_confidence_from_zscore(self, abs_z_score: float) -> float:
        """
        Calculate confidence score from z-score magnitude
        Higher z-score = higher confidence
        """
        # Normalize z-score to 0-1 confidence
        # z-score of 2.0 = 0.67 confidence
        # z-score of 3.0 = 1.0 confidence
        confidence = min(abs_z_score / 3.0, 1.0)
        return confidence

    def get_statistics_summary(self, symbol: str) -> Dict:
        """Get statistics summary for a symbol"""
        if symbol not in self.basis_history:
            return {}

        history = list(self.basis_history[symbol])
        if not history:
            return {}

        return {
            'data_points': len(history),
            'mean': np.mean(history),
            'std': np.std(history),
            'min': min(history),
            'max': max(history),
            'current': history[-1] if history else 0.0
        }