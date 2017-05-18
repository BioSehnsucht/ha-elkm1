"""
Support the Elk M1 Gold, Elk M1 EZ8, etc alarm / integration panels

For configuration details ...
URL
"""
from collections import namedtuple
from collections import deque
import logging
import serial
import serial.threaded
import time
import sys
import traceback

DOMAIN = "elkm1"
REQUIREMENTS = []

ELK = None

_LOGGER = logging.getLogger(__name__)

SUPPORTED_DOMAINS = ['binary_sensor', 'sensor']

"""Set up the Elk M1 platform."""

code = '1234'
#host = 'loop://'
host = 'socket://1.2.3.4:2101'

"""
Internal PyElk
"""

class ElkEvent(object):
    ELK_EVENT_INSTALLER_CONNECT = 'RP' # ELKRP Connected
    ELK_EVENT_INSTALLER_EXIT = 'IE' # Installer Program Mode Exited

    ELK_EVENT_TROUBLE_STATUS = 'ss' # Request System Trouble Status
    ELK_EVENT_TROUBLE_STATUS_REPLY = 'SS' # Reply System Trouble Status

    ELK_EVENT_DISARM = 'a0' # Disarm
    ELK_EVENT_ARM_AWAY = 'a1' # Arm to Away
    ELK_EVENT_ARM_STAY = 'a2' # Arm to Stay (Home)
    ELK_EVENT_ARM_STAY_INSTANT = 'a3' # Arm to Stay Instant
    ELK_EVENT_ARM_NIGHT = 'a4' # Arm to Night
    ELK_EVENT_ARM_NIGHT_INSTANT = 'a5' # Arm to Night Instant
    ELK_EVENT_ARM_VACATION = 'a6' # Arm to Vacation
    ELK_EVENT_ARM_NEXT_AWAY = 'a7' # Arm, Step to Next Away mode
    ELK_EVENT_ARM_NEXT_STAY = 'a8' # Arm, Step to Next Stay mode
    ELK_EVENT_ARM_FORCE_AWAY = 'a9' # Force Arm to Away Mode
    ELK_EVENT_ARM_FORCE_STAY = 'a:' # Force Arm to Stay Mode
    ELK_EVENT_ARMING_STATUS = 'as' # Arming Status Request
    ELK_EVENT_ARMING_STATUS_REPORT = 'AS' # Reply Arming Status Report Data
    ELK_EVENT_ALARM_ZONE = 'az' # Alarm By Zone Request
    ELK_EVENT_ALARM_ZONE_REPORT = 'AZ' # Reply Alarm By zone Report Data
    ELK_EVENT_ALARM_MEMORY = 'AM' # Alarm Memory Update

    ELK_EVENT_ENTRY_EXIT_TIMER = 'EE' # Entry / Exit Timer Data

    ELK_EVENT_USER_CODE_ENTERED = 'IC' # Send Valid User Number And Invalid
                                       # User Code

    ELK_EVENT_KEYPAD_AREA = 'ka' # Request Keypad Area Assignments
    ELK_EVENT_KEYPAD_AREA_REPLY = 'KA' # Reply With Keypad Areas
    ELK_EVENT_KEYPAD_STATUS = 'kc' # Request Keypad Function Key Illumination
    ELK_EVENT_KEYPAD_STATUS_REPORT = 'KC' # Keypad KeyChange Update
                                   # Status
    ELK_EVENT_KEYPAD_PRESS = 'kf' # Request Keypad Function Key Press
    ELK_EVENT_KEYPAD_PRESS_REPLY = 'KF' # Reply Keypad Function Key Press
    ELK_EVENT_KEYPAD_TEXT = 'dm' # Display Text on LCD Screen

    ELK_EVENT_TEMP_ALL = 'lw' # Request Temperature Data (All Zones / Keypads)
    ELK_EVENT_TEMP_ALL_REPLY = 'LW' # Reply Temperature Data (All)
    ELK_EVENT_TEMP_REQUEST = 'st' # Request Temperature format
    ELK_EVENT_TEMP_REQUEST_REPLY = 'ST' # Reply With Requested Temperature

    ELK_EVENT_SPEAK_WORD = 'sw' # Speak Word at Voice/Siren Output
    ELK_EVENT_SPEAK_PHRASE = 'sp' # Speak Phrase at Voice/Siren Output

    ELK_EVENT_TASK_ACTIVATE = 'tn' # Task Activation
    ELK_EVENT_TASK_UPDATE = 'TC' # Tasks Change Update

    ELK_EVENT_VERSION = 'vn' # Request M1 Version Number
    ELK_EVENT_VERSION_REPLY = 'VN' # Request M1 Version Reply

    ELK_EVENT_OUTPUT_UPDATE = 'CC' # Output Change Update
    ELK_EVENT_OUTPUT_OFF = 'cf' # Control Output Off
    ELK_EVENT_OUTPUT_ON = 'cn' # Control Output On
    ELK_EVENT_OUTPUT_STATUS = 'cs' # Control Output Status Request
    ELK_EVENT_OUTPUT_STATUS_REPORT = 'CS' # Control Output Status Report
    ELK_EVENT_OUTPUT_TOGGLE = 'ct' # Control Output Toggle

    ELK_EVENT_ZONE_UPDATE = 'ZC' # Zone Change Update
    ELK_EVENT_ZONE_BYPASS = 'zb' # Zone Bypass Request
    ELK_EVENT_ZONE_BYPASS_REPLY = 'ZB' # Reply With Bypassed Zone State
    ELK_EVENT_ZONE_PARTITION = 'zp' # Zone Partition Request
    ELK_EVENT_ZONE_PARTITION_REPORT = 'ZP' # Zone Partition Report
    ELK_EVENT_ZONE_STATUS = 'zs' # Zone Status Request
    ELK_EVENT_ZONE_STATUS_REPORT = 'ZS' # Zone Status Report
    ELK_EVENT_ZONE_DEFINITION = 'zd' # Request Zone Definition
    ELK_EVENT_ZONE_DEFINITION_REPLY = 'ZD' # Reply Zone Definition Data
    ELK_EVENT_ZONE_TRIGGER = 'zt' # Zone Trigger
    ELK_EVENT_ZONE_VOLTAGE = 'zv' # Request Zone Voltage
    ELK_EVENT_ZONE_VOLTAGE_REPLY = 'ZV' # Reply Zone Analog Voltage Data

    ELK_EVENT_VALUE_READ = 'cr' # Read Custom Value
    ELK_EVENT_VALUE_READ_ALL = 'cp' # Read ALL Custom Values
    ELK_EVENT_VALUE_READ_REPLY = 'CR' # Reply With Custom Value
    ELK_EVENT_VALUE_READ_ALL_REPLY = 'CP' # Reply With ALL Custom Values
    ELK_EVENT_VALUE_WRITE = 'cw' # Write Custom Value

    ELK_EVENT_COUNTER_READ = 'cv' # Read Counter Value
    ELK_EVENT_COUNTER_WRITE = 'cx' # Write Counter Value
    ELK_EVENT_COUNTER_REPLY = 'CV' # Reply With Counter Value Format

    ELK_EVENT_DESCRIPTION = 'sd' # Request ASCII String Text Descriptions
    ELK_EVENT_DESCRIPTION_REPLY = 'SD' # Reply with ASCII String Text
                                       # Description
    ELK_EVENT_ETHERNET_TEST = 'XK' # Elk to M1XEP test ping / time heartbeat

    DESCRIPTION_ZONE_NAME = 0
    DESCRIPTION_AREA_NAME = 1
    DESCRIPTION_USER_NAME = 2
    DESCRIPTION_KEYPAD_NAME = 3
    DESCRIPTION_OUTPUT_NAME = 4
    DESCRIPTION_TASK_NAME = 5
    DESCRIPTION_TELEPHONE_NAME = 6
    DESCRIPTION_LIGHT_NAME = 7
    DESCRIPTION_ALARM_DURATION_NAME = 8
    DESCRIPTION_CUSTOM_SETTING = 9
    DESCRIPTION_COUNTER_NAME = 10
    DESCRIPTION_THERMOSTAT_NAME = 11
    DESCRIPTION_FUNCTION_KEY_1_NAME = 12
    DESCRIPTION_FUNCTION_KEY_2_NAME = 13
    DESCRIPTION_FUNCTION_KEY_3_NAME = 14
    DESCRIPTION_FUNCTION_KEY_4_NAME = 15
    DESCRIPTION_FUNCTION_KEY_5_NAME = 16
    DESCRIPTION_FUNCTION_KEY_6_NAME = 17

    elk_auto_map = [
            ELK_EVENT_INSTALLER_EXIT,
            ELK_EVENT_ALARM_MEMORY,
            ELK_EVENT_ENTRY_EXIT_TIMER,
            ELK_EVENT_USER_CODE_ENTERED,
            ELK_EVENT_TASK_UPDATE,
            ELK_EVENT_OUTPUT_UPDATE,
            ELK_EVENT_ZONE_UPDATE,
            ELK_EVENT_KEYPAD_STATUS_REPORT,
            ELK_EVENT_ETHERNET_TEST
            ]

    elk_events_map = {
        'RP' : ELK_EVENT_INSTALLER_CONNECT,
        'IE' : ELK_EVENT_INSTALLER_EXIT,
        'ss' : ELK_EVENT_TROUBLE_STATUS,
        'SS' : ELK_EVENT_TROUBLE_STATUS_REPLY,
        'a0' : ELK_EVENT_DISARM,
        'a1' : ELK_EVENT_ARM_AWAY,
        'a2' : ELK_EVENT_ARM_STAY,
        'a3' : ELK_EVENT_ARM_STAY_INSTANT,
        'a4' : ELK_EVENT_ARM_NIGHT,
        'a5' : ELK_EVENT_ARM_NIGHT_INSTANT,
        'a6' : ELK_EVENT_ARM_VACATION,
        'a7' : ELK_EVENT_ARM_NEXT_AWAY,
        'a8' : ELK_EVENT_ARM_NEXT_STAY,
        'a9' : ELK_EVENT_ARM_FORCE_AWAY,
        'a:' : ELK_EVENT_ARM_FORCE_STAY,
        'as' : ELK_EVENT_ARMING_STATUS,
        'AS' : ELK_EVENT_ARMING_STATUS_REPORT,
        'az' : ELK_EVENT_ALARM_ZONE,
        'AZ' : ELK_EVENT_ALARM_ZONE_REPORT,
        'AM' : ELK_EVENT_ALARM_MEMORY,
        'EE' : ELK_EVENT_ENTRY_EXIT_TIMER,
        'IC' : ELK_EVENT_USER_CODE_ENTERED,
        'ka' : ELK_EVENT_KEYPAD_AREA,
        'KA' : ELK_EVENT_KEYPAD_AREA_REPLY,
        'kc' : ELK_EVENT_KEYPAD_STATUS,
        'KC' : ELK_EVENT_KEYPAD_STATUS_REPORT,
        'kf' : ELK_EVENT_KEYPAD_PRESS,
        'KF' : ELK_EVENT_KEYPAD_PRESS_REPLY,
        'dm' : ELK_EVENT_KEYPAD_TEXT,
        'lw' : ELK_EVENT_TEMP_ALL,
        'LW' : ELK_EVENT_TEMP_ALL_REPLY,
        'st' : ELK_EVENT_TEMP_REQUEST,
        'ST' : ELK_EVENT_TEMP_REQUEST_REPLY,
        'sw' : ELK_EVENT_SPEAK_WORD,
        'sp' : ELK_EVENT_SPEAK_PHRASE,
        'tn' : ELK_EVENT_TASK_ACTIVATE,
        'TC' : ELK_EVENT_TASK_UPDATE,
        'vn' : ELK_EVENT_VERSION,
        'VN' : ELK_EVENT_VERSION_REPLY,
        'CC' : ELK_EVENT_OUTPUT_UPDATE,
        'cf' : ELK_EVENT_OUTPUT_OFF,
        'cn' : ELK_EVENT_OUTPUT_ON,
        'cs' : ELK_EVENT_OUTPUT_STATUS,
        'CS' : ELK_EVENT_OUTPUT_STATUS_REPORT,
        'ct' : ELK_EVENT_OUTPUT_TOGGLE,
        'ZC' : ELK_EVENT_ZONE_UPDATE,
        'zb' : ELK_EVENT_ZONE_BYPASS,
        'ZB' : ELK_EVENT_ZONE_BYPASS_REPLY,
        'zp' : ELK_EVENT_ZONE_PARTITION,
        'ZP' : ELK_EVENT_ZONE_PARTITION_REPORT,
        'zs' : ELK_EVENT_ZONE_STATUS,
        'ZS' : ELK_EVENT_ZONE_STATUS_REPORT,
        'zd' : ELK_EVENT_ZONE_DEFINITION,
        'ZD' : ELK_EVENT_ZONE_DEFINITION_REPLY,
        'zt' : ELK_EVENT_ZONE_TRIGGER,
        'zv' : ELK_EVENT_ZONE_VOLTAGE,
        'ZV' : ELK_EVENT_ZONE_VOLTAGE_REPLY,
        'cr' : ELK_EVENT_VALUE_READ,
        'cp' : ELK_EVENT_VALUE_READ_ALL,
        'CR' : ELK_EVENT_VALUE_READ_REPLY,
        'CP' : ELK_EVENT_VALUE_READ_ALL_REPLY,
        'cw' : ELK_EVENT_VALUE_WRITE,
        'cv' : ELK_EVENT_COUNTER_READ,
        'cx' : ELK_EVENT_COUNTER_WRITE,
        'CV' : ELK_EVENT_COUNTER_REPLY,
        'sd' : ELK_EVENT_DESCRIPTION,
        'SD' : ELK_EVENT_DESCRIPTION_REPLY
    }



    _len = 0
    _type = ''
    _data = []
    _data_str = ''
    _reserved = '00'
    _checksum = ''
    _time = 0

    def __init__(self, pyelk = None):
        _time = time.time()
        self._pyelk = pyelk

    def age(self):
        return time.time() - self._time

    def dump(self):
        sys.stdout.write('Event Len: {}\n'.format(repr(self._len)))
        sys.stdout.write('Event Type: {}\n'.format(repr(self._type)))
        sys.stdout.write('Event Data: {}\n'.format(repr(self._data)))
        sys.stdout.write('Event Checksum: {}\n'.format(repr(self._checksum)))
        sys.stdout.write('Event Computed Checksum: {}\n'.format(self.checksum_generate()))

    def parse(self, data):
        sys.stdout.write('Parsing: {}\n'.format(repr(data)))
        self._len = data[:2]
        self._type = data[2:4]
        if (len(data) > 8):
            self._data_str = data[4:-4]
            self._data = list(self._data_str)
        else:
            self._data_str = ''
            self._data = []
        self._reserved = data[-4:-2]
        self._checksum = data[-2:]
        
    def to_string(self):
        event_str = ''
        if (self._data_str == ''):
            self._data_str = ''.join(self._data)
        event_str += self._type 
        event_str += self._data_str
        event_str += self._reserved
        self._len = format(len(event_str) + 2, '02x')
        self._checksum = self.checksum_generate(self._len + event_str)
        return self._len + event_str + self._checksum

    def checksum_generate(self, data = False):
        if (data == False):
            data = self._len + self._type + self._data_str + self._reserved
        CC = 0
        for c in data:
            CC += ord(c)
        CC = CC % 256
        CC = CC ^ 255
        CC += 1
        return format(CC, '02x').upper()

    def checksum_check(self):
        calculated = self.checksum_generate()
        if (calculated == self._checksum):
            return True
        else:
            return False

    def data_dehex(self, fake = False):
        data = [] 
        for i in range(0,len(self._data)):
            data.append(str(ord(self._data[i]) - ord('0')))
            if (not fake) and (ord(data[i]) > 9):
                data[i] = str(ord(data[i]) - 7)
        return data

    def data_str_dehex(self, fake = False):
        return ''.join(self.data_dehex(fake))
    
