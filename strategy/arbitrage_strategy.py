# strategy/arbitrage_strategy.py

"""
Spot-Futures Arbitrage Strategy Implementation
Monitors and trades spread opportunities between spot and futures
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from config.settings import (
    FyersConfig, ArbitrageStrategyConfig, TradingConfig, SignalType
)
from config.symbols import symbol_manager, get_arbitrage_symbols
from models.trading_models import (
    LiveQuote, SpotFuturesSpread, ArbitrageSignal, ArbitragePosition,
    ArbitrageTradeResult, StrategyMetrics, MarketState,
    create_arbitrage_signal_from_spread, create_position_from_signal,
    create_trade_result_from_position, calculate_portfolio_risk
)

logger = logging.getLogger(__name__)


class SpotFuturesArbitrageStrategy:
    """
    Spot-Futures Arbitrage Strategy
    Trades spread mispricing between spot and futures contracts
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

        # Strategy state
        self.positions: Dict[str, ArbitragePosition] = {}
        self.completed_trades: List[ArbitrageTradeResult] = []
        self.metrics = StrategyMetrics()
        self.market_state = MarketState(timestamp=datetime.now())

        # Spread tracking
        self.current_spreads: Dict[str, SpotFuturesSpread] = {}
        self.spread_history: Dict[str, List[SpotFuturesSpread]] = defaultdict(list)

        # Live quotes
        self.spot_quotes: Dict[str, LiveQuote] = {}
        self.futures_quotes: Dict[str, LiveQuote] = {}

        # Trading universe
        self.trading_symbols = get_arbitrage_symbols()

        # Performance tracking
        self.daily_pnl = 0.0
        self.max_daily_loss = strategy_config.portfolio_value * 0.03  # 3% max loss

        # Signals generated today
        self.signals_generated_today = []

        logger.info(f"Arbitrage Strategy initialized with {len(self.trading_symbols)} pairs")

    async def initialize(self) -> bool:
        """Initialize strategy and connections"""
        try:
            logger.info("Initializing Spot-Futures Arbitrage Strategy...")

            # Initialize data services (to be implemented)
            # self.data_service = ArbitrageDataService(...)
            # self.order_manager = OrderManager(...)

            # Subscribe to symbols
            # await self._subscribe_to_symbols()

            logger.info("Arbitrage Strategy initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            return False

    def calculate_spread(self, symbol: str) -> Optional[SpotFuturesSpread]:
        """Calculate current spread for a symbol"""
        try:
            spot_quote = self.spot_quotes.get(symbol)
            futures_quote = self.futures_quotes.get(symbol)

            if not spot_quote or not futures_quote:
                return None

            # Get contract info
            contract = symbol_manager.get_contract_info(symbol)
            if not contract:
                return None

            # Create spread object
            spread = SpotFuturesSpread(
                symbol=symbol,
                spot_price=spot_quote.ltp,
                futures_price=futures_quote.ltp,
                spread=futures_quote.ltp - spot_quote.ltp,
                spread_pct=0.0,  # Calculated in __post_init__
                basis=0.0,
                spot_volume=spot_quote.volume,
                futures_volume=futures_quote.volume,
                volume_ratio=0.0,
                timestamp=datetime.now(),
                days_to_expiry=contract.days_to_expiry
            )

            # Calculate historical context if available
            history = self.spread_history.get(symbol, [])
            if len(history) >= 30:
                spreads = [s.spread_pct for s in history[-30:]]
                import numpy as np
                spread.avg_spread = float(np.mean(spreads))
                spread.std_spread = float(np.std(spreads))

                if spread.std_spread > 0:
                    spread.z_score = (spread.spread_pct - spread.avg_spread) / spread.std_spread

            # Check convergence
            if len(history) >= 5:
                recent_spreads = [s.spread_pct for s in history[-5:]]
                spread.is_converging = self._is_spread_converging(recent_spreads)
                spread.convergence_rate = self._calculate_convergence_rate(recent_spreads)

            return spread

        except Exception as e:
            logger.error(f"Error calculating spread for {symbol}: {e}")
            return None

    def _is_spread_converging(self, spreads: List[float]) -> bool:
        """Check if spread is converging (narrowing)"""
        if len(spreads) < 3:
            return False

        # Check if spread is getting smaller
        recent_trend = spreads[-1] < spreads[-3]
        return recent_trend

    def _calculate_convergence_rate(self, spreads: List[float]) -> float:
        """Calculate rate of spread convergence"""
        if len(spreads) < 2:
            return 0.0

        # Simple rate calculation
        rate = (spreads[-1] - spreads[0]) / len(spreads)
        return rate

    def evaluate_arbitrage_opportunity(
            self,
            symbol: str,
            spread: SpotFuturesSpread
    ) -> Optional[ArbitrageSignal]:
        """Evaluate if spread presents arbitrage opportunity"""
        try:
            # Check basic thresholds
            abs_spread = abs(spread.spread_pct)

            if abs_spread < self.strategy_config.min_spread_threshold:
                logger.debug(f"{symbol}: Spread too narrow ({abs_spread:.3f}%)")
                return None

            if abs_spread > self.strategy_config.max_spread_threshold:
                logger.debug(f"{symbol}: Spread too wide ({abs_spread:.3f}%)")
                return None

            # Check mispricing
            mispricing = spread.mispricing

            # Determine signal type based on mispricing
            if mispricing > self.strategy_config.min_spread_threshold:
                # Futures overpriced - short futures, long spot
                signal_type = SignalType.LONG_SPOT_SHORT_FUTURES
            elif mispricing < -self.strategy_config.min_spread_threshold:
                # Futures underpriced - long futures, short spot
                signal_type = SignalType.SHORT_SPOT_LONG_FUTURES
            else:
                return None

            # Check convergence requirement
            if self.strategy_config.require_convergence_trend and not spread.is_converging:
                logger.debug(f"{symbol}: No convergence trend detected")
                return None

            # Check liquidity
            if spread.volume_ratio < self.strategy_config.min_liquidity_ratio:
                logger.debug(f"{symbol}: Insufficient liquidity ({spread.volume_ratio:.2f})")
                return None

            # Calculate position size
            lot_size = symbol_manager.get_lot_size(symbol)
            if not lot_size:
                return None

            # Calculate quantity (number of lots)
            risk_capital = self.strategy_config.portfolio_value * (self.strategy_config.risk_per_trade_pct / 100)
            value_per_lot = lot_size * spread.futures_price
            quantity = max(1, int(risk_capital / value_per_lot))

            # Calculate targets and stops
            if signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
                target_spread = spread.spread - (spread.spread * self.strategy_config.target_profit_pct / 100)
                stop_loss_spread = spread.spread + (spread.spread * self.strategy_config.stop_loss_pct / 100)
            else:
                target_spread = spread.spread + (spread.spread * self.strategy_config.target_profit_pct / 100)
                stop_loss_spread = spread.spread - (spread.spread * self.strategy_config.stop_loss_pct / 100)

            # Calculate confidence
            confidence = self._calculate_signal_confidence(spread)

            if confidence < self.strategy_config.min_confidence:
                logger.debug(f"{symbol}: Low confidence ({confidence:.2f})")
                return None

            # Calculate risk/reward
            risk_amount = abs(stop_loss_spread - spread.spread) * lot_size * quantity
            reward_amount = abs(target_spread - spread.spread) * lot_size * quantity

            # Create signal
            signal = create_arbitrage_signal_from_spread(
                symbol=symbol,
                spread_data=spread,
                signal_type=signal_type,
                quantity=quantity,
                lot_size=lot_size,
                target_spread=target_spread,
                stop_loss_spread=stop_loss_spread,
                confidence=confidence,
                capital_required=value_per_lot * quantity,
                risk_amount=risk_amount,
                reward_amount=reward_amount,
                sector=symbol_manager.get_sector(symbol) or "GENERAL"
            )

            logger.info(f"Arbitrage Signal: {symbol} {signal_type.value} - "
                        f"Spread: {spread.spread_pct:.3f}%, "
                        f"Mispricing: {mispricing:.3f}%, "
                        f"Confidence: {confidence:.2f}")

            return signal

        except Exception as e:
            logger.error(f"Error evaluating arbitrage for {symbol}: {e}")
            return None

    def _calculate_signal_confidence(self, spread: SpotFuturesSpread) -> float:
        """Calculate confidence score for arbitrage signal"""
        confidence = 0.0

        # Z-score component (30%)
        if spread.z_score != 0:
            z_confidence = min(abs(spread.z_score) / 3.0, 1.0)  # Normalize to 0-1
            confidence += z_confidence * 0.3
        else:
            confidence += 0.15  # Neutral score

        # Volume component (25%)
        volume_confidence = min(spread.volume_ratio / 2.0, 1.0)
        confidence += volume_confidence * 0.25

        # Convergence component (25%)
        if spread.is_converging:
            convergence_confidence = min(abs(spread.convergence_rate) * 10, 1.0)
            confidence += convergence_confidence * 0.25

        # Days to expiry component (20%)
        # More confidence with more time
        expiry_confidence = min(spread.days_to_expiry / 20, 1.0)
        confidence += expiry_confidence * 0.2

        return min(confidence, 1.0)

    async def execute_signal(self, signal: ArbitrageSignal) -> bool:
        """Execute arbitrage signal"""
        try:
            logger.info(f"Executing arbitrage signal for {signal.symbol}")

            # Create position
            position = create_position_from_signal(signal)

            # Place orders (to be implemented with OrderManager)
            # success = await self.order_manager.place_arbitrage_orders(position)

            # For now, just track position
            self.positions[signal.symbol] = position
            self.signals_generated_today.append(signal)

            logger.info(f"Arbitrage position opened: {signal.symbol} - "
                        f"Spot: {signal.entry_spot_price:.2f}, "
                        f"Futures: {signal.entry_futures_price:.2f}, "
                        f"Spread: {signal.spread_pct:.3f}%")

            return True

        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False

    async def monitor_positions(self):
        """Monitor existing arbitrage positions"""
        try:
            positions_to_close = []

            for symbol, position in self.positions.items():
                # Get current quotes
                spot_quote = self.spot_quotes.get(symbol)
                futures_quote = self.futures_quotes.get(symbol)

                if not spot_quote or not futures_quote:
                    continue

                # Update position prices
                position.update_current_prices(spot_quote.ltp, futures_quote.ltp)

                # Check exit conditions
                exit_reason = self._check_exit_conditions(position)

                if exit_reason:
                    positions_to_close.append((symbol, exit_reason))

            # Close positions
            for symbol, reason in positions_to_close:
                await self._close_position(symbol, reason)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    def _check_exit_conditions(self, position: ArbitragePosition) -> Optional[str]:
        """Check if position should be exited"""
        current_spread = position.current_spread

        # Target reached
        if position.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
            if current_spread <= position.target_spread:
                return "TARGET"
        else:
            if current_spread >= position.target_spread:
                return "TARGET"

        # Stop loss hit
        if position.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
            if current_spread >= position.current_stop_spread:
                return "STOP_LOSS"
        else:
            if current_spread <= position.current_stop_spread:
                return "STOP_LOSS"

        # Near expiry
        if position.days_to_expiry <= 3:
            return "EXPIRY_EXIT"

        # Time-based exit (end of day)
        now = datetime.now()
        if now.hour >= 15 and now.minute >= 15:
            return "TIME_EXIT"

        return None

    async def _close_position(self, symbol: str, reason: str):
        """Close arbitrage position"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return

            spot_quote = self.spot_quotes.get(symbol)
            futures_quote = self.futures_quotes.get(symbol)

            if not spot_quote or not futures_quote:
                logger.warning(f"Cannot close {symbol} - missing quotes")
                return

            # Create trade result
            trade_result = create_trade_result_from_position(
                position=position,
                exit_spot_price=spot_quote.ltp,
                exit_futures_price=futures_quote.ltp,
                exit_reason=reason
            )

            # Update daily P&L
            self.daily_pnl += trade_result.net_pnl

            # Store result
            self.completed_trades.append(trade_result)

            # Remove position
            del self.positions[symbol]

            logger.info(f"Position closed: {symbol} - {reason} - "
                        f"P&L: ₹{trade_result.net_pnl:.2f} - "
                        f"Spread change: {trade_result.spread_change:.3f}")

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

    async def run_strategy_cycle(self):
        """Main strategy cycle"""
        try:
            # Update market state
            self._update_market_state()

            # Update all spreads
            self._update_all_spreads()

            # Monitor existing positions
            await self.monitor_positions()

            # Scan for new opportunities
            if self._should_scan_for_opportunities():
                await self._scan_opportunities()

            # Update metrics
            self._update_metrics()

        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")

    def _update_all_spreads(self):
        """Update spread calculations for all symbols"""
        for symbol in self.trading_symbols:
            spread = self.calculate_spread(symbol)
            if spread:
                self.current_spreads[symbol] = spread
                self.spread_history[symbol].append(spread)

                # Keep last 1000 spreads
                if len(self.spread_history[symbol]) > 1000:
                    self.spread_history[symbol] = self.spread_history[symbol][-1000:]

    def _should_scan_for_opportunities(self) -> bool:
        """Check if we should scan for new opportunities"""
        if len(self.positions) >= self.strategy_config.max_positions:
            return False

        if self.daily_pnl < -abs(self.max_daily_loss):
            logger.warning("Daily loss limit reached")
            return False

        # Don't open new positions near market close
        now = datetime.now()
        if now.hour >= 15:
            return False

        return True

    async def _scan_opportunities(self):
        """Scan for arbitrage opportunities"""
        try:
            signals = []

            for symbol in self.trading_symbols:
                # Skip if already have position
                if symbol in self.positions:
                    continue

                spread = self.current_spreads.get(symbol)
                if not spread:
                    continue

                signal = self.evaluate_arbitrage_opportunity(symbol, spread)
                if signal:
                    signals.append(signal)

            # Sort by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)

            # Execute top signals
            available_slots = self.strategy_config.max_positions - len(self.positions)
            for signal in signals[:available_slots]:
                await self.execute_signal(signal)

        except Exception as e:
            logger.error(f"Error scanning opportunities: {e}")

    def _update_market_state(self):
        """Update market state"""
        self.market_state.timestamp = datetime.now()
        self.market_state.max_positions_reached = len(self.positions) >= self.strategy_config.max_positions
        self.market_state.daily_loss_limit_hit = self.daily_pnl < -abs(self.max_daily_loss)

        # Calculate average basis
        if self.current_spreads:
            spreads = [s.spread_pct for s in self.current_spreads.values()]
            import numpy as np
            self.market_state.avg_basis = float(np.mean(spreads))
            self.market_state.basis_std = float(np.std(spreads))

    def _update_metrics(self):
        """Update strategy metrics"""
        self.metrics.update_metrics(self.completed_trades)
        self.metrics.daily_pnl = self.daily_pnl

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())

        risk_metrics = calculate_portfolio_risk(
            list(self.positions.values()),
            self.strategy_config.portfolio_value
        )

        return {
            'strategy_name': 'Spot-Futures Arbitrage',
            'timestamp': datetime.now().isoformat(),
            'total_pnl': self.metrics.total_pnl,
            'daily_pnl': self.daily_pnl,
            'unrealized_pnl': total_unrealized,
            'active_positions': len(self.positions),
            'max_positions': self.strategy_config.max_positions,
            'completed_trades': len(self.completed_trades),
            'win_rate': self.metrics.win_rate,
            'avg_spread_captured': self.metrics.avg_spread_captured,
            'risk_metrics': risk_metrics,
            'market_state': {
                'avg_basis': self.market_state.avg_basis,
                'basis_std': self.market_state.basis_std,
                'max_positions_reached': self.market_state.max_positions_reached,
                'daily_loss_limit_hit': self.market_state.daily_loss_limit_hit
            }
        }

    async def run(self):
        """Main strategy execution loop"""
        logger.info("Starting Spot-Futures Arbitrage Strategy")

        if not await self.initialize():
            logger.error("Strategy initialization failed")
            return

        try:
            while True:
                # Check trading hours
                # if not self.timing_service.is_trading_time():
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
        finally:
            logger.info("Strategy shutdown complete")