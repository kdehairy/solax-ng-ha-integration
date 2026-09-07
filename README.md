# SolaX Power (dev)

Custom-integration build of the Home Assistant core `solax` integration, published for testing
changes ahead of upstream merge (manual inverter model select).

Not affiliated with SolaX; not intended for the HACS default store — install as a custom
repository only.

## Installation via HACS

1. HACS → ⋮ → Custom repositories → add this repo URL, category **Integration**.
2. Install "SolaX Power (dev)", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → SolaX Power.

## Development

### Testing

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=custom_components/solax --cov-report=html
```

### Notes

- Shares the `solax` domain with the core integration, so only one can be active in a given HA
  instance at a time — this one takes priority since `custom_components/` is loaded first.
- Bump the `version` field in `custom_components/solax/manifest.json` and cut a new GitHub
  release for HACS to pick up updates.