class ElkZone(object):
    STATE_UNCONFIGURED = 0
    STATE_OPEN = 1
    STATE_EOL = 2
    STATE_SHORT = 3

    STATUS_NORMAL = 0
    STATUS_TROUBLE = 1
    STATUS_VIOLATED = 2
    STATUS_BYPASSED = 3

    DEFINITION_DISABLED = 0
    DEFINITION_BURGLAR_1 = 1
    DEFINITION_BURGLAR_2 = 2
    DEFINITION_BURGLAR_PERIMETER_INSTANT = 3
    DEFINITION_BURGLAR_INTERIOR = 4
    DEFINITION_BURGLAR_INTERIOR_FOLLOWER = 5
    DEFINITION_BURGLAR_INTERIOR_NIGHT = 6
    DEFINITION_BURGLAR_INTERIOR_NIGHT_DELAY = 7
    DEFINITION_BURGLAR_24_HOUR = 8
    DEFINITION_BURGLAR_BOX_TAMPER = 9
    DEFINITION_FIRE_ALARM = 10
    DEFINITION_FIRE_VERIFIED = 11
    DEFINITION_FIRE_SUPERVISORY = 12
    DEFINITION_AUX_ALARM_1 = 13
    DEFINITION_AUX_ALARM_2 = 14
    DEFINITION_KEYFOB = 15
    DEFINITION_NON_ALARM = 16
    DEFINITION_CARBON_MONOXIDE = 17
    DEFINITION_EMERGENCY_ALARM = 18
    DEFINITION_FREEZE_ALARM = 19
    DEFINITION_GAS_ALARM = 20
    DEFINITION_HEAT_ALARM = 21
    DEFINITION_MEDICAL_ALARM = 22
    DEFINITION_POLICE_ALARM = 23
    DEFINITION_POLICE_NO_INDICATION = 24
    DEFINITION_WATER_ALARM = 25
    DEFINITION_KEY_MOMENTARY_ARM_DISARM = 26
    DEFINITION_KEY_MOMENTARY_ARM_AWAY = 27
    DEFINITION_KEY_MOMENTARY_ARM_STAY = 28
    DEFINITION_KEY_MOMENTARY_DISARM = 29
    DEFINITION_KEY_ON_OFF = 30
    DEFINITION_MUTE_AUDIBLES = 31
    DEFINITION_POWER_SUPERVISORY = 32
    DEFINITION_TEMPERATURE = 33
    DEFINITION_ANALOG_ZONE = 34
    DEFINITION_PHONE_KEY = 35
    DEFINITION_INTERCOM_KEY = 36

    ALARM_DISABLED = 0
    ALARM_BURGLAR_1 = 1
    ALARM_BURGLAR_2 = 2
    ALARM_BURGLAR_PERIMETER_INSTANT = 3
    ALARM_BURGLAR_INTERIOR = 4
    ALARM_BURGLAR_INTERIOR_FOLLOWER = 5
    ALARM_BURGLAR_INTERIOR_NIGHT = 6
    ALARM_BURGLAR_INTERIOR_NIGHT_DELAY = 7
    ALARM_BURGLAR_24_HOUR = 8
    ALARM_BURGLAR_BOX_TAMPER = 9
    ALARM_FIRE_ALARM = 10
    ALARM_FIRE_VERIFIED = 11
    ALARM_FIRE_SUPERVISORY = 12
    ALARM_AUX_ALARM_1 = 13
    ALARM_AUX_ALARM_2 = 14
    ALARM_KEYFOB = 15
    ALARM_NON_ALARM = 16
    ALARM_CARBON_MONOXIDE = 17
    ALARM_EMERGENCY_ALARM = 18
    ALARM_FREEZE_ALARM = 19
    ALARM_GAS_ALARM = 20
    ALARM_HEAT_ALARM = 21
    ALARM_MEDICAL_ALARM = 22
    ALARM_POLICE_ALARM = 23
    ALARM_POLICE_NO_INDICATION = 24
    ALARM_WATER_ALARM = 25


    STATE_STR = {
        STATE_UNCONFIGURED : 'Unconfigured',
        STATE_OPEN : 'Open',
        STATE_EOL : 'EOL',
        STATE_SHORT : 'Short'
        }

    STATUS_STR = {
        STATUS_NORMAL : 'Normal',
        STATUS_TROUBLE : 'Trouble',
        STATUS_VIOLATED : 'Violated',
        STATUS_BYPASSED : 'Bypassed'
        }

    DEFINITION_STR = {
        DEFINITION_DISABLED : 'Disabled',
        DEFINITION_BURGLAR_1 : 'Burglar Entry/Exit 1',
        DEFINITION_BURGLAR_2 : 'Burglar Entry/Exit 2',
        DEFINITION_BURGLAR_PERIMETER_INSTANT : 'Burglar Perimeter Instant',
        DEFINITION_BURGLAR_INTERIOR : 'Burgler Interior',
        DEFINITION_BURGLAR_INTERIOR_FOLLOWER : 'Burgler Interior Follower',
        DEFINITION_BURGLAR_INTERIOR_NIGHT : 'Burgler Interior Night',
        DEFINITION_BURGLAR_INTERIOR_NIGHT_DELAY : 'Burglar Interior Night Delay',
        DEFINITION_BURGLAR_24_HOUR : 'Burglar 24 Hour',
        DEFINITION_BURGLAR_BOX_TAMPER : 'Burglar Box Tamper',
        DEFINITION_FIRE_ALARM : 'Fire Alarm',
        DEFINITION_FIRE_VERIFIED : 'Fire Verified',
        DEFINITION_FIRE_SUPERVISORY : 'Fire Supervisory',
        DEFINITION_AUX_ALARM_1 : 'Aux Alarm 1',
        DEFINITION_AUX_ALARM_2 : 'Aux Alarm 2',
        DEFINITION_KEYFOB : 'Keyfob',
        DEFINITION_NON_ALARM : 'Non Alarm',
        DEFINITION_CARBON_MONOXIDE : 'Carbon Monoxide',
        DEFINITION_EMERGENCY_ALARM : 'Emergency Alarm',
        DEFINITION_FREEZE_ALARM : 'Freeze Alarm',
        DEFINITION_GAS_ALARM : 'Gas Alarm',
        DEFINITION_HEAT_ALARM : 'Heat Alarm',
        DEFINITION_MEDICAL_ALARM : 'Medical Alarm',
        DEFINITION_POLICE_ALARM : 'Police Alarm',
        DEFINITION_POLICE_NO_INDICATION : 'Police No Indication',
        DEFINITION_WATER_ALARM : 'Water Alarm',
        DEFINITION_KEY_MOMENTARY_ARM_DISARM : 'Key Momentary Arm / Disarm',
        DEFINITION_KEY_MOMENTARY_ARM_AWAY : 'Key Momentary Arm Away',
        DEFINITION_KEY_MOMENTARY_ARM_STAY : 'Key Momentary Arm Stay',
        DEFINITION_KEY_MOMENTARY_DISARM : 'Key Momentary Disarm',
        DEFINITION_KEY_ON_OFF : 'Key On/Off',
        DEFINITION_MUTE_AUDIBLES : 'Mute Audibles',
        DEFINITION_POWER_SUPERVISORY : 'Power Supervisory',
        DEFINITION_TEMPERATURE : 'Temperature',
        DEFINITION_ANALOG_ZONE : 'Analog Zone',
        DEFINITION_PHONE_KEY : 'Phone Key',
        DEFINITION_INTERCOM_KEY : 'Intercom Key'
        }

    ALARM_STR = {
        ALARM_DISABLED : 'Disabled',
        ALARM_BURGLAR_1 : 'Burglar Entry/Exit 1',
        ALARM_BURGLAR_2 : 'Burglar Entry/Exit 2',
        ALARM_BURGLAR_PERIMETER_INSTANT : 'Burglar Perimeter Instant',
        ALARM_BURGLAR_INTERIOR : 'Burgler Interior',
        ALARM_BURGLAR_INTERIOR_FOLLOWER : 'Burgler Interior Follower',
        ALARM_BURGLAR_INTERIOR_NIGHT : 'Burgler Interior Night',
        ALARM_BURGLAR_INTERIOR_NIGHT_DELAY : 'Burglar Interior Night Delay',
        ALARM_BURGLAR_24_HOUR : 'Burglar 24 Hour',
        ALARM_BURGLAR_BOX_TAMPER : 'Burglar Box Tamper',
        ALARM_FIRE_ALARM : 'Fire Alarm',
        ALARM_FIRE_VERIFIED : 'Fire Verified',
        ALARM_FIRE_SUPERVISORY : 'Fire Supervisory',
        ALARM_AUX_ALARM_1 : 'Aux Alarm 1',
        ALARM_AUX_ALARM_2 : 'Aux Alarm 2',
        ALARM_KEYFOB : 'Keyfob',
        ALARM_NON_ALARM : 'Non Alarm',
        ALARM_CARBON_MONOXIDE : 'Carbon Monoxide',
        ALARM_EMERGENCY_ALARM : 'Emergency Alarm',
        ALARM_FREEZE_ALARM : 'Freeze Alarm',
        ALARM_GAS_ALARM : 'Gas Alarm',
        ALARM_HEAT_ALARM : 'Heat Alarm',
        ALARM_MEDICAL_ALARM : 'Medical Alarm',
        ALARM_POLICE_ALARM : 'Police Alarm',
        ALARM_POLICE_NO_INDICATION : 'Police No Indication',
        ALARM_WATER_ALARM : 'Water Alarm'
        }

    _state = 0
    _status = 0
    _definition = 0
    _alarm = 0
    _number = 0
    _description = ''
    _partition = 0
    _voltage = 0.0
    _updated_at = 0

    def __init__(self, pyelk = None):
        self._pyelk = pyelk

    def age(self):
        return time.time() - self._updated_at

    """
    ElkEvent.ELK_EVENT_ALARM_ZONE_REPORT
    """
    def unpack_event_alarm_zone(self, event):
        data = event.data_dehex(True)[self._number-1]
        if (self._alarm == data):
            return
        self._alarm = data
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ZONE_DEFINITION_REPLY
    """
    def unpack_event_zone_definition(self, event):
        data = event.data_dehex(True)[self._number-1]
        if (self._definition == data):
            return
        self._definition = data
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ZONE_PARTITION_REPORT
    """
    def unpack_event_zone_partition(self, event):
        data = event.data_dehex(True)[self._number-1]
        if (self._partition == data):
            return
        self._partition = data
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ZONE_VOLTAGE_REPLY
    """
    def unpack_event_zone_voltage(self, event):
        data = int(event._data_str[2:4]) / 10.0
        if (self._voltage == data):
            return
        self._voltage = data
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ZONE_STATUS_REPORT
    """
    def unpack_event_zone_status_report(self, event):
        data = int(event.data_dehex()[self._number-1])
        state = data & 0b11
        status = (data & 0b1100) >> 2
        if ((self._state == state) and (self._status == status)):
            return
        self._state = state
        self._status = status
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ZONE_UPDATE
    """
    def unpack_event_zone_update(self, event):
        data = int(event.data_dehex_str()[3:3])
        state = data & 0b11
        status = (data & 0b1100) >> 2
        if ((self._state == state) and (self._status == status)):
            return
        self._state = state
        self._status = status
        self._updated_at = event._time

    def state(self):
        return self.STATE_STR[self._state]

    def status(self):
        return self.STATUS_STR[self._status]

    def alarm(self):
        return self.ALARM_STR[self._alarm]

    def definition(self):
        return self.DEFINITION_STR[self._definition]

    def description(self):
        if (self._description == ''):
            return 'Zone ' + str(self._number)
        return self._description

    def dump(self):
        sys.stdout.write('Zone State: {}\n'.format(repr(self.state())))
        sys.stdout.write('Zone Status: {}\n'.format(repr(self.status())))
        sys.stdout.write('Zone Definition: {}\n'.format(repr(self.definition())))
        sys.stdout.write('Zone Description: {}\n'.format(repr(self.description())))


class ElkOutput(object):
    STATUS_OFF = 0
    STATUS_ON = 1

    STATUS_STR = {
        STATUS_OFF : 'Off',
        STATUS_ON : 'On'
    }

    _status = 0
    _number = 0
    _description = ''
    _updated_at = 0

    def __init__(self, pyelk = None):
        self._pyelk = pyelk

    """
    ElkEvent.ELK_EVENT_OUTPUT_STATUS_REPORT
    """
    def unpack_event_output_status_report(self, event):
        data = event.data_dehex()[self._number-1]
        if (self._status == data):
            return
        self._status = data
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_OUTPUT_UPDATE
    """
    def unpack_event_output_update(self, event):
        data = int(event.data_dehex()[3])
        if (self._status == data):
            return
        self._status = data
        self._updated_at = event._time

    def age(self):
        return time.time() - self._updated_at

    def status(self):
        return self.STATUS_STR[self._status]

    def description(self):
        if (self._description == ''):
            return 'Output ' + str(self._number)
        return self._description

    def dump(self):
        sys.stdout.write('Output Status: {}\n'.format(repr(self.status())))
        sys.stdout.write('Output Description: {}\n'.format(repr(self.description())))

