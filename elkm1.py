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
import re

from functools import partial

import voluptuous as vol

from homeassistant.core import HomeAssistant  # noqa
from homeassistant.const import (
    CONF_HOST,
    CONF_EXCLUDE, CONF_INCLUDE,
    CONF_USERNAME, CONF_PASSWORD,
    EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery, config_validation as cv
from homeassistant.helpers.typing import ConfigType # noqa

DOMAIN = "elkm1"
REQUIREMENTS = [
    'elkm1==0.4.7',
    ]

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
#CONF_AUTOHIDE = 'autohide'  # True to enable autohide
#                             (include / exclude override autohiding)
#CONF_FASTLOAD = 'fastload'  # True to enable fastload
#CONF_FASTLOAD_FILE = 'fastload_file'    # Set fastload filename

DEFAULT_ENABLED = True                  # Enable subdomains
DEFAULT_EXCLUDE = []                    # Exclude none
#DEFAULT_FASTLOAD = True     # Default enabled
#DEFAULT_FASTLOAD_FILE = '/config/PyElk-fastload.json'   # Default

#DEFAULT_INCLUDE = {
#    CONF_AREA: ['1-8'],         # Include all
#    CONF_COUNTER: ['1-64'],    # Include all
#    CONF_KEYPAD: ['1-16'],     # Include all
#    CONF_OUTPUT: ['1-208'],    # Include all
#    CONF_SETTING: ['1-20'],      # Include all
#    CONF_TASK: ['1-32'],       # Include all
#    CONF_THERMOSTAT: ['1-16'],  # Include all
#    CONF_USER: ['1-203'],      # Include all
#    CONF_X10: ['a1-p16'],      # Include all
#    CONF_ZONE: ['1-208'],      # Include all
#    }

EVENT_PYELK_UPDATE = 'elkm1_pyelk_update'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA_SUBDOMAIN = vol.Schema({
    vol.Optional(CONF_ENABLED, default=DEFAULT_ENABLED): cv.boolean,
    vol.Optional(CONF_INCLUDE): list,
    vol.Optional(CONF_EXCLUDE): list,
    vol.Optional(CONF_HIDE): list,
    vol.Optional(CONF_SHOW): list,
    })

#CONFIG_SCHEMA_SUBDOMAIN = vol.Schema({
#    vol.Optional(CONF_ENABLED, default=DEFAULT_ENABLED): cv.boolean,
#    vol.Optional(CONF_AUTOHIDE, default=DEFAULT_ENABLED): cv.boolean,
#    vol.Optional(CONF_EXCLUDE, default=DEFAULT_EXCLUDE):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_AREA = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_AREA]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_COUNTER = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_COUNTER]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_KEYPAD = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_KEYPAD]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_OUTPUT = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_OUTPUT]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_SETTING = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_SETTING]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_TASK = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_TASK]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_THERMOSTAT = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_THERMOSTAT]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_USER = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_USER]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_X10 = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_X10]):
#        vol.All(cv.ensure_list_csv),
#    })
#CONFIG_SCHEMA_SUBDOMAIN_ZONE = CONFIG_SCHEMA_SUBDOMAIN.extend({
#    vol.Optional(CONF_INCLUDE, default=DEFAULT_INCLUDE[CONF_ZONE]):
#        vol.All(cv.ensure_list_csv),
#    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_LOVELACE, default=False): cv.boolean,
        #vol.Optional(CONF_FASTLOAD, default=DEFAULT_FASTLOAD): cv.boolean,
        #vol.Optional(CONF_FASTLOAD_FILE, default=DEFAULT_FASTLOAD_FILE): cv.string,
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

SUPPORTED_DOMAINS = ['sensor', 'switch', 'alarm_control_panel', 'climate',
                     'light']


@asyncio.coroutine
def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Elk M1 platform."""
    ## Voluptuous won't fill in missing optional sub-schema with their
    ## defaults, but will fill in empty ones...
    #for config_key, config_value in sorted(DEFAULT_INCLUDE.items()):
    #    if config_key not in config[DOMAIN]:
    #        # Create empty dict section
    #        config[DOMAIN][config_key] = {}
    ## Re-run the schema
    #config = CONFIG_SCHEMA(config)

    from elkm1.const import Max

    elk_config_raw = config.get(DOMAIN)
    elk_config = {}

    if elk_config_raw[CONF_HOST].startswith('elks'):
        if (CONF_USERNAME in elk_config_raw) and (CONF_PASSWORD in elk_config_raw):
            elk_config[CONF_USERNAME] = elk_config_raw[CONF_USERNAME]
            elk_config[CONF_PASSWORD] = elk_config_raw[CONF_PASSWORD]
        else:
            _LOGGER.error('Must specify username and password for secure connection')
            return False
    elk_config[CONF_HOST] = elk_config_raw[CONF_HOST]
    elk_config[CONF_LOVELACE] = elk_config_raw[CONF_LOVELACE]

    def housecode_to_int(hc):
        """Convert house / device code to integer device number."""
        hc_split = re.split(r'(\d+)', hc.upper())
        house = ord(hc_split[0]) - ord('A') + 1
        code = int(hc_split[1])
        if (house >= 1) and (house <= 16) and (code > 0) and (code <= 16):
            return ((house - 1) * 16) + code
        return None

    for subconfig in [CONF_AREA, CONF_COUNTER, CONF_KEYPAD, CONF_OUTPUT, CONF_PANEL, CONF_PLC, CONF_SETTING, CONF_TASK, CONF_THERMOSTAT, CONF_USER, CONF_ZONE]:
        max = 0
        if subconfig == CONF_AREA:
            max = Max.AREAS.value
        elif subconfig == CONF_COUNTER:
            max = Max.COUNTERS.value
        elif subconfig == CONF_KEYPAD:
            max = Max.KEYPADS.value
        elif subconfig == CONF_PANEL:
            max = 1
        elif subconfig == CONF_PLC:
            max = Max.LIGHTS.value
        elif subconfig == CONF_OUTPUT:
            max = Max.OUTPUTS.value
        elif subconfig == CONF_SETTING:
            max = Max.SETTINGS.value
        elif subconfig == CONF_TASK:
            max = Max.TASKS.value
        elif subconfig == CONF_THERMOSTAT:
            max = Max.THERMOSTATS.value
        elif subconfig == CONF_USER:
            max = Max.USERS.value
        elif subconfig == CONF_ZONE:
            max = Max.ZONES.value
        elk_config[subconfig] = {
            CONF_ENABLED : True,
            CONF_INCLUDE : [True] * max,
            CONF_EXCLUDE : [False] * max,
            CONF_SHOW : [False] * max,
            CONF_HIDE : [False] * max,
            }
        if subconfig in elk_config_raw:
            if CONF_ENABLED in elk_config_raw[subconfig]:
                elk_config[subconfig][CONF_ENABLED] = elk_config_raw[subconfig][CONF_ENABLED]
            for listset in [CONF_INCLUDE, CONF_EXCLUDE, CONF_SHOW, CONF_HIDE]:
                if listset in elk_config_raw[subconfig]:
                    if listset == CONF_INCLUDE:
                        # If overriding default include list, set to False first
                        elk_config[subconfig][listset] = [False] * max
                    data = elk_config_raw[subconfig][listset]
                    if not isinstance(data, list):
                        data = [data]
                    result = []
                    for ranges in data:
                        if (isinstance(ranges, int)):
                            ranges = str(ranges)
                        num_start = 0
                        num_end = 0
                        if '-' in ranges:
                            split_start, split_end = ranges.split('-')
                            if (split_start.isdigit()) and (split_end.isdigit()):
                                # Numeric ranges
                                num_start, num_end = int(split_start), int(split_end)
                            else:
                                # X10 house/device code ranges
                                num_start = housecode_to_int(split_start)
                                num_end = housecode_to_int(split_end)
                            if num_start is not None and num_end is not None:
                                range_start = num_start - 1
                                range_end = num_end - 1
                                result.extend(list(range(range_start, range_end + 1)))
                        else:
                            num_start = None
                            if ranges.isdigit():
                                num_start = int(ranges)
                            else:
                                num_start = housecode_to_int(ranges)
                            if num_start is not None:
                                result.append(num_start - 1)
                    for element in result:
                        if element < max and element >= 0:
                            elk_config[subconfig][listset][element] = True
        # Combine include / exclude into single True/False list
        # True : include
        # False : exclude
        included = [False] * max
        for element in range(0,max):
            if elk_config[subconfig][CONF_INCLUDE][element] and not elk_config[subconfig][CONF_EXCLUDE][element]:
                included[element] = True
        del elk_config[subconfig][CONF_INCLUDE]
        del elk_config[subconfig][CONF_EXCLUDE]
        elk_config[subconfig]['included'] = included
        # Combine show / hide into single True/False/None list
        # True : force show
        # False : force hide
        # None : default automatic show/hide
        shown = [None] * max
        for element in range(0,max):
            if elk_config[subconfig][CONF_SHOW][element] and not elk_config[subconfig][CONF_HIDE][element]:
                shown[element] = True
            if elk_config[subconfig][CONF_HIDE][element]:
                shown[element] = False
        del elk_config[subconfig][CONF_SHOW]
        del elk_config[subconfig][CONF_HIDE]
        elk_config[subconfig]['shown'] = shown

    _LOGGER.debug('Elk config : %s', elk_config)

    # Connect to Elk panel
    import elkm1

    #bound_event_callback = partial(_callback_from_pyelk, hass, config)

    elk_obj_config = {'url': elk_config[CONF_HOST]}
    if CONF_USERNAME in elk_config and CONF_PASSWORD in elk_config:
        elk_obj_config['userid'] = elk_config[CONF_USERNAME]
        elk_obj_config['password'] = elk_config[CONF_PASSWORD]

    elk = elkm1.Elk(elk_obj_config, loop=hass.loop)

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
        yield from elk._connect()

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
