"""Support for Elk zones as sensors."""
import asyncio
import logging
import time
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
                   async_add_devices: Callable[[list], None], discovery_info=[]):
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
    from elkm1.panel import Panel as ElkPanel

    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather panel
        discovery_info.append(elk.panel)
        # Gather zones
        if elk_config['zone']['enabled']:
            for element in elk.zones:
                if element:
                    if elk_config['zone']['included'][element._index] is True:
                        discovery_info.append(element)
        # Gather Keypads
        if elk_config['keypad']['enabled']:
            for element in elk.keypads:
                if element:
                    if elk_config['keypad']['included'][element._index] is True:
                        discovery_info.append(element)
        # Gather Thermostats
        if elk_config['thermostat']['enabled']:
            for element in elk.thermostats:
                if element:
                    if elk_config['thermostat']['included'][element._index] is True:
                        discovery_info.append(element)
        # Gather Counters
        if elk_config['counter']['enabled']:
            for element in elk.counters:
                if element:
                    if elk_config['counter']['included'][element._index] is True:
                        discovery_info.append(element)
        # Gather Settings
        if elk_config['setting']['enabled']:
            for element in elk.settings:
                if element:
                    if elk_config['setting']['included'][element._index] is True:
                        discovery_info.append(element)
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for element in discovery_info:
    #        if element.included is True and element.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(element)
    # Add discovered devices
    element_name = ''
    for element in discovery_info:
        if isinstance(element, ElkZone) or isinstance(element, ElkKeypad) or\
        isinstance(element, ElkThermostat) or isinstance(element, ElkCounter) or\
        isinstance(element, ElkSetting) or isinstance(element, ElkPanel):
            element_name = 'sensor.' + 'elkm1_' + element.default_name('_')
            if element_name not in discovered_devices:
                _LOGGER.debug('Loading Elk %s: %s', element.__class__.__name__, element.name)
                device = ElkSensorDevice(element)
                discovered_devices[element_name] = device
                devices.append(device)
            else:
                _LOGGER.debug('Skipping already loaded Elk %s: %s', element.__class__.__name__, element.name)
        else:
            continue

    async_add_devices(devices, True)
    return True


