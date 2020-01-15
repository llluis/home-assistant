"""Support for tracking Tesla cars."""
import logging

from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.util import slugify

from . import DOMAIN, TeslaFi, TeslaFiDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, async_see, discovery_info=None):
    """Set up the TeslaFi tracker."""
    tracker = TeslaFiDeviceTracker(
        hass, config, async_see, hass.data[DOMAIN]["controller"]
    )
    await tracker.update_info()
    async_track_utc_time_change(hass, tracker.update_info, second=range(0, 60, 30))
    return True


class TeslaFiDeviceTracker:
    """A class representing a TeslaFi device tracker."""

    def __init__(self, hass, config, see, controller):
        """Initialize the TeslaFi device scanner."""
        self.hass = hass
        self.see = see
        self._controller = controller
        self._name = f"teslafi_{self._controller.name()}"
        self._uid = f"teslafi_{self._controller.uniq_name()}"
        self._device_name = "_device_tracker"

    async def update_info(self, now=None):
        """Update the device info."""
        self._controller.update()
    
        if self.available:
            name = self.name
            dev_id = self.unique_id
            _LOGGER.debug("Updating device position: %s", name)
    
            lat = self._controller.get_data()['latitude']
            lon = self._controller.get_data()['longitude']
            attrs = {"trackr_id": dev_id, "id": dev_id, "name": name}
            await self.see(
                dev_id=dev_id, host_name=name, gps=(lat, lon), attributes=attrs
            )

    @property
    def name(self):
        """Return the name of the device."""
        return f"{self._name}{self._device_name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._uid}{self._device_name}"

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def available(self):
        """Return the polling state."""
        return self._controller.is_online()

    @property
    def icon(self):
        """Icon handling."""
        return "mdi:car"
