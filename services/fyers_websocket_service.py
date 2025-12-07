# services/fyers_websocket_service.py

"""
Enhanced Fyers WebSocket service for Spot-Futures Arbitrage strategy
Handles real-time data for both spot and futures instruments
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Optional
from datetime import datetime
from collections import defaultdict

# Import the official Fyers API
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

from config.settings import FyersConfig
from config.websocket_config import WebSocketConfig
from config.symbols import get_arbitrage_pairs, get_spot_symbol, get_futures_symbol
from models.trading_models import LiveQuote, SpotFuturesSpread

logger = logging.getLogger(__name__)


class ArbitrageWebSocketService:
    """Enhanced WebSocket service for Arbitrage strategy"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config

        # Connection state
        self.is_connected = False
        self.reconnect_count = 0

        # Data management
        self.subscribed_symbols = set()
        self.live_quotes: Dict[str, LiveQuote] = {}
        self.data_callbacks: List[Callable] = []

        # Arbitrage specific data
        self.spread_data: Dict[str, SpotFuturesSpread] = {}
        self.arbitrage_pairs = get_arbitrage_pairs()

        # Fyers WebSocket instance
        self.fyers_socket = None

    def connect(self) -> bool:
        """Connect using official Fyers WebSocket"""
        try:
            logger.info("Connecting to Fyers WebSocket for Arbitrage strategy...")

            # Create Fyers WebSocket instance
            self.fyers_socket = data_ws.FyersDataSocket(
                access_token=self.fyers_config.access_token,
                log_path="",
                litemode=False,
                write_to_file=False,
                reconnect=True,
                reconnect_retry=self.ws_config.max_reconnect_attempts,
                on_message=self._on_message,
                on_connect=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error
            )

            # Start connection in background thread
            self._start_connection_thread()

            # Wait for connection
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < self.ws_config.connection_timeout:
                time.sleep(0.1)

            if self.is_connected:
                logger.info("Fyers WebSocket connected successfully for Arbitrage strategy")
                return True
            else:
                logger.error("Fyers WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Fyers WebSocket: {e}")
            return False

    def _start_connection_thread(self):
        """Start WebSocket connection in background thread"""

        def run_connection():
            try:
                self.fyers_socket.connect()
            except Exception as e:
                logger.error(f"Connection thread error: {e}")

        connection_thread = threading.Thread(target=run_connection)
        connection_thread.daemon = True
        connection_thread.start()

    def disconnect(self):
        """Disconnect from Fyers WebSocket"""
        try:
            self.is_connected = False
            if self.fyers_socket:
                self.fyers_socket.close_connection()
            logger.info("Fyers WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def subscribe_arbitrage_pairs(self) -> bool:
        """Subscribe to all spot-futures pairs"""
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False

            # Get all symbols (both spot and futures)
            all_symbols = []
            for pair in self.arbitrage_pairs:
                spot_symbol = get_spot_symbol(pair['spot'])
                futures_symbol = get_futures_symbol(pair['futures'])

                if spot_symbol:
                    all_symbols.append(spot_symbol)
                    self.subscribed_symbols.add(pair['spot'])

                if futures_symbol:
                    all_symbols.append(futures_symbol)
                    self.subscribed_symbols.add(pair['futures'])

            if not all_symbols:
                logger.error("No valid symbols to subscribe")
                return False

            # Subscribe using official API
            self.fyers_socket.subscribe(symbols=all_symbols, data_type="SymbolUpdate")

            logger.info(f"Subscribed to {len(all_symbols)} symbols ({len(self.arbitrage_pairs)} pairs)")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False

    def get_spread(self, pair_name: str) -> Optional[SpotFuturesSpread]:
        """Get calculated spread for a pair"""
        return self.spread_data.get(pair_name)

    def get_all_spreads(self) -> Dict[str, SpotFuturesSpread]:
        """Get all calculated spreads"""
        return self.spread_data.copy()

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get latest live quote"""
        return self.live_quotes.get(symbol)

    def add_data_callback(self, callback: Callable):
        """Add callback for data updates"""
        self.data_callbacks.append(callback)

    def _on_open(self):
        """WebSocket opened"""
        self.is_connected = True
        self.reconnect_count = 0
        logger.info("Fyers WebSocket opened for Arbitrage strategy")

    def _on_close(self, message):
        """WebSocket closed"""
        self.is_connected = False
        logger.warning(f"Fyers WebSocket closed: {message}")

    def _on_error(self, message):
        """WebSocket error"""
        self.is_connected = False
        logger.error(f"Fyers WebSocket error: {message}")

    def _on_message(self, message):
        """Handle incoming message from Fyers WebSocket"""
        try:
            self._process_fyers_data(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _process_fyers_data(self, data):
        """Process data from Fyers WebSocket"""
        try:
            if isinstance(data, dict):
                symbol_data = data.get('symbol', '')

                # Extract base symbol from Fyers format
                display_symbol = self._extract_display_symbol(symbol_data)

                if display_symbol and isinstance(data, dict):
                    # Create LiveQuote from Fyers data
                    live_quote = LiveQuote(
                        symbol=display_symbol,
                        ltp=float(data.get('ltp', data.get('last_price', 0))),
                        open_price=float(data.get('open_price', data.get('open', 0))),
                        high_price=float(data.get('high_price', data.get('high', 0))),
                        low_price=float(data.get('low_price', data.get('low', 0))),
                        volume=int(data.get('volume', data.get('vol_traded_today', 0))),
                        previous_close=float(data.get('prev_close_price', data.get('prev_close', 0))),
                        timestamp=datetime.now()
                    )

                    # Update storage
                    self.live_quotes[display_symbol] = live_quote

                    # Calculate spreads
                    self._calculate_spreads(display_symbol, live_quote)

                    # Notify callbacks
                    for callback in self.data_callbacks:
                        try:
                            callback(display_symbol, live_quote)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

        except Exception as e:
            logger.error(f"Error processing Fyers data: {e}")

    def _extract_display_symbol(self, fyers_symbol: str) -> Optional[str]:
        """Extract display symbol from Fyers format"""
        try:
            # Remove exchange prefix and suffix
            # Example: "NSE:RELIANCE-EQ" -> "RELIANCE"
            if ':' in fyers_symbol:
                symbol_part = fyers_symbol.split(':')[1]
                # Remove suffix like -EQ, -FUT
                if '-' in symbol_part:
                    return symbol_part.split('-')[0]
                return symbol_part
            return fyers_symbol
        except:
            return None

    def _calculate_spreads(self, updated_symbol: str, live_quote: LiveQuote):
        """Calculate spreads when data is updated"""
        try:
            # Find which pairs this symbol belongs to
            for pair in self.arbitrage_pairs:
                spot_key = pair['spot']
                futures_key = pair['futures']

                # Check if this is a spot or futures update for this pair
                if spot_key in updated_symbol or futures_key in updated_symbol:
                    spot_quote = self.live_quotes.get(spot_key)
                    futures_quote = self.live_quotes.get(futures_key)

                    if spot_quote and futures_quote:
                        # Calculate spread
                        spread = self._compute_spread(
                            pair_name=spot_key,
                            spot_quote=spot_quote,
                            futures_quote=futures_quote,
                            pair_info=pair
                        )

                        if spread:
                            self.spread_data[spot_key] = spread

        except Exception as e:
            logger.error(f"Error calculating spreads: {e}")

    def _compute_spread(self, pair_name: str, spot_quote: LiveQuote,
                        futures_quote: LiveQuote, pair_info: dict) -> Optional[SpotFuturesSpread]:
        """Compute spread between spot and futures"""
        try:
            from models.trading_models import SpotFuturesSpread

            # Basic spread calculation
            spread_value = futures_quote.ltp - spot_quote.ltp
            spread_pct = (spread_value / spot_quote.ltp) * 100 if spot_quote.ltp > 0 else 0

            # Volume ratio
            volume_ratio = futures_quote.volume / spot_quote.volume if spot_quote.volume > 0 else 0

            spread = SpotFuturesSpread(
                pair_name=pair_name,
                spot_symbol=pair_info['spot'],
                futures_symbol=pair_info['futures'],
                spot_price=spot_quote.ltp,
                futures_price=futures_quote.ltp,
                spread_value=spread_value,
                spread_pct=spread_pct,
                spot_volume=spot_quote.volume,
                futures_volume=futures_quote.volume,
                volume_ratio=volume_ratio,
                timestamp=datetime.now()
            )

            return spread

        except Exception as e:
            logger.error(f"Error computing spread for {pair_name}: {e}")
            return None


# REST API Fallback Service
class ArbitrageFallbackDataService:
    """Fallback service using REST API"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config
        self.is_connected = False
        self.subscribed_symbols = set()
        self.live_quotes: Dict[str, LiveQuote] = {}
        self.spread_data: Dict[str, SpotFuturesSpread] = {}
        self.data_callbacks: List[Callable] = []

        self.fyers = fyersModel.FyersModel(
            client_id=fyers_config.client_id,
            token=fyers_config.access_token
        )

        self.polling_thread = None
        self.stop_event = threading.Event()

    def connect(self) -> bool:
        """Start fallback data service"""
        try:
            logger.info("Starting Arbitrage fallback REST API data service...")
            profile = self.fyers.get_profile()

            if profile.get('s') != 'ok':
                logger.error("Fyers API authentication failed")
                return False

            logger.info(f"Connected to Fyers API - User: {profile.get('data', {}).get('name', 'Unknown')}")
            self.is_connected = True
            self._start_polling()
            return True

        except Exception as e:
            logger.error(f"Fallback connection error: {e}")
            return False

    def _start_polling(self):
        """Start polling thread"""
        self.polling_thread = threading.Thread(target=self._poll_data)
        self.polling_thread.daemon = True
        self.polling_thread.start()

    def _poll_data(self):
        """Poll for data"""
        while not self.stop_event.is_set() and self.is_connected:
            try:
                if self.subscribed_symbols:
                    self._fetch_quotes()
                time.sleep(self.ws_config.rest_polling_interval)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(10)

    def _fetch_quotes(self):
        """Fetch quotes via REST API"""
        # Implementation similar to ORB fallback service
        pass

    def subscribe_arbitrage_pairs(self) -> bool:
        """Subscribe to arbitrage pairs"""
        pairs = get_arbitrage_pairs()
        for pair in pairs:
            self.subscribed_symbols.add(pair['spot'])
            self.subscribed_symbols.add(pair['futures'])
        logger.info(f"Subscribed to {len(self.subscribed_symbols)} symbols in fallback mode")
        return True

    def add_data_callback(self, callback: Callable):
        """Add data callback"""
        self.data_callbacks.append(callback)

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get live quote"""
        return self.live_quotes.get(symbol)

    def get_spread(self, pair_name: str) -> Optional[SpotFuturesSpread]:
        """Get spread data"""
        return self.spread_data.get(pair_name)

    def get_all_spreads(self) -> Dict[str, SpotFuturesSpread]:
        """Get all spreads"""
        return self.spread_data.copy()

    def disconnect(self):
        """Disconnect fallback service"""
        self.stop_event.set()
        self.is_connected = False


# Hybrid service
class HybridArbitrageDataService:
    """Hybrid service that tries WebSocket first, falls back to REST API"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config
        self.primary_service = None
        self.fallback_service = None
        self.using_fallback = False
        self.is_connected = False
        self.data_callbacks = []

    def connect(self) -> bool:
        """Try WebSocket first, fallback to REST API"""
        logger.info("Attempting hybrid Arbitrage connection (WebSocket -> REST fallback)")

        # Try WebSocket first
        try:
            self.primary_service = ArbitrageWebSocketService(self.fyers_config, self.ws_config)
            if self.primary_service.connect():
                logger.info("Using WebSocket service for Arbitrage strategy")
                self.is_connected = True
                self._setup_callbacks(self.primary_service)
                return True
        except Exception as e:
            logger.warning(f"Arbitrage WebSocket failed: {e}")

        # Fallback to REST API
        try:
            logger.info("Falling back to REST API polling for Arbitrage strategy...")
            self.fallback_service = ArbitrageFallbackDataService(self.fyers_config, self.ws_config)
            if self.fallback_service.connect():
                logger.info("Using REST API fallback for Arbitrage strategy")
                self.using_fallback = True
                self.is_connected = True
                self._setup_callbacks(self.fallback_service)
                return True
        except Exception as e:
            logger.error(f"Arbitrage Fallback also failed: {e}")

        return False

    def _setup_callbacks(self, service):
        """Setup callbacks for the active service"""
        for callback in self.data_callbacks:
            service.add_data_callback(callback)

    def subscribe_arbitrage_pairs(self) -> bool:
        """Subscribe using active service"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        if active_service:
            return active_service.subscribe_arbitrage_pairs()
        return False

    def add_data_callback(self, callback: Callable):
        """Add callback"""
        self.data_callbacks.append(callback)
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        if active_service:
            active_service.add_data_callback(callback)

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get live quote"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        return active_service.get_live_quote(symbol) if active_service else None

    def get_spread(self, pair_name: str) -> Optional[SpotFuturesSpread]:
        """Get spread data"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        return active_service.get_spread(pair_name) if active_service else None

    def get_all_spreads(self) -> Dict[str, SpotFuturesSpread]:
        """Get all spreads"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        return active_service.get_all_spreads() if active_service else {}

    def disconnect(self):
        """Disconnect active service"""
        if self.primary_service:
            self.primary_service.disconnect()
        if self.fallback_service:
            self.fallback_service.disconnect()
        self.is_connected = False