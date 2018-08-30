"""
Each ElkM1 area will be created as a separate alarm_control_panel in HASS.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.elkm1/
"""

import asyncio
import time

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (ATTR_CODE, ATTR_ENTITY_ID,
                                 STATE_ALARM_ARMED_AWAY,
                                 STATE_ALARM_ARMED_HOME,
                                 STATE_ALARM_ARMED_NIGHT, STATE_ALARM_ARMING,
                                 STATE_ALARM_DISARMED, STATE_ALARM_DISARMING,
                                 STATE_ALARM_PENDING, STATE_ALARM_TRIGGERED,
                                 STATE_UNKNOWN)

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices
from elkm1_lib.const import AlarmState, ArmedStatus, ArmLevel, ArmUpState

DEPENDENCIES = ['elkm1']

STATE_ALARM_ARMED_VACATION = 'armed_vacation'
STATE_ALARM_ARMED_HOME_INSTANT = 'armed_home_instant'
STATE_ALARM_ARMED_NIGHT_INSTANT = 'armed_night_instant'

SERVICE_TO_ELK = {
    'alarm_arm_vacation': ArmLevel.ARMED_VACATION.value,
    'alarm_arm_home_instant': ArmLevel.ARMED_STAY_INSTANT.value,
    'alarm_arm_night_instant': ArmLevel.ARMED_NIGHT_INSTANT.value,
}

ELK_STATE_TO_HASS_STATE = {
    ArmedStatus.DISARMED.value:               STATE_ALARM_DISARMED,
    ArmedStatus.ARMED_AWAY.value:             STATE_ALARM_ARMED_AWAY,
    ArmedStatus.ARMED_STAY.value:             STATE_ALARM_ARMED_HOME,
    ArmedStatus.ARMED_STAY_INSTANT.value:     STATE_ALARM_ARMED_HOME,
    ArmedStatus.ARMED_TO_NIGHT.value:         STATE_ALARM_ARMED_NIGHT,
    ArmedStatus.ARMED_TO_NIGHT_INSTANT.value: STATE_ALARM_ARMED_NIGHT,
    ArmedStatus.ARMED_TO_VACATION.value:      STATE_ALARM_ARMED_AWAY,
}

import logging
_LOGGER = logging.getLogger(__name__)

# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk switch platform."""

    elk = hass.data['elkm1']['connection']
    devices = create_elk_devices(hass, elk.areas, 'area', ElkArea, [])
    async_add_devices(devices, True)

    async def async_alarm_service_handler(service):
        """Map services to methods on Alarm."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        code = service.data.get(ATTR_CODE)
        target_devices = [device for device in devices
                          if device.entity_id in entity_ids]

        for device in target_devices:
            device.async_alarm_service(service.service, code)

    for service in SERVICE_TO_ELK:
        hass.services.async_register(alarm.DOMAIN, service,
                                     async_alarm_service_handler,
                                     schema=alarm.ALARM_SERVICE_SCHEMA)
    return True


class ElkArea(ElkDeviceBase, alarm.AlarmControlPanel):
    """Representation of an Area / Partition within the Elk M1 alarm panel."""

    def __init__(self, device, hass, config):
        """Initialize Area as Alarm Control Panel."""
        ElkDeviceBase.__init__(self, 'alarm_control_panel', device,
                               hass, config)
        self._changed_by = -1
        self._changed_by_keypad = -1
        self._changed_by_time = 0

        for keypad in self._elk.keypads:
            keypad.add_callback(self._watch_keypad)

    def _watch_keypad(self, keypad, changeset):
        if keypad.area != self._element.index:
            return
        _LOGGER.warn( "watch keypad1 %d %d %s", self._element.index, keypad.area, changeset)
        last_user = changeset.get('last_user')
        if last_user is not None:
            _LOGGER.warn( "watch keypad2 %d %d %s", self._element.index, keypad.area, changeset)
            self._changed_by = last_user
            self._changed_by_keypad = keypad.index
            self._changed_by_time = time.time()
            self.async_schedule_update_ha_state(True)

    @property
    def code_format(self):
        """Return the alarm code format."""
        return '^[0-9]{4}([0-9]{2})?$'

    @property
    def changed_by(self):
        """Return name of last person to make change."""
        if self._changed_by < 0 or self._changed_by > 203:
            return ""
        if self._changed_by < self._elk.users.max_elements:
            return self._elk.users[self._changed_by].name
        if self._changed_by == 201:
            return "Program"
        if self._changed_by == 202:
            return "Elk RP"
        if self._changed_by == 203:
            return "Quick arm"

    @property
    def device_state_attributes(self):
        """Attributes of the area."""
        attrs = self.initial_attrs()
        el = self._element
        attrs['is_exit'] = el.is_exit
        attrs['timer1'] = el.timer1
        attrs['timer2'] = el.timer2
        attrs['armed_status'] = STATE_UNKNOWN if el.armed_status is None \
            else ArmedStatus(el.armed_status).name.lower()
        attrs['arm_up_state'] = STATE_UNKNOWN if el.arm_up_state is None \
            else ArmUpState(self._element.arm_up_state).name.lower()
        attrs['alarm_state'] = STATE_UNKNOWN if el.alarm_state is None \
            else AlarmState(self._element.alarm_state).name.lower()

        attrs['changed_by_user'] = self._changed_by + 1
        attrs['changed_by_time'] = self._changed_by_time
        attrs['changed_by_keypad'] = self._changed_by_keypad + 1
        attrs['changed_by_keypad_name'] = \
            self._elk.keypads[self._changed_by_keypad].name \
                if self._changed_by_keypad >= 0 else ''
        return attrs

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        if self._element.alarm_state is None:
            self._state = STATE_UNKNOWN
        elif self._area_is_in_alarm_state():
            self._state = STATE_ALARM_TRIGGERED
        elif self._entry_exit_timer_is_running():
            # Fix this when put into HASS
            # self._state = STATE_ALARM_ARMING \
            #     if self._element.is_exit else STATE_ALARM_PENDING
            self._state = STATE_ALARM_PENDING
        else:
            self._state = ELK_STATE_TO_HASS_STATE[self._element.armed_status]

    def _entry_exit_timer_is_running(self):
        return self._element.timer1 > 0 or self._element.timer2 > 0

    def _area_is_in_alarm_state(self):
        return self._element.alarm_state >= AlarmState.FIRE_ALARM.value

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._element.disarm(int(code))

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._element.arm(ArmLevel.ARMED_STAY.value, int(code))

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._element.arm(ArmLevel.ARMED_AWAY.value, int(code))

    def alarm_arm_night(self, code=None):
        """Send arm away command."""
        self._element.arm(ArmLevel.ARMED_NIGHT.value, int(code))

    def async_alarm_service(self, service, code):
        """Send arm night instant command."""
        self._element.arm(SERVICE_TO_ELK[service], int(code))
