"""
Each ElkM1 area will be created as a separate alarm_control_panel in HASS.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/alarm_control_panel.elkm1/
"""

import asyncio
import logging
import time

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_ARMING, STATE_ALARM_DISARMING, STATE_ALARM_PENDING,
    STATE_UNKNOWN, STATE_ALARM_TRIGGERED, STATE_ALARM_ARMED_NIGHT,
    ATTR_ENTITY_ID, ATTR_CODE)
from homeassistant.core import callback

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices

from elkm1_lib.const import ArmLevel, ArmedStatus, ArmUpState, AlarmState

DEPENDENCIES = ['elkm1']

STATE_ALARM_ARMED_VACATION = 'armed_vacation'
STATE_ALARM_ARMED_HOME_INSTANT = 'armed_home_instant'
STATE_ALARM_ARMED_NIGHT_INSTANT = 'armed_night_instant'

SERVICE_ALARM_VACATION = 'alarm_arm_vacation'
SERVICE_ALARM_HOME_INSTANT = 'alarm_arm_home_instant'
SERVICE_ALARM_NIGHT_INSTANT = 'alarm_arm_night_instant'

SERVICE_TO_METHOD = {
    SERVICE_ALARM_VACATION: 'async_alarm_arm_vacation',
    SERVICE_ALARM_HOME_INSTANT: 'async_alarm_arm_home_instant',
    SERVICE_ALARM_NIGHT_INSTANT: 'async_alarm_arm_night_instant',
}

_LOGGER = logging.getLogger(__name__)

ELK_STATE_TO_HASS_STATE = {
    ArmedStatus.DISARMED.value:               STATE_ALARM_DISARMED,
    ArmedStatus.ARMED_AWAY.value:             STATE_ALARM_ARMED_AWAY,
    ArmedStatus.ARMED_STAY.value:             STATE_ALARM_ARMED_HOME,
    ArmedStatus.ARMED_STAY_INSTANT.value:     STATE_ALARM_ARMED_HOME_INSTANT,
    ArmedStatus.ARMED_TO_NIGHT.value:         STATE_ALARM_ARMED_NIGHT,
    ArmedStatus.ARMED_TO_NIGHT_INSTANT.value: STATE_ALARM_ARMED_NIGHT_INSTANT,
    ArmedStatus.ARMED_TO_VACATION.value:      STATE_ALARM_ARMED_VACATION,
}


# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk switch platform."""

    elk = hass.data['elkm1']['connection']
    devices = create_elk_devices(hass, elk.areas, 'area', ElkArea, [])
    async_add_devices(devices, True)

    @asyncio.coroutine
    def async_alarm_service_handler(service):
        """Map services to methods on Alarm."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        code = service.data.get(ATTR_CODE)
        method = SERVICE_TO_METHOD[service.service]
        target_devices = [device for device in devices
                          if device.entity_id in entity_ids]

        for device in target_devices:
            getattr(device, method)(code)

    for service in SERVICE_TO_METHOD:
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
        self._lovelace = hass.data['elkm1']['config']['lovelace']
        self._changed_by = -1
        self._changed_by_time = 0

        for keypad in self._elk.keypads:
            keypad.add_callback(self._watch_keypad)

    def _watch_keypad(self, element, attribute, value):
        if element.index != self._element.index:
            return
        if attribute == 'last_user':
            self._changed_by = value
            self._changed_by_time = time.time()
            self.async_schedule_update_ha_state(True)

    @property
    def code_format(self):
        """Return the alarm code format."""
        return '^[0-9]{4}([0-9]{2})?$'

    @property
    def changed_by(self):
        """Return name of last person to make change."""
        if self._changed_by < 0:
            return ""
        return self._elk.users[self._changed_by].name

    @property
    def device_state_attributes(self):
        """Attributes of the area."""
        el = self._element
        attrs = {
            'is_exit': el.is_exit,
            'timer1': el.timer1,
            'timer2': el.timer2,
            'state': self._state,
            'changed_by_time': self._changed_by_time,
        }
        attrs['armed_status'] = STATE_UNKNOWN if el.armed_status is None \
            else ArmedStatus(el.armed_status).name.lower()
        attrs['arm_up_state'] = STATE_UNKNOWN if el.arm_up_state is None \
            else ArmUpState(self._element.arm_up_state).name.lower()
        attrs['alarm_state'] = STATE_UNKNOWN if el.alarm_state is None \
            else AlarmState(self._element.alarm_state).name.lower()
        return attrs

    # pylint: disable=unused-argument
    @callback
    def _element_callback(self, element, attribute, value):
        """Callback handler from the Elk."""
        if self._element.alarm_state is None:
            self._state = STATE_UNKNOWN
        elif self._area_is_in_alarm_state():
            self._state = STATE_ALARM_TRIGGERED
        elif self._entry_exit_timer_is_running():
            if self._lovelace:
                self._state = STATE_ALARM_ARMING if self._element.is_exit \
                    else STATE_ALARM_DISARMING
            else:
                self._state = STATE_ALARM_PENDING
        else:
            self._state = ELK_STATE_TO_HASS_STATE[self._element.armed_status]
        self._hidden = self._element.is_default_name()
        self.async_schedule_update_ha_state(True)

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

    def async_alarm_arm_vacation(self, code=None):
        """Send arm vacation command."""
        self._element.arm(ArmLevel.ARMED_VACATION.value, int(code))

    def async_alarm_arm_home_instant(self, code=None):
        """Send arm home instant command."""
        self._element.arm(ArmLevel.ARMED_STAY_INSTANT.value, int(code))

    def async_alarm_arm_night_instant(self, code=None):
        """Send arm night instant command."""
        self._element.arm(ArmLevel.ARMED_NIGHT_INSTANT.value, int(code))
