from pathlib import Path
from typing import Any

import yaml
from loguru import logger


def read_config(config_path: str) -> dict[str, Any]:
    try:
        if Path(config_path).exists():
            with open(config_path, encoding="utf-8") as file:
                data = yaml.safe_load(file)
                return data or {}
        else:
            logger.error("❌ Check config-file path!")
            return {}
    except yaml.YAMLError:
        logger.error("❌ YAML syntax")
        return {}
