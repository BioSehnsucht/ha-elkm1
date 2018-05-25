"""Support for control of Elk-connected thermostats."""
import asyncio
import logging
from typing import Callable  # noqa

from homeassistant.helpers.typing import ConfigType

from homeassistant.components.climate import (
    STATE_IDLE, STATE_HEAT, STATE_COOL, STATE_AUTO, STATE_FAN_ONLY,
    ATTR_TEMPERATURE, ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH,
    ATTR_CURRENT_TEMPERATURE, PRECISION_WHOLE, ClimateDevice,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_TARGET_TEMPERATURE_HIGH,
    SUPPORT_TARGET_TEMPERATURE_LOW, SUPPORT_FAN_MODE,
    SUPPORT_OPERATION_MODE, SUPPORT_AUX_HEAT,
    )
from homeassistant.const import (
    TEMP_FAHRENHEIT, STATE_UNKNOWN, ATTR_TEMPERATURE, STATE_ON, STATE_OFF,
    ATTR_SUPPORTED_FEATURES
    )

from homeassistant.core import callback

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE_HIGH | SUPPORT_TARGET_TEMPERATURE_LOW |
                 SUPPORT_OPERATION_MODE | SUPPORT_FAN_MODE | SUPPORT_AUX_HEAT)

@asyncio.coroutine
def async_setup_platform(hass, config: ConfigType,
                   async_add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk climate platform."""
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
    from elkm1.thermostats import Thermostat as ElkThermostat
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather thermostats
        if elk_config['thermostat']['enabled']:
            for element in elk.thermostats:
                if element:
                    if elk_config['thermostat']['included'][element._index] is True:
                        discovery_info.append([element, elk_config['thermostat']['shown'][element._index]])
    # If discovery info was passed in, check if we want to include it
    #else:
    #    for node in discovery_info:
    #        if node.included is True and node.enabled is True:
    #            continue
    #        else:
    #            discovery_info.remove(node)
    # Add discovered devices
    element_name = ''
    for element in discovery_info:
        if isinstance(element[0], ElkThermostat):
            element_name = 'climate.' + 'elkm1_' + element[0].default_name('_')
        else:
            continue
        if element_name not in discovered_devices:
            _LOGGER.debug('Loading Elk %s: %s', element[0].__class__.__name__, element[0].name)
            device = ElkClimateDevice(element[0], elk, hass, element[1])
            discovered_devices[element_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', element[0].__class__.__name__, element[0].name)

    async_add_devices(devices, True)
    return True


class ElkClimateDevice(ClimateDevice):
    """Elk connected thermostat as Climate device."""

    def __init__(self, device, elk, hass, show_override):
        """Initialize device sensor."""
        self._type = None
        self._element = device
        self._hidden = self._element.is_default_name()
        self._name = 'elkm1_' + self._element.default_name('_').lower()
        self.entity_id = 'climate.' + self._name
        self._element.add_callback(self.trigger_update)
        self._show_override = show_override

    @callback
    def trigger_update(self, attribute, value):
        """Target of PyElk callback."""
        if self.hass:
            self.async_schedule_update_ha_state(True)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the Thermostat."""
        return self._element.name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self._element.current_temp is not None and self._element.current_temp > 0:
                return self._element.current_temp
        return None

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    @property
    def state(self):
        """Return the current state."""
        from elkm1.const import ThermostatSetting, ThermostatMode, ThermostatFan, ThermostatHold
        # We can't actually tell if it's actively running in any of these
        # modes, just what mode is set
        if (self._element.mode == ThermostatMode.OFF.value) and (
                self._element.fan == ThermostatFan.ON.value):
            return STATE_FAN_ONLY
        elif self._element.mode == ThermostatMode.OFF.value:
            return STATE_IDLE
        elif (self._element.mode == ThermostatMode.HEAT.value) or (
            self._element.mode == ThermostatMode.EMERGENCY_HEAT.value):
            return STATE_HEAT
        elif self._element.mode == ThermostatMode.COOL.value:
            return STATE_COOL
        elif self._element.mode == ThermostatMode.AUTO.value:
            return STATE_AUTO
        return STATE_UNKNOWN

    @property
    def precision(self):
        """Return the precision of the system."""
        return PRECISION_WHOLE

    @property
    def device_state_attributes(self):
        """Return the optional state attributes."""
        # TODO: convert RH from Elk to AH ?
        #if self.current_humidity > 0:
        #    humidity = self.current_humidity
        if self._show_override is None:
            hidden = self._hidden
        else:
            hidden = not self._show_override
        data = {
            'hidden': hidden,
            'temp_unit' : self.temperature_unit,
            }
        # Pending Omni2 support
        #if self._element.temp_outside is not None and self._element.temp_outside > -460:
        #    data['temp_outside'] = self._element.temp_outside
        #if self._element.temp_3 is not None and self._element.temp_3 > -460:
        #    data['temp_3'] = self._element.temp_3
        #if self._element.temp_4 is not None and self._element.temp_4 > -460:
        #    data['temp_4'] = self._element.temp_4
        return data

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and update the state."""
        #if self._element.age() > 5:
        #    # Only poll device if last update was more than 5 seconds ago
        #    self.request_temp()
        self._hidden = self._element.is_default_name()
        return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement to display."""
        return self.temperature_unit

    @property
    def current_humidity(self):
        """Return the current humidity."""
        # FIXME: Should this be converted from RH to AH?
        if self._element.humidity is not None and self._element.humidity > 0:
            return self._element.humidity
        return STATE_UNKNOWN

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        from elkm1.const import ThermostatMode
        return self._element.mode == ThermostatMode.EMERGENCY_HEAT.value

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        from elkm1.const import ThermostatMode
        if (self._element.mode == ThermostatMode.HEAT.value) or (
            self._element.mode == ThermostatMode.EMERGENCY_HEAT.value):
            return self._element.heat_setpoint
        if self._element.mode == ThermostatMode.COOL.value:
            return self._element.cool_setpoint
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        return self._element.cool_setpoint

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        return self._element.heat_setpoint

    @property
    def min_temp(self):
        """Return the minimum temp supported."""
        return 1

    @property
    def max_temp(self):
        """Return the maximum temp supported."""
        return 99

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self.state

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return [
            STATE_IDLE,
            STATE_HEAT,
            STATE_COOL,
            STATE_AUTO,
            STATE_FAN_ONLY,
        ]

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        from elkm1.const import ThermostatFan
        if self._element.fan == ThermostatFan.AUTO.value:
            return STATE_AUTO
        elif self._element.fan == ThermostatFan.ON.value:
            return STATE_ON
        return STATE_UNKNOWN

    def set_operation_mode(self, operation_mode):
        """Set mode."""
        from elkm1.const import ThermostatMode, ThermostatSetting, ThermostatFan
        if operation_mode == STATE_IDLE:
            self._element.set(ThermostatSetting.MODE.value, ThermostatMode.OFF.value)
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)
        elif operation_mode == STATE_HEAT:
            self._element.set(ThermostatSetting.MODE.value, ThermostatMode.HEAT.value)
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)
        elif operation_mode == STATE_COOL:
            self._element.set(ThermostatSetting.MODE.value, ThermostatMode.COOL.value)
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)
        elif operation_mode == STATE_AUTO:
            self._element.set(ThermostatSetting.MODE.value, ThermostatMode.AUTO.value)
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)
        elif operation_mode == STATE_FAN_ONLY:
            self._element.set(ThermostatSetting.MODE.value, ThermostatMode.OFF.value)
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.ON.value)

    def turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        from elkm1.const import ThermostatMode, ThermostatSetting, ThermostatFan
        self._element.set(ThermostatSetting.MODE.value, ThermostatMode.EMERGENCY_HEAT.value)
        self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)

    def turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        from elkm1.const import ThermostatMode, ThermostatSetting, ThermostatFan
        self._element.set(ThermostatSetting.MODE.value, ThermostatMode.HEAT.value)
        self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return [
            STATE_AUTO,
            STATE_ON,
        ]

    def set_fan_mode(self, fan):
        """Set new target fan mode."""
        from elkm1.const import ThermostatSetting, ThermostatFan
        if fan == STATE_AUTO:
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.AUTO.value)
        elif fan == STATE_ON:
            self._element.set(ThermostatSetting.FAN.value, ThermostatFan.ON.value)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        from elkm1.const import ThermostatMode, ThermostatSetting
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if low_temp is not None:
            low_temp = round(low_temp)
            self._element.set(ThermostatSetting.HEAT_SETPOINT.value, low_temp)
        if high_temp is not None:
            high_temp = round(high_temp)
            self._element.set(ThermostatSetting.COOL_SETPOINT.value, high_temp)

    #def request_temp(self):
    #    """Request temperature."""
    #    self._element.request_temp()
