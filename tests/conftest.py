"""Shared fixtures for rustdyno-mcp tests."""

import shutil
from pathlib import Path

import pytest
import tomli_w

BOARDS_DIR = Path(__file__).parent / "fixtures" / "boards"


@pytest.fixture(autouse=True)
def _patch_boards_dir(monkeypatch):
    """Point server.BOARDS_DIR at the test fixture boards."""
    import server

    monkeypatch.setattr(server, "BOARDS_DIR", BOARDS_DIR)


@pytest.fixture()
def tmp_project(tmp_path):
    """Create a minimal project directory with .rustdyno/rustdyno.toml."""
    rdyno = tmp_path / ".rustdyno"
    rdyno.mkdir()
    settings = {"default": "rpi-pico.toml", "target": "src/main.rs"}
    (rdyno / "rustdyno.toml").write_text(tomli_w.dumps(settings))
    return tmp_path


@pytest.fixture()
def cargo_project(tmp_path):
    """Create a directory with a minimal Cargo.toml (as cargo new would)."""
    cargo = {
        "package": {"name": "test-proj", "version": "0.1.0", "edition": "2021"},
        "dependencies": {},
    }
    (tmp_path / "Cargo.toml").write_text(tomli_w.dumps(cargo))
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text('fn main() { println!("hello"); }\n')
    return tmp_path
