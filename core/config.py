from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    """
    Configuration reader that parses configuration settings from config/config.yaml.
    """

    def __init__(self) -> None:
        config_file = BASE_DIR / "config" / "config.yaml"

        with open(config_file, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get(self, *keys: str) -> Any:
        """
        Lookup configuration values nesting down using subsequent key arguments.
        """
        value = self.data
        for key in keys:
            value = value[key]
        return value


config = Config()