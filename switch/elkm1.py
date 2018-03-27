"""Support for Elk outputs as switches, and task activation as switches."""

import logging
from typing import Callable  # noqa

from homeassistant.const import (STATE_OFF, STATE_ON)

from homeassistant.helpers.typing import ConfigType

from homeassistant.helpers.entity import ToggleEntity

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
    from PyElk.Output import Output as ElkOutput
    from PyElk.Task import Task as ElkTask
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather outputs
        for node in elk.OUTPUTS:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
        # Gather tasks
        for node in elk.TASKS:
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
        if isinstance(node, ElkOutput):
            node_name = 'switch.' + 'elk_output_' + format(node.number, '03')
        elif isinstance(node, ElkTask):
            node_name = 'switch.' + 'elk_task_' + format(node.number, '03')
        else:
            continue
        if node_name not in discovered_devices:
            if isinstance(node, ElkOutput):
                device = ElkOutputDevice(node)
            if isinstance(node, ElkTask):
                device = ElkTaskDevice(node)
            _LOGGER.debug('Loading Elk %s: %s', node.classname, node.description_pretty())
            discovered_devices[node_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', node.classname, node.description_pretty())

    add_devices(devices, True)
    return True


class ElkOutputDevice(ToggleEntity):
    """Elk Output as Toggle Switch."""

    def __init__(self, output):
        """Initialize output switch."""
        self._device = output
        self._name = 'elk_output_' + format(output.number, '03')
        self.entity_id = 'switch.' + self._name
        self._state = None
        self._device.callback_add(self.trigger_update)
        self.update()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._device.description_pretty()

    @property
    def state(self):
        """Return the state of the switch."""
        _LOGGER.debug('Output updating : ' + str(self._device.number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of output ' + str(
            self._device.number))
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
            'hidden': self._hidden,
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if self._device.status == self._device.STATUS_ON:
            return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self):
        """Turn on output."""
        self._device.turn_on()

    def turn_off(self):
        """Turn off output."""
        self._device.turn_off()


class ElkTaskDevice(ToggleEntity):
    """Elk Task as Toggle Switch."""

    def __init__(self, task):
        """Initialize task switch."""
        self._device = task
        self._name = 'elk_task_' + format(task.number, '03')
        self.entity_id = 'switch.' + self._name
        self._state = None
        self._device.callback_add(self.trigger_update)
        self.update()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._device.description_pretty()

    @property
    def state(self):
        """Return the state of the switch."""
        _LOGGER.debug('Task updating : ' + str(self._device.number))
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    def trigger_update(self, node):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of task ' + str(
            self._device.number))
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
            'last_activated': self._device.last_activated,
            'hidden': self._hidden,
            }

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return False

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        if self._device.status == self._device.STATUS_ON:
            return True
        return False

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self):
        """Turn on output."""
        self._device.turn_on()

    def turn_off(self):
        """Turn off output."""
        self._device.turn_off()
