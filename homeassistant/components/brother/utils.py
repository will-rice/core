"""Brother helpers functions."""
import logging

import pysnmp.hlapi.asyncio as hlapi
from pysnmp.hlapi.asyncio.cmdgen import lcd

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers import singleton

from .const import DOMAIN, SNMP

_LOGGER = logging.getLogger(__name__)


@singleton.singleton("snmp_engine")
def get_snmp_engine(hass):
    """Get SNMP engine."""
    _LOGGER.debug("Creating SNMP engine")
    snmp_engine = hlapi.SnmpEngine()

    @callback
    def shutdown_listener(ev):
        if hass.data.get(DOMAIN):
            _LOGGER.debug("Unconfiguring SNMP engine")
            lcd.unconfigure(hass.data[DOMAIN][SNMP], None)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown_listener)

    return snmp_engine
