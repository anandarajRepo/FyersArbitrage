# config/settings.py

"""
Configuration Settings for Spot-Futures Arbitrage Trading Strategy
Updated to use Z-Score based logic matching Arbitrage.py backtest
"""

import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ArbitrageType(Enum):
    """Types of arbitrage strategies"""
    SPOT_FUTURES = "SPOT_FUTURES"
    CALENDAR_SPREAD = "CALENDAR_SPREAD"
    EXCHANGE_ARBITRAGE = "EXCHANGE_ARBITRAGE"


class SignalType(Enum):
    """Arbitrage signal types - matching backtest logic"""
    LONG_FUTURES_SHORT_SPOT = "long_futures"  # Z-score < -threshold (futures underpriced)
    SHORT_FUTURES_LONG_SPOT = "short_futures"  # Z-score > +threshold (futures overpriced)
    CLOSE_POSITION = "CLOSE_POSITION"


@dataclass
class FyersConfig:
    """Fyers API Configuration"""
    client_id: str
    secret_key: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    base_url: str = "https://api-t1.fyers.in/api/v3"


@dataclass
class ArbitrageStrategyConfig:
    """
    Spot-Futures Arbitrage Strategy Configuration
    Z-Score Based Strategy - Matching Arbitrage.py Backtest

    Entry Logic:
    - Long Futures + Short Spot: When z-score < -entry_threshold (futures underpriced)
    - Short Futures + Long Spot: When z-score > +entry_threshold (futures overpriced)

    Exit Logic:
    - Basis Convergence: |z-score| < exit_threshold
    - Stop Loss: Loss exceeds stop_loss_pct
    - Square-off: End of day (3:20 PM IST)
    """
    # Portfolio settings
    portfolio_value: float = 100000  # 1 lakh capital
    risk_per_trade_pct: float = 2.0  # 2% risk per arbitrage pair
    max_positions: int = 5  # Maximum concurrent arbitrage positions
    capital_per_leg_pct: float = 50.0  # 50% capital per leg (spot + futures = 100%)

    # Z-score based parameters (CORE LOGIC - matching backtest)
    basis_lookback: int = 50  # Rolling window for basis mean/std calculation
    entry_zscore_threshold: float = 2.0  # Enter when |z-score| > 2.0
    exit_zscore_threshold: float = 0.5  # Exit when |z-score| < 0.5

    # Risk management
    stop_loss_pct: float = 1.0  # Stop loss on total position value (1%)

    # Position management
    max_holding_days: int = 25  # Close positions before expiry
    days_before_expiry_to_exit: int = 3  # Exit 3 days before contract expiry

    # Volume/liquidity filters
    min_volume_ratio: float = 0.3  # Minimum futures/spot volume ratio
    min_total_volume: int = 5000  # Minimum combined volume

    # Basis volatility filter
    min_basis_std: float = 0.01  # Minimum basis std dev (filter low volatility pairs)

    # Data requirements
    min_data_points: int = 60  # Minimum data points before trading

    # Lot sizing
    lot_size_multiplier: int = 1  # Futures lot size multiplier


@dataclass
class TradingConfig:
    """Trading Session Configuration"""
    # Market hours (IST)
    market_start_hour: int = 9
    market_start_minute: int = 15
    market_end_hour: int = 15
    market_end_minute: int = 30

    # Square-off time (matching backtest)
    square_off_hour: int = 15
    square_off_minute: int = 20  # 3:20 PM IST mandatory square-off

    # Expiry management
    days_before_expiry_to_exit: int = 3  # Exit 3 days before expiry
    expiry_day_close_time: str = "15:00"  # Close all on expiry day

    # Monitoring intervals
    monitoring_interval: int = 5  # Check spreads every 5 seconds
    position_update_interval: int = 3  # Update positions every 3 seconds
    spread_calculation_interval: int = 2  # Calculate spreads every 2 seconds

    # Data requirements
    historical_data_days: int = 30  # Days of historical data for analysis
    tick_data_buffer_size: int = 100  # Keep last 100 ticks


@dataclass
class ExpiryConfig:
    """Futures Expiry Configuration"""
    # NSE expiry conventions
    expiry_day: str = "Thursday"  # Last Thursday of month
    expiry_time: str = "15:30"  # 3:30 PM IST

    # Auto-rollover settings
    enable_auto_rollover: bool = False  # Disabled for safety
    rollover_days_before_expiry: int = 2  # Rollover 2 days before expiry

    # Expiry alerts
    enable_expiry_alerts: bool = True
    alert_days_before: list = None  # Will be set in __post_init__

    def __post_init__(self):
        if self.alert_days_before is None:
            self.alert_days_before = [7, 3, 1]  # Alert at 7, 3, 1 days before