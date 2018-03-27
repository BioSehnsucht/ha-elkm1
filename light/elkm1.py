"""Support for Elk X10 devices as lights."""

import logging
from typing import Callable  # noqa
import math

from homeassistant.const import (STATE_OFF, STATE_ON)

from homeassistant.helpers.typing import ConfigType

from homeassistant.components.light import (Light, ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS)
DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk switch platform."""
    elk = hass.data['PyElk']['connection']
    discovered_devices = hass.data['PyElk']['discovered_devices']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False

    devices = []
    from PyElk.X10 import X10 as ElkX10
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather areas
        for node in elk.X10:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
    # If discovery info was passed in, check if we want to include it
    else:
        for node in discovery_info:
            if node.included is True and node.enabled is True:
                continue
            else:
                discovery_info.remove(node)
    # Add discovered devices
    for node in discovery_info:
        if isinstance(node, ElkX10):
            node_name = 'light.' + ElkX10Device.entity_name(node)
        else:
            continue
        if node_name not in discovered_devices:
            device = ElkX10Device(node)
            _LOGGER.debug('Loading Elk %s: %s', node.classname, node.description_pretty())
            discovered_devices[node_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', node.classname, node.description_pretty())

    add_devices(devices, True)
    return True


class ElkX10Device(Light):
    """Elk X10 device as Switch."""
    @classmethod
    def entity_name(cls, device):
        from PyElk import Elk as ElkSystem
        from PyElk.X10 import X10 as ElkX10
        name = 'elk_x10_' + device.house_pretty + device.device_pretty
        return name

    def __init__(self, device):
        """Initialize X10 switch."""
        self._device = device
        self._name = ElkX10Device.entity_name(device)
        # FIXME: Why does this work for sensor but not anywhere else?
        #self.entity_id = ENTITY_ID_FORMAT.format(self._name)
        self.entity_id = 'light.' + self._name
        self._state = None
        self._hidden = not self._device.enabled
        self._device.callback_add(self.trigger_update)
        self.update()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._device.description_pretty()

    @property
    def state(self):
        """Return the state of the switch."""
        _LOGGER.debug('X10 updating : ' + str(self._device.number))
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:' + 'lightbulb'

    @property
    def brightness(self) -> float:
        """Get the brightness of the X10 light."""
        return self._device.level / 100.0

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    def trigger_update(self, node):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of X10 '
                      + self._device.house_pretty
                      + ' ' + self._device.device_pretty)
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        if self.is_on:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF
        self._hidden = not self._device.enabled

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'House Code': self._device.house_pretty,
            'Device': self._device.device_pretty,
            'unique_id': self._device.house_pretty + self._device.device_pretty,
            'hidden': self._hidden,
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if (self._device.status == self._device.STATUS_ON) or (
                self._device.status == self._device.STATUS_DIMMED):
            return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self, **kwargs):
        """Turn on output."""
        if ATTR_BRIGHTNESS in kwargs:
            level = math.ceil(kwargs[ATTR_BRIGHTNESS] * 100)
            self._device.set_level(level)
        else:
            self._device.turn_on()

    def turn_off(self):
        """Turn off output."""
        self._device.turn_off()
