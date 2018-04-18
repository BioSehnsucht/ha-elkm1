"""Support for Elk zones as sensors."""
import asyncio
import logging
from typing import Callable  # noqa

from homeassistant.const import (TEMP_FAHRENHEIT, STATE_UNKNOWN)

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.typing import ConfigType

from homeassistant.core import callback

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk sensor platform."""
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
    from elkm1.zones import Zone as ElkZone
    from elkm1.thermostats import Thermostat as ElkThermostat
    from elkm1.keypads import Keypad as ElkKeypad
    from elkm1.counters import Counter as ElkCounter
    from elkm1.settings import Setting as ElkSetting
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather zones
        for element in elk.zones:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
        # Gather Keypads
        for element in elk.keypads:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
        # Gather Thermostats
        for element in elk.thermostats:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
        # Gather Counters
        for element in elk.counters:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
        # Gather Settings
        for element in elk.settings:
            if element:
                #if element.included is True and element.enabled is True:
                    discovery_info.append(element)
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for element in discovery_info:
    #        if element.included is True and element.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(element)
    # Add discovered devices
    for element in discovery_info:
        if isinstance(element, ElkZone) or isinstance(element, ElkKeypad) or\
        isinstance(element, ElkThermostat) or isinstance(element, ElkCounter) or\
        isinstance(element, ElkSetting):
            element_name = 'sensor.' + ElkSensorDevice.entity_name(element)[0]
            if element_name not in discovered_devices:
                _LOGGER.debug('Loading Elk %s: %s', element.__class__.__name__, element.name)
                device = ElkSensorDevice(element)
                discovered_devices[element_name] = device
                devices.append(device)
            else:
                _LOGGER.debug('Skipping already loaded Elk %s: %s', element.__class__.__name__, element.name)
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
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        from elkm1.zones import Zone as ElkZone
        from elkm1.thermostats import Thermostat as ElkThermostat
        from elkm1.keypads import Keypad as ElkKeypad
        from elkm1.counters import Counter as ElkCounter
        from elkm1.settings import Setting as ElkSetting
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
            if device.definition == ZoneType.Temperature:
                # Temperature Zone
                type = cls.TYPE_ZONE_TEMP
                name = 'elk_temp_z_'
            elif device.definition == ZoneType.AnalogZone:
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
            name = name + format(device.index + 1, '0' + str(padding))

        return name, type

    def __init__(self, device):
        """Initialize device sensor."""
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        from elkm1.zones import Zone as ElkZone
        from elkm1.thermostats import Thermostat as ElkThermostat
        from elkm1.keypads import Keypad as ElkKeypad
        from elkm1.counters import Counter as ElkCounter
        from elkm1.settings import Setting as ElkSetting
        self._type = None
        self._hidden = True
        self._element = device

        self._name, self._type = ElkSensorDevice.entity_name(device)
        self.entity_id = 'sensor.' + self._name
        self._state = None
        #if hasattr(self._element, '_temp_enabled'):
        #    self._hidden = not self._element.temp_enabled
        #else:
        #    self._hidden = not self._element.enabled
        self._icon = {
            ZoneType.Disabled.value : '',
            ZoneType.BurlarEntryExit1.value : 'alarm-bell',
            ZoneType.BurlarEntryExit2.value : 'alarm-bell',
            ZoneType.BurglarPerimeterInstant.value : 'alarm-bell',
            ZoneType.BurglarInterior.value : 'alarm-bell',
            ZoneType.BurglarInteriorFollower.value : 'alarm-bell',
            ZoneType.BurglarInteriorNight.value : 'alarm-bell',
            ZoneType.BurglarInteriorNightDelay.value : 'alarm-bell',
            ZoneType.Burglar24Hour.value : 'alarm-bell',
            ZoneType.BurglarBoxTamper.value : 'alarm-bell',
            ZoneType.FireAlarm.value : 'fire',
            ZoneType.FireVerified.value : 'fire',
            ZoneType.FireSupervisory.value : 'fire',
            ZoneType.AuxAlarm1.value : 'alarm-bell',
            ZoneType.AuxAlarm2.value : 'alarm-bell',
            ZoneType.KeyFob.value : 'key',
            ZoneType.NonAlarm.value : 'alarm-off',
            ZoneType.CarbonMonoxide.value : 'alarm-bell',
            ZoneType.EmergencyAlarm.value : 'alarm-bell',
            ZoneType.FreezeAlarm.value : 'alarm-bell',
            ZoneType.GasAlarm.value : 'alarm-bell',
            ZoneType.HeatAlarm.value : 'alarm-bell',
            ZoneType.MedicalAlarm.value : 'medical-bag',
            ZoneType.PoliceAlarm.value : 'alarm-light',
            ZoneType.PoliceNoIndication.value : 'alarm-light',
            ZoneType.WaterAlarm.value : 'alarm-bell',
            ZoneType.KeyMomentaryArmDisarm.value : 'power',
            ZoneType.KeyMomentaryArmAway.value : 'power',
            ZoneType.KeyMomentaryArmStay.value : 'power',
            ZoneType.KeyMomentaryDisarm.value : 'power',
            ZoneType.KeyOnOff.value : 'toggle-switch',
            ZoneType.MuteAudibles.value : 'volume-mute',
            ZoneType.PowerSupervisory.value : 'power-plug',
            ZoneType.Temperature.value : 'thermometer-lines',
            ZoneType.AnalogZone.value : 'speedometer',
            ZoneType.PhoneKey.value : 'phone-classic',
            ZoneType.IntercomKey.value : 'deskphone'
            }
        self._definition_temperature = ZoneType.Temperature.value
        self._element.add_callback(self.trigger_update)
        self.update()

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def name(self):
        """Return the name of the sensor."""
        friendly_name = self._element.name
        ## Adjust friendly name as applicable
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
            return 'mdi:' + self._icon[self._element.definition]
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
    def hidden(self):
        """Return the name of the sensor."""
        return self._hidden

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        attributes = {
    #        'hidden': self._hidden,
            }
    #    # If we're some kind of Zone, add Zone attributes
        if (self._type == self.TYPE_ZONE) or (
                self._type == self.TYPE_ZONE_TEMP)\
                or (self._type == self.TYPE_ZONE_VOLTAGE):
            attributes['Physical Status'] = ZonePhysicalStatus(self._element.physical_status).name
    #        attributes['State'] = self._element.state_pretty()
    #        attributes['Alarm'] = self._element.alarm_pretty()
            attributes['Definition'] = ZoneType(self._element.definition).name
    #    # If necessary, hide
    #    # TODO : Use custom state card or in some other way make use of
    #    #        input_number / etc
    #    if (self._type == self.TYPE_COUNTER) or (
    #            self._type == self.TYPE_SETTING):
    #        attributes['hidden'] = True
        if self._type == self.TYPE_SETTING:
            attributes['Value Format'] = self._element.value_format
        return attributes

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        #_LOGGER.debug('Triggering auto update of device ' + str(
        #    self._element.index))
        self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        #if hasattr(self._element, '_temp_enabled'):
        #    self._hidden = not self._element.temp_enabled
        #else:
        #    self._hidden = not self._element.enabled
        # Set state according to device type
        state = None
        if self._type == self.TYPE_ZONE:
            state = ZoneLogicalStatus(self._element.logical_status).name
            self._hidden = self._element.definition == ZoneType.Disabled.value
        if (self._type == self.TYPE_ZONE_TEMP) or (
             self._type == self.TYPE_KEYPAD_TEMP):
            if self._element.temperature and self._element.temperature > -40:
                state = self._element.temperature
                self._hidden = False
            else:
                self._hidden = True
        if self._type == self.TYPE_THERMOSTAT_TEMP:
            if self._element.current_temp and self._element.current_temp > 0:
                state = self._element.current_temp
                self._hidden = False
            else:
                self._hidden = True
        if self._type == self.TYPE_ZONE_VOLTAGE:
            state = self._element.voltage
        if (self._type == self.TYPE_COUNTER) or (
                self._type == self.TYPE_SETTING):
            state = self._element.value
        if state is not None:
            self._state = state
        else:
            self._state = STATE_UNKNOWN