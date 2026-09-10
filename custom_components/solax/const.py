"""Constants for the solax integration."""

from importlib.metadata import EntryPoint, entry_points

from solaxng.inverter import Inverter

DOMAIN = "solax"

MANUFACTURER = "SolaX Power"

SOLAX_INVERTER_ENTRY_POINT_GROUP = "solaxng.inverter"

INVERTER_MODELS: dict[str, EntryPoint] = {
    ep.name: ep for ep in entry_points(group=SOLAX_INVERTER_ENTRY_POINT_GROUP)
}


def model_name_for_inverter(inverter: Inverter) -> str:
    """Return the INVERTER_MODELS key matching a discovered inverter instance."""
    return next(
        name
        for name, entry_point in INVERTER_MODELS.items()
        if inverter.__class__ is entry_point.load()
    )


def friendly_name_for_model(model: str) -> str:
    """Return the friendly display name for a model."""
    name: str = INVERTER_MODELS[model].load().friendly_name()
    return name
