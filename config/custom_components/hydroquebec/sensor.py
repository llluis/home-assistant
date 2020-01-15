"""
Support for HydroQuebec.
Official component deprecated after HA 100.3
Use as custom_component
pip3 install --target /config/deps --no-dependencies https://github.com/titilambert/pyhydroquebec/archive/master.zip#pyhydroquebec==3.0.0

Get data from 'My Consumption Profile' page:
https://www.hydroquebec.com/portail/en/group/clientele/portrait-de-consommation
"""
import logging
import asyncio
from datetime import datetime, timedelta
from dateutil import tz

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    ENERGY_KILO_WATT_HOUR,
    CONF_NAME,
    CONF_MONITORED_VARIABLES,
    TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

from pyhydroquebec.error import PyHydroQuebecHTTPError
from pyhydroquebec.client import HydroQuebecClient

_LOGGER = logging.getLogger(__name__)

KILOWATT_HOUR = ENERGY_KILO_WATT_HOUR
PRICE = "CAD"
DAYS = "days"
CONF_CONTRACT = "contract"

DEFAULT_NAME = "HydroQuebec"

REQUESTS_TIMEOUT = 15
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=3)
SCAN_INTERVAL = timedelta(hours=3)
# MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)
# SCAN_INTERVAL = timedelta(minutes=60)

SENSOR_TYPES = {
    "yesterday_total_consumption": [
        "Yesterday total consumption",
        KILOWATT_HOUR,
        "mdi:flash",
        "total_consumption",
    ],
    "yesterday_lower_price_consumption": [
        "Yesterday lower price consumption",
        KILOWATT_HOUR,
        "mdi:flash",
        "lower_price_consumption",
    ],
    "yesterday_higher_price_consumption": [
        "Yesterday higher price consumption",
        KILOWATT_HOUR,
        "mdi:flash",
        "higher_price_consumption",
    ],
    "yesterday_average_temperature": [
        "Yesterday average temperature",
        TEMP_CELSIUS,
        "mdi:thermometer",
        "average_temperature",
    ],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MONITORED_VARIABLES): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_CONTRACT): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the HydroQuebec sensor."""
    # Create a data fetcher to support all of the configured sensors. Then make
    # the first call to init the data.

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    contract = config.get(CONF_CONTRACT)
    name = config.get(CONF_NAME)
    time_zone = str(hass.config.time_zone)

    httpsession = hass.helpers.aiohttp_client.async_get_clientsession()
    hydroquebec_data = HydroquebecData(username, password, httpsession, contract, time_zone)

    await hydroquebec_data.async_update()

    sensors = []
    for variable in config[CONF_MONITORED_VARIABLES]:
        sensors.append(HydroQuebecSensor(hydroquebec_data, variable, name))

    async_add_entities(sensors, True)

    return True


class HydroQuebecSensor(Entity):
    """Implementation of a HydroQuebec sensor."""

    def __init__(self, hydroquebec_data, sensor_type, name):
        """Initialize the sensor."""
        self.client_name = name
        self.type = sensor_type
        self._name = SENSOR_TYPES[sensor_type][0]
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self._icon = SENSOR_TYPES[sensor_type][2]
        self.hydroquebec_data = hydroquebec_data
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client_name} {self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    async def async_update(self):
        """Get the latest data from Hydroquebec and update the state."""
        await self.hydroquebec_data.async_update()

        curr = self.hydroquebec_data.data.current_daily_data
        yesterday_date = list(curr.keys())[0]
        val = curr[yesterday_date][SENSOR_TYPES[self.type][3]]
        if val is not None:
            self._state = round(val, 2)
        else:
            self._state = None


class HydroquebecData:
    """Get data from HydroQuebec."""

    def __init__(self, username, password, httpsession, contract=None, time_zone='America/Montreal'):
        """Initialize the data object."""

        self.client = HydroQuebecClient(
            username, password, REQUESTS_TIMEOUT #, httpsession#, 'DEBUG'
         )

        self._tz = tz.gettz(time_zone)
        self._contract = contract
        self.data = {}


    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Return the latest collected data from HydroQuebec."""

        _LOGGER.debug("Updating HQ sensor")

        await self.client.login()

        for customer in self.client.customers:
            if customer.contract_id != self._contract and self._contract is not None:
                continue
            if self._contract is None:
                _LOGGER.warning("Contract id not specified, using first available.")

            yesterday = datetime.now(self._tz) - timedelta(days=1)
            yesterday_str = yesterday.strftime("%Y-%m-%d")
            await customer.fetch_daily_data(yesterday_str, yesterday_str)

            # Close to midnight, yesterday not yet available. Get the day before then.
            if not customer.current_daily_data:
                yesterday = yesterday - timedelta(days=1)
                yesterday_str = yesterday.strftime("%Y-%m-%d")
                await customer.fetch_daily_data(yesterday_str, yesterday_str)

            self.data = customer

            await self.client.close_session()

            return
