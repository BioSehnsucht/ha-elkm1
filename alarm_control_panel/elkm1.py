"""
Support for Elk M1 Gold / M1 EZ8 alarm control and integration panels.

Each non-Empty Area will be created as a separate Alarm panel in HASS.
"""

import logging
from typing import Callable  # noqa

from homeassistant.helpers.typing import ConfigType

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_ARMING, STATE_ALARM_DISARMING, STATE_ALARM_TRIGGERED,
    STATE_ALARM_ARMED_NIGHT,
    )

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
    from PyElk.Area import Area as ElkArea
    from PyElk.Keypad import Keypad as ElkKeypad
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather areas
        for node in elk.AREAS:
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
        if isinstance(node, ElkArea):
            node_name = 'alarm_control_panel.' + 'elk_area_' + format(node.number, '01')
        elif isinstance(node, ElkKeypad):
            if node.area > 0:
                node_name = 'alarm_control_panel.' + 'elk_area_' + format(node.area, '01')
                if node_name in discovered_devices:
                    discovered_devices[node_name].trigger_update(node)
            continue
        else:
            continue
        if node_name not in discovered_devices:
            device = ElkAreaDevice(node, elk)
            _LOGGER.debug('Loading Elk %s: %s', node.classname, node.description_pretty())
            discovered_devices[node_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', node.classname, node.description_pretty())

    add_devices(devices, True)
    return True


class ElkAreaDevice(alarm.AlarmControlPanel):
    """Representation of an Area / Partition within the Elk M1 alarm panel."""

    def __init__(self, area, pyelk):
        """Initialize Area as Alarm Control Panel."""
        self._device = area
        self._pyelk = pyelk
        self._state = None
        self._state_ext = ''
        self._hidden = False
        self._name = 'elk_area_' + str(area.number)
        self.entity_id = 'alarm_control_panel.' + self._name
        self._keypads = None
        self._device.callback_add(self.trigger_update)
        self._sync_keypads()
        self.update()

    def _sync_keypads(self):
        """Synchronize list of member keypads and update callbacks."""
        self._keypads = self._device.member_keypad
        for keypad, member in enumerate(self._keypads):
            if member:
                self._pyelk.KEYPADS[keypad].callback_add(self.trigger_update)
            else:
                self._pyelk.KEYPADS[keypad].callback_remove(self.trigger_update)

    @property
    def name(self):
        """Return the name of the Area."""
        return self._device.description_pretty()

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
        return {
            'hidden': self._hidden,
            'Readiness': self._device.arm_up_pretty(),
            'Status': self._device.status_pretty(),
            'State': self._state,
            'Alarm': self._device.alarm_pretty(),
            'last_armed_at': self._device.last_armed_at,
            'last_disarmed_at': self._device.last_disarmed_at,
            'last_user_num': self._device.last_user_num,
            'last_user_at': self._device.last_user_at,
            'last_user_name': self._device.last_user_name,
            'last_keypad_num': self._device.last_keypad_num,
            'last_keypad_name': self._device.last_keypad_name,
            }

    def trigger_update(self, node):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of area ' + str(
            self._device.number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        # Set status based on arm state
        if self._device.status == self._device.STATUS_DISARMED:
            self._state = STATE_ALARM_DISARMED
        elif self._device.status == self._device.STATUS_ARMED_AWAY:
            self._state = STATE_ALARM_ARMED_AWAY
        elif self._device.status == self._device.STATUS_ARMED_STAY:
            self._state = STATE_ALARM_ARMED_HOME
        elif self._device.status == self._device.STATUS_ARMED_STAY_INSTANT:
            self._state = STATE_ALARM_ARMED_HOME
        elif self._device.status == self._device.STATUS_ARMED_NIGHT:
            self._state = STATE_ALARM_ARMED_HOME
        elif self._device.status == self._device.STATUS_ARMED_NIGHT_INSTANT:
            self._state = STATE_ALARM_ARMED_HOME
        elif self._device.status == self._device.STATUS_ARMED_VACATION:
            self._state = STATE_ALARM_ARMED_AWAY
        # If there's an entry / exit timer running,
        # show that we're pending arming
        if self._device.timers_active is self._device.STATUS_TIMER_ENTRY:
            self._state = STATE_ALARM_ARMING
        if self._device.timers_active is self._device.STATUS_TIMER_EXIT:
            self._state = STATE_ALARM_DISARMING
        # If alarm is triggered, show that instead
        if self._device.alarm_active is True:
            self._state = STATE_ALARM_TRIGGERED
        # If we should be hidden due to lack of member devices, hide us
        if (self._device.member_keypads_count == 0) and (
                self._device.member_zones_count == 0):
            self._hidden = True
            _LOGGER.debug('hiding alarm ' + self._name + ' with ' + str(self._device.member_keypads_count) + ' keypads and ' + str(self._device.member_zones_count) + ' zones')
        else:
            self._hidden = False
            _LOGGER.debug('unhiding alarm ' + self._name + ' with ' + str(self._device.member_keypads_count) + ' keypads and ' + str(self._device.member_zones_count) + ' zones')
        # Update which keypads are members of this Area
        self._sync_keypads()
        return

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._device.disarm(code)
        return

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._device.arm(self._device.ARM_STAY, code)
        return

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._device.arm(self._device.ARM_AWAY, code)
        return
