# SolaX Power Ng

Custom-integration build of the Home Assistant core `solax` integration, built on the maintained
[`solax-ng`](https://github.com/kdehairy/solax-ng) fork instead of the unmaintained `solax`
library, and published for testing changes ahead of upstream merge (manual inverter model select,
reconfigure support).

Not affiliated with SolaX; not intended for the HACS default store — install as a custom
repository only.

**Shares the `solax` domain with the core integration** — only one can be active in a given HA
instance at a time. Since Home Assistant loads `custom_components/` before core integrations of
the same domain, installing this one takes priority; remove/disable the core `solax` integration
first if it's already configured.

## Installation

### Via HACS

1. HACS → ⋮ (top right) → **Custom repositories** → add
   `https://github.com/kdehairy/solax-ng-ha-integration`, category **Integration**.
2. Find "Solax Power Ng" in HACS → **Integrations**, click **Download**.
3. Restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → search for "SolaX Power".

Once installed via HACS, updates are detected automatically from new GitHub releases.

### Without HACS (manual)

1. Download or clone this repository.
2. Copy the `custom_components/solax` directory into your Home Assistant config directory, so you
   end up with `<config>/custom_components/solax/`.
3. Restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → search for "SolaX Power".

To update, repeat step 2 with the new version and restart again — HACS-style automatic update
notifications don't apply to a manual install.

## Development

### Testing

```bash
# Install development dependencies (creates .venv)
make init

# Run the test suite with coverage
make test

# Run the full verification suite (manifest consistency, formatting, lint, type-check, tests)
make verify
```

### Releasing

1. Run `make release BUMP=patch|minor|major`. It bumps `version` in
   `custom_components/solax/manifest.json` and `pyproject.toml`, commits both, and signs a
   `v<version>` tag.
2. Push the branch and the tag: `git push origin main v<version>`.
3. The `release` CI job creates the GitHub release from the tag — a tag on its own is not enough,
   HACS needs an actual release. HACS then detects the update automatically.

Dependency versions are declared once, in `pyproject.toml`. `manifest.json` has to carry the same
pin because that is what Home Assistant installs, so `make verify` fails if the two files disagree.
