"""Support for Elk zones as sensors."""
import asyncio
import logging
import time

from homeassistant.const import (TEMP_FAHRENHEIT, STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import callback

from elkm1 import Elk
from elkm1.const import (ZoneType, ZoneLogicalStatus, ZonePhysicalStatus, 
                         SettingFormat, ElkRPStatus)
from elkm1.util import pretty_const

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info):
    """Setup the Elk sensor platform."""

    elk = hass.data['elkm1']['connection']
    config = hass.data['elkm1']['config']

    def create_devices(elements, element_type, class_):
        for element in elements:
            if config[element_type]['included'][element._index]:
                show = config[element_type]['shown'][element._index]
                devices.append(class_(element, elk, hass, show))

    devices = []
    create_devices([elk.panel], 'panel', ElkPanel)
    create_devices(elk.zones, 'zone', ElkZone)
    create_devices(elk.keypads, 'keypad', ElkKeypad)
    create_devices(elk.thermostats, 'thermostat', ElkThermostat)
    create_devices(elk.counters, 'counter', ElkCounter)
    create_devices(elk.settings, 'setting', ElkSetting)
    async_add_devices(devices, True)
    return True

class ElkSensorBase(Entity):
    """Sensor devices on the Elk."""
    def __init__(self, element, elk, hass, show_override):
        self._elk = elk
        self._element = element
        self._hass = hass
        self._show_override = show_override
        self._state = None
        self._element.add_callback(self._element_callback)
        self.entity_id = 'sensor.elkm1_' + self._element.default_name('_').lower()

    @property
    def name(self):
        """Name of the sensor."""
        return self._element.name

    @property
    def state(self):
        """The state of the sensor."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Don't poll this device."""
        return False

    @property
    def hidden(self):
        """Return the name of the sensor."""
        return False # Debug!!!
        if self._show_override is None:
            return self._hidden
        return not self._show_override

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        return self._element.as_dict()

    @callback
    def _element_callback(self, attribute, value):
        """Callback handler from the Elk."""
        pass

    def _temperature_to_state(self, temperature, undefined_temperature):
        if temperature > undefined_temperature:
            self._state = temperature
            self._hidden = False
        else:
            self._state = STATE_UNKNOWN
            self._hidden = True

    @asyncio.coroutine
    def async_update(self):
        pass

