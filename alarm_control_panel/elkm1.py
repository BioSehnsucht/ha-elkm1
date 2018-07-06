"""
Support for Elk M1 Gold / M1 EZ8 alarm control and integration panels.

Each non-Empty Area will be created as a separate Alarm panel in HASS.
"""
import asyncio
import logging
import time
from typing import Callable  # noqa

from homeassistant.helpers.typing import ConfigType

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_ARMING, STATE_ALARM_PENDING, STATE_ALARM_TRIGGERED,
    STATE_ALARM_ARMED_NIGHT, STATE_UNKNOWN
    )

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
    from elkm1.areas import Area as ElkArea
    from elkm1.keypads import Keypad as ElkKeypad
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather areas
        if elk_config['area']['enabled']:
            for element in elk.areas:
                if element:
                    if elk_config['area']['included'][element._index] is True:
                        discovery_info.append([element, elk_config['area']['shown'][element._index]])
    ## If discovery info was passed in, check if we want to include it
    #else:
    #    for node in discovery_info:
    #        if node.included is True and node.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(node)
    # Add discovered devices
    element_name = ''
    for element in discovery_info:
        if isinstance(element[0], ElkArea):
            element_name = 'alarm_control_panel.' + 'elkm1_' + element[0].default_name('_')
        #elif isinstance(node, ElkKeypad):
        #    if node.area > 0:
        #        node_name = 'alarm_control_panel.' + 'elk_area_' + format(node.area, '01')
        #        if node_name in discovered_devices:
        #            discovered_devices[node_name].trigger_update(node)
        #    continue
        else:
            continue
        if element_name not in discovered_devices:
            device = ElkAreaDevice(element[0], elk, hass, element[1])
            _LOGGER.debug('Loading Elk %s: %s', element[0].__class__.__name__, element[0].name)
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element[0].__class__.__name__, element[0].name)

    async_add_devices(devices, True)
    return True


