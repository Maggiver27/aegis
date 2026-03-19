from pathlib import Path

import pytest

from app.core.config.msc_config_loader import MSCConfigLoader, RuntimeConfig


def test_loader_uses_canonical_profile_by_default() -> None:
    loader = MSCConfigLoader()
    assert loader.config_path == Path("config/profiles/laptop.runtime.yaml")


def test_loader_returns_structured_runtime_config(tmp_path: Path) -> None:
    profile = tmp_path / "runtime.yaml"
    profile.write_text(
        "runtime:\n"
        "  name: mcgiver-ai-core\n"
        "  version: '1.0'\n"
        "interface:\n"
        "  name: ARIX\n",
        encoding="utf-8",
    )

    config = MSCConfigLoader(profile).load()

    assert isinstance(config, RuntimeConfig)
    assert config.name == "mcgiver-ai-core"
    assert config.version == "1.0"
    assert config.interface_name == "ARIX"
    assert config.profile_path == profile


def test_loader_requires_runtime_mapping(tmp_path: Path) -> None:
    profile = tmp_path / "runtime.yaml"
    profile.write_text("interface:\n  name: ARIX\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires a 'runtime' mapping"):
        MSCConfigLoader(profile).load()


def test_loader_requires_interface_mapping(tmp_path: Path) -> None:
    profile = tmp_path / "runtime.yaml"
    profile.write_text(
        "runtime:\n"
        "  name: mcgiver-ai-core\n"
        "  version: '1.0'\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires an 'interface' mapping"):
        MSCConfigLoader(profile).load()


def test_loader_requires_non_empty_required_fields(tmp_path: Path) -> None:
    profile = tmp_path / "runtime.yaml"
    profile.write_text(
        "runtime:\n"
        "  name: ''\n"
        "  version: '1.0'\n"
        "interface:\n"
        "  name: ARIX\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="runtime.name"):
        MSCConfigLoader(profile).load()
