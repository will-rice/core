"""Tests for the pvpc_hourly_pricing config_flow."""
from datetime import datetime
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.pvpc_hourly_pricing import ATTR_TARIFF, DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .conftest import check_valid_state

from tests.common import date_util
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_config_flow(
    hass, legacy_patchable_time, pvpc_aioclient_mock: AiohttpClientMocker
):
    """
    Test config flow for pvpc_hourly_pricing.

    - Create a new entry with tariff "normal"
    - Check state and attributes
    - Check abort when trying to config another with same tariff
    - Check removal and add again to check state restoration
    """
    hass.config.time_zone = dt_util.get_time_zone("Europe/Madrid")
    mock_data = {"return_time": datetime(2019, 10, 26, 14, 0, tzinfo=date_util.UTC)}

    def mock_now():
        return mock_data["return_time"]

    with patch("homeassistant.util.dt.utcnow", new=mock_now):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "test", ATTR_TARIFF: "normal"}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        await hass.async_block_till_done()
        state = hass.states.get("sensor.test")
        check_valid_state(state, tariff="normal")
        assert pvpc_aioclient_mock.call_count == 1

        # Check abort when configuring another with same tariff
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "test", ATTR_TARIFF: "normal"}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert pvpc_aioclient_mock.call_count == 1

        # Check removal
        registry = er.async_get(hass)
        registry_entity = registry.async_get("sensor.test")
        assert await hass.config_entries.async_remove(registry_entity.config_entry_id)

        # and add it again with UI
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "test", ATTR_TARIFF: "normal"}
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        await hass.async_block_till_done()
        state = hass.states.get("sensor.test")
        check_valid_state(state, tariff="normal")
        assert pvpc_aioclient_mock.call_count == 2
