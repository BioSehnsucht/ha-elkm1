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
                   async_add_devices: Callable[[list], None], discovery_info=[]):
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
        if elk_config['output']['enabled']:
            for element in elk.outputs:
                if element:
                    if elk_config['output']['included'][element._index] is True:
                        discovery_info.append([element, elk_config['output']['shown'][element._index]])
        # Gather tasks
        if elk_config['task']['enabled']:
            for element in elk.tasks:
                if element:
                    if elk_config['task']['included'][element._index] is True:
                        discovery_info.append([element, elk_config['task']['shown'][element._index]])
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for element in discovery_info:
    #        if element.included is True and element.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(element)
    # Add discovered devices
    element_name = ''
    for element in discovery_info:
        if isinstance(element[0], ElkOutput) or isinstance(element[0], ElkTask):
            element_name = 'switch.' + 'elkm1_' + element[0].default_name('_')
        else:
            continue
        if element_name not in discovered_devices:
            if isinstance(element[0], ElkOutput):
                device = ElkOutputDevice(element[0], elk, hass, element[1])
            if isinstance(element[0], ElkTask):
                device = ElkTaskDevice(element[0], elk, hass, element[1])
            _LOGGER.debug('Loading Elk %s: %s', element[0].__class__.__name__, element[0].name)
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element[0].__class__.__name__, element[0].name)

    async_add_devices(devices, True)
    return True


class ElkOutputDevice(ToggleEntity):
    """Elk Output as Toggle Switch."""

    def __init__(self, output, elk, hass, show_override):
        """Initialize output switch."""
        self._element = output
        self._name = 'elkm1_' + self._element.default_name('_').lower()
        self.entity_id = 'switch.' + self._name
        self._state = None
        self._element.add_callback(self.trigger_update)
        self._show_override = show_override

    @property
    def name(self):
        """Return the name of the switch."""
        return self._element.name

    @property
    def state(self):
        """Return the state of the switch."""
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        if self.hass:
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
        if self._show_override is None:
            hidden = self._element.is_default_name()
        else:
            hidden = not self._show_override
        return {
            'hidden': hidden #self._element.is_default_name(),
            }

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        return self._element.output_on

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self, **kwargs):
        """Turn on output."""
        self._element.turn_on(0)

    def turn_off(self, **kwargs):
        """Turn off output."""
        self._element.turn_off()


class ElkTaskDevice(ToggleEntity):
    """Elk Task as Toggle Switch."""

    def __init__(self, task, elk, hass, show_override):
        """Initialize task switch."""
        self._element = task
        self._name = 'elkm1_' + self._element.default_name('_').lower()
        self.entity_id = 'switch.' + self._name
        self._state = STATE_OFF
        self._element.add_callback(self.trigger_update)
        self._show_override = show_override

    @property
    def name(self):
        """Return the name of the switch."""
        return self._element.name

    @property
    def state(self):
        """Return the state of the switch."""
        return self._state

#    @property
#    def icon(self):
#        """Icon to use in the frontend, if any"""
#        return 'mdi:' + 'toggle-switch'

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        if attribute == 'last_change':
            self._state = STATE_ON
        if self.hass:
            self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        if self.is_on:
            self.hass.async_add_job(self._async_auto_off)

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        if self._show_override is None:
            hidden = self._element.is_default_name()
        else:
            hidden = not self._show_override
        return {
            'Last Activated': self._element.last_change,
            'hidden': hidden
            }

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return False

    @property
    def is_on(self) -> bool:
        """True if output in the on state."""
        return self._state == STATE_ON

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    def turn_on(self, **kwargs):
        """Turn on output."""
        self._element.activate()

    def turn_off(self, **kwargs):
        """Turn off output."""
        # Tasks aren't actually ever turned off
        # Tasks are momentary, so "always" off
        self._state = STATE_OFF
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def _async_auto_off(self, timeout=2):
        """Automatically turn off to emulate momentary action."""
        yield from asyncio.sleep(timeout)
        self.turn_off()