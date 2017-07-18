"""
Support for control of Elk-connected thermostats.
"""

import logging
from typing import Callable  # noqa

from homeassistant.helpers.typing import ConfigType

from homeassistant.components.climate import STATE_IDLE, STATE_HEAT, STATE_COOL, STATE_AUTO,\
    STATE_FAN_ONLY, ATTR_TARGET_TEMP_LOW, ATTR_TARGET_TEMP_HIGH, ATTR_CURRENT_TEMPERATURE,\
    PRECISION_WHOLE, ClimateDevice
from homeassistant.util.temperature import convert
from homeassistant.const import TEMP_FAHRENHEIT, STATE_UNKNOWN, ATTR_TEMPERATURE

from PyElk.Thermostat import Thermostat

_LOGGER = logging.getLogger(__name__)

STATE_HEAT_EMERGENCY = 'heat_emergency'

def setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=None):
    """Setup the Elk climate platform."""
    elk = hass.data['PyElk']
    if elk is None:
        _LOGGER.error('Elk is None')
        return False
    if not elk.connected:
        _LOGGER.error('A connection has not been made to the Elk panel.')
        return False

    devices = []
    # Add all Thermostats
    for thermostat in elk.THERMOSTATS:
        if thermostat:
            if thermostat.included is True:
                _LOGGER.debug('Loading Elk Thermostat as Climate device: %s',
                              thermostat.description_pretty())
                device = ElkClimateDevice(thermostat)
                devices.append(device)
            else:
                _LOGGER.debug('Skipping excluded Elk Thermostat: %s',
                              thermostat.number)

    add_devices(devices, True)
    return True

class ElkClimateDevice(ClimateDevice):
    """Elk connected thermostat as Climate device."""
    def __init__(self, device):
        """Initialize device sensor."""
        self._type = None
        self._device = device
        self._hidden = not self._device.enabled
        self._name = 'elk_thermostat_' + format(device.number, '02')
        self._device.callback_add(self.trigger_update)

    def trigger_update(self):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of device ' + str(self._device.number))
        self.schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the Thermostat"""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device.temp

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def state(self):
        """Return the current state."""
        # We can't actually tell if it's actively running in any of these modes,
        # just what mode is set
        if (self._device.mode == Thermostat.MODE_OFF) and (self._device.fan == Thermostat.FAN_ON):
            return STATE_FAN_ONLY
        elif self._device.mode == Thermostat.MODE_OFF:
            return STATE_IDLE
        elif self._device.mode == Thermostat.MODE_HEAT:
            return STATE_HEAT
        elif self._device.mode == Thermostat.MODE_COOL:
            return STATE_COOL
        elif self._device.mode == Thermostat.MODE_AUTO:
            return STATE_AUTO
        elif self._device.mode == Thermostat.MODE_HEAT_EMERGENCY:
            return STATE_HEAT_EMERGENCY
        return STATE_UNKNOWN

    @property
    def precision(self):
        """Return the precision of the system."""
        return PRECISION_WHOLE

    @property
    def device_state_attributes(self):
        """Return the optional state attributes."""
        data = {
            ATTR_CURRENT_TEMPERATURE: self._convert_for_display(self._device.temp),
            'friendly_name': self._device.description_pretty(),
            'hidden': self._hidden,
            'operation': self.state,
            'fan': self.current_fan_mode,
            'mode': self.state
            }
        return data

    def update(self):
        """Get the latest data and update the state."""
        if self._device.age() > 5:
            # Only poll device if last update was more than 5 seconds ago
            self._device.request_temp()
        return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement to display."""
        return TEMP_FAHRENHEIT

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._device.humidity

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        return self._device.mode == Thermostat.MODE_HEAT_EMERGENCY

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        return self._device.setpoint_cool

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        return self._device.setpoint_heat

    @property
    def min_temp(self):
        return 1

    @property
    def max_temp(self):
        return 99

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        # We can't actually tell if it's actively running in any of these modes,
        # just what mode is set
        if (self._device.mode == Thermostat.MODE_OFF) and (self._device.fan == Thermostat.FAN_ON):
            return STATE_FAN_ONLY
        elif self._device.mode == Thermostat.MODE_OFF:
            return STATE_IDLE
        elif self._device.mode == Thermostat.MODE_HEAT:
            return STATE_HEAT
        elif self._device.mode == Thermostat.MODE_COOL:
            return STATE_COOL
        elif self._device.mode == Thermostat.MODE_AUTO:
            return STATE_AUTO
        elif self._device.mode == Thermostat.MODE_HEAT_EMERGENCY:
            return STATE_HEAT_EMERGENCY
        return STATE_UNKNOWN

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return [STATE_IDLE,
                STATE_HEAT,
                STATE_COOL,
                STATE_AUTO,
                STATE_HEAT_EMERGENCY,
                STATE_FAN_ONLY
               ]

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._device.fan

    def set_operation_mode(self, operation_mode):
        """Set mode."""
        if operation_mode == STATE_IDLE:
            self._device.set_mode(Thermostat.MODE_OFF)
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif operation_mode == STATE_HEAT:
            self._device.set_mode(Thermostat.MODE_HEAT)
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif operation_mode == STATE_COOL:
            self._device.set_mode(Thermostat.MODE_COOL)
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif operation_mode == STATE_AUTO:
            self._device.set_mode(Thermostat.MODE_AUTO)
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif operation_mode == STATE_HEAT_EMERGENCY:
            self._device.set_mode(Thermostat.MODE_HEAT_EMERGENCY)
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif operation_mode == STATE_FAN_ONLY:
            self._device.set_mode(Thermostat.MODE_OFF)
            self._device.set_fan(Thermostat.FAN_ON)

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return [STATE_AUTO,
                STATE_FAN_ONLY
               ]

    def set_fan_mode(self, fan):
        """Set new target fan mode."""
        if fan == STATE_AUTO:
            self._device.set_fan(Thermostat.FAN_AUTO)
        elif fan == STATE_FAN_ONLY:
            self._device.set_fan(Thermostat.FAN_ON)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._device.set_setpoint_heat(kwargs.get(ATTR_TARGET_TEMP_LOW))
        self._device.set_setpoint_cool(kwargs.get(ATTR_TARGET_TEMP_HIGH))