class ElkArea(object):
    STATUS_DISARMED = 0
    STATUS_ARMED_AWAY = 1
    STATUS_ARMED_STAY = 2
    STATUS_ARMED_STAY_INSTANT = 3
    STATUS_ARMED_NIGHT = 4
    STATUS_ARMED_NIGHT_INSTANT = 5
    STATUS_ARMED_VACATION = 6

    STATUS_STR = {
        STATUS_DISARMED : 'Disarmed',
        STATUS_ARMED_AWAY : 'Armed Away',
        STATUS_ARMED_STAY : 'Armed Stay',
        STATUS_ARMED_STAY_INSTANT : 'Armed Stay Instant',
        STATUS_ARMED_NIGHT : 'Armed to Night',
        STATUS_ARMED_NIGHT_INSTANT : 'Armed to Night Instant',
        STATUS_ARMED_VACATION : 'Armed to Vacation'
    }

    ARM_UP_NOT_READY = 0
    ARM_UP_READY = 1
    ARM_UP_READY_VIOLATED_BYPASS = 2
    ARM_UP_ARMED_EXIT_TIMER = 3
    ARM_UP_ARMED = 4
    ARM_UP_FORCE_ARMED_VIOLATED = 5
    ARM_UP_ARMED_BYPASS = 6

    ARM_UP_STR = {
        ARM_UP_NOT_READY : 'Not Ready To Arm',
        ARM_UP_READY : 'Ready To Arm',
        ARM_UP_READY_VIOLATED_BYPASS : 'Ready To Arm, but a zone is violated and can be Force Armed',
        ARM_UP_ARMED_EXIT_TIMER : 'Armed with Exit Timer working',
        ARM_UP_ARMED : 'Armed Fully',
        ARM_UP_FORCE_ARMED_VIOLATED : 'Force Armed with a force arm zone violated',
        ARM_UP_ARMED_BYPASS : 'Armed with a bypass'
    }

    ALARM_NONE = 0
    ALARM_ENTRANCE_DELAY = 1
    ALARM_ABORT_DELAY = 2
    ALARM_FULL_FIRE = 3
    ALARM_FULL_MEDICAL = 4
    ALARM_FULL_POLICE = 5
    ALARM_FULL_BURGLAR = 6
    ALARM_FULL_AUX_1 = 7
    ALARM_FULL_AUX_2 = 8
    ALARM_FULL_AUX_3 = 9
    ALARM_FULL_AUX_4 = 10
    ALARM_FULL_CARBON_MONOXIDE = 11
    ALARM_FULL_EMERGENCY = 12
    ALARM_FULL_FREEZE = 13
    ALARM_FULL_GAS = 14
    ALARM_FULL_HEAT = 15
    ALARM_FULL_WATER = 16
    ALARM_FULL_FIRE_SUPERVISORY = 17
    ALARM_FULL_FIRE_VERIFY = 18

    ALARM_STR = {
        ALARM_NONE : 'No Alarm Active',
        ALARM_ENTRANCE_DELAY : 'Entrance Delay is Active',
        ALARM_ABORT_DELAY : 'Alarm Abort Delay Active',
        ALARM_FULL_FIRE : 'Fire Alarm',
        ALARM_FULL_MEDICAL : 'Medical Alarm',
        ALARM_FULL_POLICE : 'Police Alarm',
        ALARM_FULL_BURGLAR : 'Burglar Alarm',
        ALARM_FULL_AUX_1 : 'Aux 1 Alarm',
        ALARM_FULL_AUX_2 : 'Aux 2 Alarm',
        ALARM_FULL_AUX_3 : 'Aux 3 Alarm',
        ALARM_FULL_AUX_4 : 'Aux 4 Alarm',
        ALARM_FULL_CARBON_MONOXIDE : 'Carbon Monoxide Alarm',
        ALARM_FULL_EMERGENCY : 'Emergency Alarm',
        ALARM_FULL_FREEZE : 'Freeze Alarm',
        ALARM_FULL_GAS : 'Gas Alarm',
        ALARM_FULL_HEAT : 'Heat Alarm',
        ALARM_FULL_WATER : 'Water Alarm',
        ALARM_FULL_FIRE_SUPERVISORY : 'Fire Supervisory',
        ALARM_FULL_FIRE_VERIFY : 'Verify Fire'
    }

    CHIME_MODE_OFF = 0b0000
    CHIME_MODE_SINGLE_BEEP = 0b0001
    CHIME_MODE_CONSTANT_BEEP = 0b0010
    CHIME_MODE_BOTH_BEEP = 0b0011
    CHIME_MODE_CHIME = 0b1000
    CHIME_MODE_CHIME_SINGLE_BEEP = 0b1001
    CHIME_MODE_CHIME_CONSTANT_BEEP = 0b1010
    CHIME_MODE_CHIME_BOTH_BEEP = 0b1011

    CHIME_MODE_STR = {
        CHIME_MODE_OFF : 'Silent',
        CHIME_MODE_SINGLE_BEEP : 'Single Beep',
        CHIME_MODE_CONSTANT_BEEP : 'Constantly Beeping',
        CHIME_MODE_BOTH_BEEP : 'Single Beep while Constantly Beeping',
        CHIME_MODE_CHIME : 'Single Chime',
        CHIME_MODE_CHIME_SINGLE_BEEP : 'Single Chime with Single Beep',
        CHIME_MODE_CHIME_CONSTANT_BEEP : 'Single Chime with Constantly Beeping',
        CHIME_MODE_CHIME_BOTH_BEEP : 'Single Chime with Single Beep and Constantly Beeping'
    }

    _status = 0
    _arm_up = 0
    _alarm = 0
    _chime_mode = 0   
    _timer_entrance_1 = 0
    _timer_entrance_2 = 0
    _timer_exit_1 = 0
    _timer_exit_2 = 0
    _number = 0
    _updated_at = 0

    def __init__(self, pyelk = None):
        self._pyelk = pyelk

    """
    ElkEvent.ELK_EVENT_ARMING_STATUS_REPORT
    """
    def unpack_event_arming_status_report(self, event):
        status = event.data_dehex()[self._number-1]
        arm_up = event.data_dehex()[8+self._number-1]
        alarm = event.data_dehex(True)[16+self._number-1]
        if ((self._status == status) and (self._arm_up == arm_up) and (self._alarm == alarm)):
            return
        self._status = status
        self._arm_up = arm_up
        self._alarm = alarm
        self._updated_at = event._time

    """
    ElkEvent.ELK_EVENT_ENTRY_EXIT_TIMER
    """
    def unpack_event_entry_exit_timer(self, event):
        if (event._data[0] == '1'):
            is_entrance = True
        else:
            is_enrtance = False
        timer_1 = int(event._data_str[1:3])
        timer_2 = int(event._data_str[4:6])
        status = event.data_dehex(True)[7]
        self._status = status
        if is_entrance:
            self._timer_entrance_1 = timer_1
            self._timer_entrance_2 = timer_2
        else:
            self._timer_exit_1 = timer_1
            self._timer_exit_2 = timer_2
        self._updated_at = event._time

    def age(self):
        return time.time() - self._updated_at

    def status(self):
        return self.STATUS_STR[self._status]

    def arm_up(self):
        return self.ARM_UP_STR[self._arm_up]

    def alarm(self):
        return self.ALARM_STR[self._alarm]

    def chime_mode(self):
        return self._CHIME_MODE_STR(self._chime_mode)

