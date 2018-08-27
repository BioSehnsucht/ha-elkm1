"""
Support the ElkM1 Gold and ElkM1 EZ8 alarm / integration panels.
Uses https://github.com/BioSehnsucht/pyelk / https://pypi.python.org/pypi/PyElk

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/elkm1/
"""

import asyncio
import logging

import voluptuous as vol
from homeassistant.const import (CONF_EXCLUDE, CONF_HOST, CONF_INCLUDE,
                                 CONF_PASSWORD, CONF_USERNAME, STATE_UNKNOWN)
from homeassistant.core import HomeAssistant, callback  # noqa
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType  # noqa

DOMAIN = "elkm1"

REQUIREMENTS = ['elkm1-lib==0.7.2']

CONF_AREA = 'area'
CONF_COUNTER = 'counter'
CONF_KEYPAD = 'keypad'
CONF_OUTPUT = 'output'
CONF_SETTING = 'setting'
CONF_TASK = 'task'
CONF_THERMOSTAT = 'thermostat'
CONF_USER = 'user'
CONF_PANEL = 'panel'
CONF_PLC = 'plc'  # Not light because HASS complains about this
CONF_ZONE = 'zone'

CONF_ENABLED = 'enabled'    # True to enable subdomain
CONF_HIDE = 'hide'
CONF_SHOW = 'show'
CONF_LOVELACE = 'lovelace'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA_SUBDOMAIN = vol.Schema({
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,
    vol.Optional(CONF_INCLUDE): list,
    vol.Optional(CONF_EXCLUDE): list,
    vol.Optional(CONF_HIDE): list,
    vol.Optional(CONF_SHOW): list,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_LOVELACE, default=False): cv.boolean,
        vol.Optional(CONF_AREA): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_COUNTER): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_KEYPAD): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_OUTPUT): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_PLC): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_SETTING): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_TASK): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_THERMOSTAT): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_USER): CONFIG_SCHEMA_SUBDOMAIN,
        vol.Optional(CONF_ZONE): CONFIG_SCHEMA_SUBDOMAIN,
    })
}, extra=vol.ALLOW_EXTRA)

SUPPORTED_DOMAINS = ['sensor', 'switch', 'alarm_control_panel',
                     'climate', 'light']


@asyncio.coroutine
def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Elk M1 platform."""

    from elkm1_lib.const import Max
    from elkm1_lib.message import housecode_to_index
    import elkm1_lib as elkm1

    CONFIGS = {
        CONF_AREA: Max.AREAS.value,
        CONF_COUNTER: Max.COUNTERS.value,
        CONF_KEYPAD: Max.KEYPADS.value,
        CONF_OUTPUT: Max.OUTPUTS.value,
        CONF_PANEL: 1,
        CONF_PLC: Max.LIGHTS.value,
        CONF_SETTING: Max.SETTINGS.value,
        CONF_TASK: Max.TASKS.value,
        CONF_THERMOSTAT: Max.THERMOSTATS.value,
        CONF_USER: Max.USERS.value,
        CONF_ZONE: Max.ZONES.value,
    }

    def parse_value(val, max_):
        """Parse a value as an int or housecode."""
        i = int(val) if val.isdigit() else (housecode_to_index(val) + 1)
        if i < 1 or i > max_:
            raise ValueError('Value not in range 1 to %d: "%s"' % (max_, val))
        return i

    def parse_range(config, item, set_to, values, max_):
        """Parse a range list, e.g. rng = "3, 45, 46, 48-51, 77."""
        if item not in config:
            return

        ranges = config[item]
        for rng in ranges:
            for one_rng in map(str.strip, str(rng).split(',')):
                if '-' in one_rng:
                    rng_vals = [s.strip() for s in one_rng.split('-')]
                    start = parse_value(rng_vals[0], max_)
                    end = parse_value(rng_vals[1], max_)
                else:
                    start = end = parse_value(one_rng, max_)
                values[start-1:end] = [set_to] * (end - start + 1)

    def parse_config(item, max_):
        """Parse a config for an element type such as: zones, plc, etc."""
        if item not in config_raw:
            return (True, [True] * max_, [True] * max_)

        conf = config_raw[item]

        if CONF_ENABLED in conf and not conf[CONF_ENABLED]:
            return (False, [False] * max_, [False] * max_)

        included = [CONF_INCLUDE not in conf] * max_
        parse_range(conf, CONF_INCLUDE, True, included, max_)
        parse_range(conf, CONF_EXCLUDE, False, included, max_)

        shown = [None] * max_
        parse_range(conf, CONF_SHOW, True, shown, max_)
        parse_range(conf, CONF_HIDE, False, shown, max_)

        return (True, included, shown)

    config_raw = hass_config.get(DOMAIN)
    config = {}

    host = config_raw[CONF_HOST]
    username = config_raw.get(CONF_USERNAME)
    password = config_raw.get(CONF_PASSWORD)
    if host.startswith('elks:'):
        if username is None or password is None:
            _LOGGER.error('Specify username & password for secure connection')
            return False

    config[CONF_LOVELACE] = config_raw[CONF_LOVELACE]

    for item, max_ in CONFIGS.items():
        config[item] = {}
        try:
            (config[item]['enabled'], config[item]['included'],
             config[item]['shown']) = parse_config(item, max_)
        except ValueError as err:
            _LOGGER.error("Config item: %s; %s", item, err)
            return False

    elk = elkm1.Elk({'url': host, 'userid': username, 'password': password})
    elk.connect()

    hass.data[DOMAIN] = {'connection': elk, 'config': config}
    for component in SUPPORTED_DOMAINS:
        hass.async_add_job(
            discovery.async_load_platform(hass, component, DOMAIN, None, None))

    return True


def create_elk_devices(hass, elk_elements, element_type, class_, devices):
    """Helper to create the ElkM1 devices of a particular class."""
    config = hass.data[DOMAIN]['config']
    for element in elk_elements:
        if config[element_type]['included'][element.index]:
            devices.append(class_(element, hass, config[element_type]))
    return devices


class ElkDeviceBase(Entity):
    """Sensor devices on the Elk."""
    def __init__(self, platform, element, hass, config):
        self._elk = hass.data[DOMAIN]['connection']
        self._element = element
        self._hass = hass
        self._show_override = config['shown'][element.index]
        self._hidden = False
        self._state = None
        self.entity_id = platform + '.elkm1_' + \
            self._element.default_name('_').lower()

    @property
    def name(self):
        """Name of the element."""
        return self._element.name

    @property
    def state(self):
        """The state of the element."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Don't poll this device."""
        return False

    @property
    def hidden(self):
        """Return if the element is hidden."""
        if self._show_override is None:
            return self._hidden
        return not self._show_override

    @property
    def device_state_attributes(self):
        """Attributes of the element."""
        return {**self._element.as_dict(), **self.initial_attrs()}

    def initial_attrs(self):
        """The underlying element's attributes as a dict."""
        attrs = {}
        attrs['index'] = self._element.index + 1
        attrs['state'] = self._state
        return attrs

    @callback
    def _element_callback(self, element, changeset):
        """Callback handler from the Elk - required to be supplied."""
        self._element_changed(element, changeset)
        self.async_schedule_update_ha_state(True)

    def _temperature_to_state(self, temperature, undefined_temperature):
        """Helper to convert a temperature to a state."""
        if temperature > undefined_temperature:
            self._state = temperature
            self._hidden = False
        else:
            self._state = STATE_UNKNOWN
            self._hidden = True

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        self._element.add_callback(self._element_callback)

    @asyncio.coroutine
    def async_update(self):
        """Default behaviour is to do nothing, override if need more."""
        pass
