"""The dsmr component."""
from asyncio import CancelledError
from contextlib import suppress

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_LISTENER, DATA_TASK, DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up DSMR from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][DATA_LISTENER] = listener

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    task = hass.data[DOMAIN][entry.entry_id][DATA_TASK]
    listener = hass.data[DOMAIN][entry.entry_id][DATA_LISTENER]

    # Cancel the reconnect task
    task.cancel()
    with suppress(CancelledError):
        await task

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)
