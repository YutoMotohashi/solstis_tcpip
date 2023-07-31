from enum import Enum
import pytest


class Scan_Type(Enum):
    """
    The scan type.
        “coarse” - BRF only, not currently available.
        “medium” - BRF + etalon tuning.
        “fine” - BRF + etalon + resonator tuning.
        “line” - Line narrow scan, BRF + etalon + cavity tuning
    """

    COURSE = 1
    MEDIUM = 2
    FINE = 3
    LINE = 4

    @property
    def lowercase_name(self):
        return self.name.lower()

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class Scan_Type_Fast(Enum):
    """
    The scan type.
        “etalon_continuous” Etalon
        “etalon_single” Etalon
        “cavity_continuous” Reference Cavity
        “cavity_single” Reference Cavity
        “resonator_continuous” Resonator
        “resonator_single” Resonator
        “ecd_continuous” ECD
        “fringe_test” Reference Cavity
        “resonator_ramp” Resonator
        “ecd_ramp” ECD
        “cavity_triangular” Reference Cavity
        “resonator_triangular” Resonator
    """

    ETALON_CONTINUOUS = 1
    ETALON_SINGLE = 2
    CAVITY_CONTINUOUS = 3
    CAVITY_SINGLE = 4
    RESONATOR_CONTINUOUS = 5
    RESONATOR_SINGLE = 6
    ECD_CONTINUOUS = 7
    FRINGE_TEST = 8
    RESONATOR_RAMP = 9
    ECD_RAMP = 10
    CAVITY_TRIANGULAR = 11
    RESONATOR_TRIANGULAR = 12

    @property
    def lowercase_name(self):
        return self.name.lower()

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class Commands(Enum):
    SET_WAVE_M = 1
    POLL_WAVE_M = 2
    LOCK_WAVE_M = 3
    STOP_WAVE_M = 4
    MOVE_WAVE_T = 5
    POLL_MOVE_WAVE_T = 6
    STOP_MOVE_WAVE_T = 7
    TUNE_ETALON = 8
    TUNE_CAVITY = 9
    FINE_TUNE_CAVITY = 10
    TUNE_RESONATOR = 11
    FINE_TUNE_RESONATOR = 12
    ETALON_LOCK = 13
    ETALON_LOCK_STATUS = 14
    REF_CAVITY_LOCK = 15
    REF_CAVITY_LOCK_STATUS = 16
    ECD_LOCK = 17
    ECD_LOCK_STATUS = 18
    MONITOR_A = 19
    MONITOR_B = 20
    SELECT_PROFILE = 21
    GET_STATUS = 22
    GET_ALIGNMENT_STATUS = 23
    BEAM_ALIGNMENT = 24
    BEAM_ADJUST_X = 25
    BEAM_ADJUST_Y = 26
    SCAN_STITCH_INITIALISE = 27
    SCAN_STITCH_OP = 28
    SCAN_STITCH_STATUS = 29
    SCAN_STITCH_OUTPUT = 30
    TERASCAN_OUTPUT = 31
    FAST_SCAN_START = 32
    FAST_SCAN_POLL = 33
    FAST_SCAN_STOP = 34
    FAST_SCAN_STOP_NR = 35
    PBA_REFERENCE = 36
    PBA_REFERENCE_STATUS = 37
    GET_WAVELENGTH_RANGE = 38
    TERASCAN_CONTINUE = 39
    READ_ALL_ADC = 40
    SET_WAVE_TOLERANCE_M = 41
    SET_WAVE_LOCK_TOLERANCE_M = 42
    DIGITAL_PID_CONTROL = 43
    DIGITAL_PID_POLL = 44
    SET_W_METER_CHANNEL = 45
    LOCK_WAVE_M_FIXED = 46
    GPIO_OUTPUT = 47
    DAC_RAMPING = 48
    DAC_RAMPING_POLL = 49
    DIGITAL_POT_OUTPUT = 50
    DAC_OUTPUT = 51
    START_LINK = 100
    PING = 101

    @property
    def command_op(self):
        return self.name.lower()

    @property
    def command_op_reply(self):
        return self.name.lower() + "_reply"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def has_command_op(cls, op):
        return any(op == member.command_op for member in cls)

    @classmethod
    def has_command_op_reply(cls, op):
        return any(op == member.command_op_reply for member in cls)

    @classmethod
    def get_value_from_op(cls, op):
        for member in cls:
            if member.command_op == op:
                return member.value
        return None

    @classmethod
    def get_value_from_op_reply(cls, op):
        for member in cls:
            if member.command_op_reply == op:
                return member.value
        return None


