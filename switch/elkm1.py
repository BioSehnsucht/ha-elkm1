"""
Support for control of ElkM1 outputs (relays) and tasks ("macros).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.elkm1/
"""

import asyncio
import logging

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.entity import ToggleEntity

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk switch platform."""
    elk = hass.data['elkm1']['connection']
    devices = create_elk_devices(hass, elk.tasks, 'task', ElkTask, [])
    devices = create_elk_devices(hass, elk.outputs,
                                 'output', ElkOutput, devices)
    async_add_devices(devices, True)
    return True


class ElkOutput(ElkDeviceBase, ToggleEntity):
    """Elk Output as Toggle Switch."""
    def __init__(self, device, hass, config):
        """Initialize output."""
        ElkDeviceBase.__init__(self, 'switch', device, hass, config)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:toggle-switch'

    @property
    def is_on(self) -> bool:
        """True if output is on."""
        return self._element.output_on

    def async_turn_on(self, **kwargs):
        """Turn on output."""
        self._element.turn_on(0)

    def async_turn_off(self, **kwargs):
        """Turn off output."""
        self._element.turn_off()

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        self._state = STATE_ON if self._element.output_on else STATE_OFF


class ElkTask(ElkDeviceBase, ToggleEntity):
    """Elk Output as Toggle Switch."""
    def __init__(self, device, hass, config):
        """Initialize output."""
        ElkDeviceBase.__init__(self, 'switch', device, hass, config)
        self._state = STATE_OFF

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:domain'

    @property
    def device_state_attributes(self):
        """Attributes of the task."""
        attrs = self.initial_attrs()
        attrs['last_change'] = self._element.last_change
        return attrs

    @property
    def is_on(self) -> bool:
        """True if task in the on state."""
        return False

    def async_turn_on(self, **kwargs):
        """Turn on task."""
        self._element.activate()

    def async_turn_off(self, **kwargs):
        """Turn off task."""
        # Tasks aren't actually ever turned off
        # Tasks are momentary, so "always" off
        pass

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        pass
