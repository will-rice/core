"""Support for Modbus Coil and Discrete Input sensors."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_BINARY_SENSORS,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CALL_TYPE_COIL,
    CALL_TYPE_DISCRETE,
    CONF_COILS,
    CONF_HUB,
    CONF_INPUT_TYPE,
    CONF_INPUTS,
    DEFAULT_HUB,
    DEFAULT_SCAN_INTERVAL,
    MODBUS_DOMAIN,
)

PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = vol.All(
    cv.deprecated(CONF_COILS, CONF_INPUTS),
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_INPUTS): [
                vol.All(
                    cv.deprecated(CALL_TYPE_COIL, CONF_ADDRESS),
                    vol.Schema(
                        {
                            vol.Required(CONF_ADDRESS): cv.positive_int,
                            vol.Required(CONF_NAME): cv.string,
                            vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
                            vol.Optional(CONF_HUB, default=DEFAULT_HUB): cv.string,
                            vol.Optional(CONF_SLAVE): cv.positive_int,
                            vol.Optional(
                                CONF_INPUT_TYPE, default=CALL_TYPE_COIL
                            ): vol.In([CALL_TYPE_COIL, CALL_TYPE_DISCRETE]),
                        }
                    ),
                )
            ]
        }
    ),
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the Modbus binary sensors."""
    sensors = []

    #  check for old config:
    if discovery_info is None:
        _LOGGER.warning(
            "Binary_sensor configuration is deprecated, will be removed in a future release"
        )
        discovery_info = {
            CONF_NAME: "no name",
            CONF_BINARY_SENSORS: config[CONF_INPUTS],
        }

    for entry in discovery_info[CONF_BINARY_SENSORS]:
        if CONF_HUB in entry:
            hub = hass.data[MODBUS_DOMAIN][entry[CONF_HUB]]
        else:
            hub = hass.data[MODBUS_DOMAIN][discovery_info[CONF_NAME]]
        if CONF_SCAN_INTERVAL not in entry:
            entry[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
        sensors.append(ModbusBinarySensor(hub, hass, entry))

    async_add_entities(sensors)


class ModbusBinarySensor(BinarySensorEntity):
    """Modbus binary sensor."""

    def __init__(self, hub, hass, entry):
        """Initialize the Modbus binary sensor."""
        self._hub = hub
        self._hass = hass
        self._name = entry[CONF_NAME]
        self._slave = entry.get(CONF_SLAVE)
        self._address = int(entry[CONF_ADDRESS])
        self._device_class = entry.get(CONF_DEVICE_CLASS)
        self._input_type = entry[CONF_INPUT_TYPE]
        self._value = None
        self._available = True
        self._scan_interval = timedelta(seconds=entry[CONF_SCAN_INTERVAL])

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        async_track_time_interval(self._hass, self.async_update, self._scan_interval)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._value

    @property
    def device_class(self) -> str | None:
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """

        # Handle polling directly in this entity
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    async def async_update(self, now=None):
        """Update the state of the sensor."""
        # remark "now" is a dummy parameter to avoid problems with
        # async_track_time_interval
        if self._input_type == CALL_TYPE_COIL:
            result = await self._hub.async_read_coils(self._slave, self._address, 1)
        else:
            result = await self._hub.async_read_discrete_inputs(
                self._slave, self._address, 1
            )
        if result is None:
            self._available = False
            self.async_write_ha_state()
            return

        self._value = result.bits[0] & 1
        self._available = True
        self.async_write_ha_state()
