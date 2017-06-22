"""
Support for Elk outputs as switches, and task activation as switches.
"""

import logging
from typing import Callable  # noqa

import PyElk

from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_OFF, STATE_ON)

from homeassistant.helpers.entity import Entity

from homeassistant.helpers.typing import ConfigType

from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

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
            if output._included == True:
                _LOGGER.debug('Loading Elk Output : %s', output.description())
                devices.append(ElkOutputDevice(output))
            else:
                _LOGGER.debug('Skipping excluded Elk Output: %s', output._number)

    for task in elk.TASKS:
        if task:
            if task._included == True:
                _LOGGER.debug('Loading Elk Task : %s', task.description())
                devices.append(ElkTaskDevice(task))
            else:
                _LOGGER.debug('Skipping excluded Elk Task: %s', task._number)

    add_devices(devices, True)
    return True


class ElkOutputDevice(ToggleEntity):
    """Elk Output as Toggle Switch."""

    def __init__(self, output):
        """Initialize output switch."""
        self._device = output
        self._device.callback_add(self.trigger_update)
        self._name = 'elk_output_' + format(output._number,'03')
        self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def state(self):
        """Return the state of the switch"""
        _LOGGER.debug('Output updating : ' + str(self._device._number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of output ' + str(self._device._number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        if (self.is_on):
            self._state = STATE_ON
        else:
            self._state = STATE_OFF

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'friendly_name' : self._device.description()
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if (self._device._status == self._device.STATUS_ON):
            return True
        return False

    @property
    def should_poll(self) -> bool:
        return False

    def turn_on(self):
        """Turn on output"""
        self._device.turn_on()

    def turn_off(self):
        """Turn off output"""
        self._device.turn_off()


class ElkTaskDevice(ToggleEntity):
    """Elk Task as Toggle Switch."""

    def __init__(self, task):
        """Initialize task switch."""
        self._device = task
        self._device.callback_add(self.trigger_update)
        self._name = 'elk_task_' + format(task._number,'03')
        self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def state(self):
        """Return the state of the switch"""
        _LOGGER.debug('Task updating : ' + str(self._device._number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of output ' + str(self._device._number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        if (self.is_on):
            self._state = STATE_ON
        else:
            self._state = STATE_OFF

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'friendly_name' : self._device.description(),
            'last_activated' : self._device._last_activated,
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if (self._device._status == self._device.STATUS_ON):
            return True
        return False

    @property
    def should_poll(self) -> bool:
        return False

    def turn_on(self):
        """Turn on output"""
        self._device.turn_on()

    def turn_off(self):
        """Turn off output"""
        self._device.turn_off()
