"""Tests for get_board_config and get_board_properties tools."""

import pytest

from server import get_board_config, get_board_properties


class TestGetBoardConfig:
    def test_returns_full_config(self):
        config = get_board_config("rpi-pico.toml")
        assert "board" in config
        assert "probe" in config
        assert "flash" in config
        assert "rtt" in config
        assert "new_project" in config

    def test_board_section_values(self):
        config = get_board_config("rpi-pico.toml")
        assert config["board"]["name"] == "Raspberry Pi Pico (RP2040)"
        assert config["board"]["chip"] == "RP2040"
        assert config["board"]["target"] == "thumbv6m-none-eabi"

    def test_probe_section(self):
        config = get_board_config("rpi-pico.toml")
        assert config["probe"]["protocol"] == "swd"
        assert config["probe"]["speed"] == 4000

    def test_rtt_section(self):
        config = get_board_config("rpi-pico.toml")
        assert config["rtt"]["enabled"] is True
        assert len(config["rtt"]["channels"]) == 1
        assert config["rtt"]["channels"][0]["name"] == "Terminal"

    def test_esp32_has_run_command(self):
        config = get_board_config("esp32c3.toml")
        assert config["run"]["command"] == "cargo run --release"

    def test_esp32_has_generate_options(self):
        config = get_board_config("esp32c3.toml")
        gen = config["new_project"]["generate"]
        assert len(gen) == 2
        assert gen[0]["label"] == "cargo generate (esp-idf-template)"

    def test_esp32_has_build_dependencies(self):
        config = get_board_config("esp32c3.toml")
        assert config["new_project"]["build-dependencies"]["embuild"] == "0.33"

    def test_microbit_has_elf_field(self):
        config = get_board_config("microbit-v2.toml")
        assert config["board"]["elf"] == "<CRATE_NAME>"

    def test_microbit_string_dependencies(self):
        config = get_board_config("microbit-v2.toml")
        deps = config["new_project"]["dependencies"]
        assert isinstance(deps, str)
        assert "microbit-v2" in deps

    def test_nonexistent_board_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            get_board_config("does-not-exist.toml")


class TestGetBoardProperties:
    def test_returns_all_when_no_section(self):
        props = get_board_properties("rpi-pico.toml")
        assert "board" in props
        assert "probe" in props

    def test_returns_specific_section(self):
        props = get_board_properties("rpi-pico.toml", section="probe")
        assert props == {"probe": {"protocol": "swd", "speed": 4000}}

    def test_board_section(self):
        props = get_board_properties("rpi-pico.toml", section="board")
        assert "board" in props
        assert props["board"]["chip"] == "RP2040"

    def test_flash_section(self):
        props = get_board_properties("rpi-pico.toml", section="flash")
        assert props["flash"]["restore_unwritten"] is False
        assert props["flash"]["halt_afterwards"] is False

    def test_missing_section_raises(self):
        with pytest.raises(KeyError, match="not found"):
            get_board_properties("rpi-pico.toml", section="nonexistent")

    def test_section_missing_from_board(self):
        # no-new-project.toml has no probe section
        with pytest.raises(KeyError):
            get_board_properties("no-new-project.toml", section="probe")
