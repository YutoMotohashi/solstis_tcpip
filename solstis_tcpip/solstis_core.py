import json
import socket
from box import BoxList
from solstis_constants import (
    Scan_Type,
    Scan_Type_Fast,
    Commands,
    status_messages_severity,
)


# Exception class for Solstis specific errors
class SolstisError(Exception):
    """Exception raised when the Solstis response indicates an error

    Attributes:
        message ~ explanation of the error
        severity ~ severity of the error (0 = warning, 1 = error, 2 = critical, 10 = communication error)
    """

    def __init__(self, message, severity=0):
        self.message = message
        self.severity = 0


class SolstisCore:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.connection = None  # Placeholder for the actual connection object.
        self.response_buffer = BoxList([])
        self._transmission_id_counter = 0

    # Public methods to communicate with SolsTiS
    def connect(self, timeout=5.0):
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(timeout)  # Set a timeout of 5 seconds
            self.connection.connect((self.server_ip, self.server_port))
        except socket.timeout:
            self.connection = None
            raise TimeoutError("Connection timed out")
        except Exception as e:
            print(f"Failed to connect to the server: {e}")
            self.connection = None

    def send_command(self, transmission_id=1, op="start_link", params=None):
        if self.connection is None:
            raise SolstisError("Not connected to the server.", severity=10)

        if params is not None:
            message = {
                "transmission_id": [transmission_id],
                "op": op,
                "parameters": params,
            }
        else:
            message = {"transmission_id": [transmission_id], "op": op}
        command = {"message": message}
        message_json = json.dumps(command)
        self.connection.sendall(message_json.encode())

    def receive_response(self):
        response = self.connection.recv(1024)  # Adjust the buffer size as needed.
        self.response_buffer += BoxList([json.loads(response.decode())])
        response_json = self.response_buffer.pop(0)
        return response_json

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    # internal methods to varify communication with SolsTiS
    def _verify_messsage(self, message, op=None, transmission_id=None):
        msgID = message["message"]["transmission_id"][0]
        msgOP = message["message"]["op"]
        if msgOP == "parse_fail":
            err_msg = "Mesage with ID " + str(msgID) + " failed to parse."
            err_msg += "\n\n" + str(message)
            raise SolstisError(err_msg, 10)
        if transmission_id is not None:
            if msgID != transmission_id:
                err_msg = (
                    "Message with ID"
                    + str(msgID)
                    + " did not match expected ID of: "
                    + str(transmission_id)
                )
                raise SolstisError(err_msg, 10)
        if op is not None:
            if msgOP != op:
                message = (
                    "Message with ID"
                    + str(msgID)
                    + "with operation command of '"
                    + msgOP
                    + "' did not match expected operation command of: "
                    + op
                )
                raise SolstisError(message)

    # Private methods to communicate with SolsTiS
    def _start_link(self, transmission_id, ip_address):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        ip_address: The IP address of the client.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        'ok' - The link has been successfully established.
        'failed' - The link could not be formed.
        """
        self.send_command(transmission_id, "start_link", {"ip_address": ip_address})
        response = self.receive_response()
        self._verify_messsage(
            response, op="start_link_reply", transmission_id=transmission_id
        )

        return response

    def _ping(self, transmission_id, text_in):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        text_in: The text to be echoed back with switched lower-upper case.

        Returns:
        The response from the Solstis device as a dictionary. The response includes the following fields:
        'text_out' - The echoed text with switched lower-upper case.
        """
        self.send_command(transmission_id, "ping", {"text_in": text_in})
        response = self.receive_response()
        self._verify_messsage(
            response, op="ping_reply", transmission_id=transmission_id
        )

        return response

    def _set_wave_m(self, transmission_id, wavelength):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        wavelength: The target wavelength value in nm within the tuning range of the SolsTiS.

        Returns:
        The response from the Solstis device as a dictionary. The response includes the following fields:
        'status' - The status of the operation:
            0 - operation successful.
            1 - no link to wavelength meter or no meter configured.
            2 - wavelength out of range.
        'current_wavelength' - The most recently obtained wavelength reading from the wavelength meter.
        'extended_zone' - Indicates if the current wavelength is in an extended zone:
            0 - current wavelength is not in an extended zone.
            1 - current wavelength is in an extended zone.
        'duration' - Time taken in seconds from receiving the task to transmitting the final report.
        """
        self.send_command(transmission_id, "set_wave_m", {"wavelength": wavelength})
        response = self.receive_response()
        self._verify_messsage(
            response, op="set_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _poll_wave_m(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The response includes the following fields:
        'status' - The status of the tuning software:
            0 - tuning software not active.
            1 - no link to wavelength meter or no meter configured.
            2 - tuning in progress.
            3 - wavelength is being maintained.
        'current_wavelength' - The most recently obtained wavelength reading from the wavelength meter.
        'lock_status' - The status of the wavelength lock:
            0 - wavelength is not being maintained.
            1 - wavelength is being maintained.
        'extended_zone' - Indicates if the current wavelength is in an extended zone:
            0 - current wavelength is not in an extended zone.
            1 - current wavelength is in an extended zone.
        """
        self.send_command(transmission_id, "poll_wave_m")
        response = self.receive_response()
        self._verify_messsage(
            response, op="poll_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _lock_wave_m(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to maintain the current wavelength or "off" to stop maintaining it.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - no link to wavelength meter.
        """
        self.send_command(transmission_id, "lock_wave_m", {"operation": operation})
        response = self.receive_response()
        self._verify_messsage(
            response, op="lock_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _stop_wave_m(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - no link to wavelength meter.
        The 'current_wavelength' field in the response is the most recently obtained wavelength reading from the wavelength meter.
        """
        self.send_command(transmission_id, "stop_wave_m")
        response = self.receive_response()
        self._verify_messsage(
            response, op="stop_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _move_wave_t(self, transmission_id, wavelength):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        wavelength: The target wavelength in nm within the tuning range of the SolsTiS.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - command failed.
        2 - wavelength out of range.
        """
        self.send_command(transmission_id, "move_wave_t", {"wavelength": wavelength})
        response = self.receive_response()
        self._verify_messsage(
            response, op="move_wave_t_reply", transmission_id=transmission_id
        )

        status = response["message"]["parameters"]["status"]
        if status != 0:
            error_messages = {1: "Command failed.", 2: "Wavelength out of range."}
            raise SolstisError(
                "Failed to move wavelength: "
                + error_messages.get(status, "Unknown error")
            )

        return response

    def _poll_move_wave_t(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Tuning completed.
        1 - Tuning in progress.
        2 - Tuning operation failed.
        """
        self.send_command(transmission_id, "poll_move_wave_t")
        response = self.receive_response()
        self._verify_messsage(
            response, op="poll_move_wave_t_reply", transmission_id=transmission_id
        )

        return response

    def _stop_move_wave_t(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following value:
        0 - operation completed.
        """
        self.send_command(transmission_id, "stop_move_wave_t")
        response = self.receive_response()
        self._verify_messsage(
            response, op="stop_move_wave_t_reply", transmission_id=transmission_id
        )

        return response

    def _tune_etalon(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The etalon tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_etalon", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_etalon_reply", transmission_id=transmission_id
        )

        return response

    def _tune_cavity(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The reference cavity tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_cavity", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_cavity_reply", transmission_id=transmission_id
        )

        return response

    def _fine_tune_cavity(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The fine reference cavity tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "fine_tune_cavity", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="fine_tune_cavity_reply", transmission_id=transmission_id
        )

        return response

    def _tune_resonator(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The resonator tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_resonator", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_resonator_reply", transmission_id=transmission_id
        )

        return response

    def _fine_tune_resonator(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The fine resonator tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "fine_tune_resonator", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="fine_tune_resonator_reply", transmission_id=transmission_id
        )

        return response

    def _etalon_lock(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to apply the lock or "off" to remove it.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        """
        self.send_command(transmission_id, "etalon_lock", {"operation": operation})
        response = self.receive_response()
        self._verify_messsage(
            response, op="etalon_lock_reply", transmission_id=transmission_id
        )

        return response

    def _etalon_lock_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The 'condition' field in the response can be one of the following:
        "off" - the lock is off.
        "on" - the lock is on.
        "debug" - the lock is in a debug condition.
        "error" - the lock operation is in error.
        "search" - the lock search algorithm is active.
        "low" - the lock is off due to low output.
        """
        self.send_command(transmission_id, "etalon_lock_status")
        response = self.receive_response()
        self._verify_messsage(
            response, op="etalon_lock_status_reply", transmission_id=transmission_id
        )

        return response

    def _cavity_lock(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to apply the lock or "off" to remove it.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        """
        self.send_command(transmission_id, "cavity_lock", {"operation": operation})
        response = self.receive_response()
        self._verify_messsage(
            response, op="cavity_lock_reply", transmission_id=transmission_id
        )

        return response

    def _cavity_lock_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The 'condition' field in the response can be one of the following:
        "off" - the lock is off.
        "on" - the lock is on.
        "debug" - the lock is in a debug condition.
        "error" - the lock operation is in error.
        "search" - the lock search algorithm is active.
        "low" - the lock is off due to low output.
        """
        self.send_command(transmission_id, "cavity_lock_status")
        response = self.receive_response()
        self._verify_messsage(
            response, op="cavity_lock_status_reply", transmission_id=transmission_id
        )

        return response

    def _ecd_lock(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to apply the lock or "off" to remove it.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        2 - ECD not fitted.
        """
        self.send_command(transmission_id, "ecd_lock", {"operation": operation})
        response = self.receive_response()
        self._verify_messsage(
            response, op="ecd_lock_reply", transmission_id=transmission_id
        )

        return response

    def _ecd_lock_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The 'condition' field in the response can be one of the following:
        "off" - the lock is off.
        "on" - the lock is on.
        "debug" - the lock is in a debug condition.
        "error" - the lock operation is in error.
        "search" - the lock search algorithm is active.
        "low" - the lock is off due to low output.
        The 'voltage' field in the response is the current ECD lock voltage.
        """
        self.send_command(transmission_id, "ecd_lock_status")
        response = self.receive_response()
        self._verify_messsage(
            response, op="ecd_lock_status_reply", transmission_id=transmission_id
        )

        return response

    def _monitor_a(self, transmission_id, signal):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        signal: The requested signal to switch. The possible values are:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1.
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error.
        15 - Etalon PD AC.
        16 - Output PD.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        """
        self.send_command(transmission_id, "monitor_a", {"signal": signal})
        response = self.receive_response()
        self._verify_messsage(
            response, op="monitor_a_reply", transmission_id=transmission_id
        )

        return response

    def _monitor_b(self, transmission_id, signal):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        signal: The requested signal to switch. The possible values are:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1.
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error.
        15 - Etalon PD AC.
        16 - Output PD.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        """
        self.send_command(transmission_id, "monitor_b", {"signal": signal})
        response = self.receive_response()
        self._verify_messsage(
            response, op="monitor_b_reply", transmission_id=transmission_id
        )

        return response

    def _select_profile(self, transmission_id, profile):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        profile: The profile number to select. The possible values are 1 to 5.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The 'current_profile' field in the response is the number of the etalon profile which is currently in use.
        The 'max_profile' field in the response is the maximum etalon profile number configured in this system.
        The 'frequency' field in the response is the dither frequency of the selected profile in kHz.
        """
        self.send_command(transmission_id, "select_profile", {"profile": profile})
        response = self.receive_response()
        self._verify_messsage(
            response, op="select_profile_reply", transmission_id=transmission_id
        )

        return response

    def _get_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The response also includes the current wavelength, temperature, temperature status, current lock conditions for the etalon, cavity and ECD, voltages for the etalon, resonator, ECD, output monitor and etalon PD DC, and the dither status.
        """
        self.send_command(transmission_id, "get_status")
        response = self.receive_response()
        self._verify_messsage(
            response, op="get_status_reply", transmission_id=transmission_id
        )

        return response

    def _get_alignment_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        The response also includes the alignment condition, X and Y alignment values, X and Y automatic alignment values from the DSP, and the quadrant.
        """
        self.send_command(transmission_id, "get_alignment_status")
        response = self.receive_response()
        self._verify_messsage(
            response, op="get_alignment_status_reply", transmission_id=transmission_id
        )

        return response

    def _beam_alignment(self, transmission_id, mode):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        mode: The new mode for the beam alignment. The possible values are:
        1 - Manual.
        2 - Automatic.
        3 - Stop (and hold current values).
        4 - One shot.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed, not fitted.
        """
        self.send_command(transmission_id, "beam_alignment", {"mode": mode})
        response = self.receive_response()
        self._verify_messsage(
            response, op="beam_alignment_reply", transmission_id=transmission_id
        )

        return response

    def _beam_adjust_x(self, transmission_id, x_value):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        x_value: The x alignment percentage value, centre = 50. The possible values are from 0 to 100.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed, not fitted.
        2 - operation failed, value out of range.
        3 - operation failed, not in manual mode.
        """
        self.send_command(transmission_id, "beam_adjust_x", {"x_value": x_value})
        response = self.receive_response()
        self._verify_messsage(
            response, op="beam_adjust_x_reply", transmission_id=transmission_id
        )

        return response

    def _beam_adjust_y(self, transmission_id, y_value):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        y_value: The y alignment percentage value, centre = 50. The possible values are from 0 to 100.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed, not fitted.
        2 - operation failed, value out of range.
        3 - operation failed, not in manual mode.
        """
        self.send_command(transmission_id, "beam_adjust_y", {"y_value": y_value})
        response = self.receive_response()
        self._verify_messsage(
            response, op="beam_adjust_y_reply", transmission_id=transmission_id
        )

        return response

    def _scan_stitch_initialise(self, transmission_id, scan, start, stop, rate, units):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values are "coarse", "medium", "fine", and "line".
        start: The start position of the scan, in nm. This should be within the range 650-1100.
        stop: The stop position of the scan, in nm. This should also be within the range 650-1100.
        rate: The scan rate. Possible values depend on the units and scan type.
        units: The units for the scan rate. Possible values are "GHz/s", "MHz/s", and "kHz/s".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - start out of range.
        2 - stop out of range.
        3 - scan out of range.
        4 - TeraScan not available.
        """
        self.send_command(
            transmission_id,
            "scan_stitch_initialise",
            {"scan": scan, "start": start, "stop": stop, "rate": rate, "units": units},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="scan_stitch_initialise_reply", transmission_id=transmission_id
        )

        return response

    def _scan_stitch_op(self, transmission_id, scan, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values are "coarse", "medium", "fine", and "line".
        operation: The operation to perform. Possible values are "start" and "stop".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        2 - TeraScan not available.
        """
        self.send_command(
            transmission_id,
            "scan_stitch_op",
            {"scan": scan, "operation": operation},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="scan_stitch_op_reply", transmission_id=transmission_id
        )

        return response

    def _scan_stitch_status(self, transmission_id, scan):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values are "coarse", "medium", "fine", and "line".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - not active.
        1 - in progress.
        2 - TeraScan not available.
        If the status is "in progress", the response also includes the current, start, and stop wavelengths, as well as the current operation.
        """
        self.send_command(
            transmission_id,
            "scan_stitch_status",
            {"scan": scan},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="scan_stitch_status_reply", transmission_id=transmission_id
        )

        return response

    def _scan_stitch_output(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Possible values are "start" and "stop".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        2 - update rate out of range. (This field is unused.)
        3 - TeraScan not available.
        """
        self.send_command(
            transmission_id,
            "scan_stitch_output",
            {"operation": operation},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="scan_stitch_output_reply", transmission_id=transmission_id
        )

        return response

    def _terascan_output(self, transmission_id, operation, delay, update, pause):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Possible values are "start" and "stop".
        delay: The delay after the start transmission in 1/100s. The value ranges from 0 to 1000.
        update: The update frequency during the mid-scan segment. The value ranges from 0 to 50.
        pause: Determines whether the TeraScan will pause at the start of each segment. Possible values are "on" and "off".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - operation failed.
        2 - delay period out of range.
        3 - update step out of range.
        4 - TeraScan not available.
        """
        self.send_command(
            transmission_id,
            "terascan_output",
            {"operation": operation, "delay": delay, "update": update, "pause": pause},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="terascan_output_reply", transmission_id=transmission_id
        )

        return response

    def _fast_scan_start(self, transmission_id, scan, width, time):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values include "etalon_continuous", "etalon_single", "cavity_continuous", "cavity_single", "resonator_continuous", "resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp", "ecd_ramp", "cavity_triangular", "resonator_triangular".
        width: The scan width.
        time: The duration of the scan in seconds.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Successful, scan in progress.
        1 - Failed, scan width too great for current tuning position.
        2 - Failed, reference cavity not fitted.
        3 - Failed, ERC not fitted.
        4 - Invalid scan type.
        5 - Time > 10000 seconds.
        """
        self.send_command(
            transmission_id,
            "fast_scan_start",
            {"scan": scan, "width": width, "time": time},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="fast_scan_start_reply", transmission_id=transmission_id
        )

        return response

    def _fast_scan_poll(self, transmission_id, scan):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values include "etalon_continuous", "etalon_single", "cavity_continuous", "cavity_single", "resonator_continuous", "resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp", "ecd_ramp", "cavity_triangular", "resonator_triangular".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Scan not in progress.
        1 - Scan in progress.
        2 - Reference cavity not fitted.
        3 - ERC not fitted.
        4 - Invalid scan type.
        The response also includes the current value of the tuning control for the given scan.
        """
        self.send_command(
            transmission_id,
            "fast_scan_poll",
            {"scan": scan},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="fast_scan_poll_reply", transmission_id=transmission_id
        )

        return response

    def _fast_scan_stop(self, transmission_id, scan):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values include "etalon_continuous", "etalon_single", "cavity_continuous", "cavity_single", "resonator_continuous", "resonator_single", "ecd_continuous", "fringe_test", "resonator_ramp", "ecd_ramp", "cavity_triangular", "resonator_triangular".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation completed.
        1 - Operation failed.
        2 - Reference cavity not fitted.
        3 - ECD not fitted.
        4 - Invalid scan type.
        """
        self.send_command(
            transmission_id,
            "fast_scan_stop",
            {"scan": scan},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="fast_scan_stop_reply", transmission_id=transmission_id
        )

        return response

    def _fast_scan_stop_nr(self, transmission_id, scan):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        scan: The scan type. Possible values include "etalon_continuous", "etalon_single", "cavity_continuous", "cavity_single", "resonator_continuous", "resonator_single", "fringe_test", "resonator_ramp", "cavity_triangular", "resonator_triangular".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation completed.
        1 - Operation failed.
        2 - Reference cavity not fitted.
        4 - Invalid scan type.
        """
        self.send_command(
            transmission_id,
            "fast_scan_stop_nr",
            {"scan": scan},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="fast_scan_stop_nr_reply", transmission_id=transmission_id
        )

        return response

    def _pba_reference(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Possible values include "start" and "stop".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation completed.
        1 - Operation failed, PBA not fitted.
        """
        self.send_command(
            transmission_id,
            "pba_reference",
            {"operation": operation},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="pba_reference_reply", transmission_id=transmission_id
        )

        return response

    def _pba_reference_status(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        "not_fitted" - Beam alignment is not fitted to this system.
        "off" - PBA reference is not running.
        "tuning" - The system is tuning to the reference wavelength.
        "optimising" - The system is optimising the PBA.
        The response also includes the current X and Y alignment as percentage values, with the center being 50.
        """
        self.send_command(
            transmission_id,
            "pba_reference_status",
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="pba_reference_status_reply", transmission_id=transmission_id
        )

        return response

    def _get_wavelength_range(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The response includes:
        - 'minimum_wavelength': The minimum wavelength that the Solstis can tune to in nanometers.
        - 'maximum_wavelength': The maximum wavelength that the Solstis can tune to in nanometers.
        - 'extended_zones': The number of extended zones in the Solstis wavelength table.
        - 'start_zone_N': Start wavelengths of extended zones in nanometers.
        - 'stop_zone_N': Stop wavelengths of extended zones in nanometers.
        """
        self.send_command(
            transmission_id,
            "get_wavelength_range",
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="get_wavelength_range_reply", transmission_id=transmission_id
        )

        return response

    def _terascan_continue(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation completed.
        1 - Operation failed, TeraScan was not paused.
        2 - TeraScan not available.
        """
        self.send_command(
            transmission_id,
            "terascan_continue",
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="terascan_continue_reply", transmission_id=transmission_id
        )

        return response

    def _read_all_adc(self, transmission_id, report=None):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        report: Optional. If set to "finished", will obtain the values from the next reading.

        Returns:
        The response from the Solstis device as a dictionary. The response includes:
        - 'status': The status of the operation. Can be 0 for operation completed, or 1 for operation failed.
        - 'channel count': The number of ADC channels in this Solstis.
        - 'channel_N': The name of the Nth ADC channel.
        - 'value_N': The current input value for the Nth ADC channel.
        - 'units_N': The measurement units for the Nth ADC channel.
        """
        params = {"report": report} if report is not None else None
        self.send_command(
            transmission_id,
            "read_all_adc",
            params,
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="read_all_adc_reply", transmission_id=transmission_id
        )

        return response

    def _set_wave_tolerance_m(self, transmission_id, tolerance):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        tolerance: The upper limit of the tuning tolerance is 1. The lower limit of the tuning tolerance depends on the precision of the wavelength meter.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation completed.
        1 - No link to wavelength meter or meter not configured.
        2 - Tolerance value out of range.
        """
        self.send_command(
            transmission_id,
            "set_wave_tolerance_m",
            {"tolerance": tolerance},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="set_wave_tolerance_m_reply", transmission_id=transmission_id
        )

        return response

    def _set_wave_lock_tolerance_m(self, transmission_id, tolerance):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        tolerance: The tolerance for the wavelength lock. The acceptable range of values depends on the precision of the wavelength meter.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - No link to wavelength meter or meter not configured.
        2 - Tolerance value out of range.
        """
        self.send_command(
            transmission_id,
            "set_wave_lock_tolerance_m",
            {"tolerance": tolerance},
        )
        response = self.receive_response()
        self._verify_messsage(
            response,
            op="set_wave_lock_tolerance_m_reply",
            transmission_id=transmission_id,
        )

        return response

    def _digital_pid_control(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "start" or "stop".

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Command failed.
        """
        self.send_command(
            transmission_id,
            "digital_pid_control",
            {"operation": operation},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="digital_pid_control_reply", transmission_id=transmission_id
        )

        return response

    def _digital_pid_poll(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The response includes:
        - 'status': The status of the operation. Can be 0 for operation successful, or 1 for command failed.
        - 'loop_status': The loop status. Can be 0 for not initialized, 1 for running, or 2 for initialized but not running.
        - 'target_output': The DAC value the PID loop has to maintain.
        - 'current_output': The current DAC value.
        """
        self.send_command(
            transmission_id,
            "digital_pid_poll",
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="digital_pid_poll_reply", transmission_id=transmission_id
        )

        return response

    def _set_w_meter_channel(self, transmission_id, channel, recovery=None):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        channel: The channel to set on the wavelength meter. Can range from 0 to 8.
        recovery: The recovery action to be taken. Can be 1 for reset and proceed, 2 for wait, or 3 for abandon. Default is None.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Command failed.
        2 - Channel out of range.
        """
        params = {"channel": channel}
        if recovery is not None:
            params["recovery"] = recovery
        self.send_command(transmission_id, "set_w_meter_channel", params)
        response = self.receive_response()
        self._verify_messsage(
            response, op="set_w_meter_channel_reply", transmission_id=transmission_id
        )

        return response

    def _lock_wave_m_fixed(self, transmission_id, operation, lock_wavelength=None):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to apply the lock or "off" to remove it.
        lock_wavelength: The wavelength to which the lock should be applied. Default is None.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - No link to wavelength meter or no meter configured.
        """
        params = {"operation": operation}
        if lock_wavelength is not None:
            params["lock_wavelength"] = lock_wavelength
        self.send_command(transmission_id, "lock_wave_m_fixed", params)
        response = self.receive_response()
        self._verify_messsage(
            response, op="lock_wave_m_fixed_reply", transmission_id=transmission_id
        )

        return response

    def _gpio_output(self, transmission_id, channel, value):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        channel: The GPIO channel number (0 - 31).
        value: The value to be output on the GPIO channel (0 or 1).

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Operation failed.
        """
        self.send_command(
            transmission_id, "gpio_output", {"channel": channel, "value": value}
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="gpio_output_reply", transmission_id=transmission_id
        )

        return response

    def _dac_ramping(
        self,
        transmission_id,
        dac_channel,
        start_stop,
        ramping_mode,
        step_mode,
        target_output,
        ramp_rate,
        update_rate,
        step_size,
    ):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        dac_channel: The DAC channel number (0 - 31).
        start_stop: The start/stop mode. 1 for start, 2 for stop.
        ramping_mode: The ramping mode. 1 for no ramping, 2 for ramp only if the target is higher than the current output, 3 for ramp only if the target is lower than the current output, 4 for always ramp in either direction.
        step_mode: The step mode. 0 for using the ramp rate and the DSP will calculate the step size to achieve the update rate, 1 for using the given step size.
        target_output: The final output for the DAC, specified in user units.
        ramp_rate: The DAC update rate specified in user units per second.
        update_rate: The time for the required update in seconds.
        step_size: The step size in user units.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Operation failed.
        """
        params = {
            "dac_channel": dac_channel,
            "start_stop": start_stop,
            "ramping_mode": ramping_mode,
            "step_mode": step_mode,
            "target_output": target_output,
            "ramp_rate": ramp_rate,
            "update_rate": update_rate,
            "step_size": step_size,
        }
        self.send_command(transmission_id, "dac_ramping", params)
        response = self.receive_response()
        self._verify_messsage(
            response, op="dac_ramping_reply", transmission_id=transmission_id
        )

        return response

    def _dac_ramping_poll(self, transmission_id, dac_channel):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        dac_channel: The DAC channel number (0 - 31).

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Operation failed.
        """
        self.send_command(
            transmission_id, "dac_ramping_poll", {"dac_channel": dac_channel}
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="dac_ramping_poll_reply", transmission_id=transmission_id
        )

        return response

    def _digital_pot_output(self, transmission_id, channel, value):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        channel: The digital potentiometer channel number (0 - 36).
        value: The value to be output (0 - 255).

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Operation failed.
        """
        self.send_command(
            transmission_id, "digital_pot_output", {"channel": channel, "value": value}
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="digital_pot_output_reply", transmission_id=transmission_id
        )

        return response

    def _dac_output(self, transmission_id, channel, output_value):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        channel: The DAC channel number (0 - 30).
        output_value: The value to be output. The range varies according to the definition of the DAC.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Operation successful.
        1 - Operation failed.
        2 - Output value out of range.
        """
        self.send_command(
            transmission_id,
            "dac_output",
            {"channel": channel, "output_value": output_value},
        )
        response = self.receive_response()
        self._verify_messsage(
            response, op="dac_output_reply", transmission_id=transmission_id
        )

        return response

    # Private methods for internal use
    def _allocate_transmission_id(self):
        self._transmission_id_counter += 1
        max_transmission_id = 2**30 - 1
        if self._transmission_id_counter > max_transmission_id:
            self._transmission_id_counter = 0
        return self._transmission_id_counter

    def _check_response(self, response):
        # switch depending on the operation
        operation = response["message"]["op"]
        if "status" in response["message"]["parameters"]:
            status = response["message"]["parameters"]["status"]
        else:
            status = 0

        def _handle_operation(operation, status):
            op_index = Commands.get_value_from_op_reply(operation)
            if Commands.has_command_op_reply(operation):
                if status in status_messages_severity[op_index]:
                    if status_messages_severity[op_index][status][1] != 0:
                        raise SolstisError(*status_messages_severity[op_index][status])
                else:
                    raise SolstisError("Unknown error.", severity=2)
            else:
                print(f"Unknown operation: {operation}")
                print(f"Status: {status}")
                raise SolstisError("Invalid operation.", severity=2)

        _handle_operation(operation, status)

    _command = {
        1: _set_wave_m,
        2: _poll_wave_m,
        3: _lock_wave_m,
        4: _stop_wave_m,
        5: _move_wave_t,
        6: _poll_move_wave_t,
        7: _stop_move_wave_t,
        8: _tune_etalon,
        9: _tune_cavity,
        10: _fine_tune_cavity,
        11: _tune_resonator,
        12: _fine_tune_resonator,
        13: _etalon_lock,
        14: _etalon_lock_status,
        15: _cavity_lock,
        16: _cavity_lock_status,
        17: _ecd_lock,
        18: _ecd_lock_status,
        19: _monitor_a,
        20: _monitor_b,
        21: _select_profile,
        22: _get_status,
        23: _get_alignment_status,
        24: _beam_alignment,
        25: _beam_adjust_x,
        26: _beam_adjust_y,
        27: _scan_stitch_initialise,
        28: _scan_stitch_op,
        29: _scan_stitch_status,
        30: _scan_stitch_output,
        31: _terascan_output,
        32: _fast_scan_start,
        33: _fast_scan_poll,
        34: _fast_scan_stop,
        35: _fast_scan_stop_nr,
        36: _pba_reference,
        37: _pba_reference_status,
        38: _get_wavelength_range,
        39: _terascan_continue,
        40: _read_all_adc,
        41: _set_wave_tolerance_m,
        42: _set_wave_lock_tolerance_m,
        43: _digital_pid_control,
        44: _digital_pid_poll,
        45: _set_w_meter_channel,
        46: _lock_wave_m_fixed,
        47: _gpio_output,
        48: _dac_ramping,
        49: _dac_ramping_poll,
        50: _digital_pot_output,
        51: _dac_output,
        100: _start_link,
        101: _ping,
    }

    # Public methods, generalized call for all commands
    def command(self, command_id, **kwargs):
        """
        Parameters:
        command_id: The ID of the command to execute.
        transmission_id: The ID for this transmission.
        kwargs: The parameters to pass to the command.

        Returns:
        The response from the Solstis device as a dictionary.
        """
        transmission_id = self._allocate_transmission_id()
        assert command_id in self._command, f"Invalid command ID. {command_id}"
        response = (self._command[command_id])(self, transmission_id, **kwargs)
        self._check_response(response)
        return response

    # Public methods, specific call for each command
    def start_link(self, ip_address: str = "192.168.1.107"):
        """
        Parameters:
        ip_address: The IP address of the client.
        """
        kw_args = {"ip_address": ip_address}
        return self.command(100, **kw_args)

    def ping(self, text_in: str):
        """
        Parameters:
        text_in: The text to be echoed back with switched lower-upper case.
        """
        kw_args = {"text_in": text_in}
        return self.command(101, **kw_args)

    def set_wave_m(self, wavelength: float):
        """
        Parameters:
        wavelength: The target wavelength value in nm within the tuning range of the SolsTiS.
        """
        kw_args = {"wavelength": wavelength}
        # the parameter of extended_zone is not used in the current version
        return self.command(1, **kw_args)

    def poll_wave_m(self):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(2, **kw_args)

    def lock_wave_m(self, operation: bool):
        """
        Parameters:
        operation: The operation to perform. Can be True to maintain the current wavelength or False to stop maintaining it.
        """
        kw_args = {"operation": "on" if operation else "off"}
        return self.command(3, **kw_args)

    def stop_wave_m(self):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(4, **kw_args)

    def move_wave_t(self, wavelength: float):
        """
        Parameters:
        wavelength: The target wavelength in nm within the tuning range of the SolsTiS.
        """
        kw_args = {"wavelength": wavelength}
        return self.command(5, **kw_args)

    def poll_move_wave_t(self):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(6, **kw_args)

    def stop_move_wave_t(self):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(7, **kw_args)

    def tune_etalon(self, setting: float):
        """
        Parameters:
        setting: The etalon tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."
        kw_args = {"setting": setting}
        return self.command(8, **kw_args)

    def tune_cavity(self, setting: float):
        """
        Parameters:
        setting: The reference cavity tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."
        kw_args = {"setting": setting}
        return self.command(9, **kw_args)

    def fine_tune_cavity(self, setting: float):
        """
        Parameters:
        setting: The fine reference cavity tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."
        kw_args = {"setting": setting}
        return self.command(10, **kw_args)

    def tune_resonator(self, setting: float):
        """
        Parameters:
        setting: The resonator tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."
        kw_args = {"setting": setting}
        return self.command(11, **kw_args)

    def fine_tune_resonator(self, setting: float):
        """
        Parameters:
        setting: The fine resonator tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."
        kw_args = {"setting": setting}
        return self.command(12, **kw_args)

    def etalon_lock(self, operation: bool):
        """
        Parameters:
        operation: The operation to perform. Can be True to apply the lock or False to remove it.
        """
        kw_args = {"operation": "on" if operation else "off"}
        return self.command(13, **kw_args)

    def etalon_lock_status(self):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(14, **kw_args)

    def ref_cavity_lock(self, operation: bool):
        """
        Parameters:
        operation: The operation to perform. Can be True to apply the lock or False to remove it.
        """

        kw_args = {"operation": "on" if operation else "off"}
        return self.command(15, **kw_args)

    def ref_cavity_lock_status(
        self,
    ):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(16, **kw_args)

    def ecd_lock(self, operation: bool):
        """
        Parameters:
        operation: The operation to perform. Can be True to apply the lock or False to remove it.
        """

        kw_args = {"operation": "on" if operation else "off"}
        return self.command(17, **kw_args)

    def ecd_lock_status(
        self,
    ):
        """
        Parameters: None
        """
        kw_args = {}
        return self.command(18, **kw_args)

    def monitor_a(self, signal: int):
        """
        Parameters:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error
        15 - Etalon PD AC
        16 - Output_PD
        """
        assert 1 <= signal <= 16, "Signal out of range."
        kw_args = {"signal": signal}
        return self.command(19, **kw_args)

    def monitor_b(self, signal: int):
        """
        Parameters:
        1 - Etalon dither.
        2 - Etalon voltage.
        3 - ECD slow voltage.
        4 - Reference cavity.
        5 - Resonator fast V.
        6 - Resonator slow V.
        7 - Aux output PD.
        8 - Etalon error.
        9 - ECD error.
        10 - ECD PD1
        11 - ECD PD2.
        12 - Input PD.
        13 - Reference cavity PD.
        14 - Resonator error
        15 - Etalon PD AC
        16 - Output_PD
        """
        assert 1 <= signal <= 16, "Signal out of range."
        kw_args = {"signal": signal}
        return self.command(20, **kw_args)

    def select_profile(self, profile: int):
        """
        Parameters:
        1 – 5 Each system can have up to 5 defined etalon profiles.
        """
        kw_args = {"profile": profile}
        return self.command(21, **kw_args)

    def get_status(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(22, **kw_args)

    def get_alignment_status(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(23, **kw_args)

    def beam_alignment(self, mode: int):
        """
        Parameters:
        mode:
        1 - Manual
        2 - Automatic
        3 - Stop (and hold current values)
        4 - One shot
        """
        kw_args = {"mode": mode}
        return self.command(24, **kw_args)

    def beam_adjust_x(self, x_value: float):
        """
        Parameters:
        x value: 0 – 100 - X alignment percentage value, centre = 50
        """
        assert 0 <= x_value <= 100, "Setting out of range."
        kw_args = {"x_value": x_value}
        return self.command(25, **kw_args)

    def beam_adjust_y(self, y_value: float):
        """
        Parameters:
        y value: 0 – 100 - Y alignment percentage value, centre = 50
        """
        assert 0 <= y_value <= 100, "Setting out of range."
        kw_args = {"y_value": y_value}
        return self.command(26, **kw_args)

    def scan_stitch_initialise(
        self, scan: int, start: float, stop: float, rate: float, units: str
    ):
        """
        Parameters:
            Scan type : see enum
            Start position
                650 – 1100 - Scan start position in nm.
                (approximate values)
            Stop position
                650 – 1100 - Scan stop position in nm.
                (approximate values)
            Scan rate, view in conjunction with units field below.
                Medium scan, units = GHz/s
                    100, 50, 20, 15, 10, 5, 2, 1.
                Fine scan and line narrow scan, units = GHz/s
                    20, 10, 5, 2, 1.
                Fine scan and line narrow scan, units = MHz/s
                    500, 200, 100, 50, 20, 10, 5, 2, 1.
                Line narrow scan, units = kHz/s
                    500, 200, 100, 50.
            Units
                “GHz/s” - medium, fine and line narrow scans.
                “MHz/s” - fine and line narrow scans only.
                “kHz/s” - line narrow scans only.
        """
        assert Scan_Type.has_value(scan), "Scan type not valid."
        assert unit in ["GHz/s", "MHz/s", "kHz/s"], "Units not valid."
        assert 650 <= start <= 1100, "Start position out of range."
        assert 650 <= stop <= 1100, "Stop position out of range."

        kw_args = {
            "scan": Scan_Type(scan).lowercase_name,
            "start": start,
            "stop": stop,
            "rate": rate,
            "units": units,
        }
        return self.command(27, **kw_args)

    def scan_stitch_op(self, scan: int, operation: bool):
        """
        Parameters:
        Scan type : see Enum
        Operation
            “start” - Start running the given scan
            “stop” - Stop running the given scan
        """
        assert Scan_Type.has_value(scan), "Scan type not valid."

        kw_args = {
            "scan": Scan_Type(scan).lowercase_name,
            "operation": "start" if operation else "stop",
        }
        return self.command(28, **kw_args)

    def scan_stitch_status(self, scan: int):
        """
        Parameters:
        Scan type : see Enum
        """
        assert Scan_Type.has_value(scan), "Scan type not valid."

        kw_args = {"scan": Scan_Type(scan).lowercase_name}
        return self.command(29, **kw_args)

    def scan_stitch_output(self, operation: bool):
        """
        Parameters:
        Operation
            “start” - Start running the given scan
            “stop” - Stop running the given scan
        """
        assert type(operation) == bool, "Operation not valid."

        kw_args = {"operation": "start" if operation else "stop"}
        return self.command(30, **kw_args)

    def terascan_output(self, operation: bool, delay: float, update: float, units: str):
        """
        Parameters:
            Operation
                “start” - Automatic Output transmissions shall be generated.
                “stop” - Automatic Output transmissions shall not be generated.
            Delay Period
                0 – 1000 - Scan delay after start transmission in 1/100s.
                0 = No delay
                1 - 1000 = 10ms to 10 s delay
            Update Step
                The scan operation in TeraScan operates by ramping a tuning DAC through its
                tuning range. The update step causes the Automatic Output message to be
                generated whenever the tuner has moved by the given step. If the step is too
                small the system will generate the message as often as it can. 0 disables mid
                scan Automatic output.
                0 – 50 - Mid scan segment update frequency.
                0 = No mid scan segment output
                1 – 50 = Generate output at these tuning points.
            Pause
                New parameter added in V42 onwards, if this parameter is not present it will be
                treated as if the value is “off”.
                When this option is enabled the TeraScan will be paused at the start of each scan
                segment until a continue command is received (See 3.39 TeraScan, Continue).
                The scan will be paused after transmitting the “automatic_output” message with
                the status “start” or “repeat”.
                “on” - TeraScan will automatically pause at the start of each
                segment.
                “off” - TeraScan will not pause at the start of any segments
        """
        kw_args = {
            "operation": "start" if operation else "stop",
            "delay": delay,
            "update": update,
            "units": units,
        }
        return self.command(31, **kw_args)

    def fast_scan_start(self, scan: int, width: float, time: float):
        """
        Parameters:
            Scan type
            width
            time
        """
        assert Scan_Type_Fast.has_value(scan), "Scan type not valid."

        kw_args = {
            "scan": Scan_Type_Fast(scan).lowercase_name,
            "width": width,
            "time": time,
        }
        return self.command(32, **kw_args)

    def fast_scan_poll(self, scan: int):
        """
        Parameters:
            Scan type
        """
        assert Scan_Type_Fast.has_value(scan), "Scan type not valid."

        kw_args = {
            "scan": Scan_Type_Fast(scan).lowercase_name,
            "width": width,
            "time": time,
        }
        return self.command(33, **kw_args)

    def fast_scan_stop(self, scan: int):
        """
        Parameters:
            Scan type
        """
        assert Scan_Type_Fast.has_value(scan), "Scan type not valid."

        kw_args = {
            "scan": Scan_Type_Fast(scan).lowercase_name,
        }
        return self.command(34, **kw_args)

    def fast_scan_stop_nr(self, scan: int):
        """
        Parameters:
            Scan type
        """
        assert Scan_Type_Fast.has_value(scan), "Scan type not valid."

        kw_args = {
            "scan": Scan_Type_Fast(scan).lowercase_name,
        }
        return self.command(35, **kw_args)

    def pba_reference(self, operation: bool):
        """
        Parameters:
        Operation
            “start” - Start
            “stop” - Stop
        """
        assert type(operation) == bool, "Operation not valid."

        kw_args = {"operation": "start" if operation else "stop"}
        return self.command(36, **kw_args)

    def pba_reference_status(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(37, **kw_args)

    def get_wavelength_range(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(38, **kw_args)

    def terascan_continue(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(39, **kw_args)

    def read_all_adc(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(40, **kw_args)

    def set_wave_tolerance_m(self, tolerance):
        """
        Parameters:
            Prior to software release V60.
            The upper limit of the tuning tolerance is 1. The lower limit of the tuning
            tolerance depends on the precision of the wavelength meter. A meter
            accurate to four decimal places has a minimum tuning tolerance of
            0.0001. A meter accurate to five decimal places has a minimum of
            0.00001.
            0.0001 – 1.0 (meter accurate to 4 decimal places)
            0.00001 – 1.0 (meter accurate to 5 decimal places)
            0.000001 – 1.0 (meter accurate to 6 decimal places)
            0.0000001 – 1.0 (meter accurate to 7 decimal places).
            V60 release onwards.
            Prior to release V60 the wavelength lock process could operate to 1
            decimal place greater than the precision of the wavelength meter. This
            increased range is now applied to this command.
            0.00001 – 1.0 (meter accurate to 4 decimal places)
            0.000001 – 1.0 (meter accurate to 5 decimal places)
            0.0000001 – 1.0 (meter accurate to 6 decimal places)
            0.00000001 – 1.0 (meter accurate to 7 decimal places)
        """

        kw_args = {"tolerance": tolerance}
        return self.command(41, **kw_args)

    def set_wave_lock_tolerance_m(self, tolerance):
        """
        Parameters:
            Prior to software release V60.
            The upper limit of the wavelength lock tolerance, lambda lock, is 0.005. The lower limit of the lock tolerance depends on the precision of the wavelength meter. A meter accurate to four decimal places has a lower limit of 0.00001. A meter accurate to five decimal places has a lower limit of 0.000001.
            0.00001 – 0.005 (meter accurate to 4 decimal places)
            0.000001 – 0.005 (meter accurate to 5 decimal places)
            0.0000001 – 0.005 (meter accurate to 6 decimal places)
            0.00000001 – 0.005 (meter accurate to 7 decimal places)
        """

        kw_args = {"tolerance": tolerance}
        return self.command(42, **kw_args)

    def digital_pid_control(self, operation: bool):
        """
        Parameters:
        Operation
            “start” - Start
            “stop” - Stop
        """
        assert type(operation) == bool, "Operation not valid."

        kw_args = {"operation": "start" if operation else "stop"}
        return self.command(43, **kw_args)

    def digital_pid_poll(
        self,
    ):
        """
        Parameters: None
        """

        kw_args = {}
        return self.command(44, **kw_args)

    def set_w_meter_channel(self, channel: int, recovery: int):
        """
        Parameters:
        Channel
            0 - 8
        recovery
            1 - 3
        """
        assert 0 <= channel <= 8, "Channel out of range."
        assert 1 <= recovery <= 3, "Recovery out of range."

        kw_args = {"channel": channel, "recovery": recovery}
        return self.command(45, **kw_args)

    def lock_wave_m_fixed(self, operation: bool):
        """
        Parameters:
        Operation
            "on" or "off"
        """
        assert type(operation) == bool, "Operation not valid."

        kw_args = {"operation": "on" if operation else "off"}
        return self.command(46, **kw_args)

    def gpio_output(self, channel: int, value: bool):
        """
        Parameters:
        Channel
            0 - 31
        value
            0 or 1
        """
        kw_args = {"channel": channel, "value": 1 if value else 0}
        return self.command(47, **kw_args)

    def dac_ramping(
        self,
        dac_channel: int,
        start_stop: int,
        ramping_mode: int,
        step_mode: int,
        target_output: float,
        ramp_rate: float,
        update_rate: float,
        step_size: float,
    ):
        """
        DAC channel number
        DAC channel number
        0 - 31
        Start/stop mode
        1 Start
        2 Stop, DAC remains at position
        Ramping mode
        1 No ramping
        2 Ramp only if the target is higher than the current output.
        3 Ramp only if the target is lower than the current output.
        4 Always ramp in either direction.
        Step mode
        0 Use the ramp rate and the DSP will calculate the step size to achieve the
        update rate.
        1 Use the step size given
        Target output
        This is the final output for the DAC and is specified in user units.
        Ramp rate
        DAC update rate specified in user units per second.
        Update rate
        The time for the required update in seconds.
        Step size
        Step size in user units.
        Status value
        0 - operation successful.
        1 - operation failed
        67 of 75
        Expected Time
        The time it will take to complete the task in seconds.
        """
        assert 0 <= dac_channel <= 31, "DAC channel out of range."
        assert 1 <= start_stop <= 2, "Start/stop mode out of range."
        assert 1 <= ramping_mode <= 4, "Ramping mode out of range."
        assert 0 <= step_mode <= 1, "Step mode out of range."

        kw_args = {
            "dac_channel": dac_channel,
            "start_stop": start_stop,
            "ramping_mode": ramping_mode,
            "step_mode": step_mode,
            "target_output": target_output,
            "ramp_rate": ramp_rate,
            "update_rate": update_rate,
            "step_size": step_size,
        }

        return self.command(48, **kw_args)

    def dac_ramping_poll(self, dac_rampping_channel: int):
        """
        Parameters:
        DAC channel number
            0 - 31
        """
        assert 0 <= dac_rampping_channel <= 31, "DAC channel out of range."

        kw_args = {"dac_rampping_channel": dac_rampping_channel}
        return self.command(49, **kw_args)

    def digital_pot_output(self, channel: int, value: int):
        """
        Parameters:
        Channel
            0 - 36
        value
            0 - 255
        """
        assert 0 <= channel <= 36, "Channel out of range."
        assert 0 <= value <= 255, "Value out of range."

        kw_args = {"channel": channel, "value": value}
        return self.command(50, **kw_args)

    def dac_output(self, channel: int, output_value: float):
        """
        Parameters:
        Channel
            0 - 30
        output_value
            unknown
        """
        assert 0 <= channel <= 30, "Channel out of range."

        kw_args = {"channel": channel, "output_value": output_value}
        return self.command(51, **kw_args)
