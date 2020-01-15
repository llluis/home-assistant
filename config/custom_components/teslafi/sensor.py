"""Support for the Tesla sensors."""
import logging
from homeassistant.helpers.entity import Entity

from . import DOMAIN, TeslaFi, TeslaFiDevice

"""=================================================================================================================="""

_LOGGER = logging.getLogger(__name__)

"""=================================================================================================================="""

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tesla sensor platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    controller = hass.data[DOMAIN]["controller"]

    devices = []
    devices.append(TeslaFiSensor(controller, '_state', None, None, 'carState'))
    devices.append(TeslaFiSensor(controller, '_location', None, None, 'location'))
    devices.append(TeslaFiSensor(controller, '_charging_state', None, None, 'charging_state'))
    devices.append(TeslaFiSensor(controller, '_charging_current', None, 'A', 'charger_actual_current'))
    devices.append(TeslaFiSensor(controller, '_charge_energy_added', None, 'kWh', 'charge_energy_added'))
    devices.append(TeslaFiSensor(controller, '_last_seen', None, None, 'Date', True))
#    devices.append(TeslaFiSensor(controller, '_battery_heater', None, None, 'battery_heater'))
#    devices.append(TeslaFiSensor(controller, '_battery_heater_on', None, None, 'battery_heater_on'))
    devices.append(TeslaFiSensor(controller, '_battery_level', 'battery', '%', 'battery_level', True))
    devices.append(TeslaFiSensor(controller, '_usable_battery_level', 'battery', '%', 'usable_battery_level', True))

    add_entities(devices, True)

"""=================================================================================================================="""

class TeslaFiSensor(TeslaFiDevice):
    """Representation of Tesla sensors."""

    def __init__(self, controller, device_name, device_type, unit, api_key, assume=False):
        """Initialize of the sensor."""
        super().__init__(controller, device_name, device_type, api_key, assume)
        self._unit = unit


    @property
    def state(self):
        """Return the state of the sensor."""
        if self._is_online:
            return self._current_value[self._api_key]
        else:
            if self._assume:
                return self._last_value[self._api_key]
            else:
                return None


    @property
    def device_class(self):
        """Return the class of this device."""
        return self._dclass

"""=================================================================================================================="""
