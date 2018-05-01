"""
Support for Elk M1 Gold / M1 EZ8 alarm control and integration panels.

Each non-Empty Area will be created as a separate Alarm panel in HASS.
"""
import asyncio
import logging
from typing import Callable  # noqa

from homeassistant.helpers.typing import ConfigType

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_ARMING, STATE_ALARM_DISARMING, STATE_ALARM_TRIGGERED,
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
        for element in elk.areas:
            if element:
                #if node.included is True and node.enabled is True:
                    discovery_info.append(element)
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
        if isinstance(element, ElkArea):
            element_name = 'alarm_control_panel.' + 'elkm1_' + element.default_name('_')
        #elif isinstance(node, ElkKeypad):
        #    if node.area > 0:
        #        node_name = 'alarm_control_panel.' + 'elk_area_' + format(node.area, '01')
        #        if node_name in discovered_devices:
        #            discovered_devices[node_name].trigger_update(node)
        #    continue
        else:
            continue
        if element_name not in discovered_devices:
            device = ElkAreaDevice(element, elk)
            _LOGGER.debug('Loading Elk %s: %s', element.__class__.__name__, element.name)
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element.__class__.__name__, element.name)

    async_add_devices(devices, True)
    return True


class ElkAreaDevice(alarm.AlarmControlPanel):
    """Representation of an Area / Partition within the Elk M1 alarm panel."""

    def __init__(self, area, elk):
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
        self._keypads_count = 0
        self._zones_count = 0
        #self._sync_keypads()
        #self._sync_zones()
        self._element.add_callback(self.trigger_update)

    def _sync_keypads(self):
        """Synchronize list of member keypads and update callbacks."""
        keypad_list = []
        for keypad in enumerate(self._elk.keypads):
            if keypad.area == self._element.index:
                keypad.add_callback(self.trigger_update)
                keypad_list.append(keypad.area)
            else:
                keypad.remove_callback(self.trigger_update)
        self._keypads = keypad_list
        self._keypads_count = len(keypad_list)

    def _sync_zones(self):
        """Synchronize count of member zones."""
        zone_list = []
        for zone in enumerate(self._elk.zones):
            if zone.area == self._area:
                zone_list.append(zone.area)
        self._zones_count = len(zone_list)

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
        attrs = {
            'hidden': self._hidden,
            #'State': self._state,
            #'last_armed_at': self._device.last_armed_at,
            #'last_disarmed_at': self._device.last_disarmed_at,
            #'last_user_num': self._device.last_user_num,
            #'last_user_at': self._device.last_user_at,
            #'last_user_name': self._device.last_user_name,
            #'last_keypad_num': self._device.last_keypad_num,
            #'last_keypad_name': self._device.last_keypad_name,
            }
        if self._element.arm_up_state is not None:
            attrs['Readiness'] = pretty_const(ArmUpState(self._element.arm_up_state).name)
        if self._element.armed_status is not None:
            attrs['Arm Status'] = pretty_const(ArmedStatus(self._element.armed_status).name),
        if self._element.alarm_state is not None:
            attrs['Alarm'] = pretty_const(AlarmState(self._element.alarm_state).name),
        return attrs

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        from elkm1.const import ArmedStatus, AlarmState
        # Set status based on arm state
        if self._element.armed_status is not None:
            if self._element.armed_status == ArmedStatus.DISARMED.value:
                self._state = STATE_ALARM_DISARMED
            elif self._element.armed_status == ArmedStatus.ARMED_AWAY.value:
                self._state = STATE_ALARM_ARMED_AWAY
            elif self._element.armed_status == ArmedStatus.ARMED_STAY.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._element.armed_status == ArmedStatus.ARMED_STAY_INSTANT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._element.armed_status == ArmedStatus.ARMED_TO_NIGHT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._element.armed_status == ArmedStatus.ARMED_TO_NIGHT_INSTANT.value:
                self._state = STATE_ALARM_ARMED_HOME
            elif self._element.armed_status == ArmedStatus.ARMED_TO_VACATION.value:
                self._state = STATE_ALARM_ARMED_AWAY
        else:
            self._state = STATE_UNKNOWN
        # TODO : Implement detection of entry/exit timer running in Gwww lib
        ## If there's an entry / exit timer running,
        ## show that we're pending arming
        #if self._element.timers_active is self._element.STATUS_TIMER_ENTRY:
        #    self._state = STATE_ALARM_ARMING
        #if self._element.timers_active is self._element.STATUS_TIMER_EXIT:
        #    self._state = STATE_ALARM_DISARMING
        # If alarm is triggered, show that instead
        if self._element.alarm_state is not None:
            if self._element.alarm_state != AlarmState.NO_ALARM_ACTIVE.value:
                self._state = STATE_ALARM_TRIGGERED
        # If we should be hidden due to lack of member devices, hide us
        # TODO: Hide based on name being set?
        #if (len(self._keypads_count) == 0) and (
        #        self._zones_count == 0):
        #    self._hidden = True
        #    #_LOGGER.debug('hiding alarm ' + self._name + ' with ' + str(self._element.member_keypads_count) + ' keypads and ' + str(self._element.member_zones_count) + ' zones')
        #else:
        #    self._hidden = False
        #    #_LOGGER.debug('unhiding alarm ' + self._name + ' with ' + str(self._element.member_keypads_count) + ' keypads and ' + str(self._element.member_zones_count) + ' zones')
        # Update which keypads and zones are members of this Area
        #self._sync_keypads()
        #self._sync_zones()
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
