"""
Support for Elk M1 Gold / M1 EZ8 alarm control and integration panels

Each non-Empty Area will be created as a separate Alarm panel in HASS
"""

import logging
from typing import Callable  # noqa

import PyElk

from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_OFF, STATE_ON)

from homeassistant.helpers.entity import Entity

from homeassistant.helpers.typing import ConfigType

from homeassistant.helpers.entity import ToggleEntity

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel import PLATFORM_SCHEMA
from homeassistant.const import (
        STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED
        )


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

    for area in elk.AREAS:
        if area:
            if area._included == True:
                _LOGGER.debug('Loading Elk Area : %s', area.description())
                devices.append(ElkAreaDevice(area))
            else:
                _LOGGER.debug('Skipping excluded Elk Area: %s', area._number)

    add_devices(devices, True)
    return True

class ElkAreaDevice(alarm.AlarmControlPanel):

    """Representation of an Area / Partition within the Elk M1 alarm panel."""
    def __init__(self, area):
        self._device = area
        self._state = None
        self._state_ext = ''
        self._hidden = False
        self._device.callback_add(self.trigger_update)
        self._name = 'elk_area_' + str(area._number)
        self.update()

    @property
    def name(self):
        """Return the name of the Area"""
        return 'elk_area_' + str(self._device._number)

    @property
    def code_format(self):
        return '[0-9]{4}([0-9]{2})?'

    @property
    def state(self):
        return self._state

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            'hidden' : self._hidden,
            'Readiness' : self._device.arm_up(),
            'Status' : self._device.status(),
            'State' : self._state,
            'Alarm' : self._device.alarm(),
            'friendly_name' : self._device.description(),
            'last_armed_by_user' : self._device._last_armed_by_user,
            'last_armed_at' : self._device._last_armed_at,
            'last_disarmed_by_user' : self._device._last_disarmed_by_user,
            'last_disarmed_at' : self._device._last_disarmed_at,
            'last_user_code' : self._device._last_user_code,
            'last_user_at' : self._device._last_user_at,
            }

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of area ' + str(self._device._number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        # Set status based on arm state
        if (self._device._status == self._device.STATUS_DISARMED):
            self._state = STATE_ALARM_DISARMED
        elif (self._device._status == self._device.STATUS_ARMED_AWAY):
            self._state = STATE_ALARM_ARMED_AWAY
        elif (self._device._status == self._device.STATUS_ARMED_STAY):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._device._state == self._device.STATUS_ARMED_STAY_INSTANT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._device._state == self._device.STATUS_ARMED_NIGHT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._device._state == self._device.STATUS_ARMED_NIGHT_INSTANT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._device._state == self._device.STATUS_ARMED_VACATION):
            self._state = STATE_ALARM_ARMED_AWAY
        # If there's an entry / exit timer running, show that we're pending arming
        if (self._device.timers_active == True):
            self._state = STATE_ALARM_PENDING
        # If alarm is triggered, show that instead
        if (self._device.alarm_active == True):
            self._state = STATE_ALARM_TRIGGERED
        # If we should be hidden due to lack of member devices, hide us
        if ((self._device.member_keypads == 0) and (self._device.member_zones == 0)):
            self._hidden = True
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
