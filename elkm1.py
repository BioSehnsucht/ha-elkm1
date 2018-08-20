"""
Support the Elk M1 Gold, Elk M1 EZ8, etc alarm / integration panels.

Uses https://github.com/BioSehnsucht/pyelk / https://pypi.python.org/pypi/PyElk

For the actual HA component, add these lines to your configuration YAML :

```yaml
elkm1:
  host: elk://1.2.3.4
```

You can use ```host: serial:///dev/ttyUSB0``` or such as well to 
speak to a directly attached serial device
"""

import asyncio
import logging
import re

import voluptuous as vol

from homeassistant.core import HomeAssistant  # noqa
from homeassistant.const import (
    CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_EXCLUDE, CONF_INCLUDE)
from homeassistant.helpers import discovery, config_validation as cv
from homeassistant.helpers.typing import ConfigType # noqa

from elkm1.const import Max
from elkm1.message import housecode_to_index
import elkm1

DOMAIN = "elkm1"
REQUIREMENTS = ['elkm1==0.4.9']

CONF_AREA = 'area'
CONF_COUNTER = 'counter'
CONF_KEYPAD = 'keypad'
CONF_OUTPUT = 'output'
CONF_SETTING = 'setting'
CONF_TASK = 'task'
CONF_THERMOSTAT = 'thermostat'
CONF_USER = 'user'
CONF_PANEL = 'panel'
CONF_PLC = 'plc' # Not light because HASS complains about this
CONF_ZONE = 'zone'

CONF_ENABLED = 'enabled'    # True to enable subdomain
CONF_HIDE = 'hide'
CONF_SHOW = 'show'
CONF_LOVELACE = 'lovelace'

EVENT_PYELK_UPDATE = 'elkm1_pyelk_update'

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

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

SUPPORTED_DOMAINS = ['sensor', 'switch', 'alarm_control_panel', 'climate', 'light']

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


@asyncio.coroutine
def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Elk M1 platform."""
    def parse_value(val, max):

        i = int(val) if val.isdigit() else (housecode_to_index(val) + 1)
        if i < 1 or i > max:
            raise ValueError('Value not in range 1 to %d: "%s"' % (max, val))
        return i

    def parse_range(config, item, set_to, values, max):
        # e.g. rng = "3, 45, 46, 48-51, 77"
        if item not in config:
            return

        ranges = config[item]
        for rng in ranges:
            for x in map(str.strip, str(rng).split(',')):
                if '-' in x:
                    xr = [s.strip() for s in x.split('-')]
                    start = parse_value(xr[0], max)
                    end = parse_value(xr[1], max)
                else:
                    start = end = parse_value(x, max)
                values[start-1:end] = [set_to] * (end - start + 1)

    def parse_config(item, max):
        if item not in config_raw:
            return (True, [True] * max, [True] * max)

        conf = config_raw[item]

        if CONF_ENABLED in conf and not conf[CONF_ENABLED]:
            return (False, [False] * max, [False] * max)

        included = [CONF_INCLUDE not in conf] * max
        parse_range(conf, CONF_INCLUDE, True, included, max)
        parse_range(conf, CONF_EXCLUDE, False, included, max)

        shown = [None] * max
        parse_range(conf, CONF_SHOW, True, shown, max)
        parse_range(conf, CONF_HIDE, False, shown, max)

        return (True, included, shown)

    config_raw = hass_config.get(DOMAIN)
    config = {}

    host = config_raw[CONF_HOST]
    username = config_raw.get(CONF_USERNAME)
    password = config_raw.get(CONF_PASSWORD)
    if host.startswith('elks:'):
        if username is None or password is None:
            _LOGGER.error('Must specify username & password for secure connection')
            return False

    config[CONF_LOVELACE] = config_raw[CONF_LOVELACE]

    for item, max in CONFIGS.items():
        config[item] = {}
        try:
            (config[item]['enabled'], config[item]['included'],
                config[item]['shown']) = parse_config(item, max)
        except ValueError as err:
            _LOGGER.error("Config item: %s; %s", item, err)
            return False

    elk = elkm1.Elk({'url': host, 'userid': username, 'password': password})

    hass.data['elkm1'] = {'connection': elk, 'discovered_devices': {},
                          'config': config}

    @asyncio.coroutine
    def connect():
        yield from elk._connect()

    hass.async_add_job(connect)

    # Load platforms for the devices in the Elk panel that we support.
    for component in SUPPORTED_DOMAINS:
        hass.async_add_job(
            discovery.async_load_platform(hass, component, DOMAIN, [], config))

    return True