class ElkKeypad(object):

    PRESSED_NONE = 0
    PRESSED_1 = 1
    PRESSED_2 = 2
    PRESSED_3 = 3
    PRESSED_4 = 4
    PRESSED_5 = 5
    PRESSED_6 = 6
    PRESSED_7 = 7
    PRESSED_8 = 8
    PRESSED_9 = 9
    PRESSED_0 = 10
    PRESSED_STAR = 11
    PRESSED_POUND = 12
    PRESSED_F1 = 13
    PRESSED_F2 = 14
    PRESSED_F3 = 15
    PRESSED_F4 = 16
    PRESSED_STAY = 17
    PRESSED_EXIT = 18
    PRESSED_CHIME = 19
    PRESSED_BYPASS = 20
    PRESSED_ELK = 21
    PRESSED_DOWN = 22
    PRESSED_UP = 23
    PRESSED_RIGHT = 24
    PRESSED_LEFT = 25
    PRESSED_F5 = 26
    PRESSED_F6 = 27
    PRESSED_DATAKEYMODE = 28

    PRESSED_STR = {
        PRESSED_NONE : 'None',
        PRESSED_1 : '1',
        PRESSED_2 : '2',
        PRESSED_3 : '3',
        PRESSED_4 : '4',
        PRESSED_5 : '5',
        PRESSED_6 : '6',
        PRESSED_7 : '7',
        PRESSED_8 : '8',
        PRESSED_9 : '9',
        PRESSED_0 : '0',
        PRESSED_STAR : '*',
        PRESSED_POUND : '#',
        PRESSED_F1 : 'F1',
        PRESSED_F2 : 'F2',
        PRESSED_F3 : 'F3',
        PRESSED_F4 : 'F4',
        PRESSED_STAY : 'Stay',
        PRESSED_EXIT : 'Exit',
        PRESSED_CHIME : 'Chime',
        PRESSED_BYPASS : 'Bypass',
        PRESSED_ELK : 'Elk',
        PRESSED_DOWN : 'Down',
        PRESSED_UP : 'Up',
        PRESSED_RIGHT : 'Right',
        PRESSED_LEFT : 'Left',
        PRESSED_F5 : 'F5',
        PRESSED_F6 : 'F6',
        PRESSED_DATAKEYMODE : 'Data Entered'
    }

    _area = 0
    _pressed = 0
    _illum = [0,0,0,0,0,0]
    _code_bypass = False
    _number = 0
    _updated_at = 0

    def __init__(self, pyelk = None):
        self._pyelk = pyelk

    """
    ELK_EVENT_KEYPAD_AREA_REPLY
    """
    def unpack_event_keypad_area_reply(self, event):
        area = event.data_dehex(True)[self._number-1]
        if (area == self._area):
            return
        self._area = area
        self._updated_at = event._time

    """
    ELK_EVENT_KEYPAD_STATUS_REPORT
    """
    def unpack_event_keypad_status_report(self, event):
        key = int(event._data_str[:2])
        if (key == self._pressed):
            return
        self._pressed = key
        for i in range(0,6):
            self._illum[i] = event.data_dehex()[2+i]
        if (event._data[8] == '1'):
            self._code_bypass = True
        else:
            self._code_bypass = False
        # By area, not keypad
        for a in range(1,9):
            self._pyelk.AREAS[a]._chime_mode = event.data_dehex(True)[8+a-1]
        self._updated_at = event._time

    def age(self):
        return time.time() - self._updated_at

