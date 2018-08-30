"""
Support for control of ElkM1 sensors. On the ElkM1 there are 5 types
of sensors:
- Zones that are on/off/voltage/temperature.
- Keypads that have temperature (not all models, but no way to know)
- Counters that are integers that can be read/set
- Settings that are used to trigger automations

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.elkm1/
"""

import asyncio
import logging
import time

from homeassistant.const import TEMP_FAHRENHEIT

from custom_components.elkm1 import ElkDeviceBase, create_elk_devices
from elkm1_lib.const import (ElkRPStatus, SettingFormat, ZoneLogicalStatus,
                             ZonePhysicalStatus, ZoneType)
from elkm1_lib.util import pretty_const

DEPENDENCIES = ['elkm1']

_ZONE_ICONS = {
    ZoneType.FIRE_ALARM.value: 'fire',
    ZoneType.FIRE_VERIFIED.value: 'fire',
    ZoneType.FIRE_SUPERVISORY.value: 'fire',
    ZoneType.KEYFOB.value: 'key',
    ZoneType.NON_ALARM.value: 'alarm-off',
    ZoneType.MEDICAL_ALARM.value: 'medical-bag',
    ZoneType.POLICE_ALARM.value: 'alarm-light',
    ZoneType.POLICE_NO_INDICATION.value: 'alarm-light',
    ZoneType.KEY_MOMENTARY_ARM_DISARM.value: 'power',
    ZoneType.KEY_MOMENTARY_ARM_AWAY.value: 'power',
    ZoneType.KEY_MOMENTARY_ARM_STAY.value: 'power',
    ZoneType.KEY_MOMENTARY_DISARM.value: 'power',
    ZoneType.KEY_ON_OFF.value: 'toggle-switch',
    ZoneType.MUTE_AUDIBLES.value: 'volume-mute',
    ZoneType.POWER_SUPERVISORY.value: 'power-plug',
    ZoneType.TEMPERATURE.value: 'thermometer-lines',
    ZoneType.ANALOG_ZONE.value: 'speedometer',
    ZoneType.PHONE_KEY.value: 'phone-classic',
    ZoneType.INTERCOM_KEY.value: 'deskphone'
}
_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk sensor platform."""

    elk = hass.data['elkm1']['connection']
    devices = create_elk_devices(hass, [elk.panel],
                                 'panel', ElkPanel, [])
    devices = create_elk_devices(hass, elk.zones,
                                 'zone', ElkZone, devices)
    devices = create_elk_devices(hass, elk.keypads,
                                 'keypad', ElkKeypad, devices)
    devices = create_elk_devices(hass, elk.thermostats,
                                 'thermostat', ElkThermostat, devices)
    devices = create_elk_devices(hass, elk.counters,
                                 'counter', ElkCounter, devices)
    devices = create_elk_devices(hass, elk.settings,
                                 'setting', ElkSetting, devices)
    async_add_devices(devices, True)
    return True


class ElkPanel(ElkDeviceBase):
    """Handle an Elk Panel."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:home"

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = self.initial_attrs()
        attrs['remote_programming_status'] = ElkRPStatus(
            self._element.remote_programming_status).name.lower()
        attrs['system_trouble_status'] = self._element.system_trouble_status
        return attrs

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        if self._elk.is_connected():
            self._state = 'Paused' if self._element.remote_programming_status \
                else 'Connected'
        else:
            self._state = 'Disconnected'


class ElkKeypad(ElkDeviceBase):
    """Handle an Elk Keypad."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)
        self._last_user_time = 0

    @property
    def temperature_unit(self):
        """The temperature scale."""
        return TEMP_FAHRENHEIT

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:thermometer-lines'

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = self.initial_attrs()
        attrs['last_user'] = self._element.last_user + 1
        attrs['last_user_name'] = \
            self._elk.users[self._element.last_user].name \
            if self._element.last_user >= 0 else ""
        attrs['last_user_time'] = self._last_user_time
        attrs['temperature'] = self._element.temperature
        attrs['area'] = self._element.area + 1
        return attrs

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        self._temperature_to_state(self._element.temperature, -40)
        if changeset.get('last_user'):
            self._last_user_time = time.time()


class ElkZone(ElkDeviceBase):
    """Handle an Elk Zone."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:' + _ZONE_ICONS.get(self._element.definition, 'alarm-bell')

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = self.initial_attrs()
        attrs['physical_status'] = ZonePhysicalStatus(
            self._element.physical_status).name.lower()
        attrs['logical_status'] = ZoneLogicalStatus(
            self._element.logical_status).name.lower()
        attrs['definition'] = ZoneType(
            self._element.definition).name.lower()
        attrs['area'] = self._element.area + 1
        attrs['bypassed'] = self._element.bypassed
        attrs['triggered_alarm'] = self._element.triggered_alarm
        if self._element.definition == ZoneType.TEMPERATURE.value:
            attrs['temperature'] = self._element.temperature
        elif self._element.definition == ZoneType.ANALOG_ZONE.value:
            attrs['voltage'] = self._element.voltage
        return attrs

    @property
    def temperature_unit(self):
        """The temperature scale."""
        return TEMP_FAHRENHEIT

    @property
    def unit_of_measurement(self):
        """Unit of measurement."""
        if self._element.definition == ZoneType.TEMPERATURE.value:
            return self.hass.config.units.temperature_unit
        if self._element.definition == ZoneType.ANALOG_ZONE.value:
            return 'volts'
        return None

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        if self._element.definition == ZoneType.TEMPERATURE.value:
            self._temperature_to_state(self._element.temperature, -60)
        elif self._element.definition == ZoneType.ANALOG_ZONE.value:
            self._state = self._element.voltage
        else:
            self._state = pretty_const(ZoneLogicalStatus(
                self._element.logical_status).name)


class ElkThermostat(ElkDeviceBase):
    """Handle an Elk thermostat."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)

    @property
    def temperature_unit(self):
        """The temperature scale."""
        return TEMP_FAHRENHEIT

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:thermometer-lines'

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        self._temperature_to_state(self._element.current_temp, 0)


# pylint: disable=too-few-public-methods
class ElkCounter(ElkDeviceBase):
    """Handle an Elk Counter."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:numeric'

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        self._state = self._element.value


class ElkSetting(ElkDeviceBase):
    """Handle an Elk setting."""
    def __init__(self, device, hass, config):
        ElkDeviceBase.__init__(self, 'sensor', device, hass, config)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:numeric'

    # pylint: disable=unused-argument
    def _element_changed(self, element, changeset):
        self._state = self._element.value

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = self.initial_attrs()
        attrs['value_format'] = SettingFormat(
            self._element.value_format).name.lower()
        attrs['value'] = self._element.value
        return attrs
