# config/__init__.py

"""
Configuration Package for Spot-Futures Arbitrage Strategy
Provides all configuration classes and settings
"""

from .settings import (
    FyersConfig,
    ArbitrageStrategyConfig,
    TradingConfig,
    ExpiryConfig,
    SignalType,
    ArbitrageType
)

from .symbols import (
    symbol_manager,
    get_arbitrage_symbols,
    get_spot_futures_pair,
    validate_arbitrage_symbol,
    get_lot_size,
    ArbitrageSymbolManager,
    FuturesContract
)

__version__ = "1.0.0"
__author__ = "Spot-Futures Arbitrage Team"

__all__ = [
    # Configuration classes
    "FyersConfig",
    "ArbitrageStrategyConfig",
    "TradingConfig",
    "ExpiryConfig",

    # Enums
    "SignalType",
    "ArbitrageType",

    # Symbol management
    "symbol_manager",
    "get_arbitrage_symbols",
    "get_spot_futures_pair",
    "validate_arbitrage_symbol",
    "get_lot_size",
    "ArbitrageSymbolManager",
    "FuturesContract",
]