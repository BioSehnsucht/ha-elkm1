"""
Support for control of ElkM1 lighting (X10, UPB, etc).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.elkm1/
"""

import asyncio

from homeassistant.components.light import (ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS, Light)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices

DEPENDENCIES = ['elkm1']


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
    def brightness(self):
        """Get the brightness of the PLC light."""
        return self._brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        """Callback handler from the Elk."""
        status = self._element.status if self._element.status != 1 else 100
        self._state = STATE_OFF if status == 0 else STATE_ON
        self._brightness = round(status * 2.55)

    @property
    def is_on(self) -> bool:
        """Is there light?"""
        return self._brightness != 0

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Let there be light!"""
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        level = round(brightness / 2.55)
        if level == 0:
            self._element.turn_off()
        elif level >= 98:
            self._element.turn_on()
        elif level == 1:
            self._element.turn_on(2)
        else:
            self._element.turn_on(level)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """In the darkness..."""
        self._brightness = 0
        self._element.turn_off()
