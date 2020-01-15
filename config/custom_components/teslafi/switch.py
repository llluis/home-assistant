"""Support for the Tesla Locks."""
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components.switch import SwitchDevice

from . import DOMAIN, TeslaFi, TeslaFiDevice

"""=================================================================================================================="""

_LOGGER = logging.getLogger(__name__)

"""=================================================================================================================="""

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla Switch platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    controller = hass.data[DOMAIN]["controller"]

    devices = []
    devices.append(TeslaFiSwitch(controller, '_wake', 'switch', 'state', 'online', 'wake_up', None))
    #devices.append(TeslaFiSwitch(controller, '_charge', 'switch', 'charge_enable_request', 'True', 'charge_start', 'charge_stop'))

    add_entities(devices, True)

"""=================================================================================================================="""

class TeslaFiSwitch(SwitchDevice, TeslaFiDevice):
    """Representation of Tesla Switches."""

    def __init__(self, controller, device_name, device_type, api_key, on_value, on_command, off_command):
        """Initialize of the switch."""
        super().__init__(controller, device_name, device_type, api_key, False)
        self._on_value = on_value
        self._on_command = on_command
        self._off_command = off_command


    @property
    def device_class(self):
        """Return the class of this device."""
        return self._dclass


    @property
    def icon(self):
        """Icon handling."""
        if self.is_on:
            return "mdi:toggle-switch"
        else:
            return "mdi:toggle-switch-off"


    def turn_on(self, **kwargs):
        """Send the turn on command."""
        _LOGGER.debug("Turn on switch for: %s", self.name)
        res = self._controller.send(self._on_command)
        # Overrides buffer with response (valid until next polling)
        if res['response'][self._api_key] == self._on_value:
            self._current_value[self._api_key] = self._on_value
        else:
            self._current_value[self._api_key] = '!' + self._on_value


    def turn_off(self, **kwargs):
        _LOGGER.debug("Turn off switch for: %s", self.name)
        if self._off_command is not None:
            res = self._controller.send(self._off_command)
            # Overrides buffer with response (valid until next polling)
            if res['response'][self._api_key] == self._on_value:
                self._current_value[self._api_key] = self._on_value
            else:
                self._current_value[self._api_key] = '!' + self._on_value


    @property
    def is_on(self):
        """Get whether the lock is in locked state."""
        return self._current_value[self._api_key] == self._on_value

"""=================================================================================================================="""
