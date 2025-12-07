# config/websocket_config.py

"""
WebSocket Configuration for Spot-Futures Arbitrage Strategy
Comprehensive configuration for Fyers WebSocket connections with fallback options
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class WebSocketMode(Enum):
    """WebSocket subscription modes"""
    QUOTES = "quotes"  # Basic quote data
    DEPTH = "depth"  # Market depth data
    FULL = "full"  # Complete market data
    LITE = "lite"  # Minimal data for low bandwidth


class ReconnectionStrategy(Enum):
    """Reconnection strategies"""
    EXPONENTIAL_BACKOFF = "exponential"  # Exponential backoff delays
    FIXED_INTERVAL = "fixed"  # Fixed interval retries
    IMMEDIATE = "immediate"  # Immediate reconnection attempts


@dataclass
class WebSocketConfig:
    """Comprehensive WebSocket configuration for Arbitrage strategy"""

    # Core WebSocket Settings
    websocket_url: str = "wss://api-t1.fyers.in/socket/v2/dataSock"
    fallback_rest_url: str = "https://api-t1.fyers.in/api/v3"

    # Connection Management
    reconnect_interval: int = 5  # Base reconnection interval (seconds)
    max_reconnect_attempts: int = 10  # Maximum reconnection attempts
    connection_timeout: int = 30  # Connection timeout (seconds)
    ping_interval: int = 30  # WebSocket ping interval (seconds)
    pong_timeout: int = 10  # Pong response timeout (seconds)

    # Data Subscription Settings
    subscription_mode: WebSocketMode = WebSocketMode.QUOTES  # Data subscription mode
    enable_heartbeat: bool = True  # Enable WebSocket heartbeat
    buffer_size: int = 8192  # WebSocket buffer size

    # Reconnection Strategy
    reconnection_strategy: ReconnectionStrategy = ReconnectionStrategy.EXPONENTIAL_BACKOFF
    max_backoff_delay: int = 300  # Maximum backoff delay (5 minutes)
    backoff_multiplier: float = 1.5  # Backoff multiplier for exponential strategy

    # Performance Settings
    enable_compression: bool = True  # Enable WebSocket compression
    max_message_size: int = 1048576  # Maximum message size (1MB)
    queue_size: int = 1000  # Internal message queue size

    # Arbitrage Strategy Specific Settings
    spread_update_frequency: int = 1  # Spread calculation frequency (seconds)
    enable_data_validation: bool = True  # Validate incoming data
    symbol_subscription_batch_size: int = 25  # Symbols per subscription batch

    # Fallback Configuration
    enable_rest_fallback: bool = True  # Enable REST API fallback
    rest_polling_interval: int = 5  # REST API polling interval (seconds)
    rest_request_timeout: int = 10  # REST API request timeout
    rest_max_retries: int = 3  # Maximum REST API retries

    # Health Monitoring
    enable_connection_monitoring: bool = True  # Monitor connection health
    health_check_interval: int = 60  # Health check interval (seconds)
    max_missed_heartbeats: int = 3  # Maximum missed heartbeats before reconnect

    # Data Quality Settings
    enable_duplicate_filtering: bool = True  # Filter duplicate messages
    enable_stale_data_detection: bool = True  # Detect stale data
    max_data_age_seconds: int = 10  # Maximum acceptable data age

    # Logging Configuration
    enable_websocket_logging: bool = True  # Enable WebSocket specific logging
    log_all_messages: bool = False  # Log all WebSocket messages (debug only)
    log_connection_events: bool = True  # Log connection/disconnection events
    log_subscription_events: bool = True  # Log symbol subscription events

    # Advanced Settings
    enable_message_compression: bool = False  # Enable individual message compression
    custom_headers: Optional[Dict[str, str]] = None  # Custom WebSocket headers
    enable_ssl_verification: bool = True  # Enable SSL certificate verification

    def __post_init__(self):
        """Validate and process configuration after initialization"""
        self._load_from_environment()
        self._validate_config()
        self._set_derived_config()

    def _load_from_environment(self):
        """Load configuration from environment variables"""
        self.reconnect_interval = int(os.environ.get('WS_RECONNECT_INTERVAL', self.reconnect_interval))
        self.max_reconnect_attempts = int(os.environ.get('WS_MAX_RECONNECT_ATTEMPTS', self.max_reconnect_attempts))
        self.connection_timeout = int(os.environ.get('WS_CONNECTION_TIMEOUT', self.connection_timeout))
        self.ping_interval = int(os.environ.get('WS_PING_INTERVAL', self.ping_interval))
        self.buffer_size = int(os.environ.get('WS_BUFFER_SIZE', self.buffer_size))
        self.queue_size = int(os.environ.get('WS_QUEUE_SIZE', self.queue_size))
        self.enable_rest_fallback = os.environ.get('ENABLE_REST_FALLBACK', 'true').lower() == 'true'
        self.rest_polling_interval = int(os.environ.get('REST_POLLING_INTERVAL', self.rest_polling_interval))
        self.enable_websocket_logging = os.environ.get('ENABLE_WS_LOGGING', 'true').lower() == 'true'

    def _validate_config(self):
        """Validate configuration parameters"""
        if self.reconnect_interval < 1:
            raise ValueError("Reconnect interval must be at least 1 second")
        if self.max_reconnect_attempts < 1:
            raise ValueError("Max reconnect attempts must be at least 1")
        if self.connection_timeout < 5:
            raise ValueError("Connection timeout must be at least 5 seconds")

    def _set_derived_config(self):
        """Set derived configuration parameters"""
        if self.custom_headers is None:
            self.custom_headers = {
                'User-Agent': 'Arbitrage-Trading-Strategy/2.0',
                'Accept': 'application/json',
                'Connection': 'Upgrade'
            }

    def get_reconnect_delay(self, attempt: int) -> int:
        """Calculate reconnect delay based on strategy and attempt number"""
        if self.reconnection_strategy == ReconnectionStrategy.IMMEDIATE:
            return 0
        elif self.reconnection_strategy == ReconnectionStrategy.FIXED_INTERVAL:
            return self.reconnect_interval
        else:  # EXPONENTIAL_BACKOFF
            delay = self.reconnect_interval * (self.backoff_multiplier ** (attempt - 1))
            return min(int(delay), self.max_backoff_delay)


# Predefined configuration profiles
class WebSocketProfiles:
    """Predefined WebSocket configuration profiles"""

    @staticmethod
    def arbitrage_optimized() -> WebSocketConfig:
        """Arbitrage strategy optimized profile"""
        return WebSocketConfig(
            reconnect_interval=5,
            max_reconnect_attempts=10,
            connection_timeout=30,
            ping_interval=30,
            subscription_mode=WebSocketMode.QUOTES,
            enable_rest_fallback=True,
            enable_compression=True,
            buffer_size=8192,
            queue_size=1000,
            spread_update_frequency=1,
            enable_data_validation=True,
            enable_duplicate_filtering=True,
            symbol_subscription_batch_size=25,
            rest_polling_interval=5,
            health_check_interval=60,
            max_data_age_seconds=10
        )

    @staticmethod
    def production() -> WebSocketConfig:
        """Production profile optimized for stability"""
        return WebSocketConfig(
            reconnect_interval=5,
            max_reconnect_attempts=15,
            connection_timeout=30,
            ping_interval=30,
            subscription_mode=WebSocketMode.QUOTES,
            enable_websocket_logging=True,
            log_all_messages=False,
            buffer_size=16384,
            queue_size=2000
        )

    @staticmethod
    def development() -> WebSocketConfig:
        """Development profile with detailed logging"""
        return WebSocketConfig(
            reconnect_interval=3,
            max_reconnect_attempts=5,
            connection_timeout=15,
            ping_interval=20,
            subscription_mode=WebSocketMode.QUOTES,
            enable_websocket_logging=True,
            log_all_messages=True,
            health_check_interval=30
        )


def create_websocket_config(profile: str = "arbitrage_optimized") -> WebSocketConfig:
    """Create WebSocket configuration based on profile name"""
    profile_map = {
        'development': WebSocketProfiles.development,
        'production': WebSocketProfiles.production,
        'arbitrage_optimized': WebSocketProfiles.arbitrage_optimized
    }

    profile_func = profile_map.get(profile.lower())
    if not profile_func:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(profile_map.keys())}")

    return profile_func()