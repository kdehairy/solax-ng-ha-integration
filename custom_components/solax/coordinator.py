"""Constants for the solax integration."""

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from solaxng import InverterResponse


class SolaxDataUpdateCoordinator(DataUpdateCoordinator[InverterResponse]):
    """DataUpdateCoordinator for solax."""
