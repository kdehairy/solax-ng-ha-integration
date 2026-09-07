# Tests

These tests are Home Assistant core's own test suite for the `solax` integration,
ported to run against `custom_components/solax` instead of the core copy.

## Running

```bash
uv sync
uv run pytest
```

## How this works

[`pytest-homeassistant-custom-component`](https://pypi.org/project/pytest-homeassistant-custom-component/)
(PHACC) vendors HA core's test infrastructure (`tests/common.py`, the core
`conftest.py` plugin, `testing_config/`) as an installable package, so custom
integrations can reuse the exact fixtures and helpers core's own tests use
(`hass`, `MockConfigEntry`, `async_fire_time_changed`, `device_registry`,
`entity_registry`, `freezer`, etc.).

Two things are required for this to work and must not be removed:

- The rootdir `conftest.py` declares `pytest_plugins =
  "pytest_homeassistant_custom_component"`. This must live in the rootdir
  `conftest.py` — pytest 9 rejects `pytest_plugins` declared in any other
  `conftest.py`.
- The autouse `auto_enable_custom_integrations` fixture (also in the rootdir
  `conftest.py`) depends on the `enable_custom_integrations` fixture. Without
  it, Home Assistant silently loads the core `solax` integration bundled in
  the `homeassistant` wheel instead of `custom_components/solax`, and the
  test run hangs.

## Re-syncing from a core checkout

`custom_components/solax` is currently byte-identical to
`homeassistant/components/solax` in HA core (aside from the added `version`
key in `manifest.json`). If core's tests change, re-copy them and re-apply
the two import rewrites:

```bash
cp /path/to/home-assistant/tests/components/solax/{conftest,test_config_flow,test_init,test_sensor}.py tests/
sed -i \
  -e 's/homeassistant\.components\.solax/custom_components.solax/g' \
  -e 's/^from tests\.common import/from pytest_homeassistant_custom_component.common import/' \
  tests/*.py
```
