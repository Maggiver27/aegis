from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class MSCConfigLoader:
    """
    MSC step 2: Core Configuration Loader

    Responsibility:
    - load MSC configuration from YAML
    - validate minimal top-level structure
    - return plain configuration data

    Non-responsibility:
    - no trading configuration
    - no runtime lifecycle handling
    - no logging setup
    - no orchestration
    """

    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)

    @property
    def config_path(self) -> Path:
        return self._config_path

    def exists(self) -> bool:
        return self._config_path.exists() and self._config_path.is_file()

    def load(self) -> dict[str, Any]:
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"MSC config file not found: {self._config_path}"
            )

        if not self._config_path.is_file():
            raise ValueError(
                f"MSC config path is not a file: {self._config_path}"
            )

        with self._config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        if not isinstance(data, dict):
            raise ValueError(
                "MSC config must contain a top-level YAML mapping"
            )

        return data