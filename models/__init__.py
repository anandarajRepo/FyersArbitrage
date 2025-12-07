# models/__init__.py

"""
Trading Models Package for Spot-Futures Arbitrage Strategy
Contains all data models for signals, positions, and trades
"""

from .trading_models import (
    # Core data models
    LiveQuote,
    SpotFuturesSpread,

    # Signal and position models
    ArbitrageSignal,
    ArbitragePosition,
    ArbitrageTradeResult,

    # Performance and metrics
    StrategyMetrics,
    MarketState,

    # Utility functions
    create_arbitrage_signal_from_spread,
    create_position_from_signal,
    create_trade_result_from_position,
    calculate_portfolio_risk,
)

__version__ = "1.0.0"
__author__ = "Spot-Futures Arbitrage Team"

__all__ = [
    # Core data models
    "LiveQuote",
    "SpotFuturesSpread",

    # Trading models
    "ArbitrageSignal",
    "ArbitragePosition",
    "ArbitrageTradeResult",

    # Analytics models
    "StrategyMetrics",
    "MarketState",

    # Utility functions
    "create_arbitrage_signal_from_spread",
    "create_position_from_signal",
    "create_trade_result_from_position",
    "calculate_portfolio_risk",
]