class LineHandler(serial.threaded.LineReader):
    _pyelk = None

    def set_pyelk(self, pyelk):
        self._pyelk = pyelk

    # Implement Protocol class functions for Threaded Serial
    def connection_made(self, transport):
        super(LineHandler, self).connection_made(transport)
        sys.stdout.write('port opened\n')
        #self._pyelk._connected = True

    def handle_line(self, data):
        # Validate event and add to incoming buffer
        self._pyelk.elk_event_enqueue(data)

    def connection_lost(self, exc):
        if exc:
            traceback.print_exc(exc)
        self._pyelk._connected = False
        sys.stdout.write('port closed\n')

class PyElk(object):
    """
    This is the main class that handles interaction with the Elk panel

    |  address: String of the IP address of the ELK-M1XEP, 
       or device name of the serial device connected to the Elk panel, 
       ex: 'socket://192.168.12.34:2101' or '/dev/ttyUSB0'
    |  usercode: String of the user code to authenticate to the Elk panel
    |  log: [optional] Log file class from logging module

    :ivar auto_reconnect: Boolean value that indicates if the class should
                          auto-reconnect to the Elk panel if the connection
                          is lost.
    :ivar auto_update: Boolean value that controls the class's subscription to
                       the event stream that allows zone, output, and etc
                       values to be updated automatically.
    :ivar connected: Read only boolean value indicating if the class is
                     connected to the panel.
    :ivar log: Logger used by the class and its children.
    :ivar zones: :class:`~PyElk.Zones.Zones` manager that interacts with Elk
                 input zones.
    :ivar outputs: :class:`~PyElk.Outputs.Outputs` manager that interacts with
                 outputs.
    :ivar areas: :class:`~PyElk.Areas.Areas` manager that interacts with areas.
    """

    EXPORTED_EVENT_NONE = 0 
    EXPORTED_EVENT_RESCAN = 1 # Rescan performed, many things may have changed
    EXPORTED_EVENT_ZONE_STATUS = 2 # Change in zone status (open/closed, violated, etc)
    EXPORTED_EVENT_OUTPUT_STATUS = 3 # Change in output status (on/off, etc)
    EXPORTED_EVENT_ALARM_STATUS = 4 # Change in alarm status (arm/disarm, alarming, etc)
    EXPORTED_EVENT_KEYPAD_STATUS = 5 # Change in keypad status (keypress, illumination, user code entered, etc)


    ZONES = []
    OUTPUTS = []
    AREAS = []
    KEYPADS = []

    _rescan_in_progress = False

    _elk_versions = None

    _connected = False

    _connectionProtocol = None
    _connectionThread = None

    auto_reconnect = True

    def __init__(self, address, usercode, log=None):
        self._events = None
        self._reconnect_thread = None
        self._usercode = usercode
        self._queue_incoming_elk_events = deque(maxlen=1000)
        self._queue_exported_events = deque(maxlen=1000)

        # Using 0..N+1 and putting None in 0 so we aren't constantly converting between 0 and 1 based ...
        for z in range(0,209):
            if z == 0:
                zone = None
            else:
                zone = ElkZone(self)
                zone._number = z
            self.ZONES.append(zone)

        for o in range(0,209):
            if o == 0:
                output = None
            else:
                output = ElkOutput(self)
                output._number = o
            self.OUTPUTS.append(output)

        for a in range(0,9):
            if a == 0:
                area = None
            else:
                area = ElkArea(self)
                area._number = a
            self.AREAS.append(area)

        for k in range(0,17):
            if k == 0:
                keypad = None
            else:
                keypad = ElkKeypad(self)
                keypad._number = k
            self.KEYPADS.append(keypad)

        if log is None:
            self.log = logging.getLogger(__name__)
            self.log.addHandler(NullHandler())
        else:
            self.log = log

        try:
            self.connect(address)

        except ValueError as e:
