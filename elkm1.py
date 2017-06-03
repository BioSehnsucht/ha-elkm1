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
from collections import namedtuple
from collections import deque
import logging
import serial
import serial.threaded
import time
import traceback

import voluptuous as vol

from homeassistant.core import HomeAssistant  # noqa
from homeassistant.const import (
    CONF_HOST, CONF_CODE,
    EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery, config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, Dict # noqa


DOMAIN = "elkm1"
REQUIREMENTS = ['PyElk==0.1.3.dev5']

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_CODE): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

SUPPORTED_DOMAINS = ['sensor','switch','alarm_control_panel','climate','light']

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Elk M1 platform."""
    elk_config = config.get(DOMAIN)

    code = elk_config.get(CONF_CODE)
    host = elk_config.get(CONF_HOST)

    # Connect to Elk panel
    import PyElk

    ELK = PyElk.Elk(address=host, usercode=code, log=_LOGGER)

    if not ELK.connected:
        return False

    hass.data['PyElk'] = ELK
    # Listen for HA stop to disconnect.
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop)

    # Load platforms for the devices in the Elk panel that we support.
    for component in SUPPORTED_DOMAINS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    #ELK.auto_update = True
    return True

def stop(event: object) -> None:
    """Stop auto updates"""
    #ELK.auto_update = False
