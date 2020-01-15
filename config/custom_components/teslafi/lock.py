"""Support for the Tesla Locks."""
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components.lock import LockDevice

from . import DOMAIN, TeslaFi, TeslaFiDevice

"""=================================================================================================================="""

_LOGGER = logging.getLogger(__name__)

"""=================================================================================================================="""

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla Lock platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    controller = hass.data[DOMAIN]["controller"]

    devices = []
    devices.append(TeslaFiLock(controller, '_door_lock', 'lock', 'locked', 'True'))

    add_entities(devices, True)

"""=================================================================================================================="""

class TeslaFiLock(LockDevice, TeslaFiDevice):
    """Representation of Tesla Locks."""

    def __init__(self, controller, device_name, device_type, api_key, on_value):
        """Initialize of the lock."""
        super().__init__(controller, device_name, device_type, api_key, False)
        self._on_value = on_value


    @property
    def device_class(self):
        """Return the class of this device."""
        return self._dclass


    @property
    def icon(self):
        """Icon handling."""
        if self.is_locked:
            return "mdi:lock"
        else:
            return "mdi:lock-open"


    def _execute(self, lock):
        """Send the lock / unlock command."""
        command = None
        rety = None
        retn = None
        if lock:
            command = 'door_lock'
            rety = self._on_value
            retn = '!' + self._on_value
        else:
            command = 'door_unlock'
            rety = '!' + self._on_value
            retn = self._on_value
        res = self._controller.send(command)
        # Overrides buffer with response (valid until next polling)
        if res['response']['result']:
            self._current_value[self._api_key] = rety
        else:
            self._current_value[self._api_key] = retn


    def lock(self, **kwargs):
        _LOGGER.debug("Locking doors for: %s", self.name)
        self._execute(True)


    def unlock(self, **kwargs):
        _LOGGER.debug("Unlocking doors for: %s", self.name)
        self._execute(False)


    @property
    def is_locked(self):
        """Get whether the lock is in locked state."""
        return self._current_value[self._api_key] == self._on_value

"""=================================================================================================================="""
