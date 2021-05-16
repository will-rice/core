"""The Bravia TV component."""

from bravia_tv import BraviaRC

from homeassistant.const import CONF_HOST, CONF_MAC

from .const import BRAVIARC, DOMAIN, UNDO_UPDATE_LISTENER

PLATFORMS = ["media_player"]


async def async_setup_entry(hass, config_entry):
    """Set up a config entry."""
    host = config_entry.data[CONF_HOST]
    mac = config_entry.data[CONF_MAC]

    undo_listener = config_entry.add_update_listener(update_listener)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        BRAVIARC: BraviaRC(host, mac),
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    hass.data[DOMAIN][config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
