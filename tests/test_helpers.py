"""Tests for internal helper functions."""

import tomli
import tomli_w

from server import _apply_template_vars, _inject_dependencies, _parse_deps


class TestApplyTemplateVars:
    def test_replaces_protocol(self):
        result = _apply_template_vars(
            "runner = \"probe-rs run --protocol {{PROTOCOL}}\"",
            {"{{PROTOCOL}}": "swd"},
        )
        assert result == 'runner = "probe-rs run --protocol swd"'

    def test_replaces_multiple_vars(self):
        result = _apply_template_vars(
            "{{PROJECT_NAME}} uses {{BOARD_FILE}}",
            {"{{PROJECT_NAME}}": "blinky", "{{BOARD_FILE}}": "rpi-pico.toml"},
        )
        assert result == "blinky uses rpi-pico.toml"

    def test_no_replacement_when_no_match(self):
        result = _apply_template_vars("no placeholders here", {"{{X}}": "y"})
        assert result == "no placeholders here"

    def test_multiple_occurrences(self):
        result = _apply_template_vars(
            "{{X}} and {{X}}", {"{{X}}": "val"}
        )
        assert result == "val and val"


class TestParseDeps:
    def test_dict_passthrough(self):
        deps = {"cortex-m": "0.7"}
        assert _parse_deps(deps) == deps

    def test_dict_with_features(self):
        deps = {"cortex-m": {"version": "0.7", "features": ["inline-asm"]}}
        assert _parse_deps(deps) == deps

    def test_string_format(self):
        raw = """
cortex-m    = { version = "0.7", features = ["inline-asm"] }
microbit-v2 = "0.16"
rtt-target  = "0.6"
"""
        result = _parse_deps(raw)
        assert result["microbit-v2"] == "0.16"
        assert result["rtt-target"] == "0.6"
        assert result["cortex-m"]["version"] == "0.7"

    def test_none_returns_empty(self):
        assert _parse_deps(None) == {}

    def test_int_returns_empty(self):
        assert _parse_deps(42) == {}


class TestInjectDependencies:
    def _make_cargo(self, tmp_path, extra_deps=None):
        cargo = {
            "package": {"name": "test", "version": "0.1.0", "edition": "2021"},
            "dependencies": extra_deps or {},
        }
        path = tmp_path / "Cargo.toml"
        path.write_text(tomli_w.dumps(cargo))
        return path

    def test_injects_table_deps(self, tmp_path):
        cargo_path = self._make_cargo(tmp_path)
        config = {
            "new_project": {
                "dependencies": {
                    "cortex-m": {"version": "0.7", "features": ["inline-asm"]},
                    "rp2040-hal": "0.10",
                }
            }
        }
        _inject_dependencies(cargo_path, config)

        result = tomli.loads(cargo_path.read_text())
        assert result["dependencies"]["rp2040-hal"] == "0.10"
        assert result["dependencies"]["cortex-m"]["version"] == "0.7"

    def test_injects_string_deps(self, tmp_path):
        cargo_path = self._make_cargo(tmp_path)
        config = {
            "new_project": {
                "dependencies": 'microbit-v2 = "0.16"\nrtt-target = "0.6"\n'
            }
        }
        _inject_dependencies(cargo_path, config)

        result = tomli.loads(cargo_path.read_text())
        assert result["dependencies"]["microbit-v2"] == "0.16"
        assert result["dependencies"]["rtt-target"] == "0.6"

    def test_injects_build_deps(self, tmp_path):
        cargo_path = self._make_cargo(tmp_path)
        config = {
            "new_project": {
                "dependencies": {"anyhow": "1"},
                "build-dependencies": {"embuild": "0.33"},
            }
        }
        _inject_dependencies(cargo_path, config)

        result = tomli.loads(cargo_path.read_text())
        assert result["dependencies"]["anyhow"] == "1"
        assert result["build-dependencies"]["embuild"] == "0.33"

    def test_preserves_existing_deps(self, tmp_path):
        cargo_path = self._make_cargo(tmp_path, {"existing-crate": "1.0"})
        config = {"new_project": {"dependencies": {"new-crate": "2.0"}}}
        _inject_dependencies(cargo_path, config)

        result = tomli.loads(cargo_path.read_text())
        assert result["dependencies"]["existing-crate"] == "1.0"
        assert result["dependencies"]["new-crate"] == "2.0"

    def test_noop_when_no_deps(self, tmp_path):
        cargo_path = self._make_cargo(tmp_path)
        original = cargo_path.read_text()
        _inject_dependencies(cargo_path, {"new_project": {}})
        assert cargo_path.read_text() == original
