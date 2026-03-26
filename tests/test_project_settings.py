"""Tests for get_project_settings and set_project_settings tools."""

import pytest
import tomli

from server import get_project_settings, set_project_settings


class TestGetProjectSettings:
    def test_reads_existing_settings(self, tmp_project):
        settings = get_project_settings(str(tmp_project))
        assert settings["default"] == "rpi-pico.toml"
        assert settings["target"] == "src/main.rs"

    def test_missing_project_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="rustdyno.toml"):
            get_project_settings(str(tmp_path))


class TestSetProjectSettings:
    def test_creates_settings_from_scratch(self, tmp_path):
        result = set_project_settings(str(tmp_path), {"default": "stm32f4.toml"})
        assert result["default"] == "stm32f4.toml"

        # Verify on disk
        on_disk = tomli.loads(
            (tmp_path / ".rustdyno" / "rustdyno.toml").read_text()
        )
        assert on_disk["default"] == "stm32f4.toml"

    def test_merges_into_existing(self, tmp_project):
        result = set_project_settings(
            str(tmp_project), {"panel_bg": "#ff0000"}
        )
        assert result["default"] == "rpi-pico.toml"  # preserved
        assert result["target"] == "src/main.rs"  # preserved
        assert result["panel_bg"] == "#ff0000"  # added

    def test_overwrites_existing_key(self, tmp_project):
        result = set_project_settings(
            str(tmp_project), {"default": "esp32c3.toml"}
        )
        assert result["default"] == "esp32c3.toml"
        assert result["target"] == "src/main.rs"  # untouched

    def test_creates_rdyno_dir_if_missing(self, tmp_path):
        set_project_settings(str(tmp_path), {"default": "rpi-pico.toml"})
        assert (tmp_path / ".rustdyno" / "rustdyno.toml").exists()

    def test_roundtrip(self, tmp_path):
        set_project_settings(str(tmp_path), {"default": "a.toml", "target": "src/lib.rs"})
        settings = get_project_settings(str(tmp_path))
        assert settings == {"default": "a.toml", "target": "src/lib.rs"}
