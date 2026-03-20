from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from app.core.logging import LogLevel, Logger


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    name: str
    version: str
    interface_name: str
    profile_path: Path


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

    def __init__(
        self,
        config_path: str | Path = "config/profiles/laptop.runtime.yaml",
        logger: Logger | None = None,
    ) -> None:
        self._config_path = Path(config_path)
        self._logger = logger or Logger()

    @property
    def config_path(self) -> Path:
        return self._config_path

    def exists(self) -> bool:
        return self._config_path.exists() and self._config_path.is_file()

    def load(self) -> RuntimeConfig:
        self._logger.log(
            LogLevel.INFO,
            "MSC config profile load attempt",
            metadata={"profile_path": str(self._config_path)},
        )
        try:
            data = self._read_yaml_mapping()
            config = self._to_runtime_config(data)
            self._logger.log(
                LogLevel.INFO,
                "MSC config profile load success",
                metadata={"profile_path": str(self._config_path)},
            )
            return config
        except Exception as exc:
            self._logger.log(
                LogLevel.ERROR,
                "MSC config profile load failure",
                metadata={
                    "profile_path": str(self._config_path),
                    "error": str(exc),
                },
            )
            raise

    def _read_yaml_mapping(self) -> dict[str, Any]:
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"MSC config file not found: {self._config_path}"
            )

        if not self._config_path.is_file():
            raise ValueError(
                f"MSC config path is not a file: {self._config_path}"
            )

        with self._config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "MSC config must contain a top-level YAML mapping"
            )

        return data

    def _to_runtime_config(self, data: Mapping[str, Any]) -> RuntimeConfig:
        runtime = data.get("runtime")
        interface = data.get("interface")

        if not isinstance(runtime, dict):
            raise ValueError("MSC config requires a 'runtime' mapping")
        if not isinstance(interface, dict):
            raise ValueError("MSC config requires an 'interface' mapping")

        name = runtime.get("name")
        version = runtime.get("version")
        interface_name = interface.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("MSC config requires runtime.name as a non-empty string")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("MSC config requires runtime.version as a non-empty string")
        if not isinstance(interface_name, str) or not interface_name.strip():
            raise ValueError("MSC config requires interface.name as a non-empty string")

        config = RuntimeConfig(
            name=name.strip(),
            version=version.strip(),
            interface_name=interface_name.strip(),
            profile_path=self._config_path,
        )
        self._logger.log(
            LogLevel.INFO,
            "MSC config validation success",
            metadata={
                "profile_path": str(self._config_path),
                "runtime_name": config.name,
                "runtime_version": config.version,
                "interface_name": config.interface_name,
            },
        )
        return config