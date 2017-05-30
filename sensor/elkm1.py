"""
Support for Elk zones as sensors.
"""

import logging
from typing import Callable  # noqa

import PyElk

from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, STATE_OFF, STATE_ON)

from homeassistant.helpers.entity import Entity

from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

elk = None

def setup_platform(hass, config: ConfigType, add_devices: Callable[[list], None], discovery_info=None):
    """Setup the Elk sensor platform."""
    elk = hass.data['PyElk']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False

    devices = []

    for zone in elk.ZONES:
        if zone:
            _LOGGER.debug('Loading Elk Zone: %s', zone.description())
            device = ElkSensorDevice(zone)
            device._hidden = True
            if not ((zone._state == zone.STATE_UNCONFIGURED) and (zone._definition == zone.DEFINITION_DISABLED)):
                device._hidden = False
            devices.append(device)

    for keypad in elk.KEYPADS:
        if keypad:
            _LOGGER.debug('Loading Elk Keypad: %s', keypad.description())
            device = ElkSensorDevice(keypad)
            """Lowest reported temp is -40F, if it's reporting -40F we assume
               it's not actually returning a valid temperature and hide it"""
            if (keypad._temp > -40):
                device._hidden = False
            devices.append(device)

    add_devices(devices, True)
    return True


class ElkSensorDevice(Entity):
    """ Elk Zone as Sensor """

    ICON = {
            0 : '',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_1 : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_2 : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_PERIMETER_INSTANT : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_INTERIOR : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_INTERIOR_FOLLOWER : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_INTERIOR_NIGHT : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_INTERIOR_NIGHT_DELAY : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_24_HOUR : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_BURGLAR_BOX_TAMPER : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_FIRE_ALARM : 'fire',
            PyElk.Zone.Zone.DEFINITION_FIRE_VERIFIED : 'fire',
            PyElk.Zone.Zone.DEFINITION_FIRE_SUPERVISORY : 'fire',
            PyElk.Zone.Zone.DEFINITION_AUX_ALARM_1 : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_AUX_ALARM_2 : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_KEYFOB : 'key',
            PyElk.Zone.Zone.DEFINITION_NON_ALARM : 'alarm-off',
            PyElk.Zone.Zone.DEFINITION_CARBON_MONOXIDE : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_EMERGENCY_ALARM : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_FREEZE_ALARM : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_GAS_ALARM : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_HEAT_ALARM : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_MEDICAL_ALARM : 'medical-bag',
            PyElk.Zone.Zone.DEFINITION_POLICE_ALARM : 'alarm-light',
            PyElk.Zone.Zone.DEFINITION_POLICE_NO_INDICATION : 'alarm-light',
            PyElk.Zone.Zone.DEFINITION_WATER_ALARM : 'alarm-bell',
            PyElk.Zone.Zone.DEFINITION_KEY_MOMENTARY_ARM_DISARM : 'power',
            PyElk.Zone.Zone.DEFINITION_KEY_MOMENTARY_ARM_AWAY : 'power',
            PyElk.Zone.Zone.DEFINITION_KEY_MOMENTARY_ARM_STAY : 'power',
            PyElk.Zone.Zone.DEFINITION_KEY_MOMENTARY_DISARM : 'power',
            PyElk.Zone.Zone.DEFINITION_KEY_ON_OFF : 'toggle-switch',
            PyElk.Zone.Zone.DEFINITION_MUTE_AUDIBLES : 'volume-mute',
            PyElk.Zone.Zone.DEFINITION_POWER_SUPERVISORY : 'power-plug',
            PyElk.Zone.Zone.DEFINITION_TEMPERATURE : 'thermometer-lines',
            PyElk.Zone.Zone.DEFINITION_ANALOG_ZONE : 'speedometer',
            PyElk.Zone.Zone.DEFINITION_PHONE_KEY : 'phone-classic',
            PyElk.Zone.Zone.DEFINITION_INTERCOM_KEY : 'deskphone'
            }

    TYPE_UNDEFINED = 0
    TYPE_ZONE = 1
    TYPE_ZONE_TEMP = 2
    TYPE_ZONE_VOLTAGE = 3
    TYPE_KEYPAD_TEMP = 4

    _type = None
    _hidden = True
    _temp = False

    def __init__(self, device):
        """ Initialize device sensor """
        self._device = device
        self._device._update_callback = self.trigger_update
        if (isinstance(self._device, PyElk.Zone.Zone)):
            self._name = 'elk_zone_'
            if self._device._definition == PyElk.Zone.Zone.DEFINITION_TEMPERATURE:
                self._type = self.TYPE_ZONE_TEMP
                self._name = 'elk_temp_z_'
            elif self._device._definition == PyElk.Zone.Zone.DEFINITION_ANALOG_ZONE:
                self._type = self.TYPE_ZONE_VOLTAGE
                self._name = 'elk_analog_z_'
            else:
                self._type = self.TYPE_ZONE
        if (isinstance(self._device, PyElk.Keypad.Keypad)):
            self._type = self.TYPE_KEYPAD_TEMP
            self._name = 'elk_temp_k_'
        self._name = self._name + str(device._number)
        self._state = None

    def trigger_update(self):
        _LOGGER.debug('Triggering auto update of device ' + str(self._device._number))
        self.schedule_update_ha_state(True)
    
    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name
    
    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        if (self._type == self.TYPE_ZONE_TEMP) or (self._type == self.TYPE_KEYPAD_TEMP):
            return TEMP_FAHRENHEIT
        elif (self._type == self.TYPE_ZONE_VOLTAGE):
            return 'volts'
        elif (self._type == self.TYPE_ZONE):
            return None

    @property
    def icon(self):
        """Icon to use in the frontend, if any"""
        if (self._type == self.TYPE_ZONE) or (self._type == self.TYPE_ZONE_TEMP) or (self._type == self.TYPE_ZONE_VOLTAGE):
            return 'mdi:' + self.ICON[self._device._definition]
        elif self._type == self.TYPE_KEYPAD_TEMP:
            return 'mdi:' + self.ICON[PyElk.Zone.Zone.DEFINITION_TEMPERATURE]
        else:
            return None

    def update(self):
        """Get the latest data and update the state."""
        self._device._pyelk.update()
        if (self._type == self.TYPE_ZONE):
            self._state = self._device.status()
        elif (self._type == self.TYPE_ZONE_TEMP) or (self._type == self.TYPE_KEYPAD_TEMP):
            self._state = self._device._temp
        elif (self._type == self.TYPE_ZONE_VOLTAGE):
            self._state = self._device.voltage
    
    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {
                'hidden' : self._hidden,                
            }
        if (self._type == self.TYPE_ZONE) or (self._type == self.TYPE_ZONE_TEMP) or (self._type == self.TYPE_ZONE_VOLTAGE):
            attributes['Status'] = self._device.status()
            attributes['State'] = self._device.state()
            attributes['Alarm'] = self._device.alarm()
            attributes['Definition'] = self._device.definition()
            attributes['friendly_name'] = self._device.description()
        if self._type == self.TYPE_KEYPAD_TEMP:
            attributes['friendly_name'] = 'Keypad ' + str(self._device._number) + ' Temp'
        return attributes

