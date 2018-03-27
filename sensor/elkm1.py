"""Support for Elk zones as sensors."""

import logging
from typing import Callable  # noqa

from homeassistant.const import (TEMP_FAHRENHEIT, STATE_UNKNOWN)

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.typing import ConfigType

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk sensor platform."""
    elk = hass.data['PyElk']['connection']
    elk_config = hass.data['PyElk']['config']
    discovered_devices = hass.data['PyElk']['discovered_devices']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False
    devices = []
    from PyElk.Zone import Zone as ElkZone
    from PyElk.Thermostat import Thermostat as ElkThermostat
    from PyElk.Keypad import Keypad as ElkKeypad
    from PyElk.Counter import Counter as ElkCounter
    from PyElk.Setting import Setting as ElkSetting
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather zones
        for node in elk.ZONES:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
        # Gather Keypads
        for node in elk.KEYPADS:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
        # Gather Thermostats
        for node in elk.THERMOSTATS:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
        # Gather Counters
        for node in elk.COUNTERS:
            if node:
                if node.included is True and node.enabled is True:
                    discovery_info.append(node)
        # Gather Settings
        for node in elk.SETTINGS:
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
        if isinstance(node, ElkZone) or isinstance(node, ElkKeypad) or\
        isinstance(node, ElkThermostat) or isinstance(node, ElkCounter) or\
        isinstance(node, ElkSetting):
            node_name = 'sensor.' + ElkSensorDevice.entity_name(node)[0]
            if node_name not in discovered_devices:
                _LOGGER.debug('Loading Elk %s: %s', node.classname, node.description_pretty())
                device = ElkSensorDevice(node)
                discovered_devices[node_name] = device
                devices.append(device)
            else:
                _LOGGER.debug('Skipping already loaded Elk %s: %s', node.classname, node.description_pretty())
        else:
            continue

    add_devices(devices, True)
    return True


class ElkSensorDevice(Entity):
    """Elk device as Sensor."""

    TYPE_UNDEFINED = 0
    #TYPE_SYSTEM = 1
    TYPE_ZONE = 2
    TYPE_ZONE_TEMP = 3
    TYPE_ZONE_VOLTAGE = 4
    TYPE_KEYPAD_TEMP = 5
    TYPE_THERMOSTAT_TEMP = 6
    TYPE_COUNTER = 7
    TYPE_SETTING = 8

    @classmethod
    def entity_name(cls, device):
        from PyElk import Elk as ElkSystem
        from PyElk.Zone import Zone as ElkZone
        from PyElk.Thermostat import Thermostat as ElkThermostat
        from PyElk.Keypad import Keypad as ElkKeypad
        from PyElk.Counter import Counter as ElkCounter
        from PyElk.Setting import Setting as ElkSetting
        padding = 3
        name = ''
        type = None
        #if isinstance(self._device, ElkSystem):
        #    # Elk System
        #    self._name = 'elk_system'
        #    self._type = TYPE_SYSTEM
        #    padding = 0
        if isinstance(device, ElkZone):
            # If our device is a Zone, what kind?
            name = 'elk_zone_'
            if device.definition == ElkZone.DEFINITION_TEMPERATURE:
                # Temperature Zone
                type = cls.TYPE_ZONE_TEMP
                name = 'elk_temp_z_'
            elif device.definition == ElkZone.DEFINITION_ANALOG_ZONE:
                # Analog voltage Zone
                type = cls.TYPE_ZONE_VOLTAGE
                name = 'elk_analog_z_'
            else:
                # Any other kind of Zone
                type = cls.TYPE_ZONE
        if isinstance(device, ElkKeypad):
            # Keypad temp sensor zone
            type = cls.TYPE_KEYPAD_TEMP
            name = 'elk_temp_k_'
            padding = 2
        if isinstance(device, ElkThermostat):
            # Thermostat temp sensor
            type = cls.TYPE_THERMOSTAT_TEMP
            name = 'elk_temp_t_'
            padding = 2
        if isinstance(device, ElkCounter):
            # Counter sensor
            type = cls.TYPE_COUNTER
            name = 'elk_counter_'
            padding = 2
        if isinstance(device, ElkSetting):
            # Setting sensor
            type = cls.TYPE_SETTING
            name = 'elk_setting_'
            padding = 2
        if padding > 0:
            name = name + format(device.number, '0' + str(padding))

        return name, type

    def __init__(self, device):
        """Initialize device sensor."""
        from PyElk import Elk as ElkSystem
        from PyElk.Zone import Zone as ElkZone
        from PyElk.Thermostat import Thermostat as ElkThermostat
        from PyElk.Keypad import Keypad as ElkKeypad
        from PyElk.Counter import Counter as ElkCounter
        from PyElk.Setting import Setting as ElkSetting
        self._type = None
        self._hidden = True
        self._device = device

        self._name, self._type = ElkSensorDevice.entity_name(device)
        self.entity_id = 'sensor.' + self._name
        self._state = None
        if hasattr(self._device, '_temp_enabled'):
            self._hidden = not self._device.temp_enabled
        else:
            self._hidden = not self._device.enabled
        self._icon = {
            0: '',
            ElkZone.DEFINITION_BURGLAR_1: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_2: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_PERIMETER_INSTANT: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_INTERIOR: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_INTERIOR_FOLLOWER: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_INTERIOR_NIGHT: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_INTERIOR_NIGHT_DELAY: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_24_HOUR: 'alarm-bell',
            ElkZone.DEFINITION_BURGLAR_BOX_TAMPER: 'alarm-bell',
            ElkZone.DEFINITION_FIRE_ALARM: 'fire',
            ElkZone.DEFINITION_FIRE_VERIFIED: 'fire',
            ElkZone.DEFINITION_FIRE_SUPERVISORY: 'fire',
            ElkZone.DEFINITION_AUX_ALARM_1: 'alarm-bell',
            ElkZone.DEFINITION_AUX_ALARM_2: 'alarm-bell',
            ElkZone.DEFINITION_KEYFOB: 'key',
            ElkZone.DEFINITION_NON_ALARM: 'alarm-off',
            ElkZone.DEFINITION_CARBON_MONOXIDE: 'alarm-bell',
            ElkZone.DEFINITION_EMERGENCY_ALARM: 'alarm-bell',
            ElkZone.DEFINITION_FREEZE_ALARM: 'alarm-bell',
            ElkZone.DEFINITION_GAS_ALARM: 'alarm-bell',
            ElkZone.DEFINITION_HEAT_ALARM: 'alarm-bell',
            ElkZone.DEFINITION_MEDICAL_ALARM: 'medical-bag',
            ElkZone.DEFINITION_POLICE_ALARM: 'alarm-light',
            ElkZone.DEFINITION_POLICE_NO_INDICATION: 'alarm-light',
            ElkZone.DEFINITION_WATER_ALARM: 'alarm-bell',
            ElkZone.DEFINITION_KEY_MOMENTARY_ARM_DISARM: 'power',
            ElkZone.DEFINITION_KEY_MOMENTARY_ARM_AWAY: 'power',
            ElkZone.DEFINITION_KEY_MOMENTARY_ARM_STAY: 'power',
            ElkZone.DEFINITION_KEY_MOMENTARY_DISARM: 'power',
            ElkZone.DEFINITION_KEY_ON_OFF: 'toggle-switch',
            ElkZone.DEFINITION_MUTE_AUDIBLES: 'volume-mute',
            ElkZone.DEFINITION_POWER_SUPERVISORY: 'power-plug',
            ElkZone.DEFINITION_TEMPERATURE: 'thermometer-lines',
            ElkZone.DEFINITION_ANALOG_ZONE: 'speedometer',
            ElkZone.DEFINITION_PHONE_KEY: 'phone-classic',
            ElkZone.DEFINITION_INTERCOM_KEY: 'deskphone'
            }
        self._definition_temperature = ElkZone.DEFINITION_TEMPERATURE
        self._device.callback_add(self.trigger_update)
        self.update()

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def name(self):
        """Return the name of the sensor."""
        friendly_name = self._device.description_pretty()
        # Adjust friendly name as applicable
        if (self._type == self.TYPE_KEYPAD_TEMP) or (
                self._type == self.TYPE_THERMOSTAT_TEMP):
            friendly_name = friendly_name + ' Temp'
        return friendly_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Unit of measurement, if applicable."""
        if (self._type == self.TYPE_ZONE_TEMP) or (
                self._type == self.TYPE_KEYPAD_TEMP) or (
                    self._type == self.TYPE_THERMOSTAT_TEMP):
            return self.temperature_unit
        elif self._type == self.TYPE_ZONE_VOLTAGE:
            # Analog voltage
            return 'volts'
        else:
            # No UOM for other sensors
            return None

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if (self._type == self.TYPE_ZONE_TEMP) or (
                self._type == self.TYPE_KEYPAD_TEMP) or (
                    self._type == self.TYPE_THERMOSTAT_TEMP):
            return 'mdi:' + self._icon[self._definition_temperature]
        if (self._type == self.TYPE_ZONE) or (
                self._type == self.TYPE_ZONE_VOLTAGE):
            return 'mdi:' + self._icon[self._device.definition]
        if self._type == self.TYPE_COUNTER:
            return 'mdi:numeric'
        if self._type == self.TYPE_SETTING:
            return 'mdi:numeric'
        return None

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {
            'hidden': self._hidden,
            }
        # If we're some kind of Zone, add Zone attributes
        if (self._type == self.TYPE_ZONE) or (
                self._type == self.TYPE_ZONE_TEMP)\
                or (self._type == self.TYPE_ZONE_VOLTAGE):
            attributes['Status'] = self._device.status_pretty()
            attributes['State'] = self._device.state_pretty()
            attributes['Alarm'] = self._device.alarm_pretty()
            attributes['Definition'] = self._device.definition_pretty()
        # If necessary, hide
        # TODO : Use custom state card or in some other way make use of
        #        input_number / etc
        if (self._type == self.TYPE_COUNTER) or (
                self._type == self.TYPE_SETTING):
            attributes['hidden'] = True
        return attributes

    def trigger_update(self, node):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of device ' + str(
            self._device.number))
        self.schedule_update_ha_state(True)

    def update(self):
        """Get the latest data and update the state."""
        if hasattr(self._device, '_temp_enabled'):
            self._hidden = not self._device.temp_enabled
        else:
            self._hidden = not self._device.enabled
        # Set state according to device type
        state = None
        if self._type == self.TYPE_ZONE:
            state = self._device.status_pretty()
        if (self._type == self.TYPE_ZONE_TEMP) or (
                self._type == self.TYPE_KEYPAD_TEMP) or (
                    self._type == self.TYPE_THERMOSTAT_TEMP):
            if self._device.temp > -40:
                state = self._device.temp
        if self._type == self.TYPE_ZONE_VOLTAGE:
            state = self._device.voltage
        if (self._type == self.TYPE_COUNTER) or (
                self._type == self.TYPE_SETTING):
            state = self._device.status
        if state is not None:
            self._state = state
        else:
            self._state = STATE_UNKNOWN
