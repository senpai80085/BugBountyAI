from pathlib import Path

import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    def __init__(self):
        config_file = BASE_DIR / "config" / "config.yaml"

        with open(config_file, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get(self, *keys):
        value = self.data
        for key in keys:
            value = value[key]
        return value


config = Config()