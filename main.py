# main.py

"""
Spot-Futures Arbitrage Trading Strategy - Main Entry Point
Complete algorithmic trading system with authentication, risk management, and monitoring
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Core imports
from config.settings import FyersConfig, ArbitrageStrategyConfig, TradingConfig
from strategy.arbitrage_strategy import SpotFuturesArbitrageStrategy

# Authentication
from utils.enhanced_auth_helper import (
    setup_auth_only,
    authenticate_fyers,
    test_authentication
)

# Load environment variables
load_dotenv()


# Configure logging
def setup_logging():
    """Setup enhanced logging"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'arbitrage_strategy.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


def load_configuration():
    """Load configuration from environment"""
    try:
        # Fyers configuration
        fyers_config = FyersConfig(
            client_id=os.environ.get('FYERS_CLIENT_ID'),
            secret_key=os.environ.get('FYERS_SECRET_KEY'),
            access_token=os.environ.get('FYERS_ACCESS_TOKEN'),
            refresh_token=os.environ.get('FYERS_REFRESH_TOKEN')
        )

        # Strategy configuration
        strategy_config = ArbitrageStrategyConfig(
            portfolio_value=float(os.environ.get('PORTFOLIO_VALUE', 100000)),
            risk_per_trade_pct=float(os.environ.get('RISK_PER_TRADE', 2.0)),
            max_positions=int(os.environ.get('MAX_POSITIONS', 5)),

            min_spread_threshold=float(os.environ.get('MIN_SPREAD_THRESHOLD', 0.5)),
            max_spread_threshold=float(os.environ.get('MAX_SPREAD_THRESHOLD', 3.0)),
            target_profit_pct=float(os.environ.get('TARGET_PROFIT_PCT', 0.3)),

            stop_loss_pct=float(os.environ.get('STOP_LOSS_PCT', 0.5)),
            min_confidence=float(os.environ.get('MIN_CONFIDENCE', 0.7))
        )

        # Trading configuration
        trading_config = TradingConfig(
            monitoring_interval=int(os.environ.get('MONITORING_INTERVAL', 5)),
            position_update_interval=int(os.environ.get('POSITION_UPDATE_INTERVAL', 3))
        )

        return fyers_config, strategy_config, trading_config

    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


