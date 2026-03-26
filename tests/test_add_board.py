"""Tests for add_board tool."""

import pytest
import tomli

from server import add_board


def test_copies_board_to_rdyno_dir(tmp_path):
    result = add_board(str(tmp_path), "rpi-pico.toml")
    dest = tmp_path / ".rustdyno" / "rpi-pico.toml"

    assert dest.exists()
    assert result["copied"] == "rpi-pico.toml"
    assert result["destination"] == str(dest)

    # Verify it's valid TOML with correct content
    config = tomli.loads(dest.read_text())
    assert config["board"]["name"] == "Raspberry Pi Pico (RP2040)"


def test_creates_rdyno_dir(tmp_path):
    assert not (tmp_path / ".rustdyno").exists()
    add_board(str(tmp_path), "rpi-pico.toml")
    assert (tmp_path / ".rustdyno").is_dir()


def test_overwrites_existing_board(tmp_path):
    rdyno = tmp_path / ".rustdyno"
    rdyno.mkdir()
    (rdyno / "rpi-pico.toml").write_text("old content")

    add_board(str(tmp_path), "rpi-pico.toml")
    content = (rdyno / "rpi-pico.toml").read_text()
    assert "old content" not in content
    assert "RP2040" in content


def test_nonexistent_board_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        add_board(str(tmp_path), "fake-board.toml")


def test_multiple_boards(tmp_path):
    add_board(str(tmp_path), "rpi-pico.toml")
    add_board(str(tmp_path), "esp32c3.toml")

    assert (tmp_path / ".rustdyno" / "rpi-pico.toml").exists()
    assert (tmp_path / ".rustdyno" / "esp32c3.toml").exists()
