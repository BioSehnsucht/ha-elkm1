"""
Support for control of ElkM1 lighting (X10, UPB, etc).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.elkm1/
"""

import asyncio
import logging
import math

from homeassistant.components.light import (ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS, Light)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN

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
        self._state = STATE_UNKNOWN

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:lightbulb'

    @property
    def brightness(self) -> float:
        """Get the brightness of the X10 light."""
        if self._element.status > 1:
            return self._element.status / 100.0
        if self._element.status == 1:
            return 1.0
        return 0.0

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def device_state_attributes(self):
        """Attributes of the light."""
        attrs = self.initial_attrs()
        attrs[ATTR_BRIGHTNESS] = round(self._brightness * 2.55)
        return attrs

    # pylint: disable=unused-argument
    def _element_changed(self, element, attribute, value):
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

    @property
    def is_on(self) -> bool:
        """Is there light!"""
        return self._state == STATE_ON

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Let there be light!"""
        if ATTR_BRIGHTNESS not in kwargs:
            self._element.turn_on()
            return

        level = math.ceil(kwargs[ATTR_BRIGHTNESS] / 2.55)
        if level == 0:
            self._element.turn_off()
        else:
            if level == 1:
                level = 2
            elif level > 98:
                level = 100
            self._element.turn_on(level)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """In the darkness..."""
        self._element.turn_off()