async def run_arbitrage_strategy():
    """Main function to run arbitrage strategy"""
    try:
        logger.info("=" * 60)
        logger.info("STARTING SPOT-FUTURES ARBITRAGE STRATEGY")
        logger.info("=" * 60)

        # Load configuration
        fyers_config, strategy_config, trading_config = load_configuration()

        # Validate credentials
        if not all([fyers_config.client_id, fyers_config.secret_key]):
            logger.error("Missing required Fyers API credentials")
            logger.error("Please set FYERS_CLIENT_ID and FYERS_SECRET_KEY")
            logger.error("Run 'python main.py auth' to setup authentication")
            return

        # Enhanced authentication with auto-refresh
        config_dict = {'fyers_config': fyers_config}
        if not authenticate_fyers(config_dict):
            logger.error("Authentication failed")
            logger.error("Run 'python main.py auth' to setup authentication")
            return

        logger.info(" Authentication successful")

        # Log strategy configuration
        logger.info(f"Portfolio Value: Rs:{strategy_config.portfolio_value:,}")
        logger.info(f"Risk per Trade: {strategy_config.risk_per_trade_pct}%")
        logger.info(f"Max Positions: {strategy_config.max_positions}")
        logger.info(f"Min Spread Threshold: {strategy_config.min_spread_threshold}%")
        logger.info(f"Target Profit: {strategy_config.target_profit_pct}%")
        logger.info(f"Stop Loss: {strategy_config.stop_loss_pct}%")

        # Create and run strategy
        strategy = SpotFuturesArbitrageStrategy(
            fyers_config=config_dict['fyers_config'],
            strategy_config=strategy_config,
            trading_config=trading_config
        )

        logger.info("Initializing Arbitrage Strategy...")
        await strategy.run()

    except KeyboardInterrupt:
        logger.info("Strategy stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.exception("Full error details:")


def show_strategy_help():
    """Show comprehensive strategy help"""
    print("\n" + "=" * 80)
    print("SPOT-FUTURES ARBITRAGE TRADING STRATEGY - CONFIGURATION GUIDE")
    print("=" * 80)

    print("\n STRATEGY OVERVIEW:")
    print("• Identifies price differences between spot and futures contracts")
    print("• Trades spread mispricing opportunities")
    print("• Profits from convergence of spot-futures spread")
    print("• Market-neutral strategy with defined risk")
    print("• Automatic position management and risk controls")

    print("\n KEY PARAMETERS:")
    print("Edit .env file or set environment variables:")

    print("\n  Portfolio Settings:")
    print("  PORTFOLIO_VALUE=100000        # Total capital (₹1 lakh)")
    print("  RISK_PER_TRADE=2.0            # Risk per trade (2%)")
    print("  MAX_POSITIONS=5               # Maximum concurrent positions")

    print("\n  Spread Thresholds:")
    print("  MIN_SPREAD_THRESHOLD=0.5      # Minimum spread to enter (0.5%)")
    print("  MAX_SPREAD_THRESHOLD=3.0      # Maximum spread to consider (3%)")
    print("  TARGET_PROFIT_PCT=0.3         # Target profit on convergence (0.3%)")

    print("\n  Risk Management:")
    print("  STOP_LOSS_PCT=0.5             # Stop loss if spread widens (0.5%)")
    print("  MIN_CONFIDENCE=0.7            # Minimum signal confidence (70%)")

    print("\n  System Settings:")
    print("  MONITORING_INTERVAL=5         # Check every 5 seconds")
    print("  POSITION_UPDATE_INTERVAL=3    # Update positions every 3 seconds")

    print("\n AVAILABLE PAIRS:")
    from config.symbols import symbol_manager
    print(f"  Total arbitrage pairs: {symbol_manager.get_trading_universe_size()}")
    print(f"  Stock pairs: {len(symbol_manager.get_stock_symbols())}")
    print(f"  Index pairs: {len(symbol_manager.get_index_symbols())}")

    print("\n  Sample pairs:")
    for symbol in symbol_manager.get_stock_symbols()[:10]:
        print(f"    {symbol}")

    print("\n EXPECTED PERFORMANCE:")
    print("  Daily Opportunities: 3-8 arbitrage signals")
    print("  Win Rate Target: 75-85%")
    print("  Avg Return per Trade: 0.2-0.5%")
    print("  Monthly Target: 8-15% portfolio growth")
    print("  Max Drawdown: <3% with proper risk management")

    print("\n RISK FACTORS:")
    print("  • Execution risk (slippage in fast markets)")
    print("  • Model risk (unexpected spread behavior)")
    print("  • Expiry risk (manage positions before expiry)")
    print("  • Liquidity risk (ensure adequate volumes)")

    print("\n IMPORTANT NOTES:")
    print("  • Start with paper trading or small amounts")
    print("  • Monitor closely during first weeks")
    print("  • Ensure stable internet connection")
    print("  • Keep trading PIN secure for token refresh")
    print("  • Close all positions before contract expiry")


def show_authentication_status():
    """Show authentication status"""
    print("\n" + "=" * 60)
    print("FYERS API AUTHENTICATION STATUS")
    print("=" * 60)

    client_id = os.environ.get('FYERS_CLIENT_ID')
    secret_key = os.environ.get('FYERS_SECRET_KEY')
    access_token = os.environ.get('FYERS_ACCESS_TOKEN')
    refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
    pin = os.environ.get('FYERS_PIN')

    print(f"\n Credential Status:")
    print(f"  Client ID: {' Set' if client_id else ' Missing'}")
    print(f"  Secret Key: {' Set' if secret_key else ' Missing'}")
    print(f"  Access Token: {' Set' if access_token else ' Missing'}")
    print(f"  Refresh Token: {' Set' if refresh_token else ' Missing'}")
    print(f"  Trading PIN: {' Set' if pin else ' Missing'}")

    print(f"\n Available Commands:")
    print(f"  Setup Auth: python main.py auth")
    print(f"  Test Auth: python main.py test-auth")
    print(f"  Run Strategy: python main.py run")


def validate_configuration():
    """Validate configuration"""
    print("\n" + "=" * 60)
    print("CONFIGURATION VALIDATION")
    print("=" * 60)

    try:
        fyers_config, strategy_config, trading_config = load_configuration()

        issues = []
        warnings = []

        # Check credentials
        if not fyers_config.client_id:
            issues.append("FYERS_CLIENT_ID not set")
        if not fyers_config.secret_key:
            issues.append("FYERS_SECRET_KEY not set")
        if not fyers_config.access_token:
            warnings.append("FYERS_ACCESS_TOKEN not set (run auth)")

        # Check strategy config
        if strategy_config.portfolio_value < 10000:
            warnings.append(f"Portfolio value is low: ₹{strategy_config.portfolio_value:,}")

        if strategy_config.risk_per_trade_pct > 5.0:
            warnings.append(f"High risk per trade: {strategy_config.risk_per_trade_pct}%")

        print("\n Configuration Check:")
        if issues:
            print("\n   CRITICAL ISSUES:")
            for issue in issues:
                print(f"    • {issue}")

        if warnings:
            print("\n  ⚠ WARNINGS:")
            for warning in warnings:
                print(f"    • {warning}")

        if not issues and not warnings:
            print("   All configurations valid!")
        elif not issues:
            print("\n   No critical issues - can run with warnings")

        return len(issues) == 0

    except Exception as e:
        print(f"\n Configuration validation failed: {e}")
        return False


def main():
    """Main entry point"""
    print("=" * 80)
    print("    SPOT-FUTURES ARBITRAGE TRADING STRATEGY")
    print("    Advanced Algorithmic Trading System v1.0")
    print("=" * 80)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "run":
            logger.info(" Starting Spot-Futures Arbitrage Strategy")
            asyncio.run(run_arbitrage_strategy())

        elif command == "auth":
            print(" Setting up Fyers API Authentication")
            setup_auth_only()

        elif command == "test-auth":
            print(" Testing Fyers API Authentication")
            test_authentication()

        elif command == "help":
            show_strategy_help()

        elif command == "status":
            show_authentication_status()

        elif command == "config":
            print(" Validating Configuration")
            if validate_configuration():
                print("\n Configuration validation passed!")
            else:
                print("\n Configuration validation failed!")

        else:
            print(f" Unknown command: {command}")
            print("\nAvailable commands:")
            commands = [
                ("run", "Run the arbitrage trading strategy"),
                ("auth", "Setup Fyers API authentication"),
                ("test-auth", "Test authentication status"),
                ("help", "Show strategy configuration guide"),
                ("status", "Show authentication status"),
                ("config", "Validate configuration settings"),
            ]

            for cmd, desc in commands:
                print(f"  python main.py {cmd:<12} - {desc}")

    else:
        # Interactive menu
        print("\n Spot-Futures Arbitrage Trading System")
        print("  Market-neutral strategy trading spread mispricing")
        print("\nSelect an option:")

        menu_options = [
            ("1", " Run Arbitrage Trading Strategy"),
            ("2", " Setup Fyers Authentication"),
            ("3", " Test Authentication"),
            ("4", " Strategy Configuration Guide"),
            ("5", " Show Authentication Status"),
            ("6", " Validate Configuration"),
            ("7", " Exit"),
        ]

        for option, description in menu_options:
            print(f"{option:>2}. {description}")

        choice = input(f"\nSelect option (1-{len(menu_options)}): ").strip()

        if choice == "1":
            logger.info(" Starting Arbitrage Strategy")
            asyncio.run(run_arbitrage_strategy())
        elif choice == "2":
            setup_auth_only()
        elif choice == "3":
            test_authentication()
        elif choice == "4":
            show_strategy_help()
        elif choice == "5":
            show_authentication_status()
        elif choice == "6":
            if validate_configuration():
                print("\n Configuration is valid!")
            else:
                print("\n Configuration has issues")
        elif choice == "7":
            print("\n Goodbye! Happy Trading!")
        else:
            print(f" Invalid choice: {choice}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n Interrupted by user - Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        logger.exception("Full error details:")
        sys.exit(1)