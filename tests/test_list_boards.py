"""Tests for list_boards tool."""

from server import list_boards


def test_returns_all_fixture_boards():
    boards = list_boards()
    files = {b["file"] for b in boards}
    assert "rpi-pico.toml" in files
    assert "esp32c3.toml" in files
    assert "microbit-v2.toml" in files
    assert "no-new-project.toml" in files


def test_board_entry_has_required_keys():
    boards = list_boards()
    for b in boards:
        assert "file" in b
        assert "name" in b
        assert "chip" in b
        assert "target" in b


def test_rpi_pico_values():
    boards = list_boards()
    pico = next(b for b in boards if b["file"] == "rpi-pico.toml")
    assert pico["name"] == "Raspberry Pi Pico (RP2040)"
    assert pico["chip"] == "RP2040"
    assert pico["target"] == "thumbv6m-none-eabi"


def test_boards_sorted_by_filename():
    boards = list_boards()
    files = [b["file"] for b in boards]
    assert files == sorted(files)
