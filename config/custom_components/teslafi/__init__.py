"""Support for Tesla cars data through TeslaFi"""
from datetime import timedelta
from urllib.request import Request, build_opener
from urllib.error import HTTPError
from urllib.parse import urlencode
import logging
import json
import time
import voluptuous as vol

from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
)

# from homeassistant.helpers.entity_component import EntityComponent
# from homeassistant.components.input_number import InputNumber

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

"""=================================================================================================================="""

DOMAIN = "teslafi"

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

NOTIFICATION_ID = "teslafi_integration_notification"
NOTIFICATION_TITLE = "TeslaFi integration setup"

TESLAFI_COMPONENTS = ["sensor", "binary_sensor", "device_tracker"] #, "lock", "switch"]

"""=================================================================================================================="""

async def async_setup(hass, base_config):
    """Set up of Tesla platform."""

    config = base_config.get(DOMAIN)

    token = config.get(CONF_ACCESS_TOKEN)
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    controller = TeslaFi(token, scan_interval)


    if hass.data.get(DOMAIN) is None:
        hass.data[DOMAIN] = {
            "controller": controller
        }

    for component in TESLAFI_COMPONENTS:
        hass.async_create_task(discovery.async_load_platform(hass, component, DOMAIN, {}, base_config))

    # component = EntityComponent(_LOGGER, DOMAIN, hass)
    # entities = []
    # entities.append(
    #     #device_name, device_name, initial, minimum, maximum, step, "mdi:power-plug", unit, mode
    #     InputNumber(f"teslafi_{controller.name()}_max_charge", f"teslafi_{controller.name()}_max_charge", 90, 20, 100, 10, "mdi:power-plug", "%", "slider")
    # )
    # component.async_register_entity_service(
    #     "set_value",
    #     {vol.Required("value"): vol.Coerce(float)},
    #     "async_set_value",
    # )
    # component.async_register_entity_service("increment", {}, "async_increment")
    # component.async_register_entity_service("decrement", {}, "async_decrement")
    # await component.async_add_entities(entities)

    return True

"""=================================================================================================================="""

class TeslaFi:
    """Representation of a TeslaFi account / connection"""

    def __init__(self, token, scan_interval):
        """Initialise of the TeslaFi device."""

        _LOGGER.debug("Initialising TeslaFi API")

        self._baseurl = 'https://www.teslafi.com'
        self._api_actual = '/feed.php?token=' + token
        self._api_last = '/feed.php?command=lastGood&token=' + token
        self._api_command = '&command='

        self._scan_interval = scan_interval

        self._id = None
        self._vehicle_id = None
        self._display_name = None
        self._vin = None

        self._was_online = True
        self._update()
        self.update = Throttle(self._scan_interval)(self._update)

        if self.is_online():
            dataId = self._data
        else:
            dataId = self._last_data

        self._id = dataId['id']
        self._vehicle_id = dataId['vehicle_id']
        self._display_name = dataId['display_name'].replace(" ", "").lower()
        self._vin = dataId['vin']

        _LOGGER.debug("TeslaFi API Initialized")

    def is_online(self):
        return not ((not self._data) or (self._data['id'] is None))
        
    def _get_data(self):
        return self._get(self._api_actual)

    def _get_last_data(self):
        return self._get(self._api_last)

    def send(self, command):
        _LOGGER.debug("Sending command TeslaFi API")
        return self._get(self._api_actual, self._api_command + command)

    def _get(self, feed, command=None):
        if feed == self._api_actual:
            _LOGGER.debug("Querying TeslaFi API current data")
        else:
            _LOGGER.debug("Querying TeslaFi API last data")

        try:
            req = Request("%s%s" % (self._baseurl, feed if command is None else feed + command))
            opener = build_opener()
            resp = opener.open(req)
            charset = resp.info().get('charset', 'utf-8')
            data = json.loads(resp.read().decode(charset))
            opener.close()
            #_LOGGER.debug(json.dumps(data))
            return data
        except HTTPError as exception_:
            _LOGGER.error("Error communicating with TeslaFi API: %s", exception_)
            return None

    def _update(self):
        self._data = self._get_data();

        if self.is_online():
            self._last_data = self._data
            self._was_online = True
        else:
            if self._was_online:
                self._last_data = self._get_last_data()
                self._was_online = False

    def name(self):
        return ('{}'.format(self._display_name) if
                self._display_name is not None
                else self.uniq_name())

    def uniq_name(self):
        return '{}'.format(self._vin[-6:])

    def get_data(self):
        return self._data

    def get_last_data(self):
        return self._last_data

"""=================================================================================================================="""

class TeslaFiDevice(Entity):
    """Representation of a TeslaFi device"""

    def __init__(self, controller, device_name, device_type, api_key, assume):
        """Initialize of the device."""
        self._controller = controller
        self._api_key = api_key
        self._dclass = device_type
        self._device_name = device_name
        self._assume = assume

        self._name = f"teslafi_{self._controller.name()}"
        self._uid = f"teslafi_{self._controller.uniq_name()}"

        self._current_value = None
        self._last_value = None
        self._unit = None

        self._should_poll = True
        self._is_online = False
        self._available = False
        self._assumed_state = False

        _LOGGER.debug("Init device - name: '%s'; uid: '%s'", self.name, self.unique_id)

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
        return self._should_poll

    @property
    def available(self):
        """Return the polling state."""
        return self._available

    @property
    def assumed_state(self):
        """Return is the state was assumed."""
        return self._assumed_state

    @property
    def unit_of_measurement(self):
        """Return the polling state."""
        return self._unit

    @property
    def icon(self):
        """Icon handling."""
        return "mdi:car"

    def update(self, force=False):
        """Update the device."""
        _LOGGER.debug("Updating device: '%s'", self.name)
        if force:
            self._controller._update()
        else:
            self._controller.update()
        self._current_value = self._controller.get_data()
        self._last_value = self._controller.get_last_data()
        self._is_online = self._controller.is_online()

        if self._is_online:
            self._available = True
            self._assumed_state = False
        else:
            if self._assume:
                self._available = True
                self._assumed_state = True
            else:
                self._available = False
                self._assumed_state = False

    async def async_added_to_hass(self):
        """Register state update callback."""
        pass

    async def async_will_remove_from_hass(self):
        """Prepare for unload."""
        pass

"""=================================================================================================================="""

# class TeslaFiInputNumber(InputNumber):
#     """Representation of TeslaFi InputNumber."""

#     def __init__(self, controller, device_name, initial, minimum, maximum, step, unit, mode):
#         _LOGGER.debug("Init InputNumber before super")
#         super().__init__(device_name, device_name, initial, minimum, maximum, step, "mdi:power-plug", unit, mode)
#         self._controller = controller


#     # async def async_set_value(self, value):
#     #     _LOGGER.debug(">>> InputNumber set value")
#     #     super().async_set_value(value)


#     # async def async_increment(self):
#     #     _LOGGER.debug(">>> InputNumber increment")
#     #     super().async_increment()

    
#     # async def async_decrement(self):    
#     #     _LOGGER.debug(">>> InputNumber decrement")
#     #     super().async_decrement()

"""=================================================================================================================="""