#            self._connected = False
            try:
                self.log.error(e.message)
            except AttributeError:
                self.log.error(e.args[0])

#        else:
#            self._connected = True

        if (self._connected):
            self._rescan()

    def __del__(self):
        self._auto_update = False
        self._connectionThread.close()

    @property
    def connected(self):
        return self._connected

    @property
    def auto_update(self):
        return self._auto_update

    def connect(self, address):
        self._connection = serial.serial_for_url(address, timeout=1)
        self._connectionThread = serial.threaded.ReaderThread(self._connection, LineHandler) # or ReaderThread(self._connection, self... ?)
        self._connectionThread.start()
        self._connectionTransport, self._connectionProtocol = self._connectionThread.connect()
        self._connectionProtocol.set_pyelk(self)
        sys.stdout.write('ReaderThread created\n')

    def _rescan(self):
        self._rescan_in_progress = True
        self.scan_zones()
        self.scan_outputs()
        self.scan_areas()
        self.scan_keypads()
        self._rescan_in_progress = False

    def exported_event_enqueue(self, data):
        self._queue_exported_events.append(data)        
    
    def elk_event_send(self, event):
        event_str = event.to_string()
        sys.stdout.write('Sending: {}\n'.format(repr(event_str)))
        self._connectionProtocol.write_line(event_str)

    def elk_event_enqueue(self, data):
        event = ElkEvent()
        event.parse(data)
        self._queue_incoming_elk_events.append(event)

    def elk_event_scan(self, event_type, timeout = 5):
        endtime = time.time() + timeout
        event_found = False
        event = None
        while not event_found:
            if (time.time() > endtime):
                break
            for elem in list(self._queue_incoming_elk_events):
                if (elem._type == event_type):
                    event_found = True
                    event = elem
                    self._queue_incoming_elk_events.remove(elem)
        if not event_found:
            return False
        else:
            return event

    def update(self):
        self.elk_queue_process()

    def elk_queue_process(self):
        while self._rescan_in_progress:
            time.sleep(1)
        for event in list(self._queue_incoming_elk_events):
            # Remove stale events
            if (event.age() > 60):
                self._queue_incoming_elk_events.remove(event)
            elif (event._type in ElkEvent.elk_auto_map):                
                self._queue_incoming_elk_events.remove(event)
                if (event._type == ElkEvent.ELK_EVENT_INSTALLER_EXIT):
                    self._rescan()
                    return
                elif (event._type == ElkEvent.ELK_EVENT_ETHERNET_TEST):
                    return
