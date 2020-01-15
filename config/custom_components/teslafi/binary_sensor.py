"""Support for the Tesla Binary Sensors."""
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components.binary_sensor import BinarySensorDevice

from . import DOMAIN, TeslaFi, TeslaFiDevice

"""=================================================================================================================="""

_LOGGER = logging.getLogger(__name__)

"""=================================================================================================================="""

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla binary sensor platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    controller = hass.data[DOMAIN]["controller"]

    devices = []
    devices.append(TeslaFiBinarySensor(controller, '_status', 'power', 'state', 'online'))
    devices.append(TeslaFiBinarySensor(controller, '_charge_enable', None, 'charge_enable_request', '1'))
    devices.append(TeslaFiBinarySensor(controller, '_climate', None, 'is_climate_on', '1'))
#    devices.append(TeslaFiBinarySensor(controller, '_locked', 'lock', 'locked', 'False'))
    devices.append(TeslaFiBinarySensor(controller, '_charge_plug', 'plug', 'charging_state', 'Disconnected', False))   # 'charge_port_latch':'Engaged'

    add_entities(devices, True)

"""=================================================================================================================="""

class TeslaFiBinarySensor(BinarySensorDevice, TeslaFiDevice):
    """Representation of Tesla binary sensors."""

    def __init__(self, controller, device_name, device_type, api_key, on_value, positive=True):
        """Initialize of the sensor."""
        super().__init__(controller, device_name, device_type, api_key, False)
        self._on_value = on_value
        self._positive = positive


    @property
    def device_class(self):
        """Return the class of this device."""
        return self._dclass

    @property
    def is_on(self):
        """Return the state of the sensor."""
        if self._positive:
            return self._current_value[self._api_key] == self._on_value
        else:
            return self._current_value[self._api_key] != self._on_value

"""=================================================================================================================="""
