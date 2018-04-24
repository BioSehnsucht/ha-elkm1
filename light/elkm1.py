"""Support for Elk X10 devices as lights."""
import asyncio
import logging
from typing import Callable  # noqa
import math

from homeassistant.const import (STATE_OFF, STATE_ON)

from homeassistant.helpers.typing import ConfigType

from homeassistant.components.light import (Light, ATTR_BRIGHTNESS,
                                            SUPPORT_BRIGHTNESS)
from homeassistant.core import callback

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk switch platform."""
    elk = hass.data['elkm1']['connection']
    elk_config = hass.data['elkm1']['config']
    discovered_devices = hass.data['elkm1']['discovered_devices']
    #if elk is None:
    #    _LOGGER.error('Elk is None')
    #    return False
    #if not elk.connected:
    #    _LOGGER.error('A connection has not been made to the Elk panel.')
    #    return False

    devices = []
    from elkm1.lights import Light as ElkLight
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather areas
        for element in elk.lights:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for node in discovery_info:
    #        if node.included is True and node.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(node)
    # Add discovered devices
    for element in discovery_info:
        if isinstance(element, ElkLight):
            element_name = 'light.' + ElkLightDevice.entity_name(element)
        else:
            continue
        if element_name not in discovered_devices:
            device = ElkLightDevice(element)
            _LOGGER.debug('Loading Elk %s: %s', element.__class__.__name__, element.name)
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element.__class__.__name__, element.name)

    add_devices(devices, True)
    return True


class ElkLightDevice(Light):
    """Elk X10 device as Switch."""
    @classmethod
    def entity_name(cls, device):
        from elkm1.lights import Light as ElkLight
        name = 'elk_light_' + format(device.index + 1, '03') #+ device.house_pretty + device.device_pretty
        return name

    def __init__(self, device):
        """Initialize X10 switch."""
        self._element = device
        self._name = ElkLightDevice.entity_name(device)
        # FIXME: Why does this work for sensor but not anywhere else?
        #self.entity_id = ENTITY_ID_FORMAT.format(self._name)
        self.entity_id = 'light.' + self._name
        self._state = None
        self._hidden = self._element.is_default_name() #not self._device.enabled
        self._element.add_callback(self.trigger_update)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._element.name

    @property
    def state(self):
        """Return the state of the switch."""
        #_LOGGER.debug('Light updating : ' + str(self._device.number))
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:' + 'lightbulb'

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

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        #_LOGGER.debug('Triggering auto update of X10 '
        #              + self._device.house_pretty
        #              + ' ' + self._device.device_pretty)
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        if self._element.status > 2:
            self._brightness = self._element.status
            self._state = STATE_ON
        if self._element.status == 1:
            self._brightness = 100
            self._state = STATE_ON
        if self._element.status == 0:
            self._brightness = 0
            self._state = STATE_OFF
        self._hidden = self._element.is_default_name()
        # TODO : Remove. I need to name devies on my Elk so they don't get hidden ...
        if self._element.index < 3:
            self._hidden = False
        #if self._hidden == False:
        #    _LOGGER.error('async_update - Elk brightness is ' + str(self._brightness))


    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            #'House Code': self._element.house_pretty,
            #'Device': self._element.device_pretty,
            #'unique_id': self._element.house_pretty + self._element.device_pretty,
            'hidden': self._hidden,
            ATTR_BRIGHTNESS : round(self._brightness * 2.55),
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if self._state == STATE_ON:
            return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        """Turn on output."""
        if ATTR_BRIGHTNESS in kwargs:
            #_LOGGER.error('async_turn_on : brightness is ' + str(kwargs[ATTR_BRIGHTNESS]))
            level = math.ceil(kwargs[ATTR_BRIGHTNESS] / 2.55 )
            #_LOGGER.error('async_turn_on : scaled brightness is ' + str(level))
            if level > 99:
                level = 99
            if level < 2:
                level = 2
            self._element.turn_on(level,0)
        else:
            #_LOGGER.error('async_turn_on')
            self._element.turn_on(100,0)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        """Turn off output."""
        self._element.turn_off()
