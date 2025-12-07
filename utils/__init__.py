# utils/__init__.py

"""
Utilities Package for Spot-Futures Arbitrage Strategy
Contains helper functions and authentication
"""

from .enhanced_auth_helper import (
    FyersAuthManager,
    setup_auth_only,
    authenticate_fyers,
    test_authentication
)

__version__ = "1.0.0"
__author__ = "Spot-Futures Arbitrage Team"

__all__ = [
    "FyersAuthManager",
    "setup_auth_only",
    "authenticate_fyers",
    "test_authentication",
]