class ElkAreaDevice(alarm.AlarmControlPanel):
    """Representation of an Area / Partition within the Elk M1 alarm panel."""

    def __init__(self, area, elk, hass, show_override):
        """Initialize Area as Alarm Control Panel."""
        self._element = area
        self._area = self._element.index + 1
        self._elk = elk
        self._state = None
        self._state_ext = ''
        self._hidden = False
        self._name = 'elkm1_' + self._element.default_name('_').lower()
        self.entity_id = 'alarm_control_panel.' + self._name
        self._keypads = []
        self._zones = []
        self._last_accessed_at = 0
        self._last_armed_at = 0
        self._last_disarmed_at = 0
        self._last_user_at = 0
        self._last_user_num = None
        self._last_user_name = None
        self._last_keypad_num = None
        self._last_keypad_name = None
        self._last_keypad_event = None
        self._element.add_callback(self.trigger_update)
        hass.bus.async_listen('elkm1_sensor_event', self._sensor_event)
        self._sync_done = False
        self._armed_status = None
        self._show_override = show_override

    def _sensor_event(self, event):
        event_data = event.data
        number = event_data['number']
        if event_data['area'] == self._area:
            if event_data['type'] == 'zone' and number not in self._zones:
                    self._zones.append(number)
            if event_data['type'] == 'keypad' and number not in self._keypads:
                    self._keypads.append(number)
            if event_data['attribute'] == 'last_user':
                self._last_keypad_event = event_data
                self._last_user_at = event_data['user_at']
                self._last_user_num = event_data['user_num']
                self._last_user_name = event_data['user_name']
                self._last_keypad_num = event_data['number']
                self._last_keypad_name = event_data['name']
        else:
            if event_data['type'] == 'zone' and number in self._zones:
                    self._zones.remove(number)
            if event_data['type'] == 'keypad' and number in self._keypads:
                    self._keypads.remove(number)
        if self.hass:
            self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the Area."""
        return self._element.name

    @property
    def code_format(self):
        """Return the alarm code format."""
        return '[0-9]{4}([0-9]{2})?'

    @property
    def state(self):
        """Return the current state of the area."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        from elkm1.const import ArmedStatus, ArmUpState, AlarmState
        from elkm1.util import pretty_const
        if self._show_override is None:
            hidden = self._hidden
        else:
            hidden = not self._show_override
        attrs = {
            'hidden': hidden,
            'Last Armed At': self._last_armed_at,
            'Last Disarmed At': self._last_disarmed_at,
            'Last User Number': self._last_user_num,
            'Last User At': self._last_user_at,
            'Last User Name': self._last_user_name,
            'Last Keypad Number': self._last_keypad_num,
            'Last Keypad Name': self._last_keypad_name,
            'Readiness': STATE_UNKNOWN,
            'Arm Status': STATE_UNKNOWN,
            'Alarm': STATE_UNKNOWN
            }
        if self._element.arm_up_state is not None:
            attrs['Readiness'] = pretty_const(ArmUpState(self._element.arm_up_state).name)
        if self._element.armed_status is not None:
            attrs['Arm Status'] = pretty_const(ArmedStatus(self._element.armed_status).name),
        if self._element.alarm_state is not None:
            attrs['Alarm'] = pretty_const(AlarmState(self._element.alarm_state).name),
        if self._element.timer1 > 0 or self._element.timer2 > 0:
            if self._element.is_exit:
                attrs['Alarm'] = 'Exit Timer Running'
            else:
                attrs['Alarm'] = 'Entry Timer Running'
        return attrs

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        from elkm1.const import ArmedStatus
        if attribute == 'armed_status':
            if self._sync_done:
                if value == ArmedStatus.DISARMED.value and value != self._armed_status:
                    self._last_disarmed_at = time.time()
                elif value != self._armed_status:
                    self._last_armed_at = time.time()
            else:
                self._sync_done = True
        if self.hass:
            self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        from elkm1.const import ArmedStatus, AlarmState
        # Set status based on arm state
        self._armed_status = self._element.armed_status
        if self._armed_status is not None:
            if self._armed_status == ArmedStatus.DISARMED.value:
                self._state = STATE_ALARM_DISARMED
            elif self._armed_status == ArmedStatus.ARMED_AWAY.value:
                self._state = STATE_ALARM_ARMED_AWAY
            elif self._armed_status == ArmedStatus.ARMED_STAY.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._armed_status == ArmedStatus.ARMED_STAY_INSTANT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._armed_status == ArmedStatus.ARMED_TO_NIGHT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._armed_status == ArmedStatus.ARMED_TO_NIGHT_INSTANT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._armed_status == ArmedStatus.ARMED_TO_VACATION.value:
                self._state = STATE_ALARM_ARMED_AWAY
        else:
            self._state = STATE_UNKNOWN
        # If alarm is triggered, show that instead
        if self._element.alarm_state is not None:
            if self._element.alarm_state != AlarmState.NO_ALARM_ACTIVE.value:
                self._state = STATE_ALARM_TRIGGERED
        # Unless there's an entry / exit timer running,
        # show that we're arming or pending alarm accordingly
        if self._element.timer1 > 0 or self._element.timer2 > 0:
            if not self._element.is_exit:
                self._state = STATE_ALARM_PENDING
            # Don't displaying ARMING if exit timer running, because
            # HASS won't let you disarm during ARMING
            #else:
            #    self._state = STATE_ALARM_ARMING
        # If we should be hidden due to lack of member devices and default name, hide us
        if (len(self._keypads) == 0) and (len(self._zones) == 0) and (self._element.is_default_name()):
            self._hidden = True
        else:
            self._hidden = False
        return

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._element.disarm(int(code))
        return

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        from elkm1.const import ArmLevel
        self._element.arm(ArmLevel.ARMED_STAY.value, int(code))
        return

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        from elkm1.const import ArmLevel
        self._element.arm(ArmLevel.ARMED_AWAY.value, int(code))
        return
