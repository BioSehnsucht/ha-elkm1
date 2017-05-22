"""
Support for Elk zones as sensors.
"""

import logging
from typing import Callable  # noqa

import homeassistant.components.elkm1 as elkm1
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
            _LOGGER.error('Examining Zone: ' + str(zone._number))
            if not ((zone._state == zone.STATE_UNCONFIGURED) and (zone._definition == zone.DEFINITION_DISABLED)):
                _LOGGER.error('Loading Elk Zone%s', zone.description())
                devices.append(ElkSensorDevice(zone))
            else:
                _LOGGER.error('Zone ' + str(zone._number) + ' is both unconfigured and disabled')

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

    def __init__(self, zone):
        """ Initialize zone sensor """
        self._zone = zone
        self._zone._update_callback = self.trigger_update
        self._name = 'Zone ' + str(zone._number)
        self._state = None

    def trigger_update(self):
        _LOGGER.error('Triggering auto update of ' + str(self._zone._number))
        self.schedule_update_ha_state()
    
    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name
    
    @property
    def state(self):
        """Return the state of the sensor"""
        _LOGGER.error('Zone updating : ' + str(self._zone._number))
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any"""
        return 'mdi:' + self.ICON[self._zone._definition]

    def update(self):
        """Get the latest data and update the state."""
        self._zone._pyelk.update()
        self._state = self._zone.status()

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            'Status' : self._zone.status(),
            'State' : self._zone.state(),
            'Alarm' : self._zone.alarm(),
            'Definition' : self._zone.definition(),
            'Friendly Name' : self._zone.description()
            }
    
