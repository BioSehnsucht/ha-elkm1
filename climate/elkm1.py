"""Support for control of Elk-connected thermostats."""

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

DEPENDENCIES = ['elkm1']

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE_HIGH | SUPPORT_TARGET_TEMPERATURE_LOW |
                 SUPPORT_OPERATION_MODE | SUPPORT_FAN_MODE | SUPPORT_AUX_HEAT)

def setup_platform(hass, config: ConfigType,
                   add_devices: Callable[[list], None], discovery_info=[]):
    """Setup the Elk climate platform."""
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
    from PyElk.Thermostat import Thermostat as ElkThermostat
    # If no discovery info was passed in, discover automatically
    if len(discovery_info) == 0:
        # Gather areas
        for node in elk.THERMOSTATS:
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
        if isinstance(node, ElkThermostat):
            node_name = 'climate.' + 'elk_thermostat_' + format(node.number, '02')
        else:
            continue
        if node_name not in discovered_devices:
            _LOGGER.debug('Loading Elk %s: %s', node.classname, node.description_pretty())
            device = ElkClimateDevice(node)
            discovered_devices[node_name] = device
            devices.append(device)
        else:
            _LOGGER.debug('Skipping already loaded Elk %s: %s', node.classname, node.description_pretty())

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
        self.entity_id = 'climate.' + self._name
        self._device.callback_add(self.trigger_update)

    def trigger_update(self, node):
        """Target of PyElk callback."""
        _LOGGER.debug('Triggering auto update of device ' + str(
            self._device.number))
        self._hidden = not self._device.enabled
        self.schedule_update_ha_state(True)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the Thermostat."""
        return self._device.description_pretty()

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self._device.temp is not None and self._device.temp > -460:
                return self._device.temp
        return None

    @property
    def should_poll(self) -> bool:
        """Return whether this device should be polled."""
        return False

    @property
    def state(self):
        """Return the current state."""
        # We can't actually tell if it's actively running in any of these
        # modes, just what mode is set
        if (self._device.mode == self._device.MODE_OFF) and (
                self._device.fan == self._device.FAN_ON):
            return STATE_FAN_ONLY
        elif self._device.mode == self._device.MODE_OFF:
            return STATE_IDLE
        elif (self._device.mode == self._device.MODE_HEAT) or (
            self._device.mode == self._device.MODE_HEAT_EMERGENCY):
            return STATE_HEAT
        elif self._device.mode == self._device.MODE_COOL:
            return STATE_COOL
        elif self._device.mode == self._device.MODE_AUTO:
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
        data = {
            'hidden': self._hidden,
            'temp_unit' : self.temperature_unit,
            }
        if self._device.temp_outside is not None and self._device.temp_outside > -460:
            data['temp_outside'] = self._device.temp_outside
        if self._device.temp_3 is not None and self._device.temp_3 > -460:
            data['temp_3'] = self._device.temp_3
        if self._device.temp_4 is not None and self._device.temp_4 > -460:
            data['temp_4'] = self._device.temp_4
        return data

    def update(self):
        """Get the latest data and update the state."""
        if self._device.age() > 5:
            # Only poll device if last update was more than 5 seconds ago
            self.request_temp()
        return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement to display."""
        return self.temperature_unit

    @property
    def current_humidity(self):
        """Return the current humidity."""
        # FIXME: Should this be converted from RH to AH?
        if self._device.humidity is not None and self._device.humidity > 0:
            return self._device.humidity
        return STATE_UNKNOWN

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        return self._device.mode == self._device.MODE_HEAT_EMERGENCY

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if (self._device.mode == self._device.MODE_HEAT) or (
            self._device.mode == self._device.MODE_HEAT_EMERGENCY):
            return self._device.setpoint_heat
        if self._device.mode == self._device.MODE_COOL:
            return self._device.setpoint_cool
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
        if self._device.fan == self._device.FAN_AUTO:
            return STATE_AUTO
        elif self._device.fan == self._device.FAN_ON:
            return STATE_ON
        return STATE_UNKNOWN

    def set_operation_mode(self, operation_mode):
        """Set mode."""
        if operation_mode == STATE_IDLE:
            self._device.set_mode(self._device.MODE_OFF)
            self._device.set_fan(self._device.FAN_AUTO)
        elif operation_mode == STATE_HEAT:
            self._device.set_mode(self._device.MODE_HEAT)
            self._device.set_fan(self._device.FAN_AUTO)
        elif operation_mode == STATE_COOL:
            self._device.set_mode(self._device.MODE_COOL)
            self._device.set_fan(self._device.FAN_AUTO)
        elif operation_mode == STATE_AUTO:
            self._device.set_mode(self._device.MODE_AUTO)
            self._device.set_fan(self._device.FAN_AUTO)
        elif operation_mode == STATE_FAN_ONLY:
            self._device.set_mode(self._device.MODE_OFF)
            self._device.set_fan(self._device.FAN_ON)

    def turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        self._device.set_mode(self._device.MODE_HEAT_EMERGENCY)
        self._device.set_fan(self._device.FAN_AUTO)

    def turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        self.set_operation_mode(STATE_HEAT)

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return [
            STATE_AUTO,
            STATE_ON,
        ]

    def set_fan_mode(self, fan):
        """Set new target fan mode."""
        if fan == STATE_AUTO:
            self._device.set_fan(self._device.FAN_AUTO)
        elif fan == STATE_ON:
            self._device.set_fan(self._device.FAN_ON)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if low_temp is not None:
            low_temp = round(low_temp)
            self._device.set_setpoint_heat(low_temp)
        if high_temp is not None:
            high_temp = round(high_temp)
            self._device.set_setpoint_cool(high_temp)

    def request_temp(self):
        """Request temperature."""
        self._device.request_temp()
