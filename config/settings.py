# config/settings.py

"""
Configuration Settings for Spot-Futures Arbitrage Trading Strategy
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
    """Arbitrage signal types"""
    LONG_SPOT_SHORT_FUTURES = "LONG_SPOT_SHORT_FUTURES"  # Spot undervalued
    SHORT_SPOT_LONG_FUTURES = "SHORT_SPOT_LONG_FUTURES"  # Futures undervalued
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
    """Spot-Futures Arbitrage Strategy Configuration"""
    # Portfolio settings
    portfolio_value: float = 100000  # 1 lakh
    risk_per_trade_pct: float = 2.0  # 2% risk per arbitrage pair
    max_positions: int = 5  # Maximum arbitrage positions

    # Arbitrage parameters
    min_spread_threshold: float = 0.5  # Minimum spread % to open position
    max_spread_threshold: float = 3.0  # Maximum spread % (too wide = risky)
    target_profit_pct: float = 0.3  # Target profit % on convergence

    # Entry criteria
    min_spread_duration_seconds: int = 30  # Spread must persist for 30 seconds
    min_liquidity_ratio: float = 1.5  # Min volume ratio for entry
    max_correlation_deviation: float = 0.95  # Max acceptable correlation

    # Risk management
    stop_loss_pct: float = 0.5  # Stop loss if spread widens beyond this
    trailing_stop_enabled: bool = True
    trailing_stop_pct: float = 0.2  # Trail by 0.2%

    # Position management
    enable_partial_exits: bool = True
    partial_exit_pct: float = 50.0  # Exit 50% at target
    max_holding_days: int = 25  # Close before expiry

    # Margin and leverage
    margin_usage_pct: float = 50.0  # Use 50% of available margin
    leverage_multiplier: float = 1.0  # No leverage by default

    # Market making parameters
    enable_market_making: bool = False
    spread_capture_pct: float = 0.1  # Try to capture 0.1% spread

    # Signal filtering
    min_confidence: float = 0.7  # Minimum confidence score
    require_convergence_trend: bool = True  # Require converging spread


@dataclass
class TradingConfig:
    """Trading Session Configuration"""
    # Market hours (IST)
    market_start_hour: int = 9
    market_start_minute: int = 15
    market_end_hour: int = 15
    market_end_minute: int = 30

    # Expiry management
    days_before_expiry_to_exit: int = 3  # Exit 3 days before expiry
    expiry_day_close_time: str = "15:00"  # Close all on expiry day

    # Monitoring
    monitoring_interval: int = 5  # Check every 5 seconds
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
    enable_auto_rollover: bool = True
    rollover_days_before_expiry: int = 2  # Rollover 2 days before expiry

    # Expiry alerts
    enable_expiry_alerts: bool = True
    alert_days_before: list = None  # Will be set in __post_init__

    def __post_init__(self):
        if self.alert_days_before is None:
            self.alert_days_before = [7, 3, 1]  # Alert at 7, 3, 1 days before