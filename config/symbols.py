# config/symbols.py

"""
Symbol Configuration for Spot-Futures Arbitrage Strategy
Manages spot-futures pairs and symbol mappings
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class FuturesContract:
    """Futures contract details"""
    symbol: str
    spot_symbol: str
    expiry_date: datetime
    lot_size: int
    tick_size: float
    contract_month: str  # e.g., "25JAN", "25FEB"

    @property
    def days_to_expiry(self) -> int:
        """Calculate days remaining until expiry"""
        return (self.expiry_date - datetime.now()).days

    @property
    def is_near_expiry(self, days_threshold: int = 3) -> bool:
        """Check if contract is near expiry"""
        return self.days_to_expiry <= days_threshold


class ArbitrageSymbolManager:
    """Manages spot-futures arbitrage pairs"""

    def __init__(self):
        # Spot-Futures pair mappings
        # Format: spot_symbol -> (fyers_spot, fyers_futures, lot_size)
        self._arbitrage_pairs: Dict[str, Dict] = {
            # Nifty 50 Stocks
            "RELIANCE": {
                "spot": "NSE:RELIANCE-EQ",
                "futures": "NSE:RELIANCE25JANFUT",  # Update monthly
                "lot_size": 250,
                "tick_size": 0.05,
                "sector": "ENERGY"
            },
            "TCS": {
                "spot": "NSE:TCS-EQ",
                "futures": "NSE:TCS25JANFUT",
                "lot_size": 125,
                "tick_size": 0.05,
                "sector": "IT"
            },
            "HDFCBANK": {
                "spot": "NSE:HDFCBANK-EQ",
                "futures": "NSE:HDFCBANK25JANFUT",
                "lot_size": 550,
                "tick_size": 0.05,
                "sector": "BANKING"
            },
            "INFY": {
                "spot": "NSE:INFY-EQ",
                "futures": "NSE:INFY25JANFUT",
                "lot_size": 300,
                "tick_size": 0.05,
                "sector": "IT"
            },
            "ICICIBANK": {
                "spot": "NSE:ICICIBANK-EQ",
                "futures": "NSE:ICICIBANK25JANFUT",
                "lot_size": 1375,
                "tick_size": 0.05,
                "sector": "BANKING"
            },
            "HINDUNILVR": {
                "spot": "NSE:HINDUNILVR-EQ",
                "futures": "NSE:HINDUNILVR25JANFUT",
                "lot_size": 300,
                "tick_size": 0.05,
                "sector": "FMCG"
            },
            "ITC": {
                "spot": "NSE:ITC-EQ",
                "futures": "NSE:ITC25JANFUT",
                "lot_size": 1600,
                "tick_size": 0.05,
                "sector": "FMCG"
            },
            "SBIN": {
                "spot": "NSE:SBIN-EQ",
                "futures": "NSE:SBIN25JANFUT",
                "lot_size": 1500,
                "tick_size": 0.05,
                "sector": "BANKING"
            },
            "BHARTIARTL": {
                "spot": "NSE:BHARTIARTL-EQ",
                "futures": "NSE:BHARTIARTL25JANFUT",
                "lot_size": 1813,
                "tick_size": 0.05,
                "sector": "TELECOM"
            },
            "KOTAKBANK": {
                "spot": "NSE:KOTAKBANK-EQ",
                "futures": "NSE:KOTAKBANK25JANFUT",
                "lot_size": 400,
                "tick_size": 0.05,
                "sector": "BANKING"
            },
            "LT": {
                "spot": "NSE:LT-EQ",
                "futures": "NSE:LT25JANFUT",
                "lot_size": 300,
                "tick_size": 0.05,
                "sector": "INFRASTRUCTURE"
            },
            "WIPRO": {
                "spot": "NSE:WIPRO-EQ",
                "futures": "NSE:WIPRO25JANFUT",
                "lot_size": 1200,
                "tick_size": 0.05,
                "sector": "IT"
            },
            "AXISBANK": {
                "spot": "NSE:AXISBANK-EQ",
                "futures": "NSE:AXISBANK25JANFUT",
                "lot_size": 1200,
                "tick_size": 0.05,
                "sector": "BANKING"
            },
            "MARUTI": {
                "spot": "NSE:MARUTI-EQ",
                "futures": "NSE:MARUTI25JANFUT",
                "lot_size": 100,
                "tick_size": 0.05,
                "sector": "AUTO"
            },
            "SUNPHARMA": {
                "spot": "NSE:SUNPHARMA-EQ",
                "futures": "NSE:SUNPHARMA25JANFUT",
                "lot_size": 400,
                "tick_size": 0.05,
                "sector": "PHARMA"
            },
            "NTPC": {
                "spot": "NSE:NTPC-EQ",
                "futures": "NSE:NTPC25JANFUT",
                "lot_size": 3000,
                "tick_size": 0.05,
                "sector": "ENERGY"
            },
            "TATAMOTORS": {
                "spot": "NSE:TATAMOTORS-EQ",
                "futures": "NSE:TATAMOTORS25JANFUT",
                "lot_size": 1350,
                "tick_size": 0.05,
                "sector": "AUTO"
            },
            "TATASTEEL": {
                "spot": "NSE:TATASTEEL-EQ",
                "futures": "NSE:TATASTEEL25JANFUT",
                "lot_size": 6000,
                "tick_size": 0.05,
                "sector": "METALS"
            },
            "POWERGRID": {
                "spot": "NSE:POWERGRID-EQ",
                "futures": "NSE:POWERGRID25JANFUT",
                "lot_size": 2700,
                "tick_size": 0.05,
                "sector": "ENERGY"
            },
            "M&M": {
                "spot": "NSE:M&M-EQ",
                "futures": "NSE:M&M25JANFUT",
                "lot_size": 600,
                "tick_size": 0.05,
                "sector": "AUTO"
            },
        }

        # Indices
        self._index_pairs: Dict[str, Dict] = {
            "NIFTY": {
                "spot": "NSE:NIFTY50-INDEX",
                "futures": "NSE:NIFTY25JANFUT",
                "lot_size": 50,
                "tick_size": 0.05,
                "sector": "INDEX"
            },
            "BANKNIFTY": {
                "spot": "NSE:NIFTYBANK-INDEX",
                "futures": "NSE:BANKNIFTY25JANFUT",
                "lot_size": 25,
                "tick_size": 0.05,
                "sector": "INDEX"
            },
        }

        # Create reverse mappings
        self._create_reverse_mappings()

    def _create_reverse_mappings(self):
        """Create reverse lookup mappings"""
        self._spot_to_symbol = {}
        self._futures_to_symbol = {}

        for symbol, data in {**self._arbitrage_pairs, **self._index_pairs}.items():
            self._spot_to_symbol[data['spot']] = symbol
            self._futures_to_symbol[data['futures']] = symbol

    def get_arbitrage_pair(self, symbol: str) -> Optional[Dict]:
        """Get arbitrage pair details for a symbol"""
        pair = self._arbitrage_pairs.get(symbol)
        if not pair:
            pair = self._index_pairs.get(symbol)
        return pair

    def get_all_symbols(self) -> List[str]:
        """Get all available symbols for arbitrage"""
        return list(self._arbitrage_pairs.keys()) + list(self._index_pairs.keys())

    def get_stock_symbols(self) -> List[str]:
        """Get stock symbols only (excluding indices)"""
        return list(self._arbitrage_pairs.keys())

    def get_index_symbols(self) -> List[str]:
        """Get index symbols only"""
        return list(self._index_pairs.keys())

    def get_spot_symbol(self, symbol: str) -> Optional[str]:
        """Get Fyers spot symbol"""
        pair = self.get_arbitrage_pair(symbol)
        return pair['spot'] if pair else None

    def get_futures_symbol(self, symbol: str) -> Optional[str]:
        """Get Fyers futures symbol"""
        pair = self.get_arbitrage_pair(symbol)
        return pair['futures'] if pair else None

    def get_lot_size(self, symbol: str) -> Optional[int]:
        """Get futures lot size"""
        pair = self.get_arbitrage_pair(symbol)
        return pair['lot_size'] if pair else None

    def get_tick_size(self, symbol: str) -> Optional[float]:
        """Get tick size"""
        pair = self.get_arbitrage_pair(symbol)
        return pair['tick_size'] if pair else None

    def get_sector(self, symbol: str) -> Optional[str]:
        """Get sector classification"""
        pair = self.get_arbitrage_pair(symbol)
        return pair['sector'] if pair else None

    def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid for arbitrage"""
        return symbol in self.get_all_symbols()

    def get_symbol_from_fyers(self, fyers_symbol: str) -> Optional[str]:
        """Convert Fyers symbol back to display symbol"""
        return self._spot_to_symbol.get(fyers_symbol) or self._futures_to_symbol.get(fyers_symbol)

    def get_all_fyers_symbols(self) -> Dict[str, List[str]]:
        """Get all Fyers symbols for WebSocket subscription"""
        spot_symbols = []
        futures_symbols = []

        for symbol in self.get_all_symbols():
            pair = self.get_arbitrage_pair(symbol)
            if pair:
                spot_symbols.append(pair['spot'])
                futures_symbols.append(pair['futures'])

        return {
            'spot': spot_symbols,
            'futures': futures_symbols,
            'all': spot_symbols + futures_symbols
        }

    def update_futures_contract(self, symbol: str, new_contract_month: str):
        """Update futures contract symbol for rollover"""
        pair = self.get_arbitrage_pair(symbol)
        if pair:
            # Update the futures symbol with new contract month
            base_symbol = pair['futures'].split('25')[0]  # Extract base part
            new_futures = f"{base_symbol}{new_contract_month}FUT"

            if symbol in self._arbitrage_pairs:
                self._arbitrage_pairs[symbol]['futures'] = new_futures
            elif symbol in self._index_pairs:
                self._index_pairs[symbol]['futures'] = new_futures

            # Update reverse mappings
            self._create_reverse_mappings()

            return True
        return False

    def get_contract_info(self, symbol: str) -> Optional[FuturesContract]:
        """Get detailed futures contract information"""
        pair = self.get_arbitrage_pair(symbol)
        if not pair:
            return None

        # Extract contract month from futures symbol
        futures_symbol = pair['futures']
        # Assuming format like "NSE:RELIANCE25JANFUT"
        parts = futures_symbol.split('25')
        if len(parts) >= 2:
            contract_month = '25' + parts[1].replace('FUT', '')
        else:
            contract_month = "25JAN"

        # Calculate expiry (last Thursday of contract month)
        # This is a simplified calculation - you'd want to handle this more robustly
        expiry_date = self._calculate_expiry_date(contract_month)

        return FuturesContract(
            symbol=symbol,
            spot_symbol=pair['spot'],
            expiry_date=expiry_date,
            lot_size=pair['lot_size'],
            tick_size=pair['tick_size'],
            contract_month=contract_month
        )

    def _calculate_expiry_date(self, contract_month: str) -> datetime:
        """Calculate expiry date from contract month"""
        # Extract year and month
        year = int('20' + contract_month[:2])
        month_str = contract_month[2:].upper()

        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }

        month = month_map.get(month_str, 1)

        # Find last Thursday of the month
        # Start from last day of month and work backwards
        from calendar import monthrange
        last_day = monthrange(year, month)[1]

        for day in range(last_day, 0, -1):
            date = datetime(year, month, day)
            if date.weekday() == 3:  # Thursday
                return date.replace(hour=15, minute=30)

        # Fallback
        return datetime(year, month, last_day, 15, 30)

    def get_pairs_by_sector(self, sector: str) -> List[str]:
        """Get all symbols in a sector"""
        symbols = []
        for symbol in self.get_all_symbols():
            pair = self.get_arbitrage_pair(symbol)
            if pair and pair.get('sector') == sector:
                symbols.append(symbol)
        return symbols

    def get_trading_universe_size(self) -> int:
        """Get total number of arbitrage pairs"""
        return len(self.get_all_symbols())


