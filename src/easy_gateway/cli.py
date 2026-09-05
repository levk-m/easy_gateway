import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from loguru import logger

from easy_gateway.gateway.core import EasyGateway

ascii_logo = r"""
______                   _____       _
|  ____|                 / ____|     | |
| |__   __ _ ___ _   _  | |  __  __ _| |_ _____      ____ _ _   _
|  __| / _` / __| | | | | | |_ |/ _` | __/ _ \ \ /\ / / _` | | | |
| |___| (_| \__ \ |_| | | |__| | (_| | ||  __/\ V  V / (_| | |_| |
|______\__,_|___/\__, |  \_____|\__,_|\__\___| \_/\_/ \__,_|\__, |
                 __/ |                                      __/ |
                |___/                                      |___/
"""


def setup_logger() -> None:
    logger.remove()

    log_format = "<cyan>{time:HH:mm:ss}</cyan> | <level>{level: <8}</level> | <level>{message}</level>"

    logger.add(sys.stderr, format=log_format, level="DEBUG")


def validate_config(config_path: Path) -> bool:
    """Validate config file existence and readability"""
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return False

    if not config_path.is_file():
        logger.error(f"Config path is not a file: {config_path}")
        return False

    try:
        from easy_gateway.config import read_config

        read_config(str(config_path))
        return True
    except Exception as e:
        logger.error(f"Failed to parse config file: {e}")
        return False


def main() -> None:
    vers = version("easy-gateway")
    parser = argparse.ArgumentParser(
        description="🚀 Easy Gateway - simple API gateway",
        usage="easy-gateway [OPTIONS]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  easy-gateway                     # Use default easy_conf.yaml
  easy-gateway -c custom.yaml      # Use custom config
  easy-gateway -c --no-banner      # Without banner (logo)
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to your config-file",
        default="easy_conf.yaml",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=vers,
    )

    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Disable ASCII art banner",
    )

    args = parser.parse_args()

    # Setup logger first
    setup_logger()

    config_path = Path(args.config)
    if not validate_config(config_path):
        sys.exit(1)

    if not args.no_banner:
        print(ascii_logo)

    separator = "─" * (len(str(config_path.absolute())) + 20)
    logger.info(separator)
    logger.info("🚀 Starting Easy Gateway...")
    logger.info(f"📁 Config file: {config_path.absolute()}")
    logger.info(separator)

    try:
        gateway = EasyGateway(config_path=str(config_path))
        gateway.run()

    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"❌ Failed to start gateway: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
