"""The kraken integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

import async_timeout
import krakenex
import pykrakenapi

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_TRACKED_ASSET_PAIRS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACKED_ASSET_PAIR,
    DISPATCH_CONFIG_UPDATED,
    DOMAIN,
)
from .utils import get_tradable_asset_pairs

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up kraken from a config entry."""
    kraken_data = KrakenData(hass, config_entry)
    await kraken_data.async_setup()
    hass.data[DOMAIN] = kraken_data
    config_entry.async_on_unload(
        config_entry.add_update_listener(async_options_updated)
    )
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        for unsub_listener in hass.data[DOMAIN].unsub_listeners:
            unsub_listener()
        hass.data.pop(DOMAIN)

    return unload_ok


class KrakenData:
    """Define an object to hold kraken data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self._hass = hass
        self._config_entry = config_entry
        self._api = pykrakenapi.KrakenAPI(krakenex.API(), retry=0, crl_sleep=0)
        self.tradable_asset_pairs = None
        self.coordinator = None
        self.unsub_listeners = []

    async def async_update(self) -> None:
        """Get the latest data from the Kraken.com REST API.

        All tradeable asset pairs are retrieved, not the tracked asset pairs
        selected by the user. This enables us to check for an unknown and
        thus likely removed asset pair in sensor.py and only log a warning
        once.
        """
        try:
            async with async_timeout.timeout(10):
                return await self._hass.async_add_executor_job(self._get_kraken_data)
        except pykrakenapi.pykrakenapi.KrakenAPIError as error:
            if "Unknown asset pair" in str(error):
                _LOGGER.info(
                    "Kraken.com reported an unknown asset pair. Refreshing list of tradable asset pairs"
                )
                await self._async_refresh_tradable_asset_pairs()
            else:
                raise UpdateFailed(
                    f"Unable to fetch data from Kraken.com: {error}"
                ) from error
        except pykrakenapi.pykrakenapi.CallRateLimitError:
            _LOGGER.warning(
                "Exceeded the Kraken.com call rate limit. Increase the update interval to prevent this error"
            )

    def _get_kraken_data(self) -> dict:
        websocket_name_pairs = self._get_websocket_name_asset_pairs()
        ticker_df = self._api.get_ticker_information(websocket_name_pairs)
        # Rename columns to their full name
        ticker_df = ticker_df.rename(
            columns={
                "a": "ask",
                "b": "bid",
                "c": "last_trade_closed",
                "v": "volume",
                "p": "volume_weighted_average",
                "t": "number_of_trades",
                "l": "low",
                "h": "high",
                "o": "opening_price",
            }
        )
        response_dict = ticker_df.transpose().to_dict()
        return response_dict

    async def _async_refresh_tradable_asset_pairs(self) -> None:
        self.tradable_asset_pairs = await self._hass.async_add_executor_job(
            get_tradable_asset_pairs, self._api
        )

    async def async_setup(self) -> None:
        """Set up the Kraken integration."""
        if not self._config_entry.options:
            options = {
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TRACKED_ASSET_PAIRS: [DEFAULT_TRACKED_ASSET_PAIR],
            }
            self._hass.config_entries.async_update_entry(
                self._config_entry, options=options
            )
        await self._async_refresh_tradable_asset_pairs()
        await asyncio.sleep(1)  # Wait 1 second to avoid triggering the CallRateLimiter
        self.coordinator = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.async_update,
            update_interval=timedelta(
                seconds=self._config_entry.options[CONF_SCAN_INTERVAL]
            ),
        )
        await self.coordinator.async_config_entry_first_refresh()

    def _get_websocket_name_asset_pairs(self) -> list:
        return ",".join(wsname for wsname in self.tradable_asset_pairs.values())

    def set_update_interval(self, update_interval: int) -> None:
        """Set the coordinator update_interval to the supplied update_interval."""
        self.coordinator.update_interval = timedelta(seconds=update_interval)


async def async_options_updated(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Triggered by config entry options updates."""
    hass.data[DOMAIN].set_update_interval(config_entry.options[CONF_SCAN_INTERVAL])
    async_dispatcher_send(hass, DISPATCH_CONFIG_UPDATED, hass, config_entry)
