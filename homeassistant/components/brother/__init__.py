"""The Brother component."""
import asyncio
from datetime import timedelta
import logging

from brother import Brother, SnmpError, UnsupportedModel

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TYPE
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_CONFIG_ENTRY, DOMAIN, SNMP
from .utils import get_snmp_engine

PLATFORMS = ["sensor"]

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up the Brother component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Brother from a config entry."""
    host = entry.data[CONF_HOST]
    kind = entry.data[CONF_TYPE]

    snmp_engine = get_snmp_engine(hass)

    coordinator = BrotherDataUpdateCoordinator(
        hass, host=host, kind=kind, snmp_engine=snmp_engine
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CONFIG_ENTRY, {})
    hass.data[DOMAIN][DATA_CONFIG_ENTRY][entry.entry_id] = coordinator
    hass.data[DOMAIN][SNMP] = snmp_engine

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][DATA_CONFIG_ENTRY].pop(entry.entry_id)
        if not hass.data[DOMAIN][DATA_CONFIG_ENTRY]:
            hass.data[DOMAIN].pop(SNMP)
            hass.data[DOMAIN].pop(DATA_CONFIG_ENTRY)

    return unload_ok


class BrotherDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Brother data from the printer."""

    def __init__(self, hass, host, kind, snmp_engine):
        """Initialize."""
        self.brother = Brother(host, kind=kind, snmp_engine=snmp_engine)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self.brother.async_update()
        except (ConnectionError, SnmpError, UnsupportedModel) as error:
            raise UpdateFailed(error) from error
        return self.brother.data
