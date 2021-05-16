"""Support for Modbus."""
import asyncio
import logging

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient
from pymodbus.constants import Defaults
from pymodbus.exceptions import ModbusException
from pymodbus.transaction import ModbusRtuFramer

from homeassistant.const import (
    CONF_DELAY,
    CONF_HOST,
    CONF_METHOD,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_TYPE,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import callback
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import async_call_later

from .const import (
    ATTR_ADDRESS,
    ATTR_HUB,
    ATTR_STATE,
    ATTR_UNIT,
    ATTR_VALUE,
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CLOSE_COMM_ON_ERROR,
    CONF_PARITY,
    CONF_STOPBITS,
    DEFAULT_HUB,
    MODBUS_DOMAIN as DOMAIN,
    PLATFORMS,
    SERVICE_WRITE_COIL,
    SERVICE_WRITE_REGISTER,
)

_LOGGER = logging.getLogger(__name__)


async def async_modbus_setup(
    hass, config, service_write_register_schema, service_write_coil_schema
):
    """Set up Modbus component."""

    hass.data[DOMAIN] = hub_collect = {}
    for conf_hub in config[DOMAIN]:
        my_hub = ModbusHub(hass, conf_hub)
        hub_collect[conf_hub[CONF_NAME]] = my_hub

        # modbus needs to be activated before components are loaded
        # to avoid a racing problem
        await my_hub.async_setup()

        # load platforms
        for component, conf_key in PLATFORMS:
            if conf_key in conf_hub:
                hass.async_create_task(
                    async_load_platform(hass, component, DOMAIN, conf_hub, config)
                )

    async def async_stop_modbus(event):
        """Stop Modbus service."""

        for client in hub_collect.values():
            await client.async_close()
            del client

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop_modbus)

    async def async_write_register(service):
        """Write Modbus registers."""
        unit = int(float(service.data[ATTR_UNIT]))
        address = int(float(service.data[ATTR_ADDRESS]))
        value = service.data[ATTR_VALUE]
        client_name = (
            service.data[ATTR_HUB] if ATTR_HUB in service.data else DEFAULT_HUB
        )
        if isinstance(value, list):
            await hub_collect[client_name].async_write_registers(
                unit, address, [int(float(i)) for i in value]
            )
        else:
            await hub_collect[client_name].async_write_register(
                unit, address, int(float(value))
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_REGISTER,
        async_write_register,
        schema=service_write_register_schema,
    )

    async def async_write_coil(service):
        """Write Modbus coil."""
        unit = service.data[ATTR_UNIT]
        address = service.data[ATTR_ADDRESS]
        state = service.data[ATTR_STATE]
        client_name = (
            service.data[ATTR_HUB] if ATTR_HUB in service.data else DEFAULT_HUB
        )
        if isinstance(state, list):
            await hub_collect[client_name].async_write_coils(unit, address, state)
        else:
            await hub_collect[client_name].async_write_coil(unit, address, state)

    hass.services.async_register(
        DOMAIN, SERVICE_WRITE_COIL, async_write_coil, schema=service_write_coil_schema
    )
    return True


