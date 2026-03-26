"""MCP server for rustdyno embedded Rust project tooling."""

import os
import shutil
import subprocess
from pathlib import Path

import tomli
import tomli_w
from mcp.server.fastmcp import FastMCP

BOARDS_DIR = Path(
    os.environ.get(
        "RUSTDYNO_BOARDS_DIR",
        str(Path(__file__).parent / ".." / "rustdyno" / "boards"),
    )
).resolve()

mcp = FastMCP("rustdyno")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_board(board: str) -> dict:
    """Load and parse a board TOML file by filename."""
    board_path = BOARDS_DIR / board
    if not board_path.exists():
        available = sorted(p.name for p in BOARDS_DIR.glob("*.toml"))
        raise FileNotFoundError(
            f"Board '{board}' not found in {BOARDS_DIR}. Available: {available}"
        )
    return tomli.loads(board_path.read_text())


def _apply_template_vars(content: str, variables: dict[str, str]) -> str:
    """Replace {{VAR}} placeholders in content."""
    for key, value in variables.items():
        content = content.replace(key, value)
    return content


def _load_project_settings(project_dir: str) -> dict:
    """Read a project's .rustdyno/rustdyno.toml."""
    settings_path = Path(project_dir) / ".rustdyno" / "rustdyno.toml"
    if not settings_path.exists():
        raise FileNotFoundError(
            f"No rustdyno.toml found at {settings_path}. "
            "Is this a rustdyno project?"
        )
    return tomli.loads(settings_path.read_text())


def _parse_deps(raw) -> dict:
    """Parse dependencies from either a TOML table (dict) or a raw string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        # Raw string fragment — wrap as [dependencies] to parse as valid TOML
        wrapped = "[dependencies]\n" + raw.strip()
        return tomli.loads(wrapped).get("dependencies", {})
    return {}


def _inject_dependencies(cargo_toml_path: Path, board_config: dict) -> None:
    """Merge board dependencies into a project's Cargo.toml."""
    np = board_config.get("new_project", {})
    deps = _parse_deps(np.get("dependencies"))
    build_deps = _parse_deps(np.get("build-dependencies"))

    if not deps and not build_deps:
        return

    cargo = tomli.loads(cargo_toml_path.read_text())

    if deps:
        cargo.setdefault("dependencies", {}).update(deps)
    if build_deps:
        cargo.setdefault("build-dependencies", {}).update(build_deps)

    cargo_toml_path.write_text(tomli_w.dumps(cargo))


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_boards() -> list[dict]:
    """List all available board configurations with name, chip, and target."""
    boards = []
    for path in sorted(BOARDS_DIR.glob("*.toml")):
        try:
            config = tomli.loads(path.read_text())
            b = config.get("board", {})
            boards.append(
                {
                    "file": path.name,
                    "name": b.get("name", ""),
                    "chip": b.get("chip", ""),
                    "target": b.get("target", ""),
                }
            )
        except Exception:
            continue
    return boards


@mcp.tool()
def get_board_config(board: str) -> dict:
    """Get the full board configuration as structured data.

    Args:
        board: Board filename, e.g. "rpi-pico.toml"
    """
    return _load_board(board)


@mcp.tool()
def get_board_properties(board: str, section: str | None = None) -> dict:
    """Get specific board properties by section.

    Args:
        board: Board filename, e.g. "rpi-pico.toml"
        section: Optional section name (board, probe, flash, rtt, tool,
                 new_project, run, actions, layout). Returns all if omitted.
    """
    config = _load_board(board)
    if section is None:
        return config
    if section not in config:
        raise KeyError(
            f"Section '{section}' not found in {board}. "
            f"Available sections: {list(config.keys())}"
        )
    return {section: config[section]}


@mcp.tool()
def get_project_settings(project_dir: str) -> dict:
    """Read a project's rustdyno.toml workspace settings.

    Args:
        project_dir: Path to the project root
    """
    return _load_project_settings(project_dir)


@mcp.tool()
def set_project_settings(project_dir: str, settings: dict) -> dict:
    """Update a project's rustdyno.toml workspace settings.

    Shallow-merges the provided settings into the existing config.

    Args:
        project_dir: Path to the project root
        settings: Keys to update (e.g. default, target, panel_bg)
    """
    settings_path = Path(project_dir) / ".rustdyno" / "rustdyno.toml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if settings_path.exists():
        existing = tomli.loads(settings_path.read_text())

    existing.update(settings)
    settings_path.write_text(tomli_w.dumps(existing))
    return existing


@mcp.tool()
def add_board(project_dir: str, board: str) -> dict:
    """Copy a built-in board TOML to a project's .rustdyno/ directory.

    Args:
        project_dir: Path to the project root
        board: Board filename from built-in boards, e.g. "rpi-pico.toml"
    """
    src = BOARDS_DIR / board
    if not src.exists():
        available = sorted(p.name for p in BOARDS_DIR.glob("*.toml"))
        raise FileNotFoundError(
            f"Board '{board}' not found. Available: {available}"
        )

    dest_dir = Path(project_dir) / ".rustdyno"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / board
    shutil.copy2(src, dest)

    return {"copied": board, "destination": str(dest)}


@mcp.tool()
def create_project(name: str, parent_dir: str, board: str) -> dict:
    """Create a new embedded Rust project with board-specific scaffolding.

    Runs cargo new, writes board template files, and injects dependencies.

    Args:
        name: Project name (alphanumeric, hyphens, underscores; starts with letter)
        parent_dir: Parent directory where the project folder will be created
        board: Board filename, e.g. "rpi-pico.toml"
    """
    config = _load_board(board)
    np = config.get("new_project")
    if not np:
        raise ValueError(f"Board '{board}' has no [new_project] section.")

    parent = Path(parent_dir).resolve()
    project_dir = parent / name

    if project_dir.exists():
        raise FileExistsError(f"Directory already exists: {project_dir}")

    # Run cargo new
    result = subprocess.run(
        ["cargo", "new", "--name", name, name],
        cwd=str(parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cargo new failed: {result.stderr.strip()}")

    # Set up .rustdyno/ with board config
    rdyno_dir = project_dir / ".rustdyno"
    rdyno_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BOARDS_DIR / board, rdyno_dir / board)

    # Template variables
    protocol = config.get("probe", {}).get("protocol", "swd")
    template_vars = {
        "{{PROTOCOL}}": protocol,
        "{{BOARD_FILE}}": board,
        "{{PROJECT_NAME}}": name,
    }

    # Write scaffolding files
    files_created = []
    for f in np.get("files", []):
        content = _apply_template_vars(f["content"], template_vars)
        file_path = f["path"]

        # rustdyno.toml goes inside .rustdyno/
        if file_path == "rustdyno.toml":
            dest = rdyno_dir / "rustdyno.toml"
        else:
            dest = project_dir / file_path

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        files_created.append(file_path)

    # Inject dependencies into Cargo.toml
    _inject_dependencies(project_dir / "Cargo.toml", config)

    # Collect generate options (not auto-run)
    generate_options = []
    gen = np.get("generate")
    if gen:
        if isinstance(gen, list):
            generate_options = [
                {
                    "label": g.get("label", ""),
                    "command": _apply_template_vars(
                        g.get("command", ""), template_vars
                    ),
                }
                for g in gen
            ]
        elif isinstance(gen, str):
            generate_options = [
                {"label": "generate", "command": _apply_template_vars(gen, template_vars)}
            ]

    return {
        "project_dir": str(project_dir),
        "board": config.get("board", {}).get("name", board),
        "files_created": files_created,
        "generate_options": generate_options,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
