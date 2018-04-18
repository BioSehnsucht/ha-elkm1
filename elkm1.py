"""
Support the Elk M1 Gold, Elk M1 EZ8, etc alarm / integration panels.

Uses https://github.com/BioSehnsucht/pyelk / https://pypi.python.org/pypi/PyElk

For the actual HA component, add these lines to your configuration YAML :

```python
elkm1:
  host: socket://1.2.3.4:2101
  code: 1234
```

Currently only the non-secure port of Elk M1XEP (port 2101) is supported.
Alarm code is currently not yet actually used, and may get removed.

You can use ```host: /dev/ttyUSB0``` or such as well to speak to a directly
attached serial device
"""
import asyncio
import logging

from functools import partial

import voluptuous as vol

from homeassistant.core import HomeAssistant  # noqa
from homeassistant.const import (
    CONF_HOST,
    CONF_EXCLUDE, CONF_INCLUDE,
    EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery, config_validation as cv
from homeassistant.helpers.typing import ConfigType # noqa

DOMAIN = "elkm1"
REQUIREMENTS = [
    'elkm1==0.3.1',
    ]

CONF_AREA = 'area'
CONF_COUNTER = 'counter'
CONF_KEYPAD = 'keypad'
CONF_OUTPUT = 'output'
CONF_SETTING = 'setting'
CONF_TASK = 'task'
CONF_THERMOSTAT = 'thermostat'
CONF_USER = 'user'
CONF_X10 = 'x10'
CONF_ZONE = 'zone'

CONF_ENABLED = 'enabled'    # True to enable subdomain
CONF_AUTOHIDE = 'autohide'  # True to enable autohide
#                             (include / exclude override autohiding)
CONF_FASTLOAD = 'fastload'  # True to enable fastload
CONF_FASTLOAD_FILE = 'fastload_file'    # Set fastload filename

DEFAULT_ENABLED = True                  # Enable subdomains
DEFAULT_EXCLUDE = []                    # Exclude none
DEFAULT_FASTLOAD = True     # Default enabled
DEFAULT_FASTLOAD_FILE = '/config/PyElk-fastload.json'   # Default

DEFAULT_INCLUDE = {
    CONF_AREA: ['1-8'],         # Include all
    CONF_COUNTER: ['1-64'],    # Include all
    CONF_KEYPAD: ['1-16'],     # Include all
    CONF_OUTPUT: ['1-208'],    # Include all
    CONF_SETTING: ['1-20'],      # Include all
    CONF_TASK: ['1-32'],       # Include all
    CONF_THERMOSTAT: ['1-16'],  # Include all
    CONF_USER: ['1-203'],      # Include all
    CONF_X10: ['a1-p16'],      # Include all
    CONF_ZONE: ['1-208'],      # Include all
    }

EVENT_PYELK_UPDATE = 'elkm1_pyelk_update'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA_SUBDOMAIN = vol.Schema({
    vol.Optional(CONF_ENABLED, default=DEFAULT_ENABLED): cv.boolean,
    vol.Optional(CONF_AUTOHIDE, default=DEFAULT_ENABLED): cv.boolean,
    vol.Optional(CONF_EXCLUDE, default=DEFAULT_EXCLUDE):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_AREA = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_AREA]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_COUNTER = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_COUNTER]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_KEYPAD = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_KEYPAD]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_OUTPUT = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_OUTPUT]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_SETTING = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_SETTING]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_TASK = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_TASK]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_THERMOSTAT = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_THERMOSTAT]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_USER = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_USER]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_X10 = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_X10]):
        vol.All(cv.ensure_list_csv),
    })
CONFIG_SCHEMA_SUBDOMAIN_ZONE = CONFIG_SCHEMA_SUBDOMAIN.extend({
    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_ZONE]):
        vol.All(cv.ensure_list_csv),
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_FASTLOAD, default=DEFAULT_FASTLOAD): cv.boolean,
        vol.Optional(CONF_FASTLOAD_FILE, default=DEFAULT_FASTLOAD_FILE): cv.string,
        vol.Optional(CONF_AREA): CONFIG_SCHEMA_SUBDOMAIN_AREA,
        vol.Optional(CONF_COUNTER): CONFIG_SCHEMA_SUBDOMAIN_COUNTER,
        vol.Optional(CONF_KEYPAD): CONFIG_SCHEMA_SUBDOMAIN_KEYPAD,
        vol.Optional(CONF_OUTPUT): CONFIG_SCHEMA_SUBDOMAIN_OUTPUT,
        vol.Optional(CONF_SETTING): CONFIG_SCHEMA_SUBDOMAIN_SETTING,
        vol.Optional(CONF_TASK): CONFIG_SCHEMA_SUBDOMAIN_TASK,
        vol.Optional(CONF_THERMOSTAT): CONFIG_SCHEMA_SUBDOMAIN_THERMOSTAT,
        vol.Optional(CONF_USER): CONFIG_SCHEMA_SUBDOMAIN_USER,
        vol.Optional(CONF_X10): CONFIG_SCHEMA_SUBDOMAIN_X10,
        vol.Optional(CONF_ZONE): CONFIG_SCHEMA_SUBDOMAIN_ZONE,
    })
}, extra=vol.ALLOW_EXTRA)

#SUPPORTED_DOMAINS = ['sensor', 'switch', 'alarm_control_panel', 'climate',
#                     'light']
SUPPORTED_DOMAINS = ['sensor', 'switch', 'light']


@asyncio.coroutine
def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Elk M1 platform."""
    # Voluptuous won't fill in missing optional sub-schema with their
    # defaults, but will fill in empty ones...
    for config_key, config_value in sorted(DEFAULT_INCLUDE.items()):
        if config_key not in config[DOMAIN]:
            # Create empty dict section
            config[DOMAIN][config_key] = {}
    # Re-run the schema
    config = CONFIG_SCHEMA(config)

    elk_config = config.get(DOMAIN)

    _LOGGER.debug('Elk config : %s', elk_config)

    # Connect to Elk panel
    import elkm1

    #bound_event_callback = partial(_callback_from_pyelk, hass, config)

    elk = elkm1.Elk({'url': elk_config[CONF_HOST]}, loop=hass.loop)

    hass.data['elkm1'] = {
        'connection' : elk,
        'discovered_devices' : {},
        'config' : elk_config,
        }
    ## Listen for HA stop to disconnect.
    #hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
    #                     hass.data['PyElk']['connection'].stop())

    @asyncio.coroutine
    def connect():
        _LOGGER.debug("Elk connect")
        yield from elk.connect()

    hass.async_add_job(connect)

    # Load platforms for the devices in the Elk panel that we support.
    for component in SUPPORTED_DOMAINS:
        hass.async_add_job(
            discovery.async_load_platform(hass, component, DOMAIN, [], elk_config))

    return True


#def stop(event: object) -> None:
#    """Stop PyElk."""
#    pyelk_instance.stop()

#
#def _callback_from_pyelk(hass, config, data):
#    """PyElk callback handler to register changes."""
#    # Determine the type of event
#
#    # New device available or device removed
#    # Currently just hide removed devices, rather than remove
#    for component in SUPPORTED_DOMAINS:
#        # Try to discover new devices
#        discovery_data = [data]
#        discovery.load_platform(hass, component, DOMAIN, discovery_data, config)
