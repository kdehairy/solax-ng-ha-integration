"""Check that the integration manifest agrees with `pyproject.toml`.

Home Assistant installs the requirements listed in `custom_components/solax/manifest.json`,
while `uv` resolves the dependencies listed in `pyproject.toml`. The two files are edited
independently and `make release` only keeps the integration's own `version` in step, so a
dependency raised in one of them silently ships a different version to users than the one CI
tested. That is how 0.4.0 ended up with `solax-ng` 3.4.0 in `pyproject.toml` and 3.3.0 in the
manifest.

Run it from anywhere; it reports every discrepancy it finds and exits non-zero if there is one.
"""

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
MANIFEST_PATH = ROOT / "custom_components" / "solax" / "manifest.json"

# Development-environment-only dependencies: Home Assistant is provided by the host running the
# integration, so it must never appear in the manifest requirements.
DEV_ONLY_PACKAGES = frozenset({"homeassistant"})

# A PEP 508 requirement opens with the project name; everything after it is extras plus the
# version specifier, optionally followed by an environment marker. Extras are compared as
# written, since a requirement that asks for extras is not the same requirement without them.
_REQUIREMENT = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<specifier>.*)$"
)


def _canonical(name: str) -> str:
    """Return the canonical (PEP 503) form of a project name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _pins(requirements: list[str]) -> dict[str, str]:
    """Map each requirement to its version specifier, keyed by canonical project name."""
    pins: dict[str, str] = {}
    for requirement in requirements:
        match = _REQUIREMENT.match(requirement)
        if match is None:
            raise ValueError(f"unparseable requirement: {requirement!r}")
        specifier = match.group("specifier").split(";", 1)[0].strip()
        pins[_canonical(match.group("name"))] = specifier
    return pins


def _problems(pyproject: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Return a description of each way in which the two files disagree."""
    problems: list[str] = []

    declared = pyproject.get("project", {}).get("version", "<missing>")
    shipped = manifest.get("version", "<missing>")
    if declared != shipped:
        problems.append(
            f"integration version: pyproject.toml says {declared}, manifest.json says {shipped}"
        )

    pyproject_pins = _pins(pyproject.get("project", {}).get("dependencies", []))
    manifest_pins = _pins(manifest.get("requirements", []))

    for package, specifier in sorted(manifest_pins.items()):
        required = pyproject_pins.get(package)
        if required is None:
            problems.append(
                f"{package}: manifest.json requires {specifier or 'any version'}, "
                "but pyproject.toml does not depend on it"
            )
        elif required != specifier:
            problems.append(
                f"{package}: manifest.json requires {specifier or 'any version'}, "
                f"pyproject.toml requires {required or 'any version'}"
            )

    for package, specifier in sorted(pyproject_pins.items()):
        if package not in manifest_pins and package not in DEV_ONLY_PACKAGES:
            problems.append(
                f"{package}: pyproject.toml requires {specifier or 'any version'}, "
                "but manifest.json does not list it as a requirement"
            )

    return problems


def main() -> int:
    """Compare the manifest with pyproject.toml and return a non-zero code on any drift."""
    for path in (PYPROJECT_PATH, MANIFEST_PATH):
        if not path.is_file():
            print(f"error: no file at {path}", file=sys.stderr)
            return 2

    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    problems = _problems(pyproject, manifest)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if problems:
        print(
            "\nmanifest.json is what Home Assistant installs, pyproject.toml is what uv and CI "
            "run against. Make them agree.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
