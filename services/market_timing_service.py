# services/market_timing_service.py

"""
Market Timing Service for Arbitrage Strategy
"""

from datetime import datetime, time
import pytz
from typing import Optional
from config.settings import TradingConfig

IST = pytz.timezone('Asia/Kolkata')


class MarketTimingService:
    """Market timing service"""

    def __init__(self, config: TradingConfig):
        self.config = config
        self.market_holidays = {
            datetime(2025, 1, 26).date(),
            datetime(2025, 3, 14).date(),
            datetime(2025, 4, 14).date(),
            datetime(2025, 4, 18).date(),
            datetime(2025, 8, 15).date(),
            datetime(2025, 10, 2).date(),
        }

    def is_trading_day(self, date_to_check: Optional[datetime] = None) -> bool:
        """Check if given date is a trading day"""
        if date_to_check is None:
            date_to_check = datetime.now(IST)

        if date_to_check.weekday() >= 5:
            return False

        if date_to_check.date() in self.market_holidays:
            return False

        return True

    def is_trading_time(self) -> bool:
        """Check if within trading hours"""
        now = datetime.now(IST)

        if not self.is_trading_day(now):
            return False

        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)

        return market_start <= now <= market_end

    def should_close_positions_for_day(self) -> bool:
        """Check if positions should be closed"""
        now = datetime.now(IST)

        if not self.is_trading_time():
            return False

        close_time = now.replace(hour=15, minute=20, second=0, microsecond=0)
        return now >= close_time

    def time_until_market_close(self) -> Optional[int]:
        """Get seconds until market closes"""
        if not self.is_trading_time():
            return None

        now = datetime.now(IST)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        return int((market_close - now).total_seconds())

    def get_current_market_phase(self) -> str:
        """Get current market phase"""
        if not self.is_trading_day():
            return "MARKET_HOLIDAY"

        if not self.is_trading_time():
            now = datetime.now(IST)
            market_start = now.replace(hour=9, minute=15)
            if now < market_start:
                return "PRE_MARKET"
            return "POST_MARKET"

        if self.should_close_positions_for_day():
            return "POSITION_CLOSING"

        return "REGULAR_TRADING"