from pathlib import Path
import yaml


class Settings:
    def __init__(self, data: dict):
        self.app_name = data["app"]["name"]
        self.version = data["app"]["version"]
        self.environment = data["app"]["environment"]

        self.host = data["server"]["host"]
        self.port = data["server"]["port"]


def load_settings() -> Settings:
    config_path = Path("config/app.yaml")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    return Settings(data)