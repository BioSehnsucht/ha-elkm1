"""Support for Elk outputs as switches, and task activation as switches."""
import asyncio
import logging
from typing import Callable  # noqa

from homeassistant.const import (STATE_OFF, STATE_ON)

from homeassistant.helpers.typing import ConfigType

from homeassistant.helpers.entity import ToggleEntity

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
    from elkm1.outputs import Output as ElkOutput
    from elkm1.tasks import Task as ElkTask
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather outputs
        for element in elk.outputs:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
        # Gather tasks
        for element in elk.tasks:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for element in discovery_info:
    #        if element.included is True and element.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(element)
    # Add discovered devices
    for element in discovery_info:
        if isinstance(element, ElkOutput):
            element_name = 'switch.' + 'elk_output_' + format(element.index + 1, '03')
        elif isinstance(element, ElkTask):
            element_name = 'switch.' + 'elk_task_' + format(element.index + 1, '03')
        else:
            continue
        if element_name not in discovered_devices:
            if isinstance(element, ElkOutput):
                device = ElkOutputDevice(element, elk)
            if isinstance(element, ElkTask):
                device = ElkTaskDevice(element, elk)
            _LOGGER.debug('Loading Elk %s: %s', element.__class__.__name__, element.name)
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element.__class__.__name__, element.name)

    add_devices(devices, True)
    return True


class ElkOutputDevice(ToggleEntity):
    """Elk Output as Toggle Switch."""

    def __init__(self, output, elk):
        """Initialize output switch."""
        self._elk = elk
        self._element = output
        self._name = 'elk_output_' + format(output.index + 1, '03')
        self.entity_id = 'switch.' + self._name
        self._state = None
        self._element.add_callback(self.trigger_update)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._element.name

    @property
    def state(self):
        """Return the state of the switch."""
        #_LOGGER.debug('Output updating : ' + str(self._element.number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        #_LOGGER.debug('Triggering auto update of output ' + str(
        #    self._element.number))
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        if self.is_on:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF
        #self._hidden = not self._element.enabled

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'hidden': False, #self._element.is_default_name(),
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        return self._element.output_on

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self):
        """Turn on output."""
        self._element.turn_on(0)

    def turn_off(self):
        """Turn off output."""
        self._element.turn_off()


class ElkTaskDevice(ToggleEntity):
    """Elk Task as Toggle Switch."""

    def __init__(self, task, elk):
        """Initialize task switch."""
        self._elk = elk
        self._element = task
        self._name = 'elk_task_' + format(task.index + 1, '03')
        self.entity_id = 'switch.' + self._name
        self._state = STATE_OFF
        self._element.add_callback(self.trigger_update)

    @property
    def name(self):
        """Return the name of the switch."""
        return self._element.name

    @property
    def state(self):
        """Return the state of the switch."""
        #_LOGGER.debug('Task updating : ' + str(self._element.number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        #_LOGGER.debug('Triggering auto update of task ' + str(
        #    self._element.number))
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        #if self.is_on:
        #    self._state = STATE_ON
        #else:
        #    self._state = STATE_OFF
        #self._hidden = not self._element.enabled
        # FIXME : Current Gwww lib doesn't handle TC?
        self._state = STATE_OFF

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return {
            'last_activated': self._element.last_change,
            'hidden': self._element.is_default_name()
            }

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return False

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        # FIXME : Current Gwww lib doesn't handle TC?
        #if self._element.status == self._element.STATUS_ON:
        #    return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self):
        """Turn on output."""
        self._element.activate()

    def turn_off(self):
        """Turn off output."""
        # Tasks aren't actually ever turned off
        # Tasks are momentary, so "always" off