class ElkSensorDevice(Entity):
    """Elk device as Sensor."""

    TYPE_UNDEFINED = 0
    TYPE_PANEL = 1
    TYPE_ZONE = 2
    TYPE_ZONE_TEMP = 3
    TYPE_ZONE_VOLTAGE = 4
    TYPE_KEYPAD = 5
    TYPE_THERMOSTAT = 6
    TYPE_COUNTER = 7
    TYPE_SETTING = 8

    def __init__(self, device):
        """Initialize device sensor."""
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        from elkm1.zones import Zone as ElkZone
        from elkm1.thermostats import Thermostat as ElkThermostat
        from elkm1.keypads import Keypad as ElkKeypad
        from elkm1.counters import Counter as ElkCounter
        from elkm1.settings import Setting as ElkSetting
        from elkm1.panel import Panel as ElkPanel
        self._type = None
        self._hidden = True
        self._element = device
        self._last_user = None
        self._last_user_at = 0

        self._name = 'elkm1_' + self._element.default_name('_').lower()
        if isinstance(device, ElkZone):
            # If our device is a Zone, what kind?
            if device.definition == ZoneType.TEMPERATURE.value:
                # Temperature Zone
                self._type = self.TYPE_ZONE_TEMP
            elif device.definition == ZoneType.ANALOG_ZONE.value:
                # Analog voltage Zone
                self._type = self.TYPE_ZONE_VOLTAGE
            else:
                # Any other kind of Zone
                self._type = self.TYPE_ZONE
        if isinstance(device, ElkKeypad):
            # Keypad sensor
            self._type = self.TYPE_KEYPAD
        if isinstance(device, ElkThermostat):
            # Thermostat sensor
            self._type = self.TYPE_THERMOSTAT
        if isinstance(device, ElkCounter):
            # Counter sensor
            self._type = self.TYPE_COUNTER
        if isinstance(device, ElkSetting):
            # Setting sensor
            self._type = self.TYPE_SETTING
        if isinstance(device, ElkPanel):
            # Panel sensor
            self._type = self.TYPE_PANEL
        self.entity_id = 'sensor.' + self._name
        self._state = None
        #if hasattr(self._element, '_temp_enabled'):
        #    self._hidden = not self._element.temp_enabled
        #else:
        #    self._hidden = not self._element.enabled
        self._icon = {
            ZoneType.DISABLED.value : '',
            ZoneType.BURLAR_ENTRY_EXIT_1.value : 'alarm-bell',
            ZoneType.BURLAR_ENTRY_EXIT_2.value : 'alarm-bell',
            ZoneType.BURGLAR_PERIMETER_INSTANT.value : 'alarm-bell',
            ZoneType.BURGLAR_INTERIOR.value : 'alarm-bell',
            ZoneType.BURGLAR_INTERIOR_FOLLOWER.value : 'alarm-bell',
            ZoneType.BURGLAR_INTERIOR_NIGHT.value : 'alarm-bell',
            ZoneType.BURGLAR_INTERIOR_NIGHT_DELAY.value : 'alarm-bell',
            ZoneType.BURGLAR24_HOUR.value : 'alarm-bell',
            ZoneType.BURGLAR_BOX_TAMPER.value : 'alarm-bell',
            ZoneType.FIRE_ALARM.value : 'fire',
            ZoneType.FIRE_VERIFIED.value : 'fire',
            ZoneType.FIRE_SUPERVISORY.value : 'fire',
            ZoneType.AUX_ALARM_1.value : 'alarm-bell',
            ZoneType.AUX_ALARM_2.value : 'alarm-bell',
            ZoneType.KEYFOB.value : 'key',
            ZoneType.NON_ALARM.value : 'alarm-off',
            ZoneType.CARBON_MONOXIDE.value : 'alarm-bell',
            ZoneType.EMERGENCY_ALARM.value : 'alarm-bell',
            ZoneType.FREEZE_ALARM.value : 'alarm-bell',
            ZoneType.GAS_ALARM.value : 'alarm-bell',
            ZoneType.HEAT_ALARM.value : 'alarm-bell',
            ZoneType.MEDICAL_ALARM.value : 'medical-bag',
            ZoneType.POLICE_ALARM.value : 'alarm-light',
            ZoneType.POLICE_NO_INDICATION.value : 'alarm-light',
            ZoneType.WATER_ALARM.value : 'alarm-bell',
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
        self._definition_temperature = ZoneType.TEMPERATURE.value
        self._element.add_callback(self.trigger_update)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def name(self):
        """Return the name of the sensor."""
        friendly_name = self._element.name
        ## Adjust friendly name as applicable
        #if (self._type == self.TYPE_KEYPAD) or (
        #        self._type == self.TYPE_THERMOSTAT):
        #    friendly_name = friendly_name + ' Temp'
        return friendly_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Unit of measurement, if applicable."""
        if (self._type == self.TYPE_ZONE_TEMP) or (
                self._type == self.TYPE_KEYPAD) or (
                    self._type == self.TYPE_THERMOSTAT):
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
        if self._type in [self.TYPE_ZONE_TEMP, self.TYPE_KEYPAD, self.TYPE_THERMOSTAT]:
            return 'mdi:' + self._icon[self._definition_temperature]
        if self._type in [self.TYPE_ZONE, self.TYPE_ZONE_VOLTAGE]:
            return 'mdi:' + self._icon[self._element.definition]
        if self._type in [self.TYPE_COUNTER, self.TYPE_SETTING]:
            return 'mdi:numeric'
        if self._type == self.TYPE_PANEL:
            return None
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
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus, SettingFormat, ElkRPStatus
        from elkm1.util import pretty_const
        attributes = {
    #        'hidden': self._hidden,
            }
    #    # If we're some kind of Zone, add Zone attributes
        if self._type == self.TYPE_ZONE:
            attributes['Physical Status'] = pretty_const(ZonePhysicalStatus(self._element.physical_status).name)
    #        attributes['State'] = self._element.state_pretty()
    #        attributes['Alarm'] = self._element.alarm_pretty()
            attributes['Definition'] = pretty_const(ZoneType(self._element.definition).name)
    #    # If necessary, hide
    #    # TODO : Use custom state card or in some other way make use of
    #    #        input_number / etc
    #    if (self._type == self.TYPE_COUNTER) or (
    #            self._type == self.TYPE_SETTING):
    #        attributes['hidden'] = True
        if self._type in [self.TYPE_KEYPAD, self.TYPE_ZONE, self.TYPE_ZONE_TEMP, self.TYPE_ZONE_VOLTAGE]:
            if self._element.area is not None:
                attributes['Area'] = self._element.area + 1
        if self._type == self.TYPE_KEYPAD:
            if self._element.last_user:
                attributes['Last User'] = self._element.last_user + 1
            if self._last_user_at:
                attributes['Last User At'] = self._last_user_at
        if self._type == self.TYPE_SETTING:
            if self._element.value_format:
                attributes['Value Format'] = pretty_const(SettingFormat(self._element.value_format).name)
        if self._type == self.TYPE_PANEL:
            if self._element.elkm1_version:
                attributes['Elk M1 Version'] = self._element.elkm1_version
            if self._element.elkm1_version:
                attributes['Elk M1XEP Version'] = self._element.elkm1_version
            if self._element.real_time_clock:
                attributes['Real Time Clock'] = self._element.real_time_clock
            if self._element.remote_programming_status is not None:
                attributes['ElkRP'] = pretty_const(ElkRPStatus(self._element.remote_programming_status).name)
        return attributes

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        if attribute == 'last_user':
            self._last_user_at = time.time()
        if self.hass:
            self.async_schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        from elkm1.const import ZoneType, ZoneLogicalStatus, ZonePhysicalStatus
        from elkm1.util import pretty_const
        #if hasattr(self._element, '_temp_enabled'):
        #    self._hidden = not self._element.temp_enabled
        #else:
        #    self._hidden = not self._element.enabled
        # Set state according to device type
        state = None
        if self._type == self.TYPE_ZONE:
            state = pretty_const(ZoneLogicalStatus(self._element.logical_status).name)
            self._hidden = self._element.definition == ZoneType.DISABLED.value
        if self._type == self.TYPE_ZONE_TEMP:
            if self._element.temperature and self._element.temperature > -60:
                state = self._element.temperature
                self._hidden = False
            else:
                self._hidden = True
        if self._type == self.TYPE_KEYPAD:
            if self._element.temperature and self._element.temperature > -40:
                state = self._element.temperature
                self._hidden = False
            else:
                self._hidden = True
        if self._type == self.TYPE_THERMOSTAT:
            if self._element.current_temp and self._element.current_temp > 0:
                state = self._element.current_temp
                self._hidden = False
            else:
                self._hidden = True
        if self._type == self.TYPE_ZONE_VOLTAGE:
            state = self._element.voltage
            self._hidden = False
        if self._type in [self.TYPE_COUNTER, self.TYPE_SETTING]:
            state = self._element.value
        if self._type == self.TYPE_PANEL:
            self._hidden = False
            if self._element._elk._conn is not None:
                if self._element.remote_programming_status:
                    state = 'Paused'
                else:
                    state = 'Normal'
            else:
                state = 'Disconnected'
        if state is not None:
            self._state = state
        else:
            self._state = STATE_UNKNOWN