#                elif (event._type == ElkEvent.ELK_EVENT_ALARM_MEMORY):
                elif (event._type == ElkEvent.ELK_EVENT_ENTRY_EXIT_TIMER):
                    area_number = int(event._data_str[1])
                    self.AREAS[area_number].unpack_event_entry_exit_timer(event)
#                elif (event._type == ElkEvent.ELK_EVENT_USER_CODE_ENTERED):
#                elif (event._type == ElkEvent.ELK_EVENT_TASK_UPDATE):
                elif (event._type == ElkEvent.ELK_EVENT_OUTPUT_UPDATE):
                    output_number = int(event._data_str[:3])
                    self.OUTPUTS[output_number].unpack_event_output_update(event)
                elif (event._type == ElkEvent.ELK_EVENT_ZONE_UPDATE):
                    zone_number = int(event._data_str[:3])
                    self.ZONES[zone_number].unpack_event_zone_update(event)
                elif (event._type == ElkEvent.ELK_EVENT_KEYPAD_STATUS_REPORT):
                    keypad_number = int(event._data_str[:2])
                    self.KEYPADS[keypad_number].unpack_event_keypad_status_report(event)

    def get_version(self):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_VERSION
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_VERSION_REPLY)
        if (reply):
            version_elk = reply._data_str[:2] + '.' + reply._data_str[2:4] + '.' + reply._data_str[4:6]
            version_m1xep = reply._data_str[6:8] + '.' + reply._data_str[8:10] + '.' + reply._data_str[10:12]
            self._elk_versions = {'Elk M1' : version_elk, 'M1XEP' : version_m1xep}
            return self._elk_versions
        else:
            return False

    def scan_zones(self):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_ZONE_STATUS
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ZONE_STATUS_REPORT)
        if (reply):
            for z in range(1,209):
                self.ZONES[z].unpack_event_zone_status_report(reply)
        else:
            return False

        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_ALARM_ZONE
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ALARM_ZONE_REPORT)
        if (reply):
            for z in range(1,209):
                self.ZONES[z].unpack_event_alarm_zone(reply)

        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_ZONE_DEFINITION
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ZONE_DEFINITION_REPLY)
        if (reply):
            for z in range(1,209):
                self.ZONES[z].unpack_event_zone_definition(reply)

        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_ZONE_PARTITION
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ZONE_PARTITION_REPORT)
        if (reply):
            for z in range (1,209):
                self.ZONES[z].unpack_event_zone_partition(reply)

        z = 1
        while z < 209:
            if (self.ZONES[z]._definition == ElkZone.DEFINITION_ANALOG_ZONE):
                event = ElkEvent()
                event._type = ElkEvent.ELK_EVENT_ZONE_VOLTAGE
                event._data_str = format(z,'03')
                self.elk_event_send(event)
                reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ZONE_VOLTAGE_REPLY)
                if (reply):
                    zone_number = int(reply._data_str[0:2])
                    self.ZONES[zone_number].unpack_event_zone_voltage(reply)
            z += 1

        z = 1
        while z < 209:
            z = self.get_description(ElkEvent.DESCRIPTION_ZONE_NAME,z)

    def scan_outputs(self):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_OUTPUT_STATUS
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_OUTPUT_STATUS_REPORT)
        if (reply):
            for o in range(1,209):
                self.OUTPUTS[o].unpack_event_output_status_report(reply)
        else:
            return False

        o = 1
        while o < 209:
            o = self.get_description(ElkEvent.DESCRIPTION_OUTPUT_NAME,o)

    def scan_areas(self):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_ARMING_STATUS
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_ARMING_STATUS_REPORT)
        if (reply):
            for a in range (1,9):
                self.AREAS[a].unpack_event_arming_status_report(reply)
        else:
            return False

        a = 1
        while a < 9:
            a = self.get_description(ElkEvent.DESCRIPTION_AREA_NAME,a)

    def scan_keypads(self):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_KEYPAD_AREA
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_KEYPAD_AREA_REPLY)
        if (reply):
            for k in range (1,17):
                self.KEYPADS[k].unpack_event_keypad_area_reply(reply)
                event = ElkEvent()
                event._type = ElkEvent.ELK_EVENT_KEYPAD_STATUS
                event._data_str = format(k,'02')
                self.elk_event_send(event)                
                report = self.elk_event_scan(ElkEvent.ELK_EVENT_KEYPAD_STATUS_REPORT)
                if (report):
                    keypad_number = int(report._data_str[:2])
                    self.KEYPADS[keypad_number].unpack_event_keypad_status_report(report)
        else:
            return False



    def get_description(self, description_type, number):
        event = ElkEvent()
        event._type = ElkEvent.ELK_EVENT_DESCRIPTION
        data = format(description_type,'02') + format(number,'03')
        event._data_str = data
        self.elk_event_send(event)
        reply = self.elk_event_scan(ElkEvent.ELK_EVENT_DESCRIPTION_REPLY)
        if (reply):
            #reply.dump()
            reply_type = int(reply._data_str[:2])
            reply_number = int(reply._data_str[2:5])
            reply_name = reply._data_str[5:21]
            if (reply_number >= number):
                if (reply_type == ElkEvent.DESCRIPTION_ZONE_NAME):
                    self.ZONES[reply_number]._description = reply_name.strip()
                if (reply_type == ElkEvent.DESCRIPTION_OUTPUT_NAME):
                    self.OUTPUTS[reply_number]._description = reply_name.strip()
                return (reply_number+1)
            
        return 255

"""
End internal PyElk
"""

ELK = PyElk(address=host, usercode=code, log=_LOGGER)
time.sleep(1)
versions = ELK.get_version()
from pprint import pprint
pprint(versions)
#for o in range(0,208):
#    sys.stdout.write('Output {}: '.format(repr(ELK.OUTPUTS[o].description())))
#    sys.stdout.write('{}\n'.format(repr(ELK.OUTPUTS[o].status())))

#sys.stdout.write('Output count {}\n'.format(repr(len(ELK.OUTPUTS))))
while True:
    ELK.update()
    time.sleep(1)

