# strategy/__init__.py

"""
Strategy Package for Spot-Futures Arbitrage System
Contains main arbitrage strategy and order management
"""

from .arbitrage_strategy import SpotFuturesArbitrageStrategy

__version__ = "1.0.0"
__author__ = "Spot-Futures Arbitrage Team"

__all__ = [
    "SpotFuturesArbitrageStrategy",
]