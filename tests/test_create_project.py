"""Tests for create_project tool.

These tests call cargo new, so they require cargo to be installed.
"""

import tomli
import pytest

from server import create_project, get_project_settings


class TestCreateProject:
    def test_basic_creation(self, tmp_path):
        result = create_project("blinky", str(tmp_path), "rpi-pico.toml")
        project = tmp_path / "blinky"

        assert result["board"] == "Raspberry Pi Pico (RP2040)"
        assert result["project_dir"] == str(project)
        assert "rustdyno.toml" in result["files_created"]
        assert "src/main.rs" in result["files_created"]
        assert ".cargo/config.toml" in result["files_created"]
        assert result["generate_options"] == []

    def test_cargo_toml_has_dependencies(self, tmp_path):
        create_project("dep-test", str(tmp_path), "rpi-pico.toml")
        cargo = tomli.loads((tmp_path / "dep-test" / "Cargo.toml").read_text())

        assert "cortex-m" in cargo["dependencies"]
        assert cargo["dependencies"]["cortex-m-rt"] == "0.7.5"
        assert cargo["dependencies"]["rp2040-hal"]["version"] == "0.10"

    def test_rustdyno_toml_in_rdyno_dir(self, tmp_path):
        create_project("cfg-test", str(tmp_path), "rpi-pico.toml")
        settings = get_project_settings(str(tmp_path / "cfg-test"))
        assert settings["default"] == "rpi-pico.toml"

    def test_board_toml_copied(self, tmp_path):
        create_project("board-cp", str(tmp_path), "rpi-pico.toml")
        assert (tmp_path / "board-cp" / ".rustdyno" / "rpi-pico.toml").exists()

    def test_template_vars_substituted(self, tmp_path):
        create_project("tmpl-test", str(tmp_path), "rpi-pico.toml")
        cargo_config = (tmp_path / "tmpl-test" / ".cargo" / "config.toml").read_text()
        assert "{{PROTOCOL}}" not in cargo_config
        assert "swd" in cargo_config

    def test_main_rs_written(self, tmp_path):
        create_project("main-test", str(tmp_path), "rpi-pico.toml")
        main = (tmp_path / "main-test" / "src" / "main.rs").read_text()
        assert "#![no_std]" in main

    def test_existing_dir_raises(self, tmp_path):
        (tmp_path / "exists").mkdir()
        with pytest.raises(FileExistsError):
            create_project("exists", str(tmp_path), "rpi-pico.toml")

    def test_no_new_project_section_raises(self, tmp_path):
        with pytest.raises(ValueError, match="no \\[new_project\\]"):
            create_project("fail", str(tmp_path), "no-new-project.toml")


class TestCreateProjectEsp32:
    def test_generate_options_returned(self, tmp_path):
        result = create_project("esp-test", str(tmp_path), "esp32c3.toml")
        assert len(result["generate_options"]) == 2
        labels = [g["label"] for g in result["generate_options"]]
        assert "cargo generate (esp-idf-template)" in labels
        assert "esp-generate" in labels

    def test_generate_commands_have_project_name(self, tmp_path):
        result = create_project("esp-name", str(tmp_path), "esp32c3.toml")
        for g in result["generate_options"]:
            assert "esp-name" in g["command"]

    def test_build_deps_injected(self, tmp_path):
        create_project("esp-deps", str(tmp_path), "esp32c3.toml")
        cargo = tomli.loads((tmp_path / "esp-deps" / "Cargo.toml").read_text())
        assert cargo["build-dependencies"]["embuild"] == "0.33"
        assert cargo["dependencies"]["anyhow"] == "1"


class TestCreateProjectMicrobit:
    def test_string_deps_injected(self, tmp_path):
        create_project("micro-test", str(tmp_path), "microbit-v2.toml")
        cargo = tomli.loads((tmp_path / "micro-test" / "Cargo.toml").read_text())
        assert cargo["dependencies"]["microbit-v2"] == "0.16"
        assert cargo["dependencies"]["rtt-target"] == "0.6"
        assert cargo["dependencies"]["cortex-m"]["version"] == "0.7"
