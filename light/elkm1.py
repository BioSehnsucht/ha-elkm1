"""
Support for control of ElkM1 lighting (X10, UPB, etc).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.elkm1/
"""

import asyncio
import logging
import math

from homeassistant.const import (STATE_OFF, STATE_ON)
from homeassistant.components.light import (Light, ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS)
from homeassistant.core import callback

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk light platform."""
    elk = hass.data['elkm1']['connection']
    async_add_devices(create_elk_devices(hass, elk.lights,
                                         'plc', ElkLight, []), True)
    return True


class ElkLight(ElkDeviceBase, Light):
    """Elk lighting device."""
    def __init__(self, device, hass, config):
        """Initialize light."""
        ElkDeviceBase.__init__(self, 'light', device, hass, config)
        self._brightness = self._element.status
        self._state = STATE_OFF

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:lightbulb'

    @property
    def brightness(self) -> float:
        """Get the brightness of the X10 light."""
        if self._element.status > 2:
            return self._element.status / 100.0
        if self._element.status == 1:
            return 1.0
        return self._element.status

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def device_state_attributes(self):
        """Attributes of the light."""
        return {ATTR_BRIGHTNESS: round(self._brightness * 2.55)}

    # pylint: disable=unused-argument
    @callback
    def _element_callback(self, element, attribute, value):
        """Callback handler from the Elk."""
        if self._element.status == 0:
            self._brightness = 0
            self._state = STATE_OFF
        else:
            self._state = STATE_ON
            if self._element.status == 1:
                self._brightness = 100
            else:
                self._brightness = self._element.status
        self._hidden = self._element.is_default_name()
        self.async_schedule_update_ha_state(True)

    @property
    def is_on(self) -> bool:
        """Is there light!"""
        return self._state == STATE_ON

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Let there be light!"""
        if ATTR_BRIGHTNESS in kwargs:
            level = math.ceil(kwargs[ATTR_BRIGHTNESS] / 2.55)
            if level > 98:
                level = 100
            elif level < 2:
                level = 0
            self._element.turn_on(level, 0)
        else:
            self._element.turn_on(100, 0)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """In the darkness..."""
        self._element.turn_off()
