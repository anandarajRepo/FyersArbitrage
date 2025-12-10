# strategy/arbitrage_strategy.py

"""
Spot-Futures Arbitrage Strategy Implementation
Z-Score Based Strategy - Matching Arbitrage.py Backtest

Strategy Logic:
1. Calculate basis = futures_price - spot_price
2. Calculate basis % = (basis / spot_price) * 100
3. Calculate rolling mean and std of basis %
4. Calculate z-score = (basis % - mean) / std
5. ENTRY: |z-score| > entry_threshold (2.0 default)
6. EXIT: |z-score| < exit_threshold (0.5 default) OR stop loss OR square-off
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, time
from collections import defaultdict

from config.settings import (
    FyersConfig, ArbitrageStrategyConfig, TradingConfig, SignalType
)
from config.symbols import symbol_manager, get_arbitrage_symbols
from services.analysis_service import ZScoreArbitrageAnalyzer
from models.trading_models import (
    LiveQuote, SpotFuturesSpread, ArbitrageSignal, ArbitragePosition,
    ArbitrageTradeResult, StrategyMetrics, MarketState,
    create_position_from_signal, create_trade_result_from_position,
    calculate_portfolio_risk
)

logger = logging.getLogger(__name__)


class SpotFuturesArbitrageStrategy:
    """
    Z-Score Based Spot-Futures Arbitrage Strategy

    Entry Signals:
    - Long Futures + Short Spot: z-score < -2.0 (futures underpriced)
    - Short Futures + Long Spot: z-score > +2.0 (futures overpriced)

    Exit Signals:
    - Basis Convergence: |z-score| < 0.5
    - Stop Loss: Loss exceeds 1% of position value
    - Square-off: 3:20 PM IST
    - Expiry: 3 days before contract expiry
    """

    def __init__(
            self,
            fyers_config: FyersConfig,
            strategy_config: ArbitrageStrategyConfig,
            trading_config: TradingConfig
    ):
        self.fyers_config = fyers_config
        self.strategy_config = strategy_config
        self.trading_config = trading_config

        # Initialize Z-Score Analyzer
        self.analyzer = ZScoreArbitrageAnalyzer(strategy_config)

        # Strategy state
        self.positions: Dict[str, ArbitragePosition] = {}
        self.completed_trades: List[ArbitrageTradeResult] = []
        self.metrics = StrategyMetrics()
        self.market_state = MarketState(timestamp=datetime.now())

        # Current market data
        self.current_spreads: Dict[str, SpotFuturesSpread] = {}
        self.spot_quotes: Dict[str, LiveQuote] = {}
        self.futures_quotes: Dict[str, LiveQuote] = {}

        # Trading universe
        self.trading_symbols = get_arbitrage_symbols()

        # Performance tracking
        self.daily_pnl = 0.0
        self.max_daily_loss = strategy_config.portfolio_value * 0.03  # 3% max loss

        # Square-off time
        self.square_off_time = time(
            trading_config.square_off_hour,
            trading_config.square_off_minute
        )

        logger.info("=" * 80)
        logger.info("Z-SCORE BASED SPOT-FUTURES ARBITRAGE STRATEGY")
        logger.info("=" * 80)
        logger.info(f"Trading Universe: {len(self.trading_symbols)} pairs")
        logger.info(f"Portfolio Value: ₹{strategy_config.portfolio_value:,}")
        logger.info(f"Max Positions: {strategy_config.max_positions}")
        logger.info(f"Basis Lookback: {strategy_config.basis_lookback} periods")
        logger.info(f"Entry Z-Score: ±{strategy_config.entry_zscore_threshold}")
        logger.info(f"Exit Z-Score: ±{strategy_config.exit_zscore_threshold}")
        logger.info(f"Stop Loss: {strategy_config.stop_loss_pct}%")
        logger.info(f"Square-off Time: {self.square_off_time.strftime('%H:%M')} IST")
        logger.info("=" * 80)

    async def initialize(self) -> bool:
        """Initialize strategy and connections"""
        try:
            logger.info("Initializing Z-Score Arbitrage Strategy...")

            # Initialize data services (WebSocket connection)
            # self.data_service = await self._initialize_data_service()

            # Initialize order manager
            # self.order_manager = OrderManager(self.fyers_config)

            # Subscribe to symbols
            # await self._subscribe_to_symbols()

            logger.info("✓ Z-Score Arbitrage Strategy initialized successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Strategy initialization failed: {e}")
            return False

    def update_market_data(self, symbol: str, spot_quote: LiveQuote, futures_quote: LiveQuote):
        """
        Update market data and calculate spread
        Called when new tick data arrives
        """
        try:
            # Store quotes
            self.spot_quotes[symbol] = spot_quote
            self.futures_quotes[symbol] = futures_quote

            # Calculate spread
            spread = self._calculate_spread(symbol, spot_quote, futures_quote)
            if spread:
                self.current_spreads[symbol] = spread

                # Update analyzer's basis history
                self.analyzer.update_basis_history(symbol, spread.spread_pct)

        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {e}")

    def _calculate_spread(
            self,
            symbol: str,
            spot_quote: LiveQuote,
            futures_quote: LiveQuote
    ) -> Optional[SpotFuturesSpread]:
        """Calculate spot-futures spread"""
        try:
            # Get contract info
            contract = symbol_manager.get_contract_info(symbol)
            if not contract:
                return None

            # Calculate basis (matching backtest)
            basis = futures_quote.ltp - spot_quote.ltp
            basis_pct = (basis / spot_quote.ltp) * 100 if spot_quote.ltp > 0 else 0

            # Calculate volume ratio
            volume_ratio = (futures_quote.volume / spot_quote.volume
                            if spot_quote.volume > 0 else 0)

            # Create spread object
            spread = SpotFuturesSpread(
                symbol=symbol,
                spot_price=spot_quote.ltp,
                futures_price=futures_quote.ltp,
                spread=basis,
                spread_pct=basis_pct,
                basis=basis,
                spot_volume=spot_quote.volume,
                futures_volume=futures_quote.volume,
                volume_ratio=volume_ratio,
                timestamp=datetime.now(),
                days_to_expiry=contract.days_to_expiry
            )

            # Calculate statistics using analyzer
            stats = self.analyzer.calculate_basis_statistics(symbol, basis_pct)

            if stats.get('has_sufficient_data'):
                spread.avg_spread = stats['mean']
                spread.std_spread = stats['std']
                spread.z_score = stats['z_score']

            return spread

        except Exception as e:
            logger.error(f"Error calculating spread for {symbol}: {e}")
            return None

    def scan_for_signals(self) -> List[ArbitrageSignal]:
        """
        Scan all pairs for arbitrage signals
        Uses z-score based entry logic
        """
        signals = []

        try:
            for symbol in self.trading_symbols:
                # Skip if already have position
                if symbol in self.positions:
                    continue

                # Get current spread
                spread = self.current_spreads.get(symbol)
                if not spread:
                    continue

                # Calculate statistics
                stats = self.analyzer.calculate_basis_statistics(symbol, spread.spread_pct)

                # Generate signal if z-score threshold crossed
                signal = self.analyzer.generate_entry_signal(symbol, spread, stats)

                if signal:
                    signals.append(signal)
                    logger.info(f"✓ Signal generated: {symbol} | "
                                f"Type: {signal.signal_type.value} | "
                                f"Z-Score: {signal.z_score:.2f} | "
                                f"Confidence: {signal.confidence:.2f}")

        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")

        return signals

    async def execute_signal(self, signal: ArbitrageSignal) -> bool:
        """Execute arbitrage signal"""
        try:
            logger.info(f"Executing arbitrage signal: {signal.symbol}")
            logger.info(f"  Type: {signal.signal_type.value}")
            logger.info(f"  Spot: ₹{signal.spot_price:.2f} | Futures: ₹{signal.futures_price:.2f}")
            logger.info(f"  Basis: {signal.spread_pct:.3f}% | Z-Score: {signal.z_score:.2f}")

            # Create position from signal
            position = create_position_from_signal(signal)

            # Place orders (to be implemented with order manager)
            # success = await self.order_manager.place_arbitrage_orders(position)

            # For now, just track position
            self.positions[signal.symbol] = position

            logger.info(f"✓ Position opened: {signal.symbol}")
            return True

        except Exception as e:
            logger.error(f"✗ Error executing signal for {signal.symbol}: {e}")
            return False

    async def monitor_positions(self):
        """Monitor existing positions for exit signals"""
        try:
            positions_to_close = []
            current_time = datetime.now()

            for symbol, position in self.positions.items():
                # Get current spread
                spread = self.current_spreads.get(symbol)
                if not spread:
                    continue

                # Update position with current prices
                position.update_current_prices(spread.spot_price, spread.futures_price)

                # Check mandatory square-off time (3:20 PM IST)
                if current_time.time() >= self.square_off_time:
                    positions_to_close.append((symbol, "SQUARE_OFF_3:20PM"))
                    continue

                # Check expiry proximity
                if position.days_to_expiry <= self.strategy_config.days_before_expiry_to_exit:
                    positions_to_close.append((symbol, "EXPIRY_EXIT"))
                    continue

                # Check z-score based exit and stop loss
                should_exit, exit_reason = self.analyzer.check_exit_signal(
                    symbol, position, spread
                )

                if should_exit:
                    positions_to_close.append((symbol, exit_reason))

            # Close positions
            for symbol, reason in positions_to_close:
                await self._close_position(symbol, reason)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    async def _close_position(self, symbol: str, reason: str):
        """Close arbitrage position"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return

            spread = self.current_spreads.get(symbol)
            if not spread:
                logger.warning(f"Cannot close {symbol} - missing spread data")
                return

            logger.info(f"Closing position: {symbol} - Reason: {reason}")
            logger.info(f"  Entry Spread: {position.entry_spread_pct:.3f}% | "
                        f"Current Spread: {spread.spread_pct:.3f}%")
            logger.info(f"  Entry Z-Score: {position.entry_z_score:.2f} | "
                        f"Current Z-Score: {spread.z_score:.2f}")
            logger.info(f"  Unrealized P&L: ₹{position.unrealized_pnl:.2f}")

            # Create trade result
            trade_result = create_trade_result_from_position(
                position=position,
                exit_spot_price=spread.spot_price,
                exit_futures_price=spread.futures_price,
                exit_reason=reason
            )

            # Update daily P&L
            self.daily_pnl += trade_result.net_pnl

            # Store completed trade
            self.completed_trades.append(trade_result)

            # Remove position
            del self.positions[symbol]

            # Log result
            result_symbol = "✓" if trade_result.net_pnl > 0 else "✗"
            logger.info(f"{result_symbol} Position closed: {symbol}")
            logger.info(f"  Net P&L: ₹{trade_result.net_pnl:.2f}")
            logger.info(f"  Holding Period: {trade_result.holding_period:.1f} minutes")

            # Place exit orders (to be implemented)
            # await self.order_manager.close_arbitrage_position(position)

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

    def should_scan_for_opportunities(self) -> bool:
        """Check if we should scan for new opportunities"""
        # Check position limit
        if len(self.positions) >= self.strategy_config.max_positions:
            return False

        # Check daily loss limit
        if self.daily_pnl < -abs(self.max_daily_loss):
            logger.warning(f"Daily loss limit reached: ₹{self.daily_pnl:.2f}")
            return False

        # Don't open new positions near market close (after 3:00 PM)
        current_time = datetime.now()
        if current_time.hour >= 15:
            return False

        return True

    async def run_strategy_cycle(self):
        """Main strategy cycle - runs periodically"""
        try:
            # 1. Monitor existing positions
            await self.monitor_positions()

            # 2. Scan for new opportunities (if allowed)
            if self.should_scan_for_opportunities():
                signals = self.scan_for_signals()

                # Sort by z-score magnitude (higher = better)
                signals.sort(key=lambda x: abs(x.z_score), reverse=True)

                # Execute top signals (up to max positions)
                available_slots = self.strategy_config.max_positions - len(self.positions)
                for signal in signals[:available_slots]:
                    await self.execute_signal(signal)

            # 3. Update metrics
            self._update_metrics()

            # 4. Log status periodically
            self._log_status()

        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")

    def _update_metrics(self):
        """Update strategy performance metrics"""
        self.metrics.update_metrics(self.completed_trades)
        self.metrics.daily_pnl = self.daily_pnl

        # Update market state
        self.market_state.timestamp = datetime.now()
        self.market_state.max_positions_reached = (
                len(self.positions) >= self.strategy_config.max_positions
        )
        self.market_state.daily_loss_limit_hit = (
                self.daily_pnl < -abs(self.max_daily_loss)
        )

    def _log_status(self):
        """Log current strategy status"""
        if not hasattr(self, '_last_status_log'):
            self._last_status_log = datetime.now()

        # Log every 5 minutes
        if (datetime.now() - self._last_status_log).seconds >= 300:
            logger.info("=" * 60)
            logger.info("STRATEGY STATUS")
            logger.info(f"Active Positions: {len(self.positions)}/{self.strategy_config.max_positions}")
            logger.info(f"Daily P&L: ₹{self.daily_pnl:.2f}")
            logger.info(f"Total Trades: {len(self.completed_trades)}")
            logger.info(f"Win Rate: {self.metrics.win_rate:.1f}%")

            # Show active positions
            if self.positions:
                logger.info("\nActive Positions:")
                for symbol, pos in self.positions.items():
                    spread = self.current_spreads.get(symbol)
                    z_score = spread.z_score if spread else 0
                    logger.info(f"  {symbol}: Z={z_score:.2f}, P&L=₹{pos.unrealized_pnl:.2f}")

            logger.info("=" * 60)
            self._last_status_log = datetime.now()

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())

        risk_metrics = calculate_portfolio_risk(
            list(self.positions.values()),
            self.strategy_config.portfolio_value
        )

        return {
            'strategy_name': 'Z-Score Spot-Futures Arbitrage',
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': self.strategy_config.portfolio_value,
            'total_pnl': self.metrics.total_pnl,
            'daily_pnl': self.daily_pnl,
            'unrealized_pnl': total_unrealized,
            'active_positions': len(self.positions),
            'max_positions': self.strategy_config.max_positions,
            'completed_trades': len(self.completed_trades),
            'win_rate': self.metrics.win_rate,
            'avg_spread_captured': self.metrics.avg_spread_captured,
            'risk_metrics': risk_metrics,
            'config': {
                'basis_lookback': self.strategy_config.basis_lookback,
                'entry_zscore': self.strategy_config.entry_zscore_threshold,
                'exit_zscore': self.strategy_config.exit_zscore_threshold,
                'stop_loss_pct': self.strategy_config.stop_loss_pct
            }
        }

    async def run(self):
        """Main strategy execution loop"""
        logger.info("Starting Z-Score Spot-Futures Arbitrage Strategy")

        if not await self.initialize():
            logger.error("Strategy initialization failed")
            return

        try:
            while True:
                # Check if market is open
                # if not self.is_trading_time():
                #     await asyncio.sleep(60)
                #     continue

                # Run strategy cycle
                await self.run_strategy_cycle()

                # Sleep based on monitoring interval
                await asyncio.sleep(self.trading_config.monitoring_interval)

        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in strategy: {e}")
            logger.exception("Full error details:")
        finally:
            logger.info("Strategy shutdown complete")