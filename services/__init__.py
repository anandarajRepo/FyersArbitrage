# services/__init__.py

"""
Services Package for Spot-Futures Arbitrage Strategy
Contains data services, analysis, and market timing (to be implemented)
"""

# Future implementations:
# from .fyers_websocket_service import ArbitrageDataService
# from .analysis_service import SpreadAnalysisService
# from .market_timing_service import MarketTimingService

__version__ = "1.0.0"
__author__ = "Spot-Futures Arbitrage Team"

__all__ = [
    # Services to be implemented:
    # "ArbitrageDataService",
    # "SpreadAnalysisService",
    # "MarketTimingService",
]

# Note: These services will be implemented based on the FyersORB architecture
# Key services needed:
# 1. ArbitrageDataService - WebSocket data for spot and futures
# 2. SpreadAnalysisService - Spread calculations and analysis
# 3. MarketTimingService - Market hours and expiry management
# 4. OrderManager - Order execution for arbitrage pairs