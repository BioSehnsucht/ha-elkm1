"""
Support for Elk X10 devices as lights.
"""

import logging
from typing import Callable  # noqa
import math

from homeassistant.const import (STATE_OFF, STATE_ON)

from homeassistant.helpers.typing import ConfigType

from homeassistant.components.light import (Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=None):
    """Setup the Elk switch platform."""
    elk = hass.data['PyElk']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False

    devices = []

    for device in elk.X10:
        if device:
            if device._included is True:
                _LOGGER.debug('Loading Elk X10 : %s', device.description())
                devices.append(ElkX10Device(device))
            else:
                house, code = device.housecode_from_int(device._number)
                _LOGGER.debug('Skipping excluded Elk X10: %s %s', house, code)

    add_devices(devices, True)
    return True

class ElkX10Device(Light):
    """Elk X10 device as Switch."""

    def __init__(self, device):
        """Initialize X10 switch."""
        self._device = device
        self._device.callback_add(self.trigger_update)
        self._name = 'elk_x10_' + device.HOUSE_STR[device._house] + '_' +\
        format(device._number, '02')
        self._state = None
        self._hidden = not self._device._enabled

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def state(self):
        """Return the state of the switch"""
        _LOGGER.debug('X10 updating : ' + str(self._device._number))
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any"""
        return 'mdi:' + 'lightbulb'

    @property
    def brightness(self) -> float:
        """Get the brightness of the ISY994 light."""
        return self._device._level / 100.0

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of X10 '\
                      + self._device.HOUSE_STR[self._device._house]\
                      + ' ' + str(self._device._number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        if self.is_on:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF
        self._hidden = not self._device._enabled

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'friendly_name' : self._device.description(),
            'House Code' : self._device.HOUSE_STR[self._device._house],
            'Device' : str(self._device._number),
            'unique_id' : self._device.HOUSE_STR[self._device._house] + str(self._device._number),
            'hidden' : self._hidden,
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if (self._device._status == self._device.STATUS_ON)\
        or (self._device._status == self._device.STATUS_DIMMED):
            return True
        return False

    @property
    def should_poll(self) -> bool:
        return False

    def turn_on(self, **kwargs):
        """Turn on output"""
        if ATTR_BRIGHTNESS in kwargs:
            level = math.ceil(kwargs[ATTR_BRIGHTNESS] * 100)
            self._device.set_level(level)
        else:
            self._device.turn_on()

    def turn_off(self):
        """Turn off output"""
        self._device.turn_off()