status_messages_severity = dict({
    1: {  # set_wave_m_reply
        0: ("command successful", 0),
        1: ("no link to wavelength meter or no meter configured", 2),
        2: ("Wavelength out of range", 2),
    },
    2: {  # poll_wave_m_reply
        0: ("tuning software not active", 2),
        1: ("No link to wavelength meter or no meter configured.", 2),
        2: ("Tuning in progress.", 1),
        3: (
            "pre V60: wavelength lock is on, post V60: wavelength lock being maintained",
            0,
        ),
    },
    3: {  # lock_wave_m_reply
        0: ("operation successful", 0),
        1: ("No link to wavelength meter or no meter configured", 2),
    },
    4: {  # stop_wave_m_reply
        0: ("operation successful", 0),
        1: ("No link to wavelength meter", 2),
    },
    5: {  # move_wave_t_reply
        0: ("operation successful", 0),
        1: ("command failed", 2),
        2: ("wavelength out of range", 2),
    },
    6: {  # poll_move_wave_t_reply
        0: ("tuning completed", 0),
        1: ("tuning in progress", 1),
        2: ("tuning operation failed", 2),
    },
    7: {  # stop_move_wave_t_reply
        0: ("operation completed", 0),
    },
    8: {  # tune_etalon_reply
        0: ("operation completed", 0),
        1: ("setting out of range", 2),
        2: ("command failed.", 2),
    },
    9: {  # tune_cavity_reply
        0: ("operation completed", 0),
        1: ("setting out of range", 2),
        2: ("command failed.", 2),
    },
    10: {  # fine_tune_cavity_reply
        0: ("operation completed", 0),
        1: ("setting out of range", 2),
        2: ("command failed.", 2),
    },
    11: {  # tune_resonator
        0: ("operation completed", 0),
        1: ("setting out of range", 2),
        2: ("command failed.", 2),
    },
    12: {  # fine_tune_resonator
        0: ("operation completed", 0),
        1: ("setting out of range", 2),
        2: ("command failed.", 2),
    },
    13: {  # etalon_lock
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    14: {  # etalon_lock_status
        0: ("operation completed", 0),
        1: ("command failed", 2),
    },
    15: {  # ref_cavity_lock
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    16: {  # ref_cavity_lock_status
        0: ("operation completed", 0),
        1: ("command failed", 2),
    },
    17: {  # ecd_lock
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("ecd not fitted", 2),
    },
    18: {  # ecd_lock_status
        0: ("operation completed", 0),
        1: ("command failed", 2),
    },
    19: {  # monitor_a
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    20: {  # monitor_b
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    21: {  # select_profile
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    22: {  # get_status
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    23: {  # get_alignment_status
        0: ("No message", 0),
    },
    24: {  # beam_alignment
        0: ("Operation completed", 0),
        1: ("Operation failed, not fitted", 2),
    },
    25: {  # beam_adjust_x
        0: ("No message", 0),
    },
    26: {  # beam_adjust_y
        0: ("Operation completed", 0),
        1: ("Operation failed, not fitted", 2),
        2: ("operation failed, value OOR", 2),
        3: ("operation failed, not in manual mode", 2),
    },
    27: {  # scan_stitch_initialise
        0: ("operation completed", 0),
        1: ("start out of range", 2),
        2: ("stop out of range", 2),
        3: ("scan out of range", 2),
        4: ("TeraScan not available", 2),
    },
    28: {  # scan_stitch_op
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("TeraScan not available", 2),
    },
    29: {  # scan_stitch_status
        0: ("not active", 0),
        1: ("in progress", 1),
        2: ("TeraScan not available", 2),
    },
    30: {  # scan_stitch_output
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("Unused", 0),
        3: ("TeraScan not available", 2),
    },
    31: {  # terascan_output
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("delay period out of range", 2),
        3: ("update step out of range", 2),
        4: ("TeraScan not available", 2),
    },
    32: {  # fast_scan_start
        0: ("successful, scan in progress", 0),
        1: ("failed, scan width too great for current tuning position", 2),
        2: ("failed, reference cavity not fitted", 2),
        3: ("failed, ERC not fitted", 2),
        4: ("Invalid scan type", 2),
        5: ("Time > 10000 seconds", 2),
    },
    33: {  # fast_scan_poll
        0: ("scan not in progress", 0),
        1: ("scan in progress", 1),
        2: ("reference cavity not fitted", 2),
        3: ("ERC not fitted", 2),
        4: ("Invalid scan type", 2),
    },
    34: {  # fast_scan_stop
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("reference cavity not fitted", 2),
        3: ("ERC not fitted", 2),
        4: ("Invalid scan type", 2),
    },
    35: {  # fast_scan_stop_nr
        0: ("operation completed", 0),
        1: ("operation failed", 2),
        2: ("reference cavity not fitted", 2),
        3: ("unused", 0),
        4: ("Invalid scan type", 2),
    },
    36: {  # pba_reference
        0: ("operation completed", 0),
        1: ("operation failed, not fitted", 2),
    },
    37: {  # pba_reference_status
        "not_fitted": ("Beam alignment is not fitted to this system.", 2),
        "off": ("PBA reference is not running.", 0),
        "tuning": ("The system is tuning to the reference wavelength.", 1),
        "optimising": ("The system is optimising the PBA.", 1),
    },
    38: {  # get_wavelength_range
        0: ("No message", 0),
    },
    39: {  # terascan_continue
        0: ("operation completed", 0),
        1: ("operation failed, TeraScan was not paused", 2),
        2: ("TeraScan not available", 2),
    },
    40: {  # read_all_adc
        0: ("operation completed", 0),
        1: ("operation failed", 2),
    },
    41: {  # set_wave_tolerance_m
        0: ("operation successful", 0),
        1: ("No link to wavelength meter or meter not configured", 2),
        2: ("Tolerance value out of range", 2),
    },
    42: {  # set_wave_lock_tolerance_m
        0: ("operation successful", 0),
        1: ("No link to wavelength meter or meter not configured", 2),
        2: ("Tolerance value out of range", 2),
    },
    43: {  # digital_pid_control
        0: ("operation successful", 0),
        1: ("command failed", 2),
    },
    44: {  # digital_pid_poll
        0: ("operation successful", 0),
        1: ("command failed", 2),
    },
    45: {  # set_w_meter_channel
        0: ("operation successful", 0),
        1: ("command failed", 2),
        2: ("channel out of range", 2),
    },
    46: {  # lock_wave_m_fixed
        0: ("operation successful", 0),
        1: ("No link to wavelength meter or no meter configured", 2),
    },
    47: {  # gpio_output
        0: ("operation successful", 0),
        1: ("operation failed", 2),
    },
    48: {  # dac_ramping
        0: ("operation successful", 0),
        1: ("operation failed", 2),
    },
    49: {  # dac_ramping_poll
        0: ("operation successful", 0),
        1: ("operation failed", 2),
    },
    50: {  # digital_pot_output
        0: ("operation successful", 0),
        1: ("operation failed", 2),
    },
    51: {  # dac_output
        0: ("operation successful", 0),
        1: ("operation failed", 2),
        2: ("output value out of range", 2),
    },
    100: {  # start_link_reply
        "ok": ("operation successful", 0),
        "failed": ("failed to start link", 2),
    },
    101: {  # ping_reply
        0: ("No message", 0),
    },
})

