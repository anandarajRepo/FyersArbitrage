# strategy/order_manager.py

"""
Order Management for Spot-Futures Arbitrage
Handles simultaneous order placement in spot and futures markets
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from fyers_apiv3 import fyersModel

from config.settings import FyersConfig, SignalType
from models.trading_models import ArbitragePosition, ArbitrageSignal

logger = logging.getLogger(__name__)


class ArbitrageOrderManager:
    """Manages simultaneous spot and futures order placement"""

    def __init__(self, fyers_config: FyersConfig):
        self.fyers_config = fyers_config
        self.fyers = fyersModel.FyersModel(
            client_id=fyers_config.client_id,
            token=fyers_config.access_token,
            log_path=""
        )
        self.placed_orders: Dict[str, Dict] = {}

    async def place_arbitrage_orders(self, position: ArbitragePosition) -> Tuple[bool, bool]:
        """
        Place simultaneous spot and futures orders

        Returns:
            (spot_success, futures_success)
        """
        try:
            logger.info(f"Placing arbitrage orders for {position.pair_name}")

            # Determine order directions
            if position.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
                spot_side = 1  # Buy spot
                futures_side = -1  # Sell futures
            else:  # SHORT_SPOT_LONG_FUTURES
                spot_side = -1  # Sell spot
                futures_side = 1  # Buy futures

            # Place spot order
            spot_success = await self._place_spot_order(
                position.spot_symbol,
                abs(position.spot_quantity),
                spot_side,
                position.spot_price
            )

            if not spot_success:
                logger.error(f"Failed to place spot order for {position.pair_name}")
                return False, False

            # Place futures order
            futures_success = await self._place_futures_order(
                position.futures_symbol,
                abs(position.futures_quantity),
                futures_side,
                position.futures_price,
                position.lot_size
            )

            if not futures_success:
                logger.error(f"Failed to place futures order for {position.pair_name}")
                # Consider cancelling spot order here
                return True, False

            logger.info(f"Successfully placed both orders for {position.pair_name}")
            return True, True

        except Exception as e:
            logger.error(f"Error placing arbitrage orders: {e}")
            return False, False

    async def _place_spot_order(self, symbol: str, quantity: int, side: int, price: float) -> bool:
        """Place spot market order"""
        try:
            from config.symbols import get_spot_symbol

            order_data = {
                "symbol": get_spot_symbol(symbol),
                "qty": quantity,
                "type": 2,  # Market order
                "side": side,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False
            }

            response = self.fyers.place_order(data=order_data)

            if response and response.get('s') == 'ok':
                order_id = response.get('id')
                self.placed_orders[f"spot_{symbol}"] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'type': 'SPOT',
                    'response': response
                }
                logger.info(f"Spot order placed: {order_id}")
                return True
            else:
                logger.error(f"Spot order failed: {response.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Error placing spot order: {e}")
            return False

    async def _place_futures_order(self, symbol: str, quantity: int, side: int,
                                   price: float, lot_size: int) -> bool:
        """Place futures market order"""
        try:
            from config.symbols import get_futures_symbol

            # Calculate lots
            lots = max(1, quantity // lot_size)
            actual_qty = lots * lot_size

            order_data = {
                "symbol": get_futures_symbol(symbol),
                "qty": actual_qty,
                "type": 2,  # Market order
                "side": side,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False
            }

            response = self.fyers.place_order(data=order_data)

            if response and response.get('s') == 'ok':
                order_id = response.get('id')
                self.placed_orders[f"futures_{symbol}"] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'type': 'FUTURES',
                    'response': response
                }
                logger.info(f"Futures order placed: {order_id}")
                return True
            else:
                logger.error(f"Futures order failed: {response.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Error placing futures order: {e}")
            return False

    async def close_arbitrage_position(self, position: ArbitragePosition) -> bool:
        """Close both spot and futures positions"""
        try:
            logger.info(f"Closing arbitrage position: {position.pair_name}")

            # Opposite sides for exit
            if position.signal_type == SignalType.LONG_SPOT_SHORT_FUTURES:
                spot_side = -1  # Sell spot
                futures_side = 1  # Buy futures
            else:
                spot_side = 1  # Buy spot
                futures_side = -1  # Sell futures

            # Close spot
            spot_closed = await self._place_spot_order(
                position.spot_symbol,
                abs(position.spot_quantity),
                spot_side,
                position.spot_price
            )

            # Close futures
            futures_closed = await self._place_futures_order(
                position.futures_symbol,
                abs(position.futures_quantity),
                futures_side,
                position.futures_price,
                position.lot_size
            )

            return spot_closed and futures_closed

        except Exception as e:
            logger.error(f"Error closing arbitrage position: {e}")
            return False

    def verify_broker_connection(self) -> bool:
        """Verify broker API connection"""
        try:
            response = self.fyers.get_profile()
            if response and response.get('s') == 'ok':
                logger.info("Broker connection verified")
                return True
            return False
        except Exception as e:
            logger.error(f"Broker connection error: {e}")
            return False