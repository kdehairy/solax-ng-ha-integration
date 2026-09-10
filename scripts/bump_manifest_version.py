"""Bump the `version` field in custom_components/solax/manifest.json.

Used by `make release BUMP=patch|minor|major`. Prints the new version to
stdout and nothing else, so it can be captured with shell command
substitution.
"""

import json
import sys
from pathlib import Path

MANIFEST_PATH = Path("custom_components/solax/manifest.json")


def _bump(version: str, bump: str) -> str:
    """Return `version` bumped according to `bump` (patch, minor or major)."""
    major, minor, patch = (int(part) for part in version.split("."))
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def main() -> None:
    """Bump the manifest version in place and print the new version."""
    if len(sys.argv) != 2 or sys.argv[1] not in {"patch", "minor", "major"}:
        print("Usage: bump_manifest_version.py {patch|minor|major}", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["version"] = _bump(manifest["version"], sys.argv[1])
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest["version"])


if __name__ == "__main__":
    main()
