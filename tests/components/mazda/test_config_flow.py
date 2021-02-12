"""Test the Mazda Connected Services config flow."""
from unittest.mock import patch

import aiohttp

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.mazda.config_flow import (
    MazdaAccountLockedException,
    MazdaAuthenticationException,
)
from homeassistant.components.mazda.const import DOMAIN
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_REGION
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

FIXTURE_USER_INPUT = {
    CONF_EMAIL: "example@example.com",
    CONF_PASSWORD: "password",
    CONF_REGION: "MNAO",
}
FIXTURE_USER_INPUT_REAUTH = {
    CONF_EMAIL: "example@example.com",
    CONF_PASSWORD: "password_fixed",
    CONF_REGION: "MNAO",
}


async def test_form(hass):
    """Test the entire flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        return_value=True,
    ), patch(
        "homeassistant.components.mazda.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mazda.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == FIXTURE_USER_INPUT[CONF_EMAIL]
    assert result2["data"] == FIXTURE_USER_INPUT
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=MazdaAuthenticationException("Failed to authenticate"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_account_locked(hass: HomeAssistant) -> None:
    """Test we handle account locked error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=MazdaAccountLockedException("Account locked"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "account_locked"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=aiohttp.ClientError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(hass):
    """Test we handle unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}


async def test_reauth_flow(hass: HomeAssistant) -> None:
    """Test reauth works."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=MazdaAuthenticationException("Failed to authenticate"),
    ):
        mock_config = MockConfigEntry(
            domain=DOMAIN,
            unique_id=FIXTURE_USER_INPUT[CONF_EMAIL],
            data=FIXTURE_USER_INPUT,
        )
        mock_config.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"
        assert result["errors"] == {"base": "invalid_auth"}

    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reauth", "unique_id": FIXTURE_USER_INPUT[CONF_EMAIL]},
            data=FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_ABORT
        assert result2["reason"] == "reauth_successful"


async def test_reauth_authorization_error(hass: HomeAssistant) -> None:
    """Test we show user form on authorization error."""
    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=MazdaAuthenticationException("Failed to authenticate"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result2["step_id"] == "reauth"
        assert result2["errors"] == {"base": "invalid_auth"}


async def test_reauth_account_locked(hass: HomeAssistant) -> None:
    """Test we show user form on account_locked error."""
    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=MazdaAccountLockedException("Account locked"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result2["step_id"] == "reauth"
        assert result2["errors"] == {"base": "account_locked"}


async def test_reauth_connection_error(hass: HomeAssistant) -> None:
    """Test we show user form on connection error."""
    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=aiohttp.ClientError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result2["step_id"] == "reauth"
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth_unknown_error(hass: HomeAssistant) -> None:
    """Test we show user form on unknown error."""
    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        side_effect=Exception,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result2["step_id"] == "reauth"
        assert result2["errors"] == {"base": "unknown"}


async def test_reauth_unique_id_not_found(hass: HomeAssistant) -> None:
    """Test we show user form when unique id not found during reauth."""
    with patch(
        "homeassistant.components.mazda.config_flow.MazdaAPI.validate_credentials",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth"}, data=FIXTURE_USER_INPUT
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reauth"

        # Change the unique_id of the flow in order to cause a mismatch
        flows = hass.config_entries.flow.async_progress()
        flows[0]["context"]["unique_id"] = "example2@example.com"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT_REAUTH,
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result2["step_id"] == "reauth"
        assert result2["errors"] == {"base": "unknown"}