class ElkPanel(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:home"

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        return {
            'elkm1_version': self._element.elkm1_version,
            'xep_version': self._element.xep_version,
            'remote_programming_status': ElkRPStatus(
                self._element.remote_programming_status).name.lower(),
            'real_time_clock': self._element.real_time_clock,
        }

    @callback
    def _element_callback(self, attribute, value):
        if self._elk.is_connected():
            self._state = 'Paused' if self._element.remote_programming_status \
                else 'Normal'
        else:
            self._state = 'Disconnected'
        self.async_schedule_update_ha_state(True)

class ElkKeypad(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)
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
        attrs = {}
        attrs['last_user'] = self._element.last_user + 1
        attrs['last_user_name'] = self._elk.users[self._element.last_user].name \
            if self._element.last_user >= 0 else ""
        attrs['last_user_time'] = self._last_user_time
        attrs['temperature'] = self._element.temperature
        attrs['area'] = self._element.area
        return attrs

    @callback
    def _element_callback(self, attribute, value):
        self._temperature_to_state(self._element.temperature, -40)
        if attribute == 'last_user':
            self._last_user_time = time.time()

        self.async_schedule_update_ha_state(True)

class ElkZone(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)
        self._ICONS = {
            ZoneType.FIRE_ALARM.value : 'fire',
            ZoneType.FIRE_VERIFIED.value : 'fire',
            ZoneType.FIRE_SUPERVISORY.value : 'fire',
            ZoneType.KEYFOB.value : 'key',
            ZoneType.NON_ALARM.value : 'alarm-off',
            ZoneType.MEDICAL_ALARM.value : 'medical-bag',
            ZoneType.POLICE_ALARM.value : 'alarm-light',
            ZoneType.POLICE_NO_INDICATION.value : 'alarm-light',
            ZoneType.KEY_MOMENTARY_ARM_DISARM.value : 'power',
            ZoneType.KEY_MOMENTARY_ARM_AWAY.value : 'power',
            ZoneType.KEY_MOMENTARY_ARM_STAY.value : 'power',
            ZoneType.KEY_MOMENTARY_DISARM.value : 'power',
            ZoneType.KEY_ON_OFF.value : 'toggle-switch',
            ZoneType.MUTE_AUDIBLES.value : 'volume-mute',
            ZoneType.POWER_SUPERVISORY.value : 'power-plug',
            ZoneType.TEMPERATURE.value : 'thermometer-lines',
            ZoneType.ANALOG_ZONE.value : 'speedometer',
            ZoneType.PHONE_KEY.value : 'phone-classic',
            ZoneType.INTERCOM_KEY.value : 'deskphone'
        }

        self._unit_of_measure = None
        if self._element.definition == ZoneType.TEMPERATURE.value:
            self._unit_of_measure = self.hass.config.units.temperature_unit
        elif self._element.definition == ZoneType.ANALOG_ZONE.value:
            self._unit_of_measure = 'volts'

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:' + self._ICONS.get(self._element.definition, 'alarm-bell')

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = {}
        attrs['physical_status'] = ZonePhysicalStatus(
            self._element.physical_status).name.lower()
        attrs['logical_status'] = ZoneLogicalStatus(
            self._element.logical_status).name.lower()
        attrs['definition'] = ZoneType(
            self._element.definition).name.lower()
        attrs['area'] = self._element.area + 1
        attrs['bypassed'] = self._element.bypassed
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
        return self._unit_of_measure

    @callback
    def _element_callback(self, attribute, value):
        self._hidden = False
        if self._element.definition == ZoneType.TEMPERATURE.value:
            self._temperature_to_state(self._element.temperature, -60)
        elif self._element.definition == ZoneType.ANALOG_ZONE.value:
            self._state = self._element.voltage
        else:
            self._state = pretty_const(ZoneLogicalStatus(
                self._element.logical_status).name)
            self._hidden = self._element.definition == ZoneType.DISABLED.value

        self.async_schedule_update_ha_state(True)

class ElkThermostat(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)

    @property
    def temperature_unit(self):
        """The temperature scale."""
        return TEMP_FAHRENHEIT

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:thermometer-lines'

    @callback
    def _element_callback(self, attribute, value):
        self._temperature_to_state(self._element.current_temp, 0)
        self.async_schedule_update_ha_state(True)

class ElkCounter(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:numeric'

    @callback
    def _element_callback(self, attribute, value):
        state = self._element.value
        self.async_schedule_update_ha_state(True)

class ElkSetting(ElkSensorBase, Entity):
    def __init__(self, device, elk, hass, show_override):
        ElkSensorBase.__init__(self, device, elk, hass, show_override)

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:numeric'

    @callback
    def _element_callback(self, attribute, value):
        state = self._element.value
        self.async_schedule_update_ha_state(True)

    @property
    def device_state_attributes(self):
        """Attributes of the sensor."""
        attrs = {}
        attrs['value_format'] = SettingFormat(
            self._element.value_format).name.lower()
        attrs['value'] = self._element.value
        return attrs

class OldElkSensorDevice(Entity):
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        event_data = {
            'type': '',
            'area': 0,
            'number': self._element._index + 1,
            'name': self._element.name,
            'attribute': attribute
        }
        event_send = False
        if self._type in [self.TYPE_KEYPAD, self.TYPE_ZONE,
                          self.TYPE_ZONE_TEMP, self.TYPE_ZONE_VOLTAGE]:
            event_data['area'] = self._area
        if self._type in [self.TYPE_ZONE, self.TYPE_ZONE_TEMP,
                          self.TYPE_ZONE_VOLTAGE]:
            event_data['type'] = 'zone'
        if self._type == self.TYPE_KEYPAD:
            event_data['type'] = 'keypad'

        if attribute == 'last_user':
            event_send = True
            self._last_user_at = time.time()
            self._last_user_num = value + 1
            self._last_user_name = self._element._elk.users[value].name
            event_data['user_at'] = self._last_user_at
            event_data['user_num'] = self._last_user_num,
            event_data['user_name'] = self._last_user_name
        if attribute == 'area':
            event_send = True
            self._area = self._element.area + 1
            event_data['area'] = self._area
        if event_send and self.hass and event_data['type'] != '':
            self.hass.bus.fire('elkm1_sensor_event', event_data)

    def async_update(self):
        if self._type in [self.TYPE_KEYPAD, self.TYPE_ZONE,
                          self.TYPE_ZONE_TEMP, self.TYPE_ZONE_VOLTAGE]:
            if self._element.area is not None and self._area is None:
                self._area = self._element.area + 1
                event_data = {
                    'type': '',
                    'area': self._area,
                    'number': self._element._index + 1,
                    'name': self._element.name,
                    'attribute': 'area'
                    }
                if self._type == self.TYPE_KEYPAD:
                    event_data['type'] = 'keypad'
                else:
                    event_data['type'] = 'zone'
                self.hass.bus.fire('elkm1_sensor_event', event_data)