class ModbusHub:
    """Thread safe wrapper class for pymodbus."""

    def __init__(self, hass, client_config):
        """Initialize the Modbus hub."""

        # generic configuration
        self._client = None
        self._async_cancel_listener = None
        self._in_error = False
        self._lock = asyncio.Lock()
        self.hass = hass
        self._config_name = client_config[CONF_NAME]
        self._config_type = client_config[CONF_TYPE]
        self._config_port = client_config[CONF_PORT]
        self._config_timeout = client_config[CONF_TIMEOUT]
        self._config_delay = client_config[CONF_DELAY]
        self._config_reset_socket = client_config[CONF_CLOSE_COMM_ON_ERROR]
        Defaults.Timeout = client_config[CONF_TIMEOUT]
        if self._config_type == "serial":
            # serial configuration
            self._config_method = client_config[CONF_METHOD]
            self._config_baudrate = client_config[CONF_BAUDRATE]
            self._config_stopbits = client_config[CONF_STOPBITS]
            self._config_bytesize = client_config[CONF_BYTESIZE]
            self._config_parity = client_config[CONF_PARITY]
        else:
            # network configuration
            self._config_host = client_config[CONF_HOST]

    @property
    def name(self):
        """Return the name of this hub."""
        return self._config_name

    def _log_error(self, exception_error: ModbusException, error_state=True):
        log_text = "Pymodbus: " + str(exception_error)
        if self._in_error:
            _LOGGER.debug(log_text)
        else:
            _LOGGER.error(log_text)
            self._in_error = error_state

    async def async_setup(self):
        """Set up pymodbus client."""
        try:
            if self._config_type == "serial":
                self._client = ModbusSerialClient(
                    method=self._config_method,
                    port=self._config_port,
                    baudrate=self._config_baudrate,
                    stopbits=self._config_stopbits,
                    bytesize=self._config_bytesize,
                    parity=self._config_parity,
                    timeout=self._config_timeout,
                    retry_on_empty=True,
                    reset_socket=self._config_reset_socket,
                )
            elif self._config_type == "rtuovertcp":
                self._client = ModbusTcpClient(
                    host=self._config_host,
                    port=self._config_port,
                    framer=ModbusRtuFramer,
                    timeout=self._config_timeout,
                    reset_socket=self._config_reset_socket,
                )
            elif self._config_type == "tcp":
                self._client = ModbusTcpClient(
                    host=self._config_host,
                    port=self._config_port,
                    timeout=self._config_timeout,
                    reset_socket=self._config_reset_socket,
                )
            elif self._config_type == "udp":
                self._client = ModbusUdpClient(
                    host=self._config_host,
                    port=self._config_port,
                    timeout=self._config_timeout,
                    reset_socket=self._config_reset_socket,
                )
        except ModbusException as exception_error:
            self._log_error(exception_error, error_state=False)
            return

        async with self._lock:
            await self.hass.async_add_executor_job(self._pymodbus_connect)

        # Start counting down to allow modbus requests.
        if self._config_delay:
            self._async_cancel_listener = async_call_later(
                self.hass, self._config_delay, self.async_end_delay
            )

    @callback
    def async_end_delay(self, args):
        """End startup delay."""
        self._async_cancel_listener = None
        self._config_delay = 0

    def _pymodbus_close(self):
        """Close sync. pymodbus."""
        if self._client:
            try:
                self._client.close()
            except ModbusException as exception_error:
                self._log_error(exception_error)
        self._client = None

    async def async_close(self):
        """Disconnect client."""
        if self._async_cancel_listener:
            self._async_cancel_listener()
            self._async_cancel_listener = None

        async with self._lock:
            return await self.hass.async_add_executor_job(self._pymodbus_close)

    def _pymodbus_connect(self):
        """Connect client."""
        try:
            self._client.connect()
        except ModbusException as exception_error:
            self._log_error(exception_error, error_state=False)

    def _pymodbus_call(self, unit, address, value, check_attr, func):
        """Call sync. pymodbus."""
        kwargs = {"unit": unit} if unit else {}
        try:
            result = func(address, value, **kwargs)
        except ModbusException as exception_error:
            self._log_error(exception_error)
            result = exception_error
        if not hasattr(result, check_attr):
            self._log_error(result)
            return None
        self._in_error = False
        return result

    async def async_pymodbus_call(self, unit, address, value, check_attr, func):
        """Convert async to sync pymodbus call."""
        if self._config_delay:
            return None
        async with self._lock:
            return await self.hass.async_add_executor_job(
                self._pymodbus_call, unit, address, value, check_attr, func
            )

    async def async_read_coils(self, unit, address, count):
        """Read coils."""
        return await self.async_pymodbus_call(
            unit, address, count, "bits", self._client.read_coils
        )

    async def async_read_discrete_inputs(self, unit, address, count):
        """Read discrete inputs."""
        return await self.async_pymodbus_call(
            unit, address, count, "bits", self._client.read_discrete_inputs
        )

    async def async_read_input_registers(self, unit, address, count):
        """Read input registers."""
        return await self.async_pymodbus_call(
            unit, address, count, "registers", self._client.read_input_registers
        )

    async def async_read_holding_registers(self, unit, address, count):
        """Read holding registers."""
        return await self.async_pymodbus_call(
            unit, address, count, "registers", self._client.read_holding_registers
        )

    async def async_write_coil(self, unit, address, value) -> bool:
        """Write coil."""
        return await self.async_pymodbus_call(
            unit, address, value, "value", self._client.write_coil
        )

    async def async_write_coils(self, unit, address, values) -> bool:
        """Write coil."""
        return await self.async_pymodbus_call(
            unit, address, values, "count", self._client.write_coils
        )

    async def async_write_register(self, unit, address, value) -> bool:
        """Write register."""
        return await self.async_pymodbus_call(
            unit, address, value, "value", self._client.write_register
        )

    async def async_write_registers(self, unit, address, values) -> bool:
        """Write registers."""
        return await self.async_pymodbus_call(
            unit, address, values, "count", self._client.write_registers
        )