# Global instance
symbol_manager = ArbitrageSymbolManager()


# Convenience functions
def get_arbitrage_symbols() -> List[str]:
    """Get all arbitrage symbols"""
    return symbol_manager.get_all_symbols()


def get_spot_futures_pair(symbol: str) -> Tuple[Optional[str], Optional[str]]:
    """Get spot and futures Fyers symbols"""
    spot = symbol_manager.get_spot_symbol(symbol)
    futures = symbol_manager.get_futures_symbol(symbol)
    return spot, futures


def validate_arbitrage_symbol(symbol: str) -> bool:
    """Validate symbol for arbitrage"""
    return symbol_manager.validate_symbol(symbol)


def get_lot_size(symbol: str) -> Optional[int]:
    """Get futures lot size for symbol"""
    return symbol_manager.get_lot_size(symbol)


# Example usage
if __name__ == "__main__":
    print("Arbitrage Symbol Manager Test")
    print("=" * 60)

    print(f"\nTotal arbitrage pairs: {symbol_manager.get_trading_universe_size()}")

    # Test specific symbol
    test_symbol = "RELIANCE"
    print(f"\nTesting {test_symbol}:")
    print(f"  Valid: {validate_arbitrage_symbol(test_symbol)}")

    spot, futures = get_spot_futures_pair(test_symbol)
    print(f"  Spot: {spot}")
    print(f"  Futures: {futures}")
    print(f"  Lot Size: {get_lot_size(test_symbol)}")
    print(f"  Sector: {symbol_manager.get_sector(test_symbol)}")

    # Get contract info
    contract = symbol_manager.get_contract_info(test_symbol)
    if contract:
        print(f"  Contract Month: {contract.contract_month}")
        print(f"  Days to Expiry: {contract.days_to_expiry}")
        print(f"  Near Expiry: {contract.is_near_expiry()}")

    # List all symbols
    print(f"\nStock Symbols ({len(symbol_manager.get_stock_symbols())}):")
    for sym in symbol_manager.get_stock_symbols()[:5]:
        print(f"  {sym}")

    print(f"\nIndex Symbols ({len(symbol_manager.get_index_symbols())}):")
    for sym in symbol_manager.get_index_symbols():
        print(f"  {sym}")