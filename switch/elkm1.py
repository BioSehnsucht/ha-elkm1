"""
Support for Elk outputs as switches.
"""

import logging
from typing import Callable  # noqa

import PyElk

from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_OFF, STATE_ON)

from homeassistant.helpers.entity import Entity

from homeassistant.helpers.typing import ConfigType

from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

elk = None

def setup_platform(hass, config: ConfigType, add_devices: Callable[[list], None], discovery_info=None):
    """Setup the Elk switch platform."""
    elk = hass.data['PyElk']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False

    devices = []

    for output in elk.OUTPUTS:
        if output:
            _LOGGER.debug('Loading Elk Output : %s', output.description())
            devices.append(ElkSwitchDevice(output))

    add_devices(devices, True)
    return True


class ElkSwitchDevice(ToggleEntity):
    """ Elk Output as Switch """

    def __init__(self, output):
        """ Initialize output switch """
        self._output = output
        self._output._update_callback = self.trigger_update
        self._name = 'elk_output_' + str(output._number)
        self._state = None

    def trigger_update(self):
        _LOGGER.error('Triggering auto update of ' + str(self._output._number))
        self.schedule_update_ha_state(True)
    
    @property
    def name(self):
        """Return the name of the switch"""
        return self._name
    
    @property
    def state(self):
        """Return the state of the switch"""
        _LOGGER.error('Output updating : ' + str(self._output._number))
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any"""
        return 'mdi:' + 'toggle-switch'

    def update(self):
        """Get the latest data and update the state."""
        self._output._pyelk.update()
        self._state = self._output.status()

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'Status' : self._output.status(),
            'friendly_name' : self._output.description()
            }

    @property
    def is_on(self):
        """Get whether the output is in the on state."""
        return self._output._state == 1

    @property
    def should_poll(self):
        """We should be polled?"""
        return True
    
    def turn_on(self):
        self._output.turn_on()

    def turn_off(self):
        self._output.turn_off()
