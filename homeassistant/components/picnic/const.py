"""Constants for the Picnic integration."""
from homeassistant.const import CURRENCY_EURO, DEVICE_CLASS_TIMESTAMP

DOMAIN = "picnic"

CONF_API = "api"
CONF_COORDINATOR = "coordinator"
CONF_COUNTRY_CODE = "country_code"

COUNTRY_CODES = ["NL", "DE", "BE"]
ATTRIBUTION = "Data provided by Picnic"
ADDRESS = "address"
CART_DATA = "cart_data"
SLOT_DATA = "slot_data"
LAST_ORDER_DATA = "last_order_data"

SENSOR_CART_ITEMS_COUNT = "cart_items_count"
SENSOR_CART_TOTAL_PRICE = "cart_total_price"
SENSOR_SELECTED_SLOT_START = "selected_slot_start"
SENSOR_SELECTED_SLOT_END = "selected_slot_end"
SENSOR_SELECTED_SLOT_MAX_ORDER_TIME = "selected_slot_max_order_time"
SENSOR_SELECTED_SLOT_MIN_ORDER_VALUE = "selected_slot_min_order_value"
SENSOR_LAST_ORDER_SLOT_START = "last_order_slot_start"
SENSOR_LAST_ORDER_SLOT_END = "last_order_slot_end"
SENSOR_LAST_ORDER_STATUS = "last_order_status"
SENSOR_LAST_ORDER_ETA_START = "last_order_eta_start"
SENSOR_LAST_ORDER_ETA_END = "last_order_eta_end"
SENSOR_LAST_ORDER_DELIVERY_TIME = "last_order_delivery_time"
SENSOR_LAST_ORDER_TOTAL_PRICE = "last_order_total_price"

SENSOR_TYPES = {
    SENSOR_CART_ITEMS_COUNT: {
        "icon": "mdi:format-list-numbered",
        "data_type": CART_DATA,
        "state": lambda cart: cart.get("total_count", 0),
    },
    SENSOR_CART_TOTAL_PRICE: {
        "unit": CURRENCY_EURO,
        "icon": "mdi:currency-eur",
        "default_enabled": True,
        "data_type": CART_DATA,
        "state": lambda cart: cart.get("total_price", 0) / 100,
    },
    SENSOR_SELECTED_SLOT_START: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:calendar-start",
        "default_enabled": True,
        "data_type": SLOT_DATA,
        "state": lambda slot: slot.get("window_start"),
    },
    SENSOR_SELECTED_SLOT_END: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:calendar-end",
        "default_enabled": True,
        "data_type": SLOT_DATA,
        "state": lambda slot: slot.get("window_end"),
    },
    SENSOR_SELECTED_SLOT_MAX_ORDER_TIME: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:clock-alert-outline",
        "default_enabled": True,
        "data_type": SLOT_DATA,
        "state": lambda slot: slot.get("cut_off_time"),
    },
    SENSOR_SELECTED_SLOT_MIN_ORDER_VALUE: {
        "unit": CURRENCY_EURO,
        "icon": "mdi:currency-eur",
        "default_enabled": True,
        "data_type": SLOT_DATA,
        "state": lambda slot: slot["minimum_order_value"] / 100
        if slot.get("minimum_order_value")
        else None,
    },
    SENSOR_LAST_ORDER_SLOT_START: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:calendar-start",
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("slot", {}).get("window_start"),
    },
    SENSOR_LAST_ORDER_SLOT_END: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:calendar-end",
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("slot", {}).get("window_end"),
    },
    SENSOR_LAST_ORDER_STATUS: {
        "icon": "mdi:list-status",
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("status"),
    },
    SENSOR_LAST_ORDER_ETA_START: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:clock-start",
        "default_enabled": True,
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("eta", {}).get("start"),
    },
    SENSOR_LAST_ORDER_ETA_END: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:clock-end",
        "default_enabled": True,
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("eta", {}).get("end"),
    },
    SENSOR_LAST_ORDER_DELIVERY_TIME: {
        "class": DEVICE_CLASS_TIMESTAMP,
        "icon": "mdi:timeline-clock",
        "default_enabled": True,
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("delivery_time", {}).get("start"),
    },
    SENSOR_LAST_ORDER_TOTAL_PRICE: {
        "unit": CURRENCY_EURO,
        "icon": "mdi:cash-marker",
        "data_type": LAST_ORDER_DATA,
        "state": lambda last_order: last_order.get("total_price", 0) / 100,
    },
}
