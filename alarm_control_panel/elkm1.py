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

    for area in elk.AREAS:
        if area:
            _LOGGER.debug('Loading Elk Area : %s', area.description())
            devices.append(ElkAreaDevice(area))

    add_devices(devices, True)
    return True

class ElkAreaDevice(alarm.AlarmControlPanel):
    _area = None
    _name = ''
    _state = None
    _state_ext = ''
    _hidden = False

    """Representation of an Area / Partition within the Elk M1 alarm panel"""
    def __init__(self, area):
        self._area = area
        self._area._update_callback = self.trigger_update
        self._name = 'elk_area_' + str(area._number)
        self._state = None
        self.update()

    def trigger_update(self):
        _LOGGER.debug('Triggering auto update of area ' + str(self._area._number))
        self.schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the Area"""
        return 'elk_area_' + str(self._area._number)

    @property
    def code_format(self):
        return '[0-9]{4}([0-9]{2})?'

    @property
    def state(self):
        return self._state

    def update(self):
        """Set alarm state"""
        if (self._area._status == self._area.STATUS_DISARMED):
            self._state = STATE_ALARM_DISARMED
        elif (self._area._status == self._area.STATUS_ARMED_AWAY):
            self._state = STATE_ALARM_ARMED_AWAY
        elif (self._area._status == self._area.STATUS_ARMED_STAY):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._area._state == self._area.STATUS_ARMED_STAY_INSTANT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._area._state == self._area.STATUS_ARMED_NIGHT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._area._state == self._area.STATUS_ARMED_NIGHT_INSTANT):
            self._state = STATE_ALARM_ARMED_HOME
        elif (self._area._state == self._area.STATUS_ARMED_VACATION):
            self._state = STATE_ALARM_ARMED_AWAY
        """If there's an entry / exit timer running, show that we're pending arming"""
        if (self._area.timers_active == True):
            self._state = STATE_ALARM_PENDING
        """If alarm is triggered, show that instead"""
        if (self._area.alarm_active == True):
            self._state = STATE_ALARM_TRIGGERED
        if ((self._area.member_keypads == 0) and (self._area.member_zones == 0)):
            self._hidden = True
        return

    def alarm_disarm(self, code=None):
        """Send disarm command"""
        self._area.disarm(code)
        return

    def alarm_arm_home(self, code=None):
        """Send arm home command"""
        self._area.arm(self._area.ARM_STAY, code)
        return

    def alarm_arm_away(self, code=None):
        """Send arm away command"""
        self._area.arm(self._area.ARM_AWAY, code)
        return

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            'hidden' : self._hidden,
            'Readiness' : self._area.arm_up(),
            'Status' : self._area.status(),
            'State' : self._state,
            'Alarm' : self._area.alarm(),
            'friendly_name' : self._area.description(),
            }

