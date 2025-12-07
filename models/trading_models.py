# models/trading_models.py

"""
Trading Models for Spot-Futures Arbitrage Strategy
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from config.settings import SignalType

logger = logging.getLogger(__name__)


@dataclass
class LiveQuote:
    """Real-time quote data"""
    symbol: str
    ltp: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    previous_close: float
    timestamp: datetime
    change: float = 0.0
    change_pct: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: int = 0
    ask_size: int = 0

    def __post_init__(self):
        if self.previous_close > 0:
            self.change = self.ltp - self.previous_close
            self.change_pct = (self.change / self.previous_close) * 100


@dataclass
class SpotFuturesSpread:
    """Spot-Futures spread data"""
    symbol: str
    spot_price: float
    futures_price: float
    spread: float  # Futures - Spot
    spread_pct: float  # (Futures - Spot) / Spot * 100
    basis: float  # Same as spread

    # Volume data
    spot_volume: int
    futures_volume: int
    volume_ratio: float  # Futures volume / Spot volume

    # Timing
    timestamp: datetime
    days_to_expiry: int

    # Historical context
    avg_spread: float = 0.0
    std_spread: float = 0.0
    z_score: float = 0.0  # How many std devs from mean

    # Convergence indicators
    is_converging: bool = False
    convergence_rate: float = 0.0  # Rate of spread narrowing

    def __post_init__(self):
        self.spread = self.futures_price - self.spot_price
        self.spread_pct = (self.spread / self.spot_price) * 100 if self.spot_price > 0 else 0
        self.basis = self.spread

        if self.spot_volume > 0:
            self.volume_ratio = self.futures_volume / self.spot_volume

    @property
    def fair_value_premium(self) -> float:
        """Calculate theoretical fair value premium"""
        # Simplified: Approximately 0.1% per month
        monthly_premium = 0.1
        days_premium = (monthly_premium / 30) * self.days_to_expiry
        return days_premium

    @property
    def mispricing(self) -> float:
        """Calculate mispricing relative to fair value"""
        return self.spread_pct - self.fair_value_premium


@dataclass
class ArbitrageSignal:
    """Arbitrage trading signal"""
    symbol: str
    signal_type: SignalType

    # Spread data
    spot_price: float
    futures_price: float
    spread_pct: float
    mispricing: float

    # Entry parameters
    entry_spot_price: float
    entry_futures_price: float
    target_spread: float
    stop_loss_spread: float

    # Position sizing
    lot_size: int
    quantity: int  # Number of lots
    capital_required: float

    # Signal quality
    confidence: float
    z_score: float
    volume_ratio: float
    convergence_rate: float

    # Timing
    timestamp: datetime
    days_to_expiry: int

    # Risk metrics
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float = field(init=False)

    # Sector
    sector: str = "GENERAL"

    def __post_init__(self):
        if self.risk_amount > 0:
            self.risk_reward_ratio = self.reward_amount / self.risk_amount
        else:
            self.risk_reward_ratio = 0.0


@dataclass
class ArbitragePosition:
    """Arbitrage position tracking"""
    symbol: str
    signal_type: SignalType
    sector: str

    # Position details
    spot_quantity: int  # Positive for long, negative for short
    futures_quantity: int  # Opposite of spot
    lot_size: int

    # Entry prices
    entry_spot_price: float
    entry_futures_price: float
    entry_spread: float
    entry_spread_pct: float

    # Targets and stops
    target_spread: float
    stop_loss_spread: float

    # Timing
    entry_time: datetime
    days_to_expiry: int

    # Order tracking
    spot_order_id: Optional[str] = None
    futures_order_id: Optional[str] = None
    spot_sl_order_id: Optional[str] = None
    futures_sl_order_id: Optional[str] = None

    # Performance tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    spot_pnl: float = 0.0
    futures_pnl: float = 0.0

    # Risk tracking
    max_favorable_spread: float = 0.0
    max_adverse_spread: float = 0.0

    # Current prices
    current_spot_price: float = 0.0
    current_futures_price: float = 0.0
    current_spread: float = 0.0
    current_spread_pct: float = 0.0

    # Targets and stops
    current_stop_spread: float = 0.0  # For trailing

    def __post_init__(self):
        self.current_stop_spread = self.stop_loss_spread

    def update_current_prices(self, spot_price: float, futures_price: float):
        """Update with current market prices"""
        self.current_spot_price = spot_price
        self.current_futures_price = futures_price
        self.current_spread = futures_price - spot_price
        self.current_spread_pct = (self.current_spread / spot_price) * 100 if spot_price > 0 else 0

        # Calculate P&L
        self._calculate_pnl()

        # Update spread extremes
        if self.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
            # Profitable if spread narrows
            self.max_favorable_spread = min(self.max_favorable_spread or float('inf'), self.current_spread)
            self.max_adverse_spread = max(self.max_adverse_spread or -float('inf'), self.current_spread)
        else:
            # Profitable if spread widens
            self.max_favorable_spread = max(self.max_favorable_spread or -float('inf'), self.current_spread)
            self.max_adverse_spread = min(self.max_adverse_spread or float('inf'), self.current_spread)

    def _calculate_pnl(self):
        """Calculate position P&L"""
        # Spot P&L
        if self.spot_quantity > 0:
            self.spot_pnl = (self.current_spot_price - self.entry_spot_price) * self.spot_quantity
        else:
            self.spot_pnl = (self.entry_spot_price - self.current_spot_price) * abs(self.spot_quantity)

        # Futures P&L
        if self.futures_quantity > 0:
            self.futures_pnl = (self.current_futures_price - self.entry_futures_price) * self.futures_quantity
        else:
            self.futures_pnl = (self.entry_futures_price - self.current_futures_price) * abs(self.futures_quantity)

        # Total unrealized P&L
        self.unrealized_pnl = self.spot_pnl + self.futures_pnl


@dataclass
class ArbitrageTradeResult:
    """Completed arbitrage trade result"""
    symbol: str
    signal_type: SignalType
    sector: str

    # Entry/Exit details
    entry_spot_price: float
    entry_futures_price: float
    entry_spread: float

    exit_spot_price: float
    exit_futures_price: float
    exit_spread: float

    # Position details
    quantity: int  # Number of lots
    lot_size: int

    # Timing
    entry_time: datetime
    exit_time: datetime
    holding_period: float  # minutes
    days_to_expiry_at_entry: int
    days_to_expiry_at_exit: int

    # Performance
    gross_pnl: float
    spot_pnl: float
    futures_pnl: float
    net_pnl: float = field(init=False)

    # Spread metrics
    spread_change: float  # Change in spread
    spread_change_pct: float

    # Exit reason
    exit_reason: str  # "TARGET", "STOP_LOSS", "EXPIRY", "TIME_EXIT"

    # Risk metrics
    max_favorable_spread: float
    max_adverse_spread: float

    # Costs
    commission: float = 0.0
    slippage: float = 0.0

    def __post_init__(self):
        self.net_pnl = self.gross_pnl - self.commission - self.slippage
        self.holding_period = (self.exit_time - self.entry_time).total_seconds() / 60
        self.spread_change = self.exit_spread - self.entry_spread
        self.spread_change_pct = (self.spread_change / self.entry_spread) * 100 if self.entry_spread != 0 else 0


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0

    # Arbitrage specific
    avg_spread_captured: float = 0.0
    avg_holding_period: float = 0.0

    # By signal type
    long_spot_trades: int = 0
    short_spot_trades: int = 0
    long_spot_win_rate: float = 0.0
    short_spot_win_rate: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    # Recent performance
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0

    def update_metrics(self, trades: List[ArbitrageTradeResult]):
        """Update metrics from trade list"""
        if not trades:
            return

        self.total_trades = len(trades)
        self.winning_trades = sum(1 for t in trades if t.net_pnl > 0)
        self.losing_trades = self.total_trades - self.winning_trades
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

        self.total_pnl = sum(t.net_pnl for t in trades)
        self.gross_profit = sum(t.net_pnl for t in trades if t.net_pnl > 0)
        self.gross_loss = sum(t.net_pnl for t in trades if t.net_pnl < 0)

        # Arbitrage specific
        self.avg_spread_captured = sum(abs(t.spread_change) for t in trades) / len(trades)
        self.avg_holding_period = sum(t.holding_period for t in trades) / len(trades)

        # By signal type
        long_spot_trades_list = [t for t in trades if t.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES]
        short_spot_trades_list = [t for t in trades if t.signal_type == SignalType.SHORT_SPOT_LONG_FUTURES]

        self.long_spot_trades = len(long_spot_trades_list)
        self.short_spot_trades = len(short_spot_trades_list)

        if self.long_spot_trades > 0:
            self.long_spot_win_rate = (sum(1 for t in long_spot_trades_list if t.net_pnl > 0) / self.long_spot_trades) * 100

        if self.short_spot_trades > 0:
            self.short_spot_win_rate = (sum(1 for t in short_spot_trades_list if t.net_pnl > 0) / self.short_spot_trades) * 100


@dataclass
class MarketState:
    """Current market state"""
    timestamp: datetime

    # Market indicators
    nifty_change_pct: float = 0.0
    market_trend: str = "NEUTRAL"
    volatility_regime: str = "NORMAL"

    # Volume indicators
    market_volume_ratio: float = 1.0

    # Arbitrage specific
    avg_basis: float = 0.0  # Average basis across all pairs
    basis_std: float = 0.0  # Basis volatility

    # Strategy state
    max_positions_reached: bool = False
    daily_loss_limit_hit: bool = False
    near_expiry_mode: bool = False  # Special handling near expiry


# Utility functions
def create_arbitrage_signal_from_spread(
        symbol: str,
        spread_data: SpotFuturesSpread,
        signal_type: SignalType,
        quantity: int,
        lot_size: int,
        **kwargs
) -> ArbitrageSignal:
    """Create arbitrage signal from spread data"""
    return ArbitrageSignal(
        symbol=symbol,
        signal_type=signal_type,
        spot_price=spread_data.spot_price,
        futures_price=spread_data.futures_price,
        spread_pct=spread_data.spread_pct,
        mispricing=spread_data.mispricing,
        entry_spot_price=spread_data.spot_price,
        entry_futures_price=spread_data.futures_price,
        lot_size=lot_size,
        quantity=quantity,
        timestamp=spread_data.timestamp,
        days_to_expiry=spread_data.days_to_expiry,
        z_score=spread_data.z_score,
        volume_ratio=spread_data.volume_ratio,
        convergence_rate=spread_data.convergence_rate,
        **kwargs
    )


def create_position_from_signal(signal: ArbitrageSignal, **kwargs) -> ArbitragePosition:
    """Create position from signal"""
    # Determine quantities based on signal type
    if signal.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
        spot_qty = signal.lot_size * signal.quantity
        futures_qty = -signal.lot_size * signal.quantity
    else:
        spot_qty = -signal.lot_size * signal.quantity
        futures_qty = signal.lot_size * signal.quantity

    return ArbitragePosition(
        symbol=signal.symbol,
        signal_type=signal.signal_type,
        sector=signal.sector,
        spot_quantity=spot_qty,
        futures_quantity=futures_qty,
        lot_size=signal.lot_size,
        entry_spot_price=signal.entry_spot_price,
        entry_futures_price=signal.entry_futures_price,
        entry_spread=signal.futures_price - signal.spot_price,
        entry_spread_pct=signal.spread_pct,
        target_spread=signal.target_spread,
        stop_loss_spread=signal.stop_loss_spread,
        entry_time=datetime.now(),
        days_to_expiry=signal.days_to_expiry,
        **kwargs
    )


def create_trade_result_from_position(
        position: ArbitragePosition,
        exit_spot_price: float,
        exit_futures_price: float,
        exit_reason: str
) -> ArbitrageTradeResult:
    """Create trade result from closed position"""
    # Calculate final P&L
    exit_spread = exit_futures_price - exit_spot_price

    # Spot P&L
    if position.spot_quantity > 0:
        spot_pnl = (exit_spot_price - position.entry_spot_price) * position.spot_quantity
    else:
        spot_pnl = (position.entry_spot_price - exit_spot_price) * abs(position.spot_quantity)

    # Futures P&L
    if position.futures_quantity > 0:
        futures_pnl = (exit_futures_price - position.entry_futures_price) * position.futures_quantity
    else:
        futures_pnl = (position.entry_futures_price - exit_futures_price) * abs(position.futures_quantity)

    return ArbitrageTradeResult(
        symbol=position.symbol,
        signal_type=position.signal_type,
        sector=position.sector,
        entry_spot_price=position.entry_spot_price,
        entry_futures_price=position.entry_futures_price,
        entry_spread=position.entry_spread,
        exit_spot_price=exit_spot_price,
        exit_futures_price=exit_futures_price,
        exit_spread=exit_spread,
        quantity=abs(position.spot_quantity) // position.lot_size,
        lot_size=position.lot_size,
        entry_time=position.entry_time,
        exit_time=datetime.now(),
        days_to_expiry_at_entry=position.days_to_expiry,
        days_to_expiry_at_exit=position.days_to_expiry,  # Would be updated
        gross_pnl=spot_pnl + futures_pnl,
        spot_pnl=spot_pnl,
        futures_pnl=futures_pnl,
        exit_reason=exit_reason,
        max_favorable_spread=position.max_favorable_spread,
        max_adverse_spread=position.max_adverse_spread
    )


def calculate_portfolio_risk(
        positions: List[ArbitragePosition],
        portfolio_value: float
) -> Dict[str, float]:
    """Calculate portfolio risk metrics"""
    total_capital_deployed = sum(
        abs(pos.entry_spot_price * pos.spot_quantity) +
        abs(pos.entry_futures_price * pos.futures_quantity)
        for pos in positions
    )

    total_unrealized = sum(pos.unrealized_pnl for pos in positions)

    return {
        'total_capital_deployed': total_capital_deployed,
        'capital_usage_pct': (total_capital_deployed / portfolio_value) * 100 if portfolio_value > 0 else 0,
        'total_unrealized_pnl': total_unrealized,
        'unrealized_pnl_pct': (total_unrealized / total_capital_deployed) * 100 if total_capital_deployed > 0 else 0,
        'average_capital_per_position': total_capital_deployed / len(positions) if positions else 0